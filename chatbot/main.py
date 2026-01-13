#!/usr/bin/env python3
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import Settings
from infrastructure.rag_client import RAGClient
from infrastructure.openai_llm_provider import OpenAILLMProvider
from infrastructure.grok_llm_provider import GrokLLMProvider
from infrastructure.supabase_repository import SupabaseConversationRepository
from services.chat_service import ChatService
from controllers.chat_controller import ChatController
from controllers.api_router import create_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

settings = None
router = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global settings, router
    
    settings = Settings()
    
    rag_client = RAGClient(settings)
    
    # 默認使用 OpenAI，可切換為 GrokLLMProvider
    # llm_provider = OpenAILLMProvider(settings)
    llm_provider = GrokLLMProvider(settings)  # 取消註解以使用 Grok
    
    conversation_repository = SupabaseConversationRepository(settings)
    
    chat_service = ChatService(
        rag_client=rag_client,
        llm_provider=llm_provider,
        conversation_repository=conversation_repository,
        settings=settings
    )
    
    chat_controller = ChatController(
        chat_service=chat_service,
        rag_client=rag_client,
        llm_provider=llm_provider,
        settings=settings
    )
    
    router = create_router(chat_controller)
    app.include_router(router)
    
    logger.info("法律聊天機器人 API 服務已啟動")
    logger.info(f"RAG Server: {settings.rag_server.url}")
    logger.info(f"LLM Provider: {llm_provider.__class__.__name__}")
    
    yield
    
    logger.info("法律聊天機器人 API 服務已關閉")


app = FastAPI(
    title="法律聊天機器人 API",
    description="提供基於 RAG 的法律問答服務",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def main():
    import uvicorn
    
    temp_settings = Settings()
    
    logger.info("啟動法律聊天機器人 API 服務")
    logger.info(f"API 服務運行在: http://{temp_settings.api.host}:{temp_settings.api.port}")
    logger.info(f"API 文件: http://{temp_settings.api.host}:{temp_settings.api.port}/docs")
    
    uvicorn.run(
        "main:app",
        host=temp_settings.api.host,
        port=temp_settings.api.port,
        reload=temp_settings.api.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()


# AWS Lambda Handler
from mangum import Mangum
handler = Mangum(app, lifespan="off")
