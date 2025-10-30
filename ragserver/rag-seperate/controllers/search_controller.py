import logging
import json
from typing import Dict, Any
from entities.models import SearchRequest, SearchResponse, CollectionInfo, HealthStatus
from services.search_service import SearchConfig
from domain.interfaces import ISearchService, IFilterService, IQdrantClient
from config.settings import Settings


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
    
    def search_documents(self, request: SearchRequest) -> SearchResponse:
        structured_filter_lst = self.filter_service.extract_filter_conditions(request.query_text)
        logger.info("=" * 50)
        logger.info(f"過濾條件:\n{json.dumps(structured_filter_lst, ensure_ascii=False, indent=2)}")
        logger.info("=" * 50)
        
        summary_fields = ["defendants_role", "A_fact", "B_claim", "C_court_finding", "D_court_reason", "E_legal_eval", "case_fact_summary"]
        
        for structured_filter in structured_filter_lst:
            qdrant_filter = self.filter_service.to_qdrant_filter(structured_filter)
            
            qdrant_filter_dict = qdrant_filter.model_dump(exclude_none=True) if qdrant_filter else None
            
            logger.info("=" * 50)
            logger.info(f"Qdrant 過濾條件:\n{json.dumps(qdrant_filter_dict, ensure_ascii=False, indent=2)}")
            logger.info("=" * 50)
            logger.info(f"搜尋請求: collection={request.collection}, query='{request.query_text}', mode={request.mode}")
            logger.info("=" * 50)
            
            reconstructed_query = ""
            for summary_field in summary_fields:
                if summary_field in structured_filter and structured_filter[summary_field]:
                    reconstructed_query = structured_filter[summary_field]
                    del structured_filter[summary_field]
                    break
            
            config = SearchConfig(
                collection=request.collection,
                query_text=reconstructed_query,
                mode=request.mode,
                filter=qdrant_filter,
                limit=request.limit,
                score_threshold=request.score_threshold
            )
            
            response = self.search_service.search(self.qdrant_client, config)
            results = self.search_service.flatten_points(response)
            
            logger.info(f"搜尋結果: 總共 {len(results)} 個結果")
            if len(results) > 0:
                for result in results:
                    logger.info(f"---> 搜尋結果: {result.get('payload').get('metadata').get('jid')}")
            else:
                logger.info(f"---> 搜尋結果: 沒有結果")
        
        return SearchResponse(
            results=results,
            # results=[],
            # total=0,
            # query="yes",
            total=len(results),
            query=request.query_text,
            mode=request.mode,
            collection=request.collection
        )
    
    def list_collections(self) -> Dict[str, Any]:
        collections = self.qdrant_client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        return {
            "collections": collection_names,
            "count": len(collection_names)
        }
    
    def get_collection_info(self, collection: str) -> CollectionInfo:
        info = self.qdrant_client.get_collection(collection)
        
        return CollectionInfo(
            name=collection,
            vectors_count=info.vectors_count,
            points_count=info.points_count,
            status=info.status.value
        )
    
    def health_check(self) -> HealthStatus:
        collections = self.qdrant_client.get_collections()
        return HealthStatus(
            status="healthy",
            qdrant_connection="connected",
            collections_count=len(collections.collections)
        )

