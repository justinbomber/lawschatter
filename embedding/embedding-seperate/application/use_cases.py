import logging
from typing import List
from ..domain import (
    SummaryRepository,
    MetadataRepository,
    VectorStore,
    EmbeddingDocument,
)

logger = logging.getLogger(__name__)


class EmbedDocumentsUseCase:
    
    def __init__(
        self,
        summary_repo: SummaryRepository,
        metadata_repo: MetadataRepository,
        vector_store: VectorStore,
    ):
        self.summary_repo = summary_repo
        self.metadata_repo = metadata_repo
        self.vector_store = vector_store
    
    def execute(self) -> tuple[int, int]:
        logger.info("開始執行文件嵌入流程")
        
        total_date_count = 0
        total_jid_count = 0
        
        dates = self.summary_repo.get_all_dates_desc()
        logger.info(f"找到 {len(dates)} 個獨特日期")
        
        for jdate in dates:
            processed_count = self._process_date(jdate)
            if processed_count > 0:
                total_date_count += 1
                total_jid_count += processed_count
        
        logger.info(f"嵌入完成，處理 {total_date_count} 個日期，{total_jid_count} 個判決")
        return total_date_count, total_jid_count
    
    def _process_date(self, jdate: str) -> int:
        logger.info(f"處理日期: {jdate}")
        
        unprocessed_jids = self.summary_repo.get_unprocessed_jids_by_date(jdate)
        
        if not unprocessed_jids:
            logger.info(f"日期 {jdate} 無待處理的判決")
            return 0
        
        logger.info(f"找到 {len(unprocessed_jids)} 個待處理的判決")
        
        processed_count = 0
        for jid in unprocessed_jids:
            if self._process_jid(jid):
                processed_count += 1
        
        return processed_count
    
    def _process_jid(self, jid: str) -> bool:
        logger.info(f"處理判決: {jid}")
        
        summaries = self.summary_repo.get_summaries_by_jid(jid)
        if not summaries:
            logger.warning(f"判決 {jid} 沒有 summary 記錄")
            return False
        
        metadata = self.metadata_repo.get_metadata_by_jid(jid)
        if not metadata:
            logger.warning(f"判決 {jid} 沒有 metadata 記錄")
            return False
        
        documents = self._build_documents(summaries, metadata)
        
        if not documents:
            logger.warning(f"判決 {jid} 無法建立文件")
            return False
        
        before_count = self.vector_store.get_collection_count()
        self.vector_store.add_documents(documents)
        after_count = self.vector_store.get_collection_count()
        
        logger.info(f"加入 {after_count - before_count} 個文件到向量資料庫")
        
        self.summary_repo.mark_as_embedded(jid)
        
        logger.info(f"完成處理判決 {jid}，共 {len(documents)} 個文件")
        return True
    
    def _build_documents(
        self, 
        summaries: List, 
        metadata
    ) -> List[EmbeddingDocument]:
        documents = []
        
        for summary in summaries:
            doc = EmbeddingDocument.from_summary_and_metadata(
                summary, 
                metadata
            )
            documents.append(doc)
        
        return documents

