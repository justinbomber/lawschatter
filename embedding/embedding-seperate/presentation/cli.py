import logging
from supabase import create_client
from ..config import AppConfig
from ..infrastructure import (
    SupabaseSummaryRepository,
    SupabaseMetadataRepository,
    QdrantHybridVectorStore,
)
from ..application import EmbedDocumentsUseCase

logger = logging.getLogger(__name__)


class CLI:
    
    def __init__(self, config: AppConfig):
        self.config = config
    
    def run(self) -> tuple[int, int]:
        logger.info("初始化服務")
        
        supabase_client = create_client(
            self.config.database.supabase_url,
            self.config.database.supabase_key,
        )
        
        summary_repo = SupabaseSummaryRepository(
            supabase_client,
            self.config.database.schema_name
        )
        
        metadata_repo = SupabaseMetadataRepository(
            supabase_client,
            self.config.database.schema_name
        )
        
        vector_store = QdrantHybridVectorStore(
            qdrant_url=self.config.vector_store.qdrant_url,
            collection_name=self.config.vector_store.collection_name,
            embedding_api_key=self.config.vector_store.embedding_api_key,
            stopwords_path=self.config.tokenizer.stopwords_path,
            dict_path=self.config.tokenizer.dict_path,
            embedding_model=self.config.vector_store.embedding_model,
        )
        
        use_case = EmbedDocumentsUseCase(
            summary_repo=summary_repo,
            metadata_repo=metadata_repo,
            vector_store=vector_store,
        )
        
        total_dates, total_jids = use_case.execute()
        
        logger.info(f"執行完成，處理 {total_dates} 個日期，{total_jids} 個判決")
        return total_dates, total_jids

