from fastapi import APIRouter
from entities.models import SearchRequest, SearchResponse, CollectionInfo, HealthStatus
from controllers.search_controller import SearchController
import logging

logger = logging.getLogger(__name__)


def create_router(controller: SearchController) -> APIRouter:
    router = APIRouter()
    
    @router.get("/")
    async def root():
        return {"message": "Qdrant 搜尋 API 服務運行中", "status": "healthy"}
    
    @router.get("/collections")
    async def list_collections():
        return controller.list_collections()
    
    @router.get("/collections/{collection}/info", response_model=CollectionInfo)
    async def collection_info(collection: str):
        return controller.get_collection_info(collection)
    
    @router.post("/search", response_model=SearchResponse)
    async def search_documents(request: SearchRequest):
        logger.info(f"收到搜尋請求: {request.collection} - {request.query_text}")
        return controller.search_documents(request)
    
    @router.get("/health", response_model=HealthStatus)
    async def health_check():
        return controller.health_check()
    
    return router

