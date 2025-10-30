from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class JudgmentSummary:
    point_id: str
    jid: str
    jdate: str
    summary_type: str
    content: str
    defendent_name: Optional[str] = None


@dataclass
class JudgmentMetadata:
    jid: str
    jid_full: str
    jyear: str
    jcase: str
    jno: str
    jdate: str
    jtitle: str
    case_type: str
    defendants: List[Dict[str, Any]]
    case_metadata: Dict[str, Any]


@dataclass
class EmbeddingDocument:
    content: str
    metadata: Dict[str, Any]
    document_id: str
    
    @staticmethod
    def from_summary_and_metadata(
        summary: JudgmentSummary,
        metadata: JudgmentMetadata
    ) -> "EmbeddingDocument":
        doc_metadata = {
            'jid': metadata.jid,
            'jid_full': metadata.jid_full,
            'jyear': metadata.jyear,
            'jcase': metadata.jcase,
            'jno': metadata.jno,
            'jdate': metadata.jdate,
            'jtitle': metadata.jtitle,
            'case_type': metadata.case_type,
            'summary_type': summary.summary_type,
            'case_metadata': metadata.case_metadata,
        }
        
        if summary.defendent_name:
            matching_defendant = None
            for defendant in metadata.defendants:
                if defendant.get('defendant_name') == summary.defendent_name:
                    matching_defendant = defendant
                    break
            
            if matching_defendant:
                doc_metadata['defendant'] = matching_defendant
                doc_metadata['defendant_name'] = summary.defendent_name
        else:
            doc_metadata['defendants'] = metadata.defendants
        
        return EmbeddingDocument(
            content=summary.content,
            metadata=doc_metadata,
            document_id=summary.point_id
        )

