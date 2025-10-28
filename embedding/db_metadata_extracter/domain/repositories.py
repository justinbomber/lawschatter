from abc import ABC, abstractmethod
from typing import List
from .entities import JudgmentRecord, MetadataRecord


class JudgmentRepository(ABC):
    
    @abstractmethod
    def get_all_dates_desc(self) -> List[str]:
        pass
    
    @abstractmethod
    def get_judgment(self, jid: str) -> JudgmentRecord:
        pass
    
    @abstractmethod
    def get_judgment_ids_by_date_and_titles(
        self, 
        jdate: str, 
        target_titles: List[str]
    ) -> List[str]:
        pass


class MetadataRepository(ABC):
    
    @abstractmethod
    def get_metadata_ids_by_date(self, jdate: str) -> List[str]:
        pass
    
    @abstractmethod
    def save_metadata(self, metadata: MetadataRecord) -> None:
        pass

