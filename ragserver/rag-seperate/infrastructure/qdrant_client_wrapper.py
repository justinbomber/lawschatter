from typing import List, Optional
from qdrant_client import AsyncQdrantClient, models
from domain.interfaces import IQdrantClient, PrefetchSpec, QuerySpec
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
    
    async def query_with_prefetch(
        self,
        collection_name: str,
        prefetch_queries: List[PrefetchSpec],
        main_query: Optional[QuerySpec],
        limit: int,
        filter: Optional[models.Filter] = None,
        fusion: str = "rrf"
    ) -> models.QueryResponse:
        prefetch_list = []
        for pf in prefetch_queries:
            prefetch_list.append(
                models.Prefetch(
                    query=pf.query,
                    using=pf.using,
                    limit=pf.limit,
                    filter=pf.filter
                )
            )
        
        if main_query is None:
            if fusion.lower() == "rrf":
                fusion_query = models.FusionQuery(fusion=models.Fusion.RRF)
            else:
                fusion_query = models.FusionQuery(fusion=models.Fusion.DBSF)
            
            return await self.client.query_points(
                collection_name=collection_name,
                prefetch=prefetch_list,
                query=fusion_query,
                query_filter=filter,
                limit=limit
            )
        else:
            return await self.client.query_points(
                collection_name=collection_name,
                prefetch=prefetch_list,
                query=main_query.query,
                using=main_query.using,
                query_filter=main_query.filter or filter,
                limit=limit
            )

