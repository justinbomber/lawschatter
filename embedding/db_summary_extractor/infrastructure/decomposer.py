import logging
from typing import List
from ..domain import (
    SummaryDecomposer, 
    SummaryExtractionResult, 
    SummaryRecord,
    HashGenerator,
)

logger = logging.getLogger(__name__)


class DefaultSummaryDecomposer(SummaryDecomposer):
    
    def __init__(self, hash_generator: HashGenerator):
        self.hash_generator = hash_generator
    
    def decompose(
        self, 
        jid: str, 
        jdate: str, 
        extraction: SummaryExtractionResult
    ) -> List[SummaryRecord]:
        logger.info(f"分解 summary 記錄: {jid}")
        
        records = []
        
        if extraction.case_fact_summary:
            record = SummaryRecord.create_case_fact_summary(
                jid=jid,
                jdate=jdate,
                content=extraction.case_fact_summary,
                hash_generator=self.hash_generator.generate,
            )
            records.append(record)
        
        for defendant in extraction.defendants:
            defendant_fields = {
                "role": defendant.role,
                "A_fact": defendant.A_fact,
                "B_claim": defendant.B_claim,
                "C_court_finding": defendant.C_court_finding,
                "D_court_reason": defendant.D_court_reason,
                "E_legal_eval": defendant.E_legal_eval,
            }
            
            for field_name, field_content in defendant_fields.items():
                record = SummaryRecord.create_defendant_field(
                    jid=jid,
                    jdate=jdate,
                    defendant_name=defendant.name,
                    field_name=field_name,
                    content=field_content,
                    hash_generator=self.hash_generator.generate,
                )
                records.append(record)
        
        for idx, highlight in enumerate(extraction.case_highlights):
            record = SummaryRecord.create_case_highlight(
                jid=jid,
                jdate=jdate,
                content=highlight,
                index=idx,
                hash_generator=self.hash_generator.generate,
            )
            records.append(record)
        
        logger.info(f"分解完成，產生 {len(records)} 筆記錄")
        return records

