import logging
import json
import time
from typing import List
from ..domain import (
    SummaryRepository,
    MetadataRepository,
    VectorStore,
    EmbeddingDocument,
    JudgmentSearchDocument,
)

logger = logging.getLogger(__name__)


class EmbedDocumentsUseCase:
    
    def __init__(
        self,
        summary_repo: SummaryRepository,
        metadata_repo: MetadataRepository,
        vector_store: VectorStore,
        use_v2: bool = False,
    ):
        self.summary_repo = summary_repo
        self.metadata_repo = metadata_repo
        self.vector_store = vector_store
        self.use_v2 = use_v2
        
        if self.use_v2:
            logger.info("使用 V2 Schema（一判決一 point、named vectors）")
            self.vector_store.create_v2_collection()
        else:
            logger.info("使用 V1 Schema（一判決多 points）")
    
    def execute(self) -> None:
        logger.info("開始執行文件嵌入流程")
        
        while True:
            unprocessed_jids = self.summary_repo.get_unprocessed_jids_by_date("")
            
            if not unprocessed_jids:
                logger.info("沒有未嵌入的判決，等待 2 分鐘後再次掃描")
                time.sleep(120)
                continue
            
            logger.info(f"找到 {len(unprocessed_jids)} 個待處理的判決，開始處理")
            
            processed_count = 0
            for jid in unprocessed_jids:
                if self._process_jid(jid):
                    processed_count += 1
            
            logger.info(f"本輪處理完成，處理了 {processed_count} 個判決")
    
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
        
        if self.use_v2:
            return self._process_jid_v2(jid, summaries, metadata)
        else:
            return self._process_jid_v1(jid, summaries, metadata)
    
    def _process_jid_v1(self, jid: str, summaries: List, metadata) -> bool:
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
    
    def _process_jid_v2(self, jid: str, summaries: List, metadata) -> bool:
        judgment_doc = JudgmentSearchDocument.from_summaries_and_metadata(
            summaries, metadata
        )
        
        self.vector_store.upsert_judgment(judgment_doc)
        
        self.summary_repo.mark_as_embedded(jid)
        
        logger.info(f"完成處理判決 {jid}（V2 單一 point）")
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

