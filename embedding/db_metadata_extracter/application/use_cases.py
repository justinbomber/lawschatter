import logging
from typing import List
from ..domain import (
    JudgmentRepository,
    MetadataRepository,
    MetadataExtractor,
    JudgmentFilter,
    SchemaProvider,
    MetadataRecord,
)

logger = logging.getLogger(__name__)


class ExtractMetadataUseCase:
    
    def __init__(
        self,
        judgment_repo: JudgmentRepository,
        metadata_repo: MetadataRepository,
        extractor: MetadataExtractor,
        filter_service: JudgmentFilter,
        schema_provider: SchemaProvider,
        target_titles: List[str],
        include_adjudicate: bool = False,
    ):
        self.judgment_repo = judgment_repo
        self.metadata_repo = metadata_repo
        self.extractor = extractor
        self.filter_service = filter_service
        self.schema_provider = schema_provider
        self.target_titles = target_titles
        self.include_adjudicate = include_adjudicate
    
    def execute(self) -> int:
        logger.info("開始執行 Metadata 提取流程")
        
        total_processed = 0
        dates = self.judgment_repo.get_all_dates_desc()
        logger.info(f"找到 {len(dates)} 個獨特日期")
        
        for jdate in dates:
            processed_count = self._process_date(jdate)
            total_processed += processed_count
        
        logger.info(f"Metadata 提取完成，總共處理: {total_processed} 筆")
        return total_processed
    
    def _process_date(self, jdate: str) -> int:
        logger.info(f"處理日期: {jdate}")
        
        unprocessed_jids = self._get_unprocessed_jids(jdate)
        
        if not unprocessed_jids:
            return 0
        
        logger.info(f"找到 {len(unprocessed_jids)} 筆未處理的判決")
        
        processed_count = 0
        for jid in unprocessed_jids:
            if self._process_judgment(jid, jdate):
                processed_count += 1
        
        return processed_count
    
    def _get_unprocessed_jids(self, jdate: str) -> List[str]:
        judgment_jids = set(
            self.judgment_repo.get_judgment_ids_by_date_and_titles(
                jdate, 
                self.target_titles
            )
        )
        logger.info(f"找到 {len(judgment_jids)} 筆符合條件的判決")
        
        metadata_jids = set(
            self.metadata_repo.get_metadata_ids_by_date(jdate)
        )
        
        unprocessed = list(judgment_jids - metadata_jids)
        logger.info(f"找到 {len(unprocessed)} 筆未處理的判決")
        
        return unprocessed
    
    def _process_judgment(self, jid: str, jdate: str) -> bool:
        logger.info(f"處理判決: {jid}")
        
        judgment = self.judgment_repo.get_judgment(jid)
        
        if not self.include_adjudicate:
            if self.filter_service.should_ignore(judgment):
                logger.info(f"跳過判決 {jid}（符合過濾條件）")
                return False
        
        schema = self.schema_provider.get_schema()
        extraction_result = self.extractor.extract(judgment, schema)
        
        metadata_record = MetadataRecord.from_judgment_and_extraction(
            judgment, 
            extraction_result
        )
        print("================================================")
        print(metadata_record)
        print("================================================")
        
        self.metadata_repo.save_metadata(metadata_record)
        
        logger.info(f"成功處理並插入 metadata: {jid}")
        return True

