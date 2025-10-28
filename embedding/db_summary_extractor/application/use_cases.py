import logging
from typing import List
from ..domain import (
    JudgmentRepository,
    MetadataRepository,
    SummaryRepository,
    SummaryExtractor,
    SchemaProvider,
    SummaryDecomposer,
)

logger = logging.getLogger(__name__)


class ExtractSummaryUseCase:
    
    def __init__(
        self,
        judgment_repo: JudgmentRepository,
        metadata_repo: MetadataRepository,
        summary_repo: SummaryRepository,
        extractor: SummaryExtractor,
        schema_provider: SchemaProvider,
        decomposer: SummaryDecomposer,
        sleep_interval: int = 60,
    ):
        self.judgment_repo = judgment_repo
        self.metadata_repo = metadata_repo
        self.summary_repo = summary_repo
        self.extractor = extractor
        self.schema_provider = schema_provider
        self.decomposer = decomposer
        self.sleep_interval = sleep_interval
    
    def execute(self) -> int:
        logger.info("開始執行 Summary 提取流程")
        
        total_processed = 0
        dates = self.judgment_repo.get_all_dates_from_metadata_desc()
        logger.info(f"找到 {len(dates)} 個獨特日期")
        
        for jdate in dates:
            processed_count = self._process_date(jdate)
            total_processed += processed_count
        
        logger.info(f"Summary 提取完成，總共處理: {total_processed} 筆")
        return total_processed
    
    def _process_date(self, jdate: str) -> int:
        logger.info(f"處理日期: {jdate}")
        
        unprocessed_jids = self._get_unprocessed_jids(jdate)
        
        if not unprocessed_jids:
            logger.info(f"日期 {jdate} 沒有未處理的判決")
            return 0
        
        logger.info(f"找到 {len(unprocessed_jids)} 筆未處理的判決")
        
        processed_count = 0
        for jid in unprocessed_jids:
            if self._process_judgment(jid, jdate):
                processed_count += 1
        
        return processed_count
    
    def _get_unprocessed_jids(self, jdate: str) -> List[str]:
        judgment_jids = set(
            self.judgment_repo.get_judgment_ids_by_date(jdate)
        )
        
        metadata_jids = set(
            self.metadata_repo.get_metadata_ids_by_date(jdate)
        )
        
        summary_jids = set(
            self.summary_repo.get_summary_ids_by_date(jdate)
        )
        
        unprocessed = list((judgment_jids & metadata_jids) - summary_jids)
        logger.info(f"找到 {len(unprocessed)} 筆未處理的判決")
        
        return unprocessed
    
    def _process_judgment(self, jid: str, jdate: str) -> bool:
        logger.info(f"處理判決: {jid}")
        
        judgment = self.judgment_repo.get_judgment(jid)
        
        schema = self.schema_provider.get_schema()
        extraction_result = self.extractor.extract(judgment, schema)
        
        summary_records = self.decomposer.decompose(
            jid, 
            jdate, 
            extraction_result
        )
        
        for record in summary_records:
            self.summary_repo.save_summary(record)
        
        logger.info(f"成功處理並插入 {len(summary_records)} 筆 summary: {jid}")
        return True

