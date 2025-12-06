import logging
import httpx
from supabase import create_client
from openai import OpenAI
from ..config import AppConfig
from ..infrastructure import (
    SupabaseJudgmentRepository,
    SupabaseMetadataRepository,
    OpenAIMetadataExtractor,
    OpenAIClientFactory,
    GrokMetadataExtractor,
    FileSchemaProvider,
    AdjudicateJudgmentFilter,
)
from ..application import ExtractMetadataUseCase, ExportJudgmentToJsonUseCase

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
        
        extractor_factory = None
        
        if self.config.ai_provider == "grok":
            logger.info("使用 Grok AI 服務")
            timeout = httpx.Timeout(600.0, connect=60.0)
            http_client = httpx.Client(timeout=timeout)
            
            grok_client = OpenAI(
                api_key=self.config.xai_service.api_key,
                base_url=self.config.xai_service.base_url,
                http_client=http_client,
                max_retries=0
            )
            
            extractor = GrokMetadataExtractor(
                grok_client,
                self.config.xai_service.model,
                timeout=600,
                max_wait_time=300,
                max_retries=5
            )
        else:
            logger.info("使用 OpenAI 服務")
            
            openai_factory = OpenAIClientFactory(
                self.config.openai_service,
                timeout=600
            )
            
            extractor = openai_factory.create_extractor()
            extractor_factory = openai_factory.create_extractor
        
        filter_service = AdjudicateJudgmentFilter()
        
        schema_provider = FileSchemaProvider(
            self.config.schema.schema_file_path
        )
        
        use_case = ExtractMetadataUseCase(
            judgment_repo=judgment_repo,
            metadata_repo=metadata_repo,
            extractor=extractor,
            filter_service=filter_service,
            schema_provider=schema_provider,
            target_titles=self.config.process.target_titles,
            include_adjudicate=self.config.process.include_adjudicate,
            extractor_factory=extractor_factory,
        )

        use_case_json = ExportJudgmentToJsonUseCase(
            judgment_repo=judgment_repo,
            extractor=extractor,
            schema_provider=schema_provider,
            output_dir=self.config.output_dir
        )
        
        total_processed = use_case.execute()
        # total_processed = use_case_json.execute(["TPHM,113,上訴,6418,20250617,1"])
        # total_processed = use_case_json.execute(["MLDM,113,訴,549,20250526,1","TPHM,113,上訴,6418,20250617,1"])
        # total_processed = use_case._process_judgment("TPHM,113,上訴,6418,20250617,1", "20250617")
        
        logger.info(f"執行完成，總共處理 {total_processed} 筆判決")
        return total_processed
