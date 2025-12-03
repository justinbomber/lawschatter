import logging
import json
from typing import Dict, Any, List, Set, AsyncGenerator
from domain.interfaces import IDocumentSearchOrchestrator, ISearchService, IFilterService, IQdrantClient, Message
from services.search_service import SearchConfig, MULTIVECTOR_FIELD_NAMES
from config.settings import Settings


logger = logging.getLogger(__name__)


class RRFSearchOrchestrator(IDocumentSearchOrchestrator):
    
    def __init__(
        self,
        qdrant_client: IQdrantClient,
        search_service: ISearchService,
        filter_service: IFilterService,
        settings: Settings
    ):
        self.qdrant_client = qdrant_client
        self.search_service = search_service
        self.filter_service = filter_service
        self.settings = settings
    
    def _extract_field_queries(
        self,
        structured_filter: Dict[str, Any]
    ) -> Dict[str, str]:
        field_queries = {}
        
        for field_name in MULTIVECTOR_FIELD_NAMES:
            filter_field = field_name
            if field_name == "role":
                filter_field = "defendants_role"
            
            field_value = structured_filter.get(filter_field, "")
            if field_value:
                field_queries[field_name] = field_value
        
        return field_queries
    
    def _extract_negated_fields(
        self,
        structured_filter: Dict[str, Any]
    ) -> List[str]:
        negated_fields_raw = structured_filter.get("negated_fields", []) or []
        
        negated_fields = []
        for field in negated_fields_raw:
            if field in MULTIVECTOR_FIELD_NAMES:
                negated_fields.append(field)
            elif field == "defendants_role":
                negated_fields.append("role")
        
        return negated_fields
    
    def _simplify_results(
        self,
        detailed_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        simplified_results = []
        for result in detailed_results:
            defendants = []
            payload = result.get('payload', {})
            metadata = payload.get('metadata', {})
            for defendant in metadata.get('defendants', []):
                if isinstance(defendant, dict):
                    defendants.append(defendant.get('defendant_name'))
                else:
                    defendants.append(defendant)
            simplified_results.append({
                "page_content": payload.get('page_content'),
                "jid": metadata.get('jid_full'),
                "defendants": defendants,
                "chunk_type": metadata.get('summary_type')
            })
        return simplified_results
    
    async def orchestrate_search(
        self,
        collection: str,
        query_text: str,
        mode: str,
        limit: int,
        logic: str = "AND",
        history_messages: List[Message] = None,
        hard_fields: List[str] = None,
        soft_fields: List[str] = None
    ) -> List[Dict[str, Any]]:
        logger.info("執行 Multivector RRF 搜尋協調")
        logger.info(f"collection={collection}, query={query_text}, limit={limit}")
        
        structured_filter_lst = await self.filter_service.extract_filter_conditions(query_text, history_messages)
        
        logger.info("=" * 50)
        logger.info(f"過濾條件:\n{json.dumps(structured_filter_lst, ensure_ascii=False, indent=2)}")
        logger.info("=" * 50)
        
        if not structured_filter_lst:
            structured_filter_lst = [{}]
        
        structured_filter = structured_filter_lst[0]
        qdrant_filter, filter_limit = self.filter_service.to_qdrant_filter(structured_filter)
        
        field_queries = self._extract_field_queries(structured_filter)
        negated_fields = self._extract_negated_fields(structured_filter)
        
        logger.info(f"欄位查詢: {json.dumps(field_queries, ensure_ascii=False)}")
        logger.info(f"負向欄位: {negated_fields}")
        
        if not field_queries:
            logger.info("沒有有效的欄位查詢，返回空結果")
            return []
        
        config = SearchConfig(
            collection=collection,
            filter=qdrant_filter,
            limit=limit * 10,
            field_queries=field_queries,
            negated_fields=negated_fields,
        )
        
        response = await self.search_service.search_multivector_rrf(
            client=self.qdrant_client,
            config=config
        )
        
        results = self.search_service.flatten_points(response)
        logger.info(f"RRF 搜尋返回 {len(results)} 個結果")
        
        jid_score_map: Dict[str, float] = {}
        for result in results:
            jid = result.get('payload', {}).get('jid')
            score = result.get('score', 0)
            if jid:
                if jid in jid_score_map:
                    jid_score_map[jid] = max(jid_score_map[jid], score)
                else:
                    jid_score_map[jid] = score
        
        sorted_jids = sorted(jid_score_map.items(), key=lambda x: x[1], reverse=True)[:filter_limit]
        final_jids = {jid for jid, _ in sorted_jids}
        
        logger.info(f"按分數排序後的前 {filter_limit} 個 jid: {final_jids}")
        
        if not final_jids:
            return []
        
        detailed_results = await self.filter_service.retrieve_results_by_jids(
            qdrant_client=self.qdrant_client,
            collection=self.settings.qdrant.collection_name,
            limit=filter_limit,
            aggregated_jids=final_jids
        )
        
        simplified_results = self._simplify_results(detailed_results)
        
        logger.info(f"最終搜尋結果: 總共 {len(simplified_results)} 個結果")
        return simplified_results
    
    async def orchestrate_search_stream(
        self,
        collection: str,
        query_text: str,
        mode: str,
        limit: int,
        logic: str = "AND",
        history_messages: List[Message] = None,
        hard_fields: List[str] = None,
        soft_fields: List[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"status": "正在重組你的訊息，並嘗試理解問題"}
        
        results = []
        max_retries = 3
        for retry in range(max_retries):
            retry += 1
            results = await self.orchestrate_search(
                collection=collection,
                query_text=query_text,
                mode=mode,
                limit=limit,
                logic=logic,
                history_messages=history_messages,
            )
            if len(results) > 0:
                yield {"status": f"搜尋結果為 {len(results)} 個，正在整理結果"}
                break
            else:
                yield {"status": f"搜尋結果為空，嘗試重新組合你的問題"}
                continue
        
        yield {"status": "完成向量搜尋"}
        yield {"type": "final_results", "results": results}
