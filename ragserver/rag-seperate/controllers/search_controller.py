import logging
import json
from typing import Dict, Any
from entities.models import SearchRequest, SearchResponse, CollectionInfo, HealthStatus
from services.search_service import SearchConfig
from domain.interfaces import ISearchService, IFilterService, IQdrantClient
from config.settings import Settings
from typing import List, Set

logger = logging.getLogger(__name__)


class SearchController:
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
    

    async def search_documents(self, request: SearchRequest) -> SearchResponse:
        structured_filter_lst = await self.filter_service.extract_filter_conditions(request.query_text)
        logger.info("=" * 50)
        logger.info(f"過濾條件:\n{json.dumps(structured_filter_lst, ensure_ascii=False, indent=2)}")
        logger.info("=" * 50)
        
        # summary_fields = ["defendants_role", "A_fact", "B_claim", "C_court_finding", "D_court_reason", "E_legal_eval", "case_fact_summary"]
        summary_fields = ["defendants_role", "A_fact", "B_claim", "C_court_finding", "D_court_reason", "E_legal_eval"]
        
        # 新增: 確定邏輯 (可從request.logic獲取，或從query_text解析; 這裡假設request有logic屬性，默認"AND")
        logic = getattr(request, 'logic', "AND").upper()  # "AND" 或 "OR"
        if logic not in ["AND", "OR"]:
            logic = "AND"  # 默認AND
        
        # 動態top_k: 基於limit的比例，適合百萬級數據 (factor可調整，越大越準但越慢)
        # top_k_factor = 10  # e.g., 如果limit=10，top_k=100
        # top_k = max(50, request.limit * top_k_factor)  # 最小50，確保足夠候選
        top_k = 5  # 僅取前五筆作為jid聚合依據
        
        # 收集每個條件的jid集合
        condition_jid_sets: List[Set[str]] = []
        
        for structured_filter in structured_filter_lst:
            qdrant_filter = self.filter_service.to_qdrant_filter(structured_filter)
            structured_filter_highlight = structured_filter.copy()
            structured_filter_highlight["summary_type"] = "case_highlights"
            qdrant_filter_highlight = self.filter_service.to_qdrant_filter(structured_filter_highlight)
            structured_filter_case_fact_summary = structured_filter.copy()
            structured_filter_case_fact_summary["summary_type"] = "case_fact_summary"
            qdrant_filter_case_fact_summary = self.filter_service.to_qdrant_filter(structured_filter_case_fact_summary)
            qdrant_filter_dict = qdrant_filter.model_dump(exclude_none=True) if qdrant_filter else None
            # qdrant_filter_lst = [qdrant_filter, qdrant_filter_highlight, qdrant_filter_case_fact_summary]
            qdrant_filter_lst = [qdrant_filter]
            
            logger.info("=" * 50)
            logger.info(f"Qdrant 過濾條件:\n{json.dumps(qdrant_filter_dict, ensure_ascii=False, indent=2)}")
            logger.info("=" * 50)
            logger.info(f"搜尋請求: collection={request.collection}, query='{request.query_text}', mode={request.mode}, logic={logic}")
            logger.info("=" * 50)
            
            # 從structured_filter提取特定字段的query_text (優先匹配summary_fields)
            reconstructed_query = ""
            field_type = None
            for field in summary_fields:
                if field in structured_filter and structured_filter[field]:
                    reconstructed_query = structured_filter[field]
                    field_type = field  # 記錄field_type用於過濾
                    # 不刪除structured_filter[field]，以保留原結構; 如需刪除，可添加del
                    break
            
            for qdrant_filter_sub in qdrant_filter_lst:
                config = SearchConfig(
                    collection=request.collection,
                    query_text=reconstructed_query,
                    mode=request.mode,
                    filter=qdrant_filter_sub,
                    limit=top_k,  # 使用動態top_k
                    score_threshold=0
                )
                
                response = await self.search_service.search(self.qdrant_client, config)
                results = self.search_service.flatten_points(response)
                
                # 收集此條件的jid (只保留score > threshold的)
                condition_jids = {result.get('payload').get('metadata').get('jid') for result in results if result.get('score', 0) > request.score_threshold}
                condition_jid_sets.append(condition_jids)
            
            logger.info(f"條件 '{field_type or 'general'}' 結果: {len(condition_jids)} 個 jid")
        
        # 應用邏輯聚合
        if not condition_jid_sets:
            aggregated_jids = set()
        elif logic == "AND":
            aggregated_jids = set.intersection(*condition_jid_sets) if condition_jid_sets else set()
        elif logic == "OR":
            aggregated_jids = set.union(*condition_jid_sets) if condition_jid_sets else set()
        
        logger.info(f"聚合後 jid (邏輯: {logic}): {len(aggregated_jids)} 個")
        
        detailed_results = await self.filter_service.retrieve_results_by_jids(
            qdrant_client=self.qdrant_client,
            collection=request.collection,
            limit=request.limit,
            aggregated_jids=aggregated_jids
        )
        
        simplified_results = []
        for result in detailed_results:
            payload = result.get('payload', {})
            metadata = payload.get('metadata', {})
            simplified_results.append({
                "page_content": payload.get('page_content'),
                "jid": metadata.get('jid')
            })

        logger.info(f"最終搜尋結果: 總共 {len(simplified_results)} 個結果")
        if len(simplified_results) > 0:
            for result in simplified_results:
                logger.info(f"---> 最終結果: {result.get('jid')}")
        else:
            logger.info(f"---> 最終結果: 沒有結果")
        
        return SearchResponse(
            results=simplified_results,
            total=len(simplified_results),
            query=request.query_text,
            mode=request.mode,
            collection=request.collection
        )
    
    async def list_collections(self) -> Dict[str, Any]:
        collections = await self.qdrant_client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        return {
            "collections": collection_names,
            "count": len(collection_names)
        }
    
    async def get_collection_info(self, collection: str) -> CollectionInfo:
        info = await self.qdrant_client.get_collection(collection)
        
        return CollectionInfo(
            name=collection,
            vectors_count=info.vectors_count,
            points_count=info.points_count,
            status=info.status.value
        )
    
    async def health_check(self) -> HealthStatus:
        collections = await self.qdrant_client.get_collections()
        return HealthStatus(
            status="healthy",
            qdrant_connection="connected",
            collections_count=len(collections.collections)
        )

