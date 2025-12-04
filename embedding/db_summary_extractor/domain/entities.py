from dataclasses import dataclass, fields
from typing import List, Dict, Any


@dataclass
class JudgmentRecord:
    jid: str
    jdate: str
    jfull: str


# TODO: 增加欄位 (需與 config.FieldsConfig.BASE_FIELDS 保持同步)
@dataclass
class DefendantSummary:
    name: str
    role: str
    A_fact: str
    B_claim: str
    C_court_finding: str
    D_court_reason: str
    E_legal_eval: str
    statement_inconsistency_with_previous: str
    justification_reason: str
    excuse_reason: str
    
    @classmethod
    def get_field_names(cls) -> List[str]:
        return [f.name for f in fields(cls)]


@dataclass
class SummaryExtractionResult:
    case_fact_summary: str
    defendants: List[DefendantSummary]
    case_highlights: List[str]


@dataclass
class SummaryRecord:
    point_id: str
    jid: str
    jdate: str
    summary_type: str
    content: str
    defendent_name: str = None
    
    @staticmethod
    def create_case_fact_summary(
        jid: str, 
        jdate: str, 
        content: str, 
        hash_generator
    ) -> "SummaryRecord":
        unique_string = f"{jid}_case_fact_summary"
        point_id = hash_generator(unique_string)
        return SummaryRecord(
            point_id=point_id,
            jid=jid,
            jdate=jdate,
            summary_type="case_fact_summary",
            content=content,
            defendent_name=None
        )
    
    @staticmethod
    def create_defendant_field(
        jid: str,
        jdate: str,
        defendant_name: str,
        field_name: str,
        content: str,
        hash_generator
    ) -> "SummaryRecord":
        unique_string = f"{jid}_{defendant_name}_{field_name}"
        point_id = hash_generator(unique_string)
        return SummaryRecord(
            point_id=point_id,
            jid=jid,
            jdate=jdate,
            summary_type=field_name,
            content=content,
            defendent_name=defendant_name
        )
    
    @staticmethod
    def create_case_highlight(
        jid: str,
        jdate: str,
        content: str,
        index: int,
        hash_generator
    ) -> "SummaryRecord":
        unique_string = f"{jid}_case_highlights_{index}"
        point_id = hash_generator(unique_string)
        return SummaryRecord(
            point_id=point_id,
            jid=jid,
            jdate=jdate,
            summary_type="case_highlights",
            content=content,
            defendent_name=None
        )
    
