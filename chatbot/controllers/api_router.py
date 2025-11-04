from fastapi import APIRouter
from entities.models import ChatRequest, ChatResponse, HealthStatus
from controllers.chat_controller import ChatController
import logging

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
        logger.info(f"收到聊天請求: {request.question}")
        return await controller.chat_completion(request)
    
    @router.get("/health", response_model=HealthStatus)
    async def health_check():
        return await controller.health_check()
    
    return router

