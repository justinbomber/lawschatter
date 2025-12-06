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
    OpenAIClientFactory,
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
        
        extractor_factory = None
        
        if self.config.ai_provider == "grok":
            logger.info("使用 Grok AI 服務")
            
            timeout = httpx.Timeout(600.0, connect=60.0)
            limits = httpx.Limits(
                max_keepalive_connections=20,
                max_connections=50,
                keepalive_expiry=30.0
            )
            http_client = httpx.Client(
                timeout=timeout,
                limits=limits,
                http2=True
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
                timeout=600,
                max_wait_time=300,
                max_retries=5
            )
        else:
            logger.info("使用 OpenAI 服務")
            
            openai_factory = OpenAIClientFactory(self.config.openai_service)
            extractor = openai_factory.create_extractor()
            extractor_factory = openai_factory.create_extractor
        
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
            extractor_factory=extractor_factory,
        )

        use_case.execute()

        # use_case_json=ExportJudgmentSummaryToJsonUseCase(
        #     judgment_repo=judgment_repo,
        #     extractor=extractor,
        #     schema_provider=schema_provider,
        #     output_dir=self.config.output_dir
        # )

        # use_case_json.execute(["TPHM,113,上訴,6418,20250617,1"])
        # use_case_json.execute(["MLDM,113,訴,549,20250526,1","TPHM,113,上訴,6418,20250617,1"])
        
        return 0
