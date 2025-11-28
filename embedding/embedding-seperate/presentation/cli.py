import logging
import os
from supabase import create_client
from ..config import AppConfig
from ..infrastructure import (
    SupabaseSummaryRepository,
    SupabaseMetadataRepository,
    QdrantHybridVectorStore,
    SupabaseSummaryMultivectorRepository
)
from ..application import EmbedDocumentsUseCase, EmbedJudgmentPointsUseCase

logger = logging.getLogger(__name__)


class CLI:
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.mode = config.vector_store.embedding_mode
    
    def run(self) -> tuple[int, int]:
        logger.info(f"初始化服務，模式: {self.mode}")
        
        supabase_client = create_client(
            self.config.database.supabase_url,
            self.config.database.supabase_key,
        )
        
        summary_repo = SupabaseSummaryRepository(
            supabase_client,
            self.config.database.schema_name
        )

        summary_multivector_repo = SupabaseSummaryMultivectorRepository(
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
        
        if self.mode == "judgment-point":
            logger.info("使用判決級別嵌入模式")
            vector_store.recreate_judgment_collection(
                self.config.vector_store.judgment_collection_name
            )
            use_case = EmbedJudgmentPointsUseCase(
                summary_repo=summary_multivector_repo,
                metadata_repo=metadata_repo,
                vector_store=vector_store,
                target_collection=self.config.vector_store.judgment_collection_name,
            )
        else:
            logger.info("使用區塊級別嵌入模式")
            use_case = EmbedDocumentsUseCase(
                summary_repo=summary_repo,
                metadata_repo=metadata_repo,
                vector_store=vector_store,
            )
        
        use_case.execute()
        
        return 0, 0

