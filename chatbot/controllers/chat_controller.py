import logging
from typing import Dict, Any, AsyncGenerator
from domain.interfaces import IChatService, IRAGClient, ILLMProvider
from entities.models import ChatRequest, ChatResponse, HealthStatus
from config.settings import Settings

logger = logging.getLogger(__name__)


class ChatController:
    def __init__(
        self,
        chat_service: IChatService,
        rag_client: IRAGClient,
        llm_provider: ILLMProvider,
        settings: Settings
    ):
        self.chat_service = chat_service
        self.rag_client = rag_client
        self.llm_provider = llm_provider
        self.settings = settings
    
    async def chat_completion(self, request: ChatRequest, token: str, user_id: str) -> ChatResponse:
        collection = self.settings.rag_search.collection
        mode = self.settings.rag_search.mode
        limit = self.settings.rag_search.limit
        score_threshold = self.settings.rag_search.score_threshold
        temperature = self.settings.llm.temperature
        max_tokens = self.settings.llm.max_tokens
        
        result = await self.chat_service.process_chat(
            question=request.question,
            conversation_id=request.conversation_id,
            token=token,
            user_id=user_id,
            collection=collection,
            mode=mode,
            limit=limit,
            score_threshold=score_threshold,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return ChatResponse(**result)
    
    async def chat_completion_stream(self, request: ChatRequest, token: str, user_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        collection = self.settings.rag_search.collection
        mode = self.settings.rag_search.mode
        limit = self.settings.rag_search.limit
        score_threshold = self.settings.rag_search.score_threshold
        temperature = self.settings.llm.temperature
        max_tokens = self.settings.llm.max_tokens
        
        async for chunk in self.chat_service.process_chat_stream(
            question=request.question,
            conversation_id=request.conversation_id,
            token=token,
            user_id=user_id,
            collection=collection,
            mode=mode,
            limit=limit,
            score_threshold=score_threshold,
            temperature=temperature,
            max_tokens=max_tokens
        ):
            yield chunk
    
    async def health_check(self) -> HealthStatus:
        rag_connection = "connected"
        llm_status = "available"
        error = None
        
        rag_healthy = await self.rag_client.health_check()
        if not rag_healthy:
            rag_connection = "disconnected"
            error = "RAG server is not reachable"
        
        if not self.llm_provider.is_available():
            llm_status = "unavailable"
            error = "LLM provider is not configured"
        
        status = "healthy" if rag_healthy and self.llm_provider.is_available() else "unhealthy"
        
        return HealthStatus(
            status=status,
            rag_server_connection=rag_connection,
            llm_provider=llm_status,
            error=error
        )

