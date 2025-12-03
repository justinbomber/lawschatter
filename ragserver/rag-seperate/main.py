#!/usr/bin/env python3
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from config.settings import Settings
from infrastructure.qdrant_client_wrapper import QdrantClientWrapper
from infrastructure.embeddings.dense_embedding import DenseEmbeddingProvider
from infrastructure.embeddings.sparse_embedding import SparseEmbeddingProvider
from infrastructure.supabase_repository import SupabaseConversationRepository
from services.search_service import SearchService
from services.filter_service import FilterService
from services.rerank_service import RerankService
from services.openai_extraction_service import OpenAIExtractionService
from services.grok_extraction_service import GrokExtractionService
from services.document_search_orchestrator import DocumentSearchOrchestrator
from services.rrf_search_orchestrator import RRFSearchOrchestrator
from services.multivector_filter_service import MultivectorFilterService
from controllers.search_controller import SearchController
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
    
    qdrant_client = QdrantClientWrapper(settings)
    dense_provider = DenseEmbeddingProvider(settings)
    sparse_provider = SparseEmbeddingProvider(settings)
    
    search_service = SearchService(
        dense_provider=dense_provider,
        sparse_provider=sparse_provider,
        settings=settings
    )
    
    if settings.llm_provider == "openai":
        llm_extraction_service = OpenAIExtractionService(settings)
    else:
        llm_extraction_service = GrokExtractionService(settings)
    
    filter_service = FilterService(settings, llm_extraction_service)
    multivector_filter_service = MultivectorFilterService(settings, llm_extraction_service)
    rerank_service = RerankService(settings)
    
    document_search_orchestrator = DocumentSearchOrchestrator(
        qdrant_client=qdrant_client,
        search_service=search_service,
        filter_service=filter_service,
        settings=settings
    )
    
    rrf_orchestrator = RRFSearchOrchestrator(
        qdrant_client=qdrant_client,
        search_service=search_service,
        filter_service=multivector_filter_service,
        settings=settings
    )
    
    conversation_repository = SupabaseConversationRepository(settings)
    
    search_controller = SearchController(
        qdrant_client=qdrant_client,
        document_search_orchestrator=document_search_orchestrator,
        conversation_repository=conversation_repository,
        settings=settings,
        rrf_orchestrator=rrf_orchestrator
    )
    
    router = create_router(search_controller)
    app.include_router(router)
    
    logger.info("Qdrant 搜尋 API 服務已啟動")
    logger.info(f"Qdrant URL: {settings.qdrant.url}")
    logger.info(f"Collection: {settings.qdrant.collection_name}")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"Supabase Schema: {settings.supabase.schema_name}")
    
    yield
    
    logger.info("Qdrant 搜尋 API 服務已關閉")


app = FastAPI(
    title="Qdrant 搜尋 API",
    description="提供混合嵌入向量搜尋的 REST API 服務",
    version="2.0.0",
    lifespan=lifespan
)


def main():
    import uvicorn
    
    temp_settings = Settings()
    
    logger.info("啟動 Qdrant 搜尋 API 服務")
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
