import logging
import signal
import sys
from typing import List, Optional, Callable
from openai import APITimeoutError, APIConnectionError
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
        extractor_factory: Optional[Callable[[], MetadataExtractor]] = None,
    ):
        self.judgment_repo = judgment_repo
        self.metadata_repo = metadata_repo
        self.extractor = extractor
        self.filter_service = filter_service
        self.schema_provider = schema_provider
        self.target_titles = target_titles
        self.include_adjudicate = include_adjudicate
        self.extractor_factory = extractor_factory
        self.current_processing_jid: Optional[str] = None
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame) -> None:
        logger.warning(f"接收到停止信號 {signum}，準備清理並退出")
        if self.current_processing_jid:
            logger.info(f"清理當前處理的 jid: {self.current_processing_jid}")
            self.metadata_repo.delete_lock_record(self.current_processing_jid)
        logger.info("清理完成，退出程式")
        sys.exit(0)
    
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
        unprocessed = self.judgment_repo.get_unprocessed_jids_by_date_and_titles(
            jdate,
            self.target_titles,
            self.include_adjudicate
        )
        return unprocessed
    
    def _rebuild_extractor(self) -> None:
        if self.extractor_factory:
            logger.info("重建 extractor 和 OpenAI client")
            self.extractor = self.extractor_factory()
    
    def _process_judgment(self, jid: str, jdate: str) -> bool:
        logger.info(f"處理判決: {jid}")
        
        if self.metadata_repo.has_metadata(jid):
            logger.info(f"跳過判決 {jid}（已存在 metadata）")
            return False
        
        self.current_processing_jid = jid
        lock_inserted = False
        attempt = 0
        
        while True:
            attempt += 1
            
            if attempt > 1:
                logger.info(f"重新查詢資料並嘗試處理判決 (第 {attempt} 次): {jid}")
            
            if not lock_inserted:
                self.metadata_repo.insert_lock_record(jid, jdate)
                lock_inserted = True
            
            judgment = self.judgment_repo.get_judgment(jid)
            
            if not self.include_adjudicate:
                if self.filter_service.should_ignore(judgment):
                    logger.info(f"跳過判決 {jid}（符合過濾條件）")
                    self.metadata_repo.delete_lock_record(jid)
                    self.current_processing_jid = None
                    return False
            
            schema = self.schema_provider.get_schema()
            
            try:
                extraction_result = self.extractor.extract(judgment, schema)
                
                metadata_record = MetadataRecord.from_judgment_and_extraction(
                    judgment, 
                    extraction_result
                )
                print("================================================")
                print(metadata_record)
                print("================================================")
                
                self.metadata_repo.update_metadata(metadata_record)
                
                logger.info(f"成功處理並更新 metadata: {jid}")
                self.current_processing_jid = None
                return True
                
            except (APITimeoutError, APIConnectionError) as e:
                logger.warning(
                    f"API 請求超時或連接錯誤: {jid}. 錯誤: {str(e)}. "
                    f"刪除 lock record 並重建 client 後重試..."
                )
                self.metadata_repo.delete_lock_record(jid)
                lock_inserted = False
                self._rebuild_extractor()
                continue
                
            except Exception as e:
                logger.error(f"處理判決時發生錯誤，跳過此判決: {jid}. 錯誤: {str(e)}")
                if lock_inserted:
                    self.metadata_repo.delete_lock_record(jid)
                self.current_processing_jid = None
                return False

