from abc import ABC, abstractmethod
from typing import Dict, Any
from .entities import JudgmentRecord, MetadataExtractionResult


class MetadataExtractor(ABC):
    
    @abstractmethod
    def extract(
        self, 
        judgment: JudgmentRecord, 
        schema: Dict[str, Any]
    ) -> MetadataExtractionResult:
        pass


class JudgmentFilter(ABC):
    
    @abstractmethod
    def should_ignore(self, judgment: JudgmentRecord) -> bool:
        pass


class SchemaProvider(ABC):
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        pass

