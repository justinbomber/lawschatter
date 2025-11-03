import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from qdrant_client import models
from domain.interfaces import ISearchService, IEmbeddingProvider, IQdrantClient
from config.settings import Settings


logger = logging.getLogger(__name__)


@dataclass
class SearchConfig:
    collection: str
    mode: str = "hybrid"
    query_text: str = None
    dense_name: str = "dense"
    sparse_name: str = "bm25"
    filter: models.Filter = None
    limit: int = 10
    offset: int = None
    score_threshold: float = None
    with_vectors: bool = False
    use_branch_filters: bool = False


class SearchService(ISearchService):
    def __init__(
        self,
        dense_provider: IEmbeddingProvider,
        sparse_provider: IEmbeddingProvider,
        settings: Settings
    ):
        self.dense_embeddings = dense_provider
        self.sparse_embeddings = sparse_provider
        self.settings = settings
    
    async def search(self, client: IQdrantClient, config: SearchConfig) -> models.QueryResponse:
        if not config.query_text:
            raise ValueError("需要提供 query_text")
        
        mode = config.mode.lower()
        
        if mode == "dense":
            return await self._search_dense(client, config)
        elif mode == "sparse":
            return await self._search_sparse(client, config)
        elif mode == "hybrid":
            return await self._search_hybrid(client, config)
        else:
            raise ValueError("mode 只能是 'dense'、'sparse' 或 'hybrid'")
    
    async def _search_dense(self, client: IQdrantClient, config: SearchConfig) -> models.QueryResponse:
        vector = await self.dense_embeddings.embed_query(config.query_text)
        return await client.query_points(
            collection_name=config.collection,
            query=vector,
            using=config.dense_name,
            query_filter=config.filter,
            limit=config.limit,
            offset=config.offset,
            with_vectors=config.with_vectors,
            score_threshold=config.score_threshold,
        )
    
    async def _search_sparse(self, client: IQdrantClient, config: SearchConfig) -> models.QueryResponse:
        sparse_vector = await self.sparse_embeddings.embed_query(config.query_text)
        query = models.SparseVector(
            indices=sparse_vector.indices,
            values=sparse_vector.values,
        )
        return await client.query_points(
            collection_name=config.collection,
            query=query,
            using=config.sparse_name,
            query_filter=config.filter,
            limit=config.limit,
            offset=config.offset,
            with_vectors=config.with_vectors,
            score_threshold=config.score_threshold,
        )
    
    async def _search_hybrid(self, client: IQdrantClient, config: SearchConfig) -> models.QueryResponse:
        sparse_vector = await self.sparse_embeddings.embed_query(config.query_text)
        sparse_query = models.SparseVector(
            indices=sparse_vector.indices,
            values=sparse_vector.values,
        )
        
        dense_vector = await self.dense_embeddings.embed_query(config.query_text)
        
        prefetch = [
            models.Prefetch(
                query=dense_vector,
                using=config.dense_name,
                filter=config.filter if config.use_branch_filters else None,
                limit=max(config.limit * 5, 100),
            ),
            models.Prefetch(
                query=sparse_query,
                using=config.sparse_name,
                filter=config.filter if config.use_branch_filters else None,
                limit=max(config.limit * 5, 100),
            ),
        ]
        
        fusion_query = models.FusionQuery(fusion=models.Fusion.DBSF)
        
        return await client.query_points(
            collection_name=config.collection,
            prefetch=prefetch,
            query=fusion_query,
            query_filter=None if config.use_branch_filters else config.filter,
            limit=config.limit,
            offset=config.offset,
            with_vectors=config.with_vectors,
            score_threshold=config.score_threshold,
        )
    
    def flatten_points(self, response: models.QueryResponse) -> List[Dict[str, Any]]:
        results = []
        for point in response.points or []:
            results.append({
                "id": point.id,
                "score": point.score,
                "payload": point.payload
            })
        return results

