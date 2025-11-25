from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from qdrant_client import models
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


@dataclass
class PrefetchSpec:
    query: Union[List[float], models.SparseVector]
    using: str
    limit: int
    filter: Optional[models.Filter] = None


@dataclass
class QuerySpec:
    query: Union[List[float], models.SparseVector, models.FusionQuery]
    using: Optional[str] = None
    limit: int = 100
    filter: Optional[models.Filter] = None


class IEmbeddingProvider(ABC):
    @abstractmethod
    async def embed_query(self, text: str):
        pass
    
    @abstractmethod
    async def embed_documents(self, texts: List[str]):
        pass


class IQdrantClient(ABC):
    @abstractmethod
    async def query_points(self, **kwargs) -> models.QueryResponse:
        pass
    
    @abstractmethod
    async def get_collections(self):
        pass
    
    @abstractmethod
    async def get_collection(self, collection_name: str):
        pass
    
    @abstractmethod
    async def scroll(self, **kwargs):
        pass
    
    @abstractmethod
    async def query_with_prefetch(
        self,
        collection_name: str,
        prefetch_queries: List['PrefetchSpec'],
        main_query: Optional['QuerySpec'],
        limit: int,
        filter: Optional[models.Filter] = None,
        fusion: str = "rrf"
    ) -> models.QueryResponse:
        pass


class ISearchService(ABC):
    @abstractmethod
    async def search(self, client: IQdrantClient, config: Any) -> models.QueryResponse:
        pass
    
    @abstractmethod
    def flatten_points(self, response: models.QueryResponse) -> List[Dict[str, Any]]:
        pass


class ILLMExtractionService(ABC):
    @abstractmethod
    async def extract_structured_filter(self, user_question: str, history_messages: List['Message'] = None) -> Dict[str, Any]:
        pass


class IFilterService(ABC):
    @abstractmethod
    async def extract_filter_conditions(self, user_question: str, history_messages: List['Message'] = None) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def to_qdrant_filter(self, filter_dict: dict) -> models.Filter:
        pass
    
    @abstractmethod
    async def retrieve_results_by_jids(
        self,
        qdrant_client: IQdrantClient,
        collection: str,
        limit: int,
        aggregated_jids: set
    ) -> List[Dict[str, Any]]:
        pass


class IRerankService(ABC):
    @abstractmethod
    async def rerank(self, query: str, documents: List[str], top_n: int) -> List[tuple]:
        pass


class IDocumentSearchOrchestrator(ABC):
    @abstractmethod
    async def orchestrate_search(
        self,
        collection: str,
        query_text: str,
        mode: str,
        limit: int,
        logic: str = "AND",
        history_messages: List['Message'] = None
    ) -> List[Dict[str, Any]]:
        pass


class IConversationRepository(ABC):
    @abstractmethod
    async def get_conversation_messages(self, token: str, conversation_id: str, limit: int = 10) -> List[Message]:
        pass
    
    @abstractmethod
    async def verify_user_conversation_access(self, token: str, user_id: str, conversation_id: str) -> bool:
        pass



