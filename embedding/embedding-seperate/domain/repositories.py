from abc import ABC, abstractmethod
from typing import List
from .entities import JudgmentSummary, JudgmentMetadata


class SummaryRepository(ABC):
    
    @abstractmethod
    def get_all_dates_desc(self) -> List[str]:
        pass
    
    @abstractmethod
    def get_unprocessed_jids_by_date(self, jdate: str) -> List[str]:
        pass
    
    @abstractmethod
    def get_summaries_by_jid(self, jid: str) -> List[JudgmentSummary]:
        pass
    
    @abstractmethod
    def mark_as_embedded(self, jid: str) -> None:
        pass


class MetadataRepository(ABC):
    
    @abstractmethod
    def get_metadata_by_jid(self, jid: str) -> JudgmentMetadata:
        pass

