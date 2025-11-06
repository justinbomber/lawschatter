from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from entities.models import ChatRequest, ChatResponse, HealthStatus
from controllers.chat_controller import ChatController
import logging
import json
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


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
    async def chat_completion(request: ChatRequest):
        streaming_info = f", streaming={request.streaming}" if request.streaming else ""
        logger.info(f"收到聊天請求: {request.question}{streaming_info}")
        
        if request.streaming:
            async def event_generator() -> AsyncGenerator[str, None]:
                async for chunk in controller.chat_completion_stream(request):
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
            return await controller.chat_completion(request)
    
    @router.get("/health", response_model=HealthStatus)
    async def health_check():
        return await controller.health_check()
    
    return router

