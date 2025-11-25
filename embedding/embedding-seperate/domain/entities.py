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
            'defendants': metadata.defendants,
        }
        
        if summary.defendent_name:
            matching_defendant = None
            for defendant in metadata.defendants:
                if defendant.get('defendant_name') == summary.defendent_name:
                    matching_defendant = defendant
                    break
            
            if matching_defendant:
                print("================================================")
                print(summary.defendent_name)
                print(summary.summary_type)
                print(matching_defendant)
                print("================================================")
                doc_metadata['defendants'] = [matching_defendant]
        else:
            doc_metadata['defendants'] = metadata.defendants
        
        return EmbeddingDocument(
            content=summary.content,
            metadata=doc_metadata,
            document_id=summary.point_id
        )


@dataclass
class JudgmentSearchDocument:
    judgment_id: str
    summary_content: str
    metadata: JudgmentMetadata
    
    @staticmethod
    def from_summaries_and_metadata(
        summaries: List[JudgmentSummary],
        metadata: JudgmentMetadata
    ) -> "JudgmentSearchDocument":
        combined_content = "\n\n".join([s.content for s in summaries])
        
        return JudgmentSearchDocument(
            judgment_id=metadata.jid,
            summary_content=combined_content,
            metadata=metadata
        )
    
    def to_payload(self) -> Dict[str, Any]:
        return {
            'jid': self.metadata.jid,
            'jid_full': self.metadata.jid_full,
            'jyear': self.metadata.jyear,
            'jcase': self.metadata.jcase,
            'jno': self.metadata.jno,
            'jdate': self.metadata.jdate,
            'jtitle': self.metadata.jtitle,
            'case_type': self.metadata.case_type,
            'defendants': self.metadata.defendants,
            'case_metadata': self.metadata.case_metadata,
            'summary_content': self.summary_content,
            'has_guilt': self.metadata.case_metadata.get('has_guilt'),
            'offense': self.metadata.case_metadata.get('offense', []),
            'court_level': self.metadata.case_metadata.get('court_level'),
            'used_messaging_app': self.metadata.case_metadata.get('used_messaging_app'),
            'has_recidivism': self.metadata.case_metadata.get('has_recidivism'),
            'sentence_months': self.metadata.case_metadata.get('sentence_months'),
        }

