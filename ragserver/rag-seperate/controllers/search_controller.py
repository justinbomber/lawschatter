import logging
from typing import Dict, Any
from entities.models import SearchRequest, SearchResponse, CollectionInfo, HealthStatus
from domain.interfaces import IQdrantClient, IDocumentSearchOrchestrator
from config.settings import Settings

logger = logging.getLogger(__name__)


class SearchController:
    def __init__(
        self,
        qdrant_client: IQdrantClient,
        document_search_orchestrator: IDocumentSearchOrchestrator,
        settings: Settings
    ):
        self.qdrant_client = qdrant_client
        self.document_search_orchestrator = document_search_orchestrator
        self.settings = settings

    async def search_documents(self, request: SearchRequest) -> SearchResponse:
        logic = getattr(request, 'logic', "AND")
        
        simplified_results = await self.document_search_orchestrator.orchestrate_search(
            collection=request.collection,
            query_text=request.query_text,
            mode=request.mode,
            limit=request.limit,
            logic=logic
        )
        
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

