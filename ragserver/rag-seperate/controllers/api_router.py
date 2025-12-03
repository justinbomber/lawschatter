from fastapi import APIRouter, Header, HTTPException, Depends
from entities.models import SearchRequest, SearchResponse, CollectionInfo, HealthStatus
from controllers.search_controller import SearchController
import logging
from fastapi.responses import StreamingResponse
import json
from typing import AsyncGenerator, Dict, Any, Optional
import jwt

logger = logging.getLogger(__name__)


async def get_token_and_user_id(authorization: Optional[str] = Header(None)) -> tuple[str, str]:
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少 Authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header 格式錯誤")
    
    token = authorization.replace("Bearer ", "")
    
    decoded = jwt.decode(token, options={"verify_signature": False})
    user_id = decoded.get("sub")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Token 中缺少使用者 ID")
    
    return token, user_id


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
    async def search_documents(
        request: SearchRequest,
        auth_data: tuple[str, str] = Depends(get_token_and_user_id)
    ):
        token, user_id = auth_data
        streaming_info = f", streaming={request.streaming}" if request.streaming else ""
        logger.info(f"使用者 {user_id} 收到搜尋請求: conversation_id={request.conversation_id}, query={request.query_text}{streaming_info}")
        
        if request.streaming:
            async def event_generator() -> AsyncGenerator[str, None]:
                async for chunk in controller.search_documents_stream(request, token, user_id):
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
            return await controller.search_documents(request, token, user_id)
    
    @router.get("/health", response_model=HealthStatus)
    async def health_check():
        return await controller.health_check()
    
    @router.post("/search/advanced")
    async def search_documents_advanced(
        request: SearchRequest,
        auth_data: tuple[str, str] = Depends(get_token_and_user_id)
    ):
        token, user_id = auth_data
        search_mode = request.search_mode or "chunk"
        logger.info(f"使用者 {user_id} 收到進階搜尋請求: mode={search_mode}, query={request.query_text}")
        
        async def event_generator() -> AsyncGenerator[str, None]:
            async for chunk in controller.search_documents_advanced(request, token, user_id):
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
    
    return router

