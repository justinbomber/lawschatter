import logging
import httpx
import json
from typing import Dict, Any, AsyncGenerator
from domain.interfaces import IRAGClient
from entities.models import RAGSearchRequest, RAGSearchResponse
from config.settings import Settings

logger = logging.getLogger(__name__)


class RAGClient(IRAGClient):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.rag_server.url
        self.timeout = settings.rag_server.timeout
    
    async def search(self, request: RAGSearchRequest, token: str, user_id: str) -> RAGSearchResponse:
        url = f"{self.base_url}/search"
        
        payload = {
            "query_text": request.query_text,
            "conversation_id": request.conversation_id,
            "streaming": False,
            "search_mode": request.search_mode
        }
        
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        logger.info(f"呼叫 RAG 搜尋服務: {url}")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        
        return RAGSearchResponse(**data)
    
    async def search_stream(self, request: RAGSearchRequest, token: str, user_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        url = f"{self.base_url}/search"
        
        payload = {
            "query_text": request.query_text,
            "conversation_id": request.conversation_id,
            "streaming": True,
            "search_mode": request.search_mode
        }
        
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        logger.info(f"呼叫 RAG 搜尋服務 (串流): {url}")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        chunk = json.loads(data_str)
                        yield chunk
    
    async def health_check(self) -> bool:
        url = f"{self.base_url}/health"
        
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url)
            return response.status_code == 200

