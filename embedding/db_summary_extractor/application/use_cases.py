import logging
import time
from typing import List, Dict
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
    
    def execute(self) -> None:
        logger.info("開始執行 Summary 提取流程")
        
        while True:
            unprocessed_list = self._get_unprocessed_jids()
            
            if not unprocessed_list:
                logger.info("沒有未處理的判決，等待 2 分鐘後再次掃描")
                time.sleep(120)
                continue
            
            logger.info(f"找到 {len(unprocessed_list)} 筆未處理的判決，開始處理")
            
            processed_count = 0
            for item in unprocessed_list:
                jid = item["jid"]
                jdate = item["jdate"]
                if self._process_judgment(jid, jdate):
                    processed_count += 1
            
            logger.info(f"本輪處理完成，處理了 {processed_count} 筆判決")
    
    def _get_unprocessed_jids(self) -> List[Dict[str, str]]:
        result = self.summary_repo.get_unprocessed_jids()
        return result
    
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

