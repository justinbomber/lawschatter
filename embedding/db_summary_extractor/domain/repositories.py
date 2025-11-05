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
    def has_summary_for_jid(self, jid: str) -> bool:
        pass
    
    @abstractmethod
    def insert_lock_record(self, jid: str, jdate: str, lock_point_id: str) -> None:
        pass
    
    @abstractmethod
    def delete_lock_record(self, lock_point_id: str) -> None:
        pass
    
    @abstractmethod
    def save_summary(self, summary: SummaryRecord) -> None:
        pass
    
    @abstractmethod
    def get_unprocessed_jids(self) -> List[dict]:
        pass

