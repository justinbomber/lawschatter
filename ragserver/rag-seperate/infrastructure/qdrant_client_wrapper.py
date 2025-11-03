from qdrant_client import AsyncQdrantClient, models
from domain.interfaces import IQdrantClient
from config.settings import Settings


class QdrantClientWrapper(IQdrantClient):
    def __init__(self, settings: Settings):
        self.client = AsyncQdrantClient(url=settings.qdrant.url)
    
    async def query_points(self, **kwargs) -> models.QueryResponse:
        return await self.client.query_points(**kwargs)
    
    async def get_collections(self):
        return await self.client.get_collections()
    
    async def get_collection(self, collection_name: str):
        return await self.client.get_collection(collection_name)
    
    async def scroll(self, **kwargs):
        return await self.client.scroll(**kwargs)

