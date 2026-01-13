from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from .entities import EmbeddingDocument


class VectorStore(ABC):
    
    @abstractmethod
    def get_collection_count(self, collection_name: Optional[str] = None) -> int:
        pass
    
    @abstractmethod
    def add_documents(self, documents: List[EmbeddingDocument], collection_name: Optional[str] = None) -> None:
        pass
    
    @abstractmethod
    def add_judgment_points(self, documents_by_jid: Dict[str, List[EmbeddingDocument]], collection_name: Optional[str] = None) -> None:
        pass

