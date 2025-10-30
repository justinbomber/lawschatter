from abc import ABC, abstractmethod
from typing import List
from .entities import EmbeddingDocument


class VectorStore(ABC):
    
    @abstractmethod
    def get_collection_count(self) -> int:
        pass
    
    @abstractmethod
    def add_documents(self, documents: List[EmbeddingDocument]) -> None:
        pass

