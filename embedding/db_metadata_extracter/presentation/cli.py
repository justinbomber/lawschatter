import logging
import httpx
from supabase import create_client
from openai import OpenAI
from ..config import AppConfig
from ..infrastructure import (
    SupabaseJudgmentRepository,
    SupabaseMetadataRepository,
    OpenAIMetadataExtractor,
    FileSchemaProvider,
    AdjudicateJudgmentFilter,
)
from ..application import ExtractMetadataUseCase

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
        
        # 配置 OpenAI 客戶端超時時間（10 分鐘）
        timeout = httpx.Timeout(600.0, connect=60.0)
        http_client = httpx.Client(timeout=timeout)
        
        openai_client = OpenAI(
            api_key=self.config.ai_service.openai_api_key,
            http_client=http_client,
            max_retries=0  # 禁用內建重試，使用我們自己的重試邏輯
        )
        
        judgment_repo = SupabaseJudgmentRepository(
            supabase_client, 
            self.config.database.schema_name
        )
        
        metadata_repo = SupabaseMetadataRepository(
            supabase_client, 
            self.config.database.schema_name
        )
        
        extractor = OpenAIMetadataExtractor(
            openai_client, 
            self.config.ai_service.model,
            timeout=600,  # 10 分鐘超時
            max_wait_time=300  # 最大等待時間 5 分鐘
        )
        
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
        )
        
        total_processed = use_case.execute()
        
        logger.info(f"執行完成，總共處理 {total_processed} 筆判決")
        return total_processed
