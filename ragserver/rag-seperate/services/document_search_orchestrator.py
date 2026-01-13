import logging
import json
from typing import Dict, Any, List, Set, AsyncGenerator
# from sentence_transformers import SentenceTransformer, util
import re
from domain.interfaces import IDocumentSearchOrchestrator, ISearchService, IFilterService, IQdrantClient, Message
from services.search_service import SearchConfig
from config.settings import Settings, FieldsConfig

logger = logging.getLogger(__name__)


class DocumentSearchOrchestrator(IDocumentSearchOrchestrator):
    """
    @brief 文件搜尋協調器，負責協調多個搜尋服務並處理複雜的搜尋邏輯
    
    @details 此類整合了 Qdrant 向量資料庫、搜尋服務和過濾服務，
             提供完整的文件搜尋功能，包含正面/負面條件過濾、
             多面向搜尋聚合和評分排序等進階功能
    """
    
    def __init__(
        self,
        qdrant_client: IQdrantClient,
        search_service: ISearchService,
        filter_service: IFilterService,
        settings: Settings
    ):
        """
        @brief 初始化文件搜尋協調器
        
        @param qdrant_client Qdrant 向量資料庫客戶端介面
        @param search_service 搜尋服務介面
        @param filter_service 過濾服務介面
        @param settings 應用程式設定
        """
        self.qdrant_client = qdrant_client
        self.search_service = search_service
        self.filter_service = filter_service
        self.settings = settings
        # self.semantic_model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
        # TODO: 增加欄位
        self.summary_fields = FieldsConfig.get_summary_fields()
    
    def _map_field_to_vector_name(self, field_type: str) -> str:
        """
        @brief 將 filter 欄位名稱映射為向量名稱
        
        @param field_type 過濾欄位名稱
        @return 對應的向量名稱
        """
        if field_type == "defendants_role":
            return "role"
        return field_type
    
    def _determine_query_and_field_type(
        self,
        structured_filter: Dict[str, Any],
        query_text: str
    ) -> tuple[str, str]:
        """
        @brief 決定重構後的查詢字串和欄位類型
        
        @details 遍歷 summary_fields 欄位，找出第一個在 structured_filter 中有值的欄位。
                 如果欄位值長度小於 10，則使用原始查詢；否則使用提取的欄位值。
        
        @param structured_filter 結構化的過濾條件字典
        @param query_text 原始查詢文本
        @return (重構的查詢字串, 欄位類型) 的元組
        """
        reconstructed_query = ""
        field_type = None
        for field in self.summary_fields:
            if field in structured_filter and structured_filter[field]:
                extracted_value = structured_filter[field]
                # if len(extracted_value) < 10:
                #     reconstructed_query = query_text
                #     logger.info(f"欄位 '{field}' 值過短 ('{extracted_value}')，使用原始查詢進行語義搜尋")
                # else:
                reconstructed_query = extracted_value
                field_type = field
                break
        return reconstructed_query, field_type
    
    async def _handle_scroll_search(
        self,
        collection: str,
        structured_filter: Dict[str, Any],
        top_k: int,
        filter_limit: int,
        jid_score_map: Dict[str, float]
    ) -> Set[str]:
        """
        @brief 處理沒有摘要欄位時的 scroll 搜尋
        
        @details 當查詢條件中沒有任何 summary_fields 欄位值時，
                 使用 scroll 方式直接取得符合過濾條件的所有記錄。
                 主要用於僅有基礎過濾條件（如法院、案由等）而無語義查詢的情況。
        
        @param collection Qdrant 集合名稱
        @param structured_filter 結構化的過濾條件
        @param top_k 每次搜尋的結果數量
        @param filter_limit 過濾限制數量
        @param jid_score_map JID 分數映射字典（會被修改）
        @return 符合條件的 JID 集合
        """
        logger.info("未找到任何 summary_fields 欄位，使用 scroll 方式獲取資料")
        
        structured_filter_scroll = structured_filter.copy()
        structured_filter_scroll["summary_type"] = ["case_fact_summary"]
        qdrant_filter_scroll, _ = self.filter_service.to_qdrant_filter(structured_filter_scroll)
        qdrant_filter_dict_scroll = qdrant_filter_scroll.model_dump(exclude_none=True) if qdrant_filter_scroll else None
        
        logger.info(f"Scroll 過濾條件: {json.dumps(qdrant_filter_dict_scroll, ensure_ascii=False, indent=2)}")
        
        scroll_results, _ = await self.qdrant_client.scroll(
            collection_name=collection,
            scroll_filter=qdrant_filter_scroll,
            limit=top_k*filter_limit,
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
        
        logger.info(f"Scroll 方式共取得 {len(condition_jids)} 個 jid")
        logger.info(f"條件 'scroll' 結果: {len(condition_jids)} 個 jid")
        return condition_jids
    
    async def _search_negative_conditions(
        self,
        negative_conditions: List[str],
        collection: str,
        mode: str,
        summary_filter_lst: List[Any],
        top_k: int,
        filter_limit: int
    ) -> Set[str]:
        """
        @brief 搜尋負面條件對應的文件並返回需要排除的 JID 集合
        
        @details 對每個負面條件（已轉換為正面陳述）執行向量搜尋，
                 找出匹配這些條件的文件 JID，這些 JID 將在後續被排除。
                 實現了 NAND 邏輯：「沒有X」= 排除「有X」的結果。
        
        @param negative_conditions 負面條件列表（已轉換為正面陳述）
        @param collection Qdrant 集合名稱
        @param mode 搜尋模式
        @param summary_filter_lst 摘要過濾器列表
        @param top_k 每次搜尋的結果數量
        @param filter_limit 過濾限制數量
        @return 需要排除的 JID 集合
        """
        negative_jids = set()
        neg_jid_score_map: Dict[str, float] = {}
        logger.info(f"偵測到負面條件，共 {len(negative_conditions)} 個")
        
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
                    logger.info(f"-----> 負面條件匹配到 jid: {neg_jid}, summary_type: {neg_summary_type}, score: {score}")
        
        logger.info("=" * 50)
        for neg_jid, neg_score in neg_jid_score_map.items():
            logger.info(f"-----> negmap總結： jid: {neg_jid}, score_總和: {neg_score}")
        logger.info("=" * 50)
        logger.info(f"負面條件總共匹配到 {len(negative_jids)} 個 jid，將被排除")
        return negative_jids
    
    async def _execute_positive_search(
        self,
        collection: str,
        reconstructed_query: str,
        mode: str,
        qdrant_filter_lst: List[Any],
        top_k: int,
        filter_limit: int,
        jid_score_map: Dict[str, float],
        field_type: str = None
    ) -> Set[str]:
        """
        @brief 執行正面條件的向量搜尋
        
        @details 使用重構後的查詢字串對指定過濾器列表執行向量搜尋，
                 將搜尋結果的 JID 和分數累加到 jid_score_map 中。
        
        @param collection Qdrant 集合名稱
        @param reconstructed_query 重構後的查詢字串
        @param mode 搜尋模式
        @param qdrant_filter_lst Qdrant 過濾器列表
        @param top_k 每次搜尋的結果數量
        @param filter_limit 過濾限制數量
        @param jid_score_map JID 分數映射字典（會被修改）
        @param field_type 欄位類型，用於動態設定向量名稱
        @return 符合正面條件的 JID 集合
        """
        condition_jids = set()
        
        if field_type:
            vector_field = self._map_field_to_vector_name(field_type)
            dense_name = vector_field
            sparse_name = f"{vector_field}_bm25"
        else:
            dense_name = "dense"
            sparse_name = "bm25"
        
        for qdrant_filter_sub in qdrant_filter_lst:
            config = SearchConfig(
                collection=collection,
                query_text=reconstructed_query,
                mode=mode,
                filter=qdrant_filter_sub,
                limit=top_k*filter_limit,
                score_threshold=0.95,
                dense_name=dense_name,
                sparse_name=sparse_name
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
        
        return condition_jids
    
    async def _process_single_filter_condition(
        self,
        structured_filter: Dict[str, Any],
        collection: str,
        query_text: str,
        mode: str,
        logic: str,
        top_k: int,
        filter_limit: int,
        jid_score_map: Dict[str, float]
    ) -> Set[str]:
        """
        @brief 處理單一過濾條件的完整搜尋流程
        
        @details 這是核心處理函數，負責：
                 1. 將結構化過濾條件轉換為 Qdrant 過濾器
                 2. 決定查詢字串和搜尋欄位類型
                 3. 根據欄位類型選擇 scroll 或向量搜尋
                 4. 處理負面條件並排除相應的 JID
                 5. 執行正面條件搜尋並返回符合的 JID 集合
        
        @param structured_filter 結構化的過濾條件
        @param collection Qdrant 集合名稱
        @param query_text 原始查詢文本
        @param mode 搜尋模式
        @param logic 邏輯運算符（AND/OR）
        @param top_k 每次搜尋的結果數量
        @param filter_limit 過濾限制數量
        @param jid_score_map JID 分數映射字典（會被修改）
        @return 符合條件的 JID 集合
        """
        negated_fields_original = structured_filter.get("negated_fields", []).copy()
        
        qdrant_filter, filter_limit = self.filter_service.to_qdrant_filter(structured_filter)
        structured_filter_highlight = structured_filter.copy()
        structured_filter_highlight["summary_type"] = ["case_highlights"]
        qdrant_filter_highlight, _ = self.filter_service.to_qdrant_filter(structured_filter_highlight)
        structured_filter_case_fact_summary = structured_filter.copy()
        structured_filter_case_fact_summary["summary_type"] = ["case_fact_summary"]
        qdrant_filter_case_fact_summary, _ = self.filter_service.to_qdrant_filter(structured_filter_case_fact_summary)
        qdrant_filter_dict = qdrant_filter.model_dump(exclude_none=True) if qdrant_filter else None
        qdrant_filter_lst = [qdrant_filter]
        summary_filter_lst = [qdrant_filter, qdrant_filter_highlight, qdrant_filter_case_fact_summary]
        
        logger.info("=" * 50)
        logger.info(f"Qdrant 過濾條件:\n{json.dumps(qdrant_filter_dict, ensure_ascii=False, indent=2)}")
        logger.info("=" * 50)
        logger.info(f"搜尋請求: collection={collection}, query='{query_text}', mode={mode}, logic={logic}")
        logger.info("=" * 50)
        
        reconstructed_query, field_type = self._determine_query_and_field_type(
            structured_filter, query_text
        )
        
        if field_type is None:
            condition_jids = await self._handle_scroll_search(
                collection, structured_filter, top_k, filter_limit, jid_score_map
            )
            return condition_jids
        
        # negative_conditions = self._extract_negative_conditions(reconstructed_query)
        negative_conditions = []
        for field in negated_fields_original:
            if field in self.summary_fields and field in structured_filter:
                field_value = structured_filter.get(field, "")
                if field_value:
                    negative_conditions.append(field_value)
        negative_jids = set()
        logger.info(f"------>> structured_filter: {structured_filter}")
        logger.info(f"------>> negated_fields_original: {negated_fields_original}")
        logger.info(f"------>> 負面條件: {negative_conditions}")
        
        if negative_conditions:
            negative_jids = await self._search_negative_conditions(
                negative_conditions, collection, mode, summary_filter_lst, top_k, filter_limit
            )
        else:
            logger.info("未檢測到負面條件")
        
        condition_jids = await self._execute_positive_search(
            collection, reconstructed_query, mode, qdrant_filter_lst, top_k, filter_limit, jid_score_map,
            field_type=field_type
        )
        
        if negative_jids:
            before_count = len(condition_jids)
            condition_jids = condition_jids - negative_jids
            after_count = len(condition_jids)
            logger.info(f"NAND 過濾: 排除前 {before_count} 個，排除後 {after_count} 個")
            print("=" * 50)
        
        logger.info(f"條件 '{field_type or 'general'}' 結果: {len(condition_jids)} 個 jid")
        return condition_jids
    
    def _aggregate_jids_by_logic(
        self,
        condition_jid_sets: List[Set[str]],
        logic: str,
        jid_score_map: Dict[str, float]
    ) -> Set[str]:
        """
        @brief 根據邏輯運算符聚合多個條件的 JID 集合
        
        @details 支援三種情況：
                 1. 空集合：返回空結果
                 2. 單一集合：直接返回該集合
                 3. 多個集合：根據 AND/OR 邏輯進行聚合
                    - AND：取交集，若為空則使用加權評分模式（至少出現在 70% 的面向中）
                    - OR：取聯集
        
        @param condition_jid_sets JID 集合列表
        @param logic 邏輯運算符（AND/OR）
        @param jid_score_map JID 分數映射字典
        @return 聚合後的 JID 集合
        """
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
        
        return aggregated_jids_by_logic
    
    def _sort_and_filter_jids_by_score(
        self,
        aggregated_jids_by_logic: Set[str],
        jid_score_map: Dict[str, float],
        filter_limit: int
    ) -> Set[str]:
        """
        @brief 根據累加分數對 JID 進行排序並篩選前 N 名
        
        @details 從 jid_score_map 中提取聚合後 JID 的分數，
                 按分數降序排序後取前 filter_limit 個 JID。
                 這確保了返回的結果是最相關的文件。
        
        @param aggregated_jids_by_logic 聚合後的 JID 集合
        @param jid_score_map JID 分數映射字典
        @param filter_limit 返回結果的數量限制
        @return 排序並篩選後的 JID 集合
        """
        filtered_jid_scores = {jid: jid_score_map[jid] for jid in aggregated_jids_by_logic if jid in jid_score_map}
        sorted_jids = sorted(filtered_jid_scores.items(), key=lambda x: x[1], reverse=True)[:filter_limit]
        aggregated_jids = {jid for jid, _ in sorted_jids}
        
        logger.info(f"按累加分數排序後的前三名:")
        for jid, total_score in sorted_jids:
            logger.info(f"  jid: {jid}, 累加分數: {total_score}")
        
        logger.info(f"準備檢索的 jid 集合: {aggregated_jids}")
        return aggregated_jids
    
    def _simplify_detailed_results(
        self,
        detailed_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        @brief 簡化詳細搜尋結果的格式
        
        @details 將從 Qdrant 返回的完整記錄轉換為簡化的結構，
                 只保留關鍵資訊：頁面內容、JID、被告名稱列表和區塊類型。
                 這使得前端更容易處理和顯示結果。
        
        @param detailed_results 詳細的搜尋結果列表
        @return 簡化後的結果列表
        """
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
        return simplified_results
    
    async def _execute_search_logic(
        self,
        collection: str,
        query_text: str,
        mode: str,
        limit: int,
        logic: str = "AND",
        history_messages: List[Message] = None
    ) -> List[Dict[str, Any]]:
        """
        @brief 執行完整的搜尋邏輯流程
        
        @details 這是主要的搜尋執行函數，協調整個搜尋流程：
                 1. 提取過濾條件
                 2. 處理每個過濾條件並收集 JID
                 3. 根據邏輯運算符聚合 JID
                 4. 按分數排序並篩選
                 5. 檢索完整結果並簡化格式
        
        @param collection Qdrant 集合名稱
        @param query_text 查詢文本
        @param mode 搜尋模式
        @param limit 結果數量限制
        @param logic 邏輯運算符（AND/OR），預設為 AND
        @param history_messages 歷史訊息列表，用於上下文理解
        @return 簡化後的搜尋結果列表
        """
        structured_filter_lst = await self.filter_service.extract_filter_conditions(query_text, history_messages)
        
        logger.info("=" * 50)
        logger.info(f"過濾條件:\n{json.dumps(structured_filter_lst, ensure_ascii=False, indent=2)}")
        logger.info("=" * 50)
        
        logic = logic.upper()
        if logic not in ["AND", "OR"]:
            logic = "AND"
        
        top_k = 10
        filter_limit = 3
        
        condition_jid_sets: List[Set[str]] = []
        jid_score_map: Dict[str, float] = {}
        
        for structured_filter in structured_filter_lst:
            condition_jids = await self._process_single_filter_condition(
                structured_filter=structured_filter,
                collection=collection,
                query_text=query_text,
                mode=mode,
                logic=logic,
                top_k=top_k,
                filter_limit=filter_limit,
                jid_score_map=jid_score_map
            )
            condition_jid_sets.append(condition_jids)
        
        aggregated_jids_by_logic = self._aggregate_jids_by_logic(
            condition_jid_sets, logic, jid_score_map
        )
        
        aggregated_jids = self._sort_and_filter_jids_by_score(
            aggregated_jids_by_logic, jid_score_map, filter_limit
        )
        
        detailed_results = await self.filter_service.retrieve_results_by_jids(
            qdrant_client=self.qdrant_client,
            collection=collection,
            limit=filter_limit,
            aggregated_jids=aggregated_jids
        )
        
        logger.info(f"retrieve_results_by_jids 返回了 {len(detailed_results)} 條記錄")
        
        simplified_results = self._simplify_detailed_results(detailed_results)
        
        if len(simplified_results) > 0:
            logger.info(f"最終搜尋結果: 總共 {len(simplified_results)} 個結果")
        else:
            logger.info(f"最終搜尋結果: 總共 {len(simplified_results)} 個結果")
        
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
        """
        @brief 協調搜尋的公開介面（非串流模式）
        
        @details 提供簡單的搜尋介面，直接返回完整的搜尋結果列表。
                 內部調用 _execute_search_logic 執行實際的搜尋邏輯。
        
        @param collection Qdrant 集合名稱
        @param query_text 查詢文本
        @param mode 搜尋模式
        @param limit 結果數量限制
        @param logic 邏輯運算符（AND/OR），預設為 AND
        @param history_messages 歷史訊息列表
        @return 搜尋結果列表
        """
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
        """
        @brief 協調搜尋的公開介面（串流模式）
        
        @details 提供串流式搜尋介面，在搜尋過程中持續向前端推送狀態更新。
                 包含最多 3 次重試機制，如果搜尋結果為空則重新組合問題。
                 適用於需要即時反饋的前端應用場景。
        
        @param collection Qdrant 集合名稱
        @param query_text 查詢文本
        @param mode 搜尋模式
        @param limit 結果數量限制
        @param logic 邏輯運算符（AND/OR），預設為 AND
        @param history_messages 歷史訊息列表
        @yield 包含狀態或結果的字典
               - {"status": "狀態訊息"} 表示進度更新
               - {"type": "final_results", "results": [...]} 表示最終結果
        """
        yield {"status": "正在重組你的訊息，並嘗試理解問題"}

        results = []
        max_retries = 3
        for retry in range(max_retries):
            retry+=1
            results = await self._execute_search_logic(
                collection=collection,
                query_text=query_text,
                mode=mode,
                limit=limit,
                logic=logic,
                history_messages=history_messages
            )
            if len(results) > 0:
                yield {"status": f"搜尋結果為 {len(results)} 個，正在整理結果"}
                break
            else:
                yield {"status": f"搜尋結果為空，嘗試重新組合你的問題"}
                continue
        
        yield {"status": "完成向量搜尋"}
        yield {"type": "final_results", "results": results}

