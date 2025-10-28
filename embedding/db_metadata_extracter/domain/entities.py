from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class JudgmentRecord:
    jid: str
    jid_full: str
    jyear: str
    jcase: str
    jno: str
    jdate: str
    jtitle: str
    case_type: str
    jtitle_type: str
    jfull: str


@dataclass
class MetadataExtractionResult:
    defendants: List[Dict[str, Any]]
    case_metadata: Dict[str, Any]


@dataclass
class MetadataRecord:
    jid: str
    jid_full: str
    jyear: str
    jcase: str
    jno: str
    jdate: str
    jtitle: str
    case_type: str
    jtitle_type: str
    defendants: List[Dict[str, Any]]
    case_metadata: Dict[str, Any]

    @staticmethod
    def from_judgment_and_extraction(
        judgment: JudgmentRecord,
        extraction: MetadataExtractionResult
    ) -> "MetadataRecord":
        return MetadataRecord(
            jid=judgment.jid,
            jid_full=judgment.jid_full,
            jyear=judgment.jyear,
            jcase=judgment.jcase,
            jno=judgment.jno,
            jdate=judgment.jdate,
            jtitle=judgment.jtitle,
            case_type=judgment.case_type,
            jtitle_type=judgment.jtitle_type,
            defendants=extraction.defendants,
            case_metadata=extraction.case_metadata,
        )

