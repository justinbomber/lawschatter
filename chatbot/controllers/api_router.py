from fastapi import APIRouter, Header, HTTPException, Depends
from fastapi.responses import StreamingResponse
from entities.models import ChatRequest, ChatResponse, HealthStatus
from controllers.chat_controller import ChatController
import logging
import json
import jwt
from typing import AsyncGenerator, Optional

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


def create_router(controller: ChatController) -> APIRouter:
    router = APIRouter()
    
    @router.get("/")
    async def root():
        return {
            "message": "法律聊天機器人 API 服務運行中",
            "status": "healthy",
            "endpoints": {
                "chat": "/chat/completion",
                "health": "/health"
            }
        }
    
    @router.post("/chat/completion", response_model=ChatResponse)
    async def chat_completion(
        request: ChatRequest,
        auth_data: tuple[str, str] = Depends(get_token_and_user_id)
    ):
        token, user_id = auth_data
        streaming_info = f", streaming={request.streaming}" if request.streaming else ""
        logger.info(f"使用者 {user_id} 收到聊天請求: conversation_id={request.conversation_id}, question={request.question}{streaming_info}")
        
        if request.streaming:
            async def event_generator() -> AsyncGenerator[str, None]:
                async for chunk in controller.chat_completion_stream(request, token, user_id):
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
            return await controller.chat_completion(request, token, user_id)
    
    @router.get("/health", response_model=HealthStatus)
    async def health_check():
        return await controller.health_check()
    
    return router

