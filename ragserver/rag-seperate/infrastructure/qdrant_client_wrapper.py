from qdrant_client import QdrantClient, models
from domain.interfaces import IQdrantClient
from config.settings import Settings


class QdrantClientWrapper(IQdrantClient):
    def __init__(self, settings: Settings):
        self.client = QdrantClient(url=settings.qdrant.url)
    
    def query_points(self, **kwargs) -> models.QueryResponse:
        return self.client.query_points(**kwargs)
    
    def get_collections(self):
        return self.client.get_collections()
    
    def get_collection(self, collection_name: str):
        return self.client.get_collection(collection_name)

