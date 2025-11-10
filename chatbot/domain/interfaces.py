from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator
from entities.models import RAGSearchRequest, RAGSearchResponse, ChatMessage
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Message:
    message_id: str
    conversation_id: str
    user_id: str
    sender_type: str
    content: str
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "sender_type": self.sender_type,
            "content": self.content,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }


class IRAGClient(ABC):
    @abstractmethod
    async def search(self, request: RAGSearchRequest, token: str, user_id: str) -> RAGSearchResponse:
        pass
    
    @abstractmethod
    async def search_stream(self, request: RAGSearchRequest, token: str, user_id: str) -> AsyncGenerator[Dict[str, Any], None]:
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
        max_tokens: int,
        history_messages: List[Message] = None
    ) -> str:
        pass
    
    @abstractmethod
    async def generate_response_stream(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int,
        history_messages: List[Message] = None
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
        conversation_id: str,
        token: str,
        user_id: str,
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
        conversation_id: str,
        token: str,
        user_id: str,
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


class IConversationRepository(ABC):
    @abstractmethod
    async def get_conversation_messages(self, token: str, conversation_id: str, limit: int = 10) -> List[Message]:
        pass
    
    @abstractmethod
    async def verify_user_conversation_access(self, token: str, user_id: str, conversation_id: str) -> bool:
        pass
    
    @abstractmethod
    async def save_message(
        self,
        token: str,
        conversation_id: str,
        user_id: str,
        sender_type: str,
        content: str
    ) -> None:
        pass
    
    @abstractmethod
    async def create_conversation(self, token: str, user_id: str, title: str = "新對話") -> str:
        pass
    
    @abstractmethod
    async def update_conversation_title(self, token: str, conversation_id: str, title: str) -> None:
        pass

