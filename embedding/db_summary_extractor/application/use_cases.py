import logging
import signal
import sys
import time
from typing import List, Dict, Optional, Callable
from openai import APITimeoutError, APIConnectionError
from ..domain import (
    JudgmentRepository,
    MetadataRepository,
    SummaryRepository,
    SummaryExtractor,
    SchemaProvider,
    SummaryDecomposer,
    HashGenerator,
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
        hash_generator: HashGenerator,
        sleep_interval: int = 60,
        extractor_factory: Optional[Callable[[], SummaryExtractor]] = None,
    ):
        self.judgment_repo = judgment_repo
        self.metadata_repo = metadata_repo
        self.summary_repo = summary_repo
        self.extractor = extractor
        self.schema_provider = schema_provider
        self.decomposer = decomposer
        self.hash_generator = hash_generator
        self.sleep_interval = sleep_interval
        self.extractor_factory = extractor_factory
        self.current_lock_point_id: Optional[str] = None
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame) -> None:
        logger.warning(f"接收到停止信號 {signum}，準備清理並退出")
        if self.current_lock_point_id:
            logger.info(f"清理當前處理的 lock: {self.current_lock_point_id}")
            self.summary_repo.delete_lock_record(self.current_lock_point_id)
        logger.info("清理完成，退出程式")
        sys.exit(0)
    
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
    
    def _rebuild_extractor(self) -> None:
        if self.extractor_factory:
            logger.info("重建 extractor 和 OpenAI client")
            self.extractor = self.extractor_factory()
    
    def _process_judgment(self, jid: str, jdate: str) -> bool:
        logger.info(f"處理判決: {jid}")
        
        if self.summary_repo.has_summary_for_jid(jid):
            logger.info(f"跳過判決 {jid}（已存在 summary 或正在被處理）")
            return False
        
        lock_point_id = self.hash_generator.generate(jid)
        self.current_lock_point_id = lock_point_id
        lock_inserted = False
        
        while True:
            if not lock_inserted:
                self.summary_repo.insert_lock_record(jid, jdate, lock_point_id)
                lock_inserted = True
            
            judgment = self.judgment_repo.get_judgment(jid)
            schema = self.schema_provider.get_schema()
            
            try:
                extraction_result = self.extractor.extract(judgment, schema)
                
                summary_records = self.decomposer.decompose(
                    jid, 
                    jdate, 
                    extraction_result
                )
                
                for record in summary_records:
                    self.summary_repo.save_summary(record)
                
                self.summary_repo.delete_lock_record(lock_point_id)
                
                logger.info(f"成功處理並插入 {len(summary_records)} 筆 summary: {jid}")
                self.current_lock_point_id = None
                return True
                
            except (APITimeoutError, APIConnectionError) as e:
                logger.warning(
                    f"API 請求超時或連接錯誤: {jid}. 錯誤: {str(e)}. "
                    f"刪除 lock record 並重建 client 後重試..."
                )
                self.summary_repo.delete_lock_record(lock_point_id)
                lock_inserted = False
                self._rebuild_extractor()
                continue
                
            except Exception as e:
                logger.error(f"處理判決時發生錯誤，跳過此判決: {jid}. 錯誤: {str(e)}")
                if lock_inserted:
                    self.summary_repo.delete_lock_record(lock_point_id)
                self.current_lock_point_id = None
                return False
