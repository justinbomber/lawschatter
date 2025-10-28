from abc import ABC, abstractmethod
from typing import Dict, Any, List
from .entities import JudgmentRecord, SummaryExtractionResult, SummaryRecord


class SummaryExtractor(ABC):
    
    @abstractmethod
    def extract(
        self, 
        judgment: JudgmentRecord, 
        schema: Dict[str, Any]
    ) -> SummaryExtractionResult:
        pass


class SchemaProvider(ABC):
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        pass


class HashGenerator(ABC):
    
    @abstractmethod
    def generate(self, unique_string: str) -> str:
        pass


class SummaryDecomposer(ABC):
    
    @abstractmethod
    def decompose(
        self, 
        jid: str, 
        jdate: str, 
        extraction: SummaryExtractionResult
    ) -> List[SummaryRecord]:
        pass

