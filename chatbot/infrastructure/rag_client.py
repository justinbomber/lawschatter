import logging
import httpx
from typing import Dict, Any
from domain.interfaces import IRAGClient
from entities.models import RAGSearchRequest, RAGSearchResponse
from config.settings import Settings

logger = logging.getLogger(__name__)


class RAGClient(IRAGClient):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.rag_server.url
        self.timeout = settings.rag_server.timeout
    
    async def search(self, request: RAGSearchRequest) -> RAGSearchResponse:
        url = f"{self.base_url}/search"
        
        payload = {
            "collection": request.collection,
            "query_text": request.query_text,
            "mode": request.mode,
            "limit": request.limit,
            "score_threshold": request.score_threshold
        }
        
        logger.info(f"呼叫 RAG 搜尋服務: {url}")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        
        return RAGSearchResponse(**data)
    
    async def health_check(self) -> bool:
        url = f"{self.base_url}/health"
        
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url)
            return response.status_code == 200

