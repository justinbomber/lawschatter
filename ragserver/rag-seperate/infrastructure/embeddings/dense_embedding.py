import asyncio
from typing import List
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from domain.interfaces import IEmbeddingProvider
from config.settings import Settings


class DenseEmbeddingProvider(IEmbeddingProvider):
    def __init__(self, settings: Settings):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.google_ai.model,
            google_api_key=settings.google_ai.api_key,
        )
    
    async def embed_query(self, text: str) -> List[float]:
        return await asyncio.to_thread(self.embeddings.embed_query, text)
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return await asyncio.to_thread(self.embeddings.embed_documents, texts)

