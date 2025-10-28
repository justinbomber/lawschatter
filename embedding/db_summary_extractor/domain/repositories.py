from abc import ABC, abstractmethod
from typing import List
from .entities import JudgmentRecord, SummaryRecord


class JudgmentRepository(ABC):
    
    @abstractmethod
    def get_all_dates_from_metadata_desc(self) -> List[str]:
        pass
    
    @abstractmethod
    def get_judgment(self, jid: str) -> JudgmentRecord:
        pass
    
    @abstractmethod
    def get_judgment_ids_by_date(self, jdate: str) -> List[str]:
        pass


class MetadataRepository(ABC):
    
    @abstractmethod
    def get_metadata_ids_by_date(self, jdate: str) -> List[str]:
        pass


class SummaryRepository(ABC):
    
    @abstractmethod
    def get_summary_ids_by_date(self, jdate: str) -> List[str]:
        pass
    
    @abstractmethod
    def save_summary(self, summary: SummaryRecord) -> None:
        pass

