import logging
import httpx
from supabase import create_client
from openai import OpenAI
from ..config import AppConfig
from ..infrastructure import (
    SupabaseJudgmentRepository,
    SupabaseMetadataRepository,
    SupabaseSummaryRepository,
    OpenAISummaryExtractor,
    FileSchemaProvider,
    MD5HashGenerator,
    DefaultSummaryDecomposer,
)
from ..application import ExtractSummaryUseCase

logger = logging.getLogger(__name__)


class CLI:
    
    def __init__(self, config: AppConfig):
        self.config = config
    
    def run(self) -> int:
        logger.info("初始化服務")
        
        supabase_client = create_client(
            self.config.database.supabase_url,
            self.config.database.supabase_key,
        )
        
        http_client = httpx.Client(
            timeout=httpx.Timeout(
                connect=30.0,
                read=self.config.ai_service.timeout,
                write=30.0,
                pool=30.0
            )
        )
        openai_client = OpenAI(
            api_key=self.config.ai_service.openai_api_key,
            http_client=http_client
        )
        
        judgment_repo = SupabaseJudgmentRepository(
            supabase_client, 
            self.config.database.schema_name
        )
        
        metadata_repo = SupabaseMetadataRepository(
            supabase_client, 
            self.config.database.schema_name
        )
        
        summary_repo = SupabaseSummaryRepository(
            supabase_client, 
            self.config.database.schema_name
        )
        
        extractor = OpenAISummaryExtractor(
            openai_client,
            self.config.ai_service.model,
            self.config.ai_service.reasoning_effort,
            self.config.ai_service.timeout,
        )
        
        schema_provider = FileSchemaProvider(
            self.config.schema.schema_file_path
        )
        
        hash_generator = MD5HashGenerator()
        
        decomposer = DefaultSummaryDecomposer(hash_generator)
        
        use_case = ExtractSummaryUseCase(
            judgment_repo=judgment_repo,
            metadata_repo=metadata_repo,
            summary_repo=summary_repo,
            extractor=extractor,
            schema_provider=schema_provider,
            decomposer=decomposer,
            sleep_interval=self.config.process.sleep_interval,
        )
        
        use_case.execute()
        
        return 0

