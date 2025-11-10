import logging
import json
from typing import Dict, Any, List, Set, AsyncGenerator
from sentence_transformers import SentenceTransformer, util
import re
from domain.interfaces import IDocumentSearchOrchestrator, ISearchService, IFilterService, IQdrantClient, Message
from services.search_service import SearchConfig
from config.settings import Settings

logger = logging.getLogger(__name__)


class DocumentSearchOrchestrator(IDocumentSearchOrchestrator):
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
        self.semantic_model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
    
    def _extract_negative_conditions(self, query_text: str) -> List[str]:
        negative_indicators = [
            r'沒有',
            r'未',
            r'無',
            r'不曾',
            r'從未',
            r'並未',
            r'未曾',
            r'不',
            r'否認',
            r'拒絕'
        ]
        
        negative_conditions = []
        
        for neg_word in negative_indicators:
            pattern = rf'{neg_word}([^，。！？；\s]{{2,20}})'
            matches = re.finditer(pattern, query_text)
            
            for match in matches:
                captured_content = match.group(1)
                if len(captured_content) >= 2:
                    positive_statement = f"有{captured_content}"
                    negative_conditions.append(positive_statement)
                    logger.info(f"檢測到負面條件: '{neg_word}{captured_content}' -> 正面陳述: '{positive_statement}'")
        
        return negative_conditions
    
    async def _execute_search_logic(
        self,
        collection: str,
        query_text: str,
        mode: str,
        limit: int,
        logic: str = "AND",
        history_messages: List[Message] = None
    ) -> List[Dict[str, Any]]:
        structured_filter_lst = await self.filter_service.extract_filter_conditions(query_text, history_messages)
        
        logger.info("=" * 50)
        logger.info(f"過濾條件:\n{json.dumps(structured_filter_lst, ensure_ascii=False, indent=2)}")
        logger.info("=" * 50)
        
        summary_fields = ["defendants_role", "A_fact", "B_claim", "C_court_finding", "D_court_reason", "E_legal_eval"]
        
        logic = logic.upper()
        if logic not in ["AND", "OR"]:
            logic = "AND"
        
        top_k = 15
        
        condition_jid_sets: List[Set[str]] = []
        jid_score_map: Dict[str, float] = {}
        
        for structured_filter in structured_filter_lst:
            qdrant_filter, filter_limit = self.filter_service.to_qdrant_filter(structured_filter)
            structured_filter_highlight = structured_filter.copy()
            structured_filter_highlight["summary_type"] = ["case_highlights"]
            qdrant_filter_highlight, _ = self.filter_service.to_qdrant_filter(structured_filter_highlight)
            structured_filter_case_fact_summary = structured_filter.copy()
            structured_filter_case_fact_summary["summary_type"] = ["case_fact_summary"]
            qdrant_filter_case_fact_summary, _ = self.filter_service.to_qdrant_filter(structured_filter_case_fact_summary)
            qdrant_filter_dict = qdrant_filter.model_dump(exclude_none=True) if qdrant_filter else None
            qdrant_filter_lst = [qdrant_filter]
            summary_filter_lst = [qdrant_filter_highlight, qdrant_filter_case_fact_summary]
            
            logger.info("=" * 50)
            logger.info(f"Qdrant 過濾條件:\n{json.dumps(qdrant_filter_dict, ensure_ascii=False, indent=2)}")
            logger.info("=" * 50)
            logger.info(f"搜尋請求: collection={collection}, query='{query_text}', mode={mode}, logic={logic}")
            logger.info("=" * 50)
            
            reconstructed_query = ""
            field_type = None
            for field in summary_fields:
                if field in structured_filter and structured_filter[field]:
                    extracted_value = structured_filter[field]
                    if len(extracted_value) < 10:
                        reconstructed_query = query_text
                        logger.info(f"欄位 '{field}' 值過短 ('{extracted_value}')，使用原始查詢進行語義搜尋")
                    else:
                        reconstructed_query = extracted_value
                    field_type = field
                    break
            
            if field_type is None:
                logger.info("未找到任何 summary_fields 欄位，使用 scroll 方式獲取資料")
                
                structured_filter_scroll = structured_filter.copy()
                structured_filter_scroll["summary_type"] = ["case_fact_summary"]
                qdrant_filter_scroll, _ = self.filter_service.to_qdrant_filter(structured_filter_scroll)
                qdrant_filter_dict_scroll = qdrant_filter_scroll.model_dump(exclude_none=True) if qdrant_filter_scroll else None
                
                logger.info(f"Scroll 過濾條件: {json.dumps(qdrant_filter_dict_scroll, ensure_ascii=False, indent=2)}")
                
                scroll_results, _ = await self.qdrant_client.scroll(
                    collection_name=collection,
                    scroll_filter=qdrant_filter_scroll,
                    limit=50,
                    with_payload=True,
                    with_vectors=False
                )
                
                condition_jids = set()
                for record in scroll_results or []:
                    jid = record.payload.get('metadata', {}).get('jid')
                    if jid:
                        condition_jids.add(jid)
                        score = 1.0
                        if jid in jid_score_map:
                            jid_score_map[jid] += score
                        else:
                            jid_score_map[jid] = score
                        # logger.info(f"-----> Scroll 取得 jid: {jid}")
                
                logger.info(f"Scroll 方式共取得 {len(condition_jids)} 個 jid")
                condition_jid_sets.append(condition_jids)
                logger.info(f"條件 'scroll' 結果: {len(condition_jids)} 個 jid")
                continue
            
            negative_conditions = self._extract_negative_conditions(reconstructed_query)
            negative_jids = set()
            condition_jids = set()
            
            if negative_conditions:
                neg_jid_score_map: Dict[str, float] = {}
                logger.info(f"偵測到負面條件，共 {len(negative_conditions)} 個")
                logger.info(f"負面條件轉換為正面語句: {negative_conditions}")
                
                for neg_condition in negative_conditions:
                    logger.info(f"搜尋負面條件: '{neg_condition}'")
                    
                    for qdrant_filter_sub in summary_filter_lst:
                        neg_config = SearchConfig(
                            collection=collection,
                            query_text=neg_condition,
                            mode=mode,
                            filter=qdrant_filter_sub,
                            limit=top_k*filter_limit,
                            score_threshold=0.95
                        )
                        
                        neg_response = await self.search_service.search(self.qdrant_client, neg_config)
                        neg_results = self.search_service.flatten_points(neg_response)
                        
                        for result in neg_results:
                            neg_jid = result.get('payload').get('metadata').get('jid')
                            neg_summary_type = result.get('payload').get('metadata').get('summary_type')
                            neg_content = result.get('payload').get('page_content')
                            score = result.get('score', 0)
                            if neg_jid in neg_jid_score_map:
                                neg_jid_score_map[neg_jid] += score
                            else:
                                neg_jid_score_map[neg_jid] = score
                            negative_jids.add(neg_jid)
                            logger.info(f"-----> 負面條件匹配到 jid: {neg_jid}, summary_type: {neg_summary_type}, content: {neg_content}, score: {score}")
                logger.info("=" * 50)
                for neg_jid, neg_score in neg_jid_score_map.items():
                    logger.info(f"-----> negmap總結： jid: {neg_jid}, score_總和: {neg_score}")
                logger.info("=" * 50)
                logger.info(f"負面條件總共匹配到 {len(negative_jids)} 個 jid，將被排除")
            else:
                logger.info("未檢測到負面條件")
            
            for qdrant_filter_sub in qdrant_filter_lst:
                config = SearchConfig(
                    collection=collection,
                    query_text=reconstructed_query,
                    mode=mode,
                    filter=qdrant_filter_sub,
                    limit=top_k,
                    score_threshold=0.95
                )
                
                response = await self.search_service.search(self.qdrant_client, config)
                results = self.search_service.flatten_points(response)
                
                print("=" * 50)
                for result in results:
                    jid = result.get('payload').get('metadata').get('jid')
                    score = result.get('score', 0)
                    print(f"-----> score: {score}, jid: {jid}")
                    
                    condition_jids.add(jid)
                    
                    if jid in jid_score_map:
                        jid_score_map[jid] += score
                    else:
                        jid_score_map[jid] = score
            
            if negative_jids:
                before_count = len(condition_jids)
                condition_jids = condition_jids - negative_jids
                after_count = len(condition_jids)
                logger.info(f"NAND 過濾: 排除前 {before_count} 個，排除後 {after_count} 個")
                print("=" * 50)
            
            condition_jid_sets.append(condition_jids)
            logger.info(f"條件 '{field_type or 'general'}' 結果: {len(condition_jids)} 個 jid")
        
        if not condition_jid_sets:
            aggregated_jids_by_logic = set()
            logger.info("沒有搜尋條件，結果為空")
        elif len(condition_jid_sets) == 1:
            aggregated_jids_by_logic = condition_jid_sets[0]
            logger.info(f"單一搜尋條件，直接使用結果: {len(aggregated_jids_by_logic)} 個 jid")
        else:
            logger.info(f"多面向搜尋: 共 {len(condition_jid_sets)} 個面向")
            
            if logic == "AND":
                aggregated_jids_by_logic = set.intersection(*condition_jid_sets)
                logger.info(f"使用 AND 邏輯聚合: {len(aggregated_jids_by_logic)} 個 jid")
                
                if len(aggregated_jids_by_logic) == 0:
                    logger.info("AND 邏輯沒有結果，改用加權評分 + 閾值過濾")
                    all_jids = set.union(*condition_jid_sets)
                    min_occurrence = max(1, int(len(condition_jid_sets) * 0.7))
                    
                    jid_occurrence_map = {}
                    for jid in all_jids:
                        occurrence_count = sum(1 for jid_set in condition_jid_sets if jid in jid_set)
                        jid_occurrence_map[jid] = occurrence_count
                        if occurrence_count >= min_occurrence:
                            aggregated_jids_by_logic.add(jid)
                    
                    logger.info(f"加權評分模式: 要求至少出現在 {min_occurrence}/{len(condition_jid_sets)} 個面向中")
                    logger.info(f"符合閾值的 jid: {len(aggregated_jids_by_logic)} 個")
                    
                    top_jids_by_occurrence = sorted(jid_occurrence_map.items(), key=lambda x: x[1], reverse=True)[:5]
                    logger.info(f"出現次數最多的前 5 個 jid:")
                    for jid, count in top_jids_by_occurrence:
                        logger.info(f"  jid: {jid}, 出現在 {count}/{len(condition_jid_sets)} 個面向中，累加分數: {jid_score_map.get(jid, 0):.4f}")
            elif logic == "OR":
                aggregated_jids_by_logic = set.union(*condition_jid_sets)
                logger.info(f"使用 OR 邏輯聚合: {len(aggregated_jids_by_logic)} 個 jid")
            else:
                aggregated_jids_by_logic = set.intersection(*condition_jid_sets)
                logger.info(f"預設使用 AND 邏輯聚合: {len(aggregated_jids_by_logic)} 個 jid")
        
        filtered_jid_scores = {jid: jid_score_map[jid] for jid in aggregated_jids_by_logic if jid in jid_score_map}
        sorted_jids = sorted(filtered_jid_scores.items(), key=lambda x: x[1], reverse=True)[:filter_limit]
        aggregated_jids = {jid for jid, _ in sorted_jids}
        
        logger.info(f"按累加分數排序後的前三名:")
        for jid, total_score in sorted_jids:
            logger.info(f"  jid: {jid}, 累加分數: {total_score}")
        
        logger.info(f"準備檢索的 jid 集合: {aggregated_jids}")
        
        detailed_results = await self.filter_service.retrieve_results_by_jids(
            qdrant_client=self.qdrant_client,
            collection=collection,
            # limit=limit,
            aggregated_jids=aggregated_jids
        )
        
        logger.info(f"retrieve_results_by_jids 返回了 {len(detailed_results)} 條記錄")
        
        simplified_results = []
        for result in detailed_results:
            defendants = []
            payload = result.get('payload', {})
            metadata = payload.get('metadata', {})
            for defendant in metadata.get('defendants', []):
                defendants.append(defendant.get('defendant_name'))
            summary_type = metadata.get('summary_type')
            simplified_results.append({
                "page_content": payload.get('page_content'),
                "jid": metadata.get('jid_full'),
                "defendants": defendants,
                "chunk_type": summary_type
            })
        
        if len(simplified_results) > 0:
            logger.info(f"最終搜尋結果: 總共 {len(simplified_results)} 個結果")
            # for result in simplified_results:
                # logger.info(f"---> 最終結果: {result.get('jid')}, content: {result.get('page_content')}")
        else:
            logger.info(f"最終搜尋結果: 總共 {len(simplified_results)} 個結果")
            # logger.info(f"---> 最終結果: 沒有結果")
        
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
        return await self._execute_search_logic(
            collection=collection,
            query_text=query_text,
            mode=mode,
            limit=limit,
            logic=logic,
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
        yield {"status": "正在重組你的訊息，並嘗試理解問題"}
        
        results = await self._execute_search_logic(
            collection=collection,
            query_text=query_text,
            mode=mode,
            limit=limit,
            logic=logic,
            history_messages=history_messages
        )
        
        yield {"status": "完成向量搜尋"}
        yield {"type": "final_results", "results": results}

