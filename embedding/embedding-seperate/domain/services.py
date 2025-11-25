from abc import ABC, abstractmethod
from typing import List
from .entities import EmbeddingDocument, JudgmentSearchDocument


class VectorStore(ABC):
    
    @abstractmethod
    def get_collection_count(self) -> int:
        pass
    
    @abstractmethod
    def add_documents(self, documents: List[EmbeddingDocument]) -> None:
        pass
    
    @abstractmethod
    def upsert_judgment(self, document: JudgmentSearchDocument) -> None:
        pass
    
    @abstractmethod
    def create_v2_collection(self) -> None:
        pass

