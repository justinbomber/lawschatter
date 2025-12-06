import logging
import httpx
from openai import OpenAI
from ..config import OpenAIServiceConfig
from .openai_service import OpenAIMetadataExtractor

logger = logging.getLogger(__name__)


class OpenAIClientFactory:
    
    def __init__(self, config: OpenAIServiceConfig, timeout: int = 600):
        self.config = config
        self.timeout = timeout
    
    def create_client(self) -> OpenAI:
        logger.info("建立新的 OpenAI client")
        
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
        
        client = OpenAI(
            api_key=self.config.api_key,
            http_client=http_client,
            max_retries=3
        )
        
        return client
    
    def create_extractor(self) -> OpenAIMetadataExtractor:
        client = self.create_client()
        
        extractor = OpenAIMetadataExtractor(
            client,
            self.config.model,
            timeout=self.timeout
        )
        
        return extractor

