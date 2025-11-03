from abc import ABC, abstractmethod
from typing import List, Dict, Any
from qdrant_client import models


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


class ISearchService(ABC):
    @abstractmethod
    async def search(self, client: IQdrantClient, config: Any) -> models.QueryResponse:
        pass
    
    @abstractmethod
    def flatten_points(self, response: models.QueryResponse) -> List[Dict[str, Any]]:
        pass


class IFilterService(ABC):
    @abstractmethod
    async def extract_filter_conditions(self, user_question: str) -> List[Dict[str, Any]]:
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
        logic: str = "AND"
    ) -> List[Dict[str, Any]]:
        pass

