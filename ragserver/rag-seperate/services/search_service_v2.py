import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from qdrant_client import models
from domain.interfaces import ISearchService, IEmbeddingProvider, IQdrantClient, PrefetchSpec, QuerySpec
from config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class SearchConfigV2:
    collection: str
    query_conditions: List[Dict[str, Any]]
    payload_filter: models.Filter = None
    limit: int = 100
    fusion: str = "rrf"


class SearchServiceV2(ISearchService):
    def __init__(
        self,
        dense_provider: IEmbeddingProvider,
        sparse_provider: IEmbeddingProvider,
        settings: Settings
    ):
        self.dense_embeddings = dense_provider
        self.sparse_embeddings = sparse_provider
        self.settings = settings
    
    async def search(self, client: IQdrantClient, config: Any) -> models.QueryResponse:
        if not isinstance(config, SearchConfigV2):
            raise ValueError("V2 SearchService 需要 SearchConfigV2")
        
        return await self._search_v2(client, config)
    
    async def _search_v2(self, client: IQdrantClient, config: SearchConfigV2) -> models.QueryResponse:
        if not config.query_conditions:
            raise ValueError("至少需要一個查詢條件")
        
        hard_conditions = [qc for qc in config.query_conditions if qc.get('is_hard', False)]
        soft_conditions = [qc for qc in config.query_conditions if not qc.get('is_hard', False)]
        
        logger.info(f"硬條件: {len(hard_conditions)} 個")
        logger.info(f"軟條件: {len(soft_conditions)} 個")
        
        prefetch_specs = []
        
        for hc in hard_conditions:
            query_text = hc.get('query_text', '')
            field_name = hc.get('field_name', 'summary')
            
            if not query_text:
                continue
            
            dense_vector = await self.dense_embeddings.embed_query(query_text)
            sparse_vector = await self.sparse_embeddings.embed_query(query_text)
            
            dense_using = f"{field_name}_dense"
            sparse_using = f"{field_name}_sparse"
            
            prefetch_specs.append(
                PrefetchSpec(
                    query=dense_vector,
                    using=dense_using,
                    limit=2000,
                    filter=config.payload_filter
                )
            )
            
            prefetch_specs.append(
                PrefetchSpec(
                    query=models.SparseVector(
                        indices=sparse_vector.indices,
                        values=sparse_vector.values
                    ),
                    using=sparse_using,
                    limit=2000,
                    filter=config.payload_filter
                )
            )
        
        if soft_conditions:
            main_soft = soft_conditions[0]
            query_text = main_soft.get('query_text', '')
            field_name = main_soft.get('field_name', 'summary')
            
            dense_vector = await self.dense_embeddings.embed_query(query_text)
            
            main_query = QuerySpec(
                query=dense_vector,
                using=f"{field_name}_dense",
                limit=config.limit,
                filter=config.payload_filter
            )
        else:
            main_query = None
        
        return await client.query_with_prefetch(
            collection_name=config.collection,
            prefetch_queries=prefetch_specs,
            main_query=main_query,
            limit=config.limit,
            filter=config.payload_filter,
            fusion=config.fusion
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

