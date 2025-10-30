from abc import ABC, abstractmethod
from typing import List, Dict, Any
from qdrant_client import models


class IEmbeddingProvider(ABC):
    @abstractmethod
    def embed_query(self, text: str):
        pass
    
    @abstractmethod
    def embed_documents(self, texts: List[str]):
        pass


class IQdrantClient(ABC):
    @abstractmethod
    def query_points(self, **kwargs) -> models.QueryResponse:
        pass
    
    @abstractmethod
    def get_collections(self):
        pass
    
    @abstractmethod
    def get_collection(self, collection_name: str):
        pass


class ISearchService(ABC):
    @abstractmethod
    def search(self, client: IQdrantClient, config: Any) -> models.QueryResponse:
        pass
    
    @abstractmethod
    def flatten_points(self, response: models.QueryResponse) -> List[Dict[str, Any]]:
        pass


class IFilterService(ABC):
    @abstractmethod
    def extract_filter_conditions(self, user_question: str) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def to_qdrant_filter(self, filter_dict: dict) -> models.Filter:
        pass


class IRerankService(ABC):
    @abstractmethod
    def rerank(self, query: str, documents: List[str], top_n: int) -> List[tuple]:
        pass

