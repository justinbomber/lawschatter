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
    GrokSummaryExtractor,
    FileSchemaProvider,
    MD5HashGenerator,
    DefaultSummaryDecomposer,
)
from ..application import ExtractSummaryUseCase, ExportJudgmentSummaryToJsonUseCase

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
        
        if self.config.ai_provider == "grok":
            logger.info("使用 Grok AI 服務")
            http_client = httpx.Client(
                timeout=httpx.Timeout(
                    connect=30.0,
                    read=self.config.xai_service.timeout,
                    write=30.0,
                    pool=30.0
                )
            )
            
            grok_client = OpenAI(
                api_key=self.config.xai_service.api_key,
                base_url=self.config.xai_service.base_url,
                http_client=http_client,
                max_retries=0
            )
            
            extractor = GrokSummaryExtractor(
                grok_client,
                self.config.xai_service.model,
                self.config.xai_service.reasoning_effort,
                self.config.xai_service.timeout,
                max_wait_time=300,
                max_retries=5
            )
        else:
            logger.info("使用 OpenAI 服務")
            http_client = httpx.Client(
                timeout=httpx.Timeout(
                    connect=30.0,
                    read=self.config.openai_service.timeout,
                    write=30.0,
                    pool=30.0
                )
            )
            
            openai_client = OpenAI(
                api_key=self.config.openai_service.api_key,
                http_client=http_client,
                max_retries=0
            )
            
            extractor = OpenAISummaryExtractor(
                openai_client,
                self.config.openai_service.model,
                self.config.openai_service.reasoning_effort,
                self.config.openai_service.timeout,
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
            hash_generator=hash_generator,
            sleep_interval=self.config.process.sleep_interval,
        )

        use_case.execute()

        # use_case_json=ExportJudgmentSummaryToJsonUseCase(
        #     judgment_repo=judgment_repo,
        #     extractor=extractor,
        #     schema_provider=schema_provider,
        #     output_dir=self.config.output_dir
        # )

        # use_case_json.execute([])
        
        return 0

