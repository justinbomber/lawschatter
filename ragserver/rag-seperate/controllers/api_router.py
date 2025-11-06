from fastapi import APIRouter
from entities.models import SearchRequest, SearchResponse, CollectionInfo, HealthStatus
from controllers.search_controller import SearchController
import logging
from fastapi.responses import StreamingResponse
import json
from typing import AsyncGenerator, Dict, Any

logger = logging.getLogger(__name__)


def create_router(controller: SearchController) -> APIRouter:
    router = APIRouter()
    
    @router.get("/")
    async def root():
        return {"message": "Qdrant 搜尋 API 服務運行中", "status": "healthy"}
    
    @router.get("/collections")
    async def list_collections():
        return await controller.list_collections()
    
    @router.get("/collections/{collection}/info", response_model=CollectionInfo)
    async def collection_info(collection: str):
        return await controller.get_collection_info(collection)
    
    @router.post("/search", response_model=SearchResponse)
    async def search_documents(request: SearchRequest):
        streaming_info = f", streaming={request.streaming}" if request.streaming else ""
        logger.info(f"收到搜尋請求: {request.collection} - {request.query_text}{streaming_info}")
        
        if request.streaming:
            async def event_generator() -> AsyncGenerator[str, None]:
                async for chunk in controller.search_documents_stream(request):
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control, Content-Type",
                }
            )
        else:
            return await controller.search_documents(request)
    
    @router.get("/health", response_model=HealthStatus)
    async def health_check():
        return await controller.health_check()
    
    return router

