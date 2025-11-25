import logging
import json
from typing import Dict, Any, List, AsyncGenerator
from qdrant_client import models
from domain.interfaces import IDocumentSearchOrchestrator, ISearchService, IFilterService, IQdrantClient, Message
from services.search_service_v2 import SearchConfigV2
from config.settings import Settings

logger = logging.getLogger(__name__)


class DocumentSearchOrchestratorV2(IDocumentSearchOrchestrator):
    
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
    
    def _determine_hard_soft_conditions(
        self,
        structured_filter: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        hard_fields = ['C_court_finding', 'D_court_reason', 'E_legal_eval']
        soft_fields = ['A_fact', 'B_claim', 'defendants_role']
        
        hard_conditions = []
        soft_conditions = []
        
        for field in hard_fields:
            if field in structured_filter and structured_filter[field]:
                hard_conditions.append({
                    'field_name': field.lower().replace('_', ''),
                    'query_text': structured_filter[field],
                    'is_hard': True
                })
        
        for field in soft_fields:
            if field in structured_filter and structured_filter[field]:
                soft_conditions.append({
                    'field_name': field.lower().replace('_', ''),
                    'query_text': structured_filter[field],
                    'is_hard': False
                })
        
        if not hard_conditions and not soft_conditions:
            for field in ['A_fact', 'B_claim', 'defendants_role', 'C_court_finding']:
                if field in structured_filter and structured_filter[field]:
                    soft_conditions.append({
                        'field_name': 'summary',
                        'query_text': structured_filter[field],
                        'is_hard': False
                    })
                    break
        
        logger.info(f"判定硬條件: {len(hard_conditions)} 個")
        logger.info(f"判定軟條件: {len(soft_conditions)} 個")
        
        return hard_conditions, soft_conditions
    
    async def _apply_nand_filter(
        self,
        results: List[Dict[str, Any]],
        negated_fields: List[str],
        structured_filter: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if not negated_fields:
            return results
        
        logger.info(f"應用 NAND 過濾，否定欄位: {negated_fields}")
        
        filtered_results = []
        for result in results:
            payload = result.get('payload', {})
            should_exclude = False
            
            for neg_field in negated_fields:
                if '.' in neg_field:
                    parts = neg_field.split('.')
                    value = payload
                    for part in parts:
                        if isinstance(value, dict):
                            value = value.get(part)
                        else:
                            value = None
                            break
                    
                    if value is True:
                        should_exclude = True
                        break
                else:
                    if payload.get(neg_field) is True:
                        should_exclude = True
                        break
            
            if not should_exclude:
                filtered_results.append(result)
        
        logger.info(f"NAND 過濾後: {len(filtered_results)}/{len(results)} 筆結果")
        return filtered_results
    
    def _simplify_results(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        simplified_results = []
        for result in results:
            payload = result.get('payload', {})
            simplified_results.append({
                "page_content": payload.get('summary_content', ''),
                "jid": payload.get('jid_full', ''),
                "defendants": [d.get('defendant_name', '') for d in payload.get('defendants', [])],
                "chunk_type": "judgment",
                "score": result.get('score', 0)
            })
        return simplified_results
    
    async def _execute_search_v2(
        self,
        collection: str,
        query_text: str,
        mode: str,
        limit: int,
        history_messages: List[Message] = None
    ) -> List[Dict[str, Any]]:
        structured_filter_lst = await self.filter_service.extract_filter_conditions(query_text, history_messages)
        
        logger.info("=" * 50)
        logger.info(f"V2 過濾條件:\n{json.dumps(structured_filter_lst, ensure_ascii=False, indent=2)}")
        logger.info("=" * 50)
        
        if not structured_filter_lst:
            logger.warning("沒有提取到過濾條件")
            return []
        
        structured_filter = structured_filter_lst[0]
        
        hard_conditions, soft_conditions = self._determine_hard_soft_conditions(structured_filter)
        
        all_conditions = hard_conditions + soft_conditions
        
        if not all_conditions:
            logger.warning("沒有有效的查詢條件")
            return []
        
        qdrant_filter, _ = self.filter_service.to_qdrant_filter(structured_filter)
        
        config = SearchConfigV2(
            collection=f"{collection}_v2",
            query_conditions=all_conditions,
            payload_filter=qdrant_filter,
            limit=limit,
            fusion="rrf"
        )
        
        response = await self.search_service.search(self.qdrant_client, config)
        results = self.search_service.flatten_points(response)
        
        logger.info(f"初步搜尋結果: {len(results)} 筆")
        
        negated_fields = structured_filter.get('negated_fields', [])
        if negated_fields:
            results = await self._apply_nand_filter(results, negated_fields, structured_filter)
        
        simplified_results = self._simplify_results(results)
        
        logger.info(f"V2 最終搜尋結果: {len(simplified_results)} 筆")
        
        return simplified_results
    
    async def orchestrate_search(
        self,
        collection: str,
        query_text: str,
        mode: str,
        limit: int,
        logic: str = "AND",
        history_messages: List[Message] = None
    ) -> List[Dict[str, Any]]:
        return await self._execute_search_v2(
            collection=collection,
            query_text=query_text,
            mode=mode,
            limit=limit,
            history_messages=history_messages
        )
    
    async def orchestrate_search_stream(
        self,
        collection: str,
        query_text: str,
        mode: str,
        limit: int,
        logic: str = "AND",
        history_messages: List[Message] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"status": "正在使用 V2 架構重組你的訊息"}
        
        results = await self._execute_search_v2(
            collection=collection,
            query_text=query_text,
            mode=mode,
            limit=limit,
            history_messages=history_messages
        )
        
        if len(results) > 0:
            yield {"status": f"V2 搜尋結果為 {len(results)} 個"}
        else:
            yield {"status": "V2 搜尋結果為空"}
        
        yield {"status": "完成 V2 向量搜尋"}
        yield {"type": "final_results", "results": results}

