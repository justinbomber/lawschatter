from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator
from entities.models import RAGSearchRequest, RAGSearchResponse, ChatMessage


class IRAGClient(ABC):
    @abstractmethod
    async def search(self, request: RAGSearchRequest) -> RAGSearchResponse:
        pass
    
    @abstractmethod
    async def search_stream(self, request: RAGSearchRequest) -> AsyncGenerator[Dict[str, Any], None]:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass


class ILLMProvider(ABC):
    @abstractmethod
    async def generate_response(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int
    ) -> str:
        pass
    
    @abstractmethod
    async def generate_response_stream(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[str, None]:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass


class IChatService(ABC):
    @abstractmethod
    async def process_chat(
        self,
        question: str,
        collection: str,
        mode: str,
        limit: int,
        score_threshold: float,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def process_chat_stream(
        self,
        question: str,
        collection: str,
        mode: str,
        limit: int,
        score_threshold: float,
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[Dict[str, Any], None]:
        pass
    
    @abstractmethod
    def build_prompt(
        self,
        question: str,
        rag_results: List[Dict[str, Any]]
    ) -> List[ChatMessage]:
        pass

