# qdrant_dynamic_query.py
from __future__ import annotations
from typing import Optional, Dict, Any, List, Union, Sequence
from dataclasses import dataclass
from qdrant_client import QdrantClient, models

# -------------------------
# Public types
# -------------------------
FilterSpec = Dict[str, Any]  # {"must":[...], "must_not":[...], "should":[...]}


@dataclass
class SearchConfig:
    """搜尋配置，簡化參數傳遞"""
    collection: str
    mode: str = "hybrid"  # "dense" | "sparse" | "hybrid"
    
    # 文字查詢（若提供，會自動轉向量）
    query_text: Optional[str] = None
    
    # 向量資料
    dense_name: Optional[str] = "dense"
    sparse_name: Optional[str] = "bm25"
    
    # 篩選條件（統一入口）
    # 可傳：
    # - models.Filter（直接使用）
    # - 完整規格 dict：{"must": [...], "must_not": [...], "should": [...]}
    # - 簡寫 dict：{key: value} 等值過濾
    filter: Optional[Union[FilterSpec, models.Filter, Dict[str, Any]]] = None
    
    # 結果控制
    limit: int = 10
    offset: Optional[int] = None
    score_threshold: Optional[float] = None
    
    # 向量控制
    with_vectors: Union[bool, Sequence[str]] = False
    
    # 進階設定
    use_branch_filters: bool = False


# -------------------------
# Filter builders
# -------------------------
def build_filter(spec: Optional[FilterSpec]) -> Optional[models.Filter]:
    """將簡易 dict 規格轉為 Qdrant Filter"""
    if spec is None or isinstance(spec, models.Filter):
        return spec

    def _build_condition(d: Dict[str, Any]) -> models.Condition:
        if "has_id" in d:
            return models.HasIdCondition(has_id=d["has_id"])
        
        if "key" not in d:
            raise ValueError("條件需要提供 'key'")
        
        key = d["key"]
        
        if "is_null" in d:
            return models.IsNullCondition(key=key)
        
        if "exists" in d:
            # exists == 非 null
            return models.Filter(must_not=[models.IsNullCondition(key=key)])
        
        if "match" in d:
            match = d["match"]
            if "any" in match:
                return models.FieldCondition(key=key, match=models.MatchAny(any=match["any"]))
            if "value" in match:
                return models.FieldCondition(key=key, match=models.MatchValue(value=match["value"]))
        
        if "range" in d:
            r = d["range"]
            return models.FieldCondition(
                key=key,
                range=models.Range(
                    gte=r.get("gte"), lte=r.get("lte"),
                    gt=r.get("gt"), lt=r.get("lt")
                )
            )
        
        raise ValueError(f"不支援的篩選條件: {d}")

    # 處理 must/must_not/should 邏輯
    must = [_build_condition(x) for x in spec.get("must", [])]
    must_not = [_build_condition(x) for x in spec.get("must_not", [])]
    should = [_build_condition(x) for x in spec.get("should", [])]
    
    return models.Filter(must=must, must_not=must_not, should=should)


def to_filter_spec(conditions: Dict[str, Any]) -> FilterSpec:
    """把 {key: value} 轉為等值查詢的 FilterSpec"""
    return {"must": [{"key": k, "match": {"value": v}} for k, v in conditions.items()]}


# -------------------------
# Filter ensure helper
# -------------------------
def _ensure_filter(filter_like: Optional[Union[FilterSpec, models.Filter, Dict[str, Any]]]) -> Optional[models.Filter]:
    """統一將輸入轉為 Qdrant models.Filter。支援：
    - None → None
    - models.Filter → 原樣
    - {key:value} → 轉成等值 must 條件
    - {"must": [...], ...} → 視為完整 FilterSpec 交給 build_filter
    """
    if filter_like is None:
        return None
    if isinstance(filter_like, models.Filter):
        return filter_like
    if isinstance(filter_like, dict):
        # 判斷是否為簡寫（沒有 must/must_not/should）
        if not any(k in filter_like for k in ("must", "must_not", "should")):
            return build_filter(to_filter_spec(filter_like))
        return build_filter(filter_like)  # 當作完整 FilterSpec
    # 其他型別不支援
    raise TypeError("filter 需為 models.Filter 或 dict")

# -------------------------
# Text to vector
# -------------------------
def text_to_dense_vector(text: str) -> List[float]:
    """將文字轉為語意向量"""
    try:
        from hybrid_embed import dense_embeddings
        return dense_embeddings.embed_query(text)
    except ImportError:
        raise ImportError("無法導入 dense_embeddings，請確保 hybrid_embed.py 已正確配置")

def text_to_sparse_vector(text: str) -> models.SparseVector:
    """將文字轉為bm25向量"""
    try:
        from hybrid_embed import sparse_embeddings
        return sparse_embeddings.embed_query(text)
    except ImportError:
        raise ImportError("無法導入 sparse_embeddings，請確保 hybrid_embed.py 已正確配置")

# -------------------------
# OOP wrapper (optional)
# -------------------------
class QdrantSearcher:
    """
    封裝式 Qdrant 搜尋器：
    - 統一管理 client、collection、向量欄位與預設參數
    - 以 query_text 自動轉向量，提供 dense/sparse/hybrid 三種模式
    - 過濾器使用單一 filter 入口（支援簡寫與完整規格）
    """

    def __init__(
        self,
        client: QdrantClient,
        collection: str,
        *,
        dense_name: str = "dense",
        sparse_name: str = "bm25",
        use_branch_filters: bool = False,
        with_vectors: Union[bool, Sequence[str]] = False,
        score_threshold: Optional[float] = None,
    ) -> None:
        self.client = client
        self.collection = collection
        self.dense_name = dense_name
        self.sparse_name = sparse_name
        self.use_branch_filters = use_branch_filters
        self.with_vectors = with_vectors
        self.score_threshold = score_threshold

    def search(
        self,
        *,
        mode: str = "hybrid",
        query_text: str,
        filter: Optional[Union[FilterSpec, models.Filter, Dict[str, Any]]] = None,
        limit: int = 10,
        offset: Optional[int] = None,
    ) -> models.QueryResponse:
        if not query_text:
            raise ValueError("需要提供 query_text")
        q_filter = _ensure_filter(filter)
        if mode == "dense":
            return self._search_dense(query_text, q_filter, limit, offset)
        if mode == "sparse":
            return self._search_sparse(query_text, q_filter, limit, offset)
        if mode == "hybrid":
            return self._search_hybrid(query_text, q_filter, limit, offset)
        raise ValueError("mode 必須是 'dense'、'sparse' 或 'hybrid'")

    def _search_dense(
        self,
        text: str,
        q_filter: Optional[models.Filter],
        limit: int,
        offset: Optional[int],
    ) -> models.QueryResponse:
        return self.client.query_points(
            collection_name=self.collection,
            query=text_to_dense_vector(text),
            using=self.dense_name,
            query_filter=q_filter,
            limit=limit,
            offset=offset,
            with_vectors=self.with_vectors,
            score_threshold=self.score_threshold,
        )

    def _search_sparse(
        self,
        text: str,
        q_filter: Optional[models.Filter],
        limit: int,
        offset: Optional[int],
    ) -> models.QueryResponse:
        sp = text_to_sparse_vector(text)
        sv = models.SparseVector(indices=sp.indices, values=sp.values)
        return self.client.query_points(
            collection_name=self.collection,
            query=sv,
            using=self.sparse_name,
            query_filter=q_filter,
            limit=limit,
            offset=offset,
            with_vectors=self.with_vectors,
            score_threshold=self.score_threshold,
        )

    def _search_hybrid(
        self,
        text: str,
        q_filter: Optional[models.Filter],
        limit: int,
        offset: Optional[int],
    ) -> models.QueryResponse:
        sp = text_to_sparse_vector(text)
        sv = models.SparseVector(indices=sp.indices, values=sp.values)
        prefetch = [
            models.Prefetch(
                query=text_to_dense_vector(text),
                using=self.dense_name,
                filter=q_filter if self.use_branch_filters else None,
                limit=max(limit * 5, 100),
            ),
            models.Prefetch(
                query=sv,
                using=self.sparse_name,
                filter=q_filter if self.use_branch_filters else None,
                limit=max(limit * 5, 100),
            ),
        ]
        fusion_query = models.FusionQuery(fusion=models.Fusion.DBSF)
        return self.client.query_points(
            collection_name=self.collection,
            prefetch=prefetch,
            query=fusion_query,
            query_filter=None if self.use_branch_filters else q_filter,
            limit=limit,
            offset=offset,
            with_vectors=self.with_vectors,
            score_threshold=self.score_threshold,
        )

# -------------------------
# Core search functions
# -------------------------
def _search_dense(
    client: QdrantClient,
    config: SearchConfig,
    q_filter: Optional[models.Filter],
) -> models.QueryResponse:
    """執行 dense 向量搜尋"""
    return client.query_points(
        collection_name=config.collection,
        query=text_to_dense_vector(config.query_text),
        using=config.dense_name,
        query_filter=q_filter,
        limit=config.limit,
        offset=config.offset,
        with_vectors=config.with_vectors,
        score_threshold=config.score_threshold,
    )


def _search_sparse(
    client: QdrantClient,
    config: SearchConfig,
    q_filter: Optional[models.Filter],
) -> models.QueryResponse:
    """執行 sparse 向量搜尋"""
    sparse_vector = text_to_sparse_vector(config.query_text)
    query = models.SparseVector(
        indices=sparse_vector.indices,
        values=sparse_vector.values,
    )
    return client.query_points(
        collection_name=config.collection,
        query=query,
        using=config.sparse_name,
        query_filter=q_filter,
        limit=config.limit,
        offset=config.offset,
        with_vectors=config.with_vectors,
        score_threshold=config.score_threshold,
    )


def _search_hybrid(
    client: QdrantClient,
    config: SearchConfig,
    q_filter: Optional[models.Filter],
) -> models.QueryResponse:
    """執行 hybrid 搜尋 (DBSF 融合)"""
    sparse_vector = text_to_sparse_vector(config.query_text)
    sparse_query = models.SparseVector(
        indices=sparse_vector.indices,
        values=sparse_vector.values,
    )
    # 建構 prefetch
    prefetch = [
        models.Prefetch(
            query=text_to_dense_vector(config.query_text),
            using=config.dense_name,
            filter=q_filter if config.use_branch_filters else None,
            limit=max(config.limit * 5, 100),
        ),
        models.Prefetch(
            query=sparse_query,
            using=config.sparse_name,
            filter=q_filter if config.use_branch_filters else None,
            limit=max(config.limit * 5, 100),
        ),
    ]
    
    # 使用 DBSF 融合
    fusion_query = models.FusionQuery(fusion=models.Fusion.DBSF)
    
    return client.query_points(
        collection_name=config.collection,
        prefetch=prefetch,
        query=fusion_query,
        query_filter=None if config.use_branch_filters else q_filter,
        limit=config.limit,
        offset=config.offset,
        with_vectors=config.with_vectors,
        score_threshold=config.score_threshold,
    )


# -------------------------
# Main search function
# -------------------------
def search_qdrant(client: QdrantClient, config: SearchConfig) -> models.QueryResponse:
    """主要的搜尋函式，根據配置自動選擇搜尋模式"""
    if not config.query_text:
        raise ValueError("需要提供 query_text")

    # 建構 filter（單一入口）
    q_filter = _ensure_filter(config.filter)
    # 根據模式選擇搜尋函式
    mode = config.mode.lower()
    
    if mode == "dense":
        return _search_dense(client, config, q_filter)
    
    elif mode == "sparse":
        return _search_sparse(client, config, q_filter)
    
    elif mode == "hybrid":
        return _search_hybrid(client, config, q_filter)
    
    else:
        raise ValueError("mode 只能是 'dense'、'sparse' 或 'hybrid'")


# -------------------------
# Convenience functions
# -------------------------
def search_with_json(
    client: QdrantClient,
    collection: str,
    query_data: Dict[str, Any]
) -> models.QueryResponse:
    """使用 JSON 格式的查詢資料進行搜尋"""
    config = SearchConfig(
        collection=collection,
        **query_data
    )
    return search_qdrant(client, config)


# -------------------------
# Filter-only search
# -------------------------
def search_by_filter_only(
    client: QdrantClient,
    collection: str,
    filter: Optional[Union[FilterSpec, models.Filter, Dict[str, Any]]] = None,
    limit: int = 10,
    offset: Optional[int] = None,
    with_vectors: Union[bool, Sequence[str]] = False,
):
    """只使用 filter 進行查詢，不需要 query_text，直接返回 scroll 結果"""
    q_filter = _ensure_filter(filter)
    
    # 使用 scroll 方法來獲取符合 filter 條件的所有點
    # 直接返回 scroll 的結果 (points, next_page_offset)
    return client.scroll(
        collection_name=collection,
        scroll_filter=q_filter,
        limit=limit,
        offset=offset,
        with_vectors=with_vectors,
        with_payload=True,
    )


# -------------------------
# Rerank integration
# -------------------------
def search_with_rerank(
    client: QdrantClient,
    config: SearchConfig,
    reranker=None,
    rerank_top_n: int = 10
) -> models.QueryResponse:
    """執行搜尋，可選使用 reranker 重新排序"""
    response = search_qdrant(client, config)
    
    if reranker is None:
        print("Rerank: 未啟用")
        return response
    
    if not response.points:
        print("Rerank: 無搜尋結果")
        return response
    
    print(f"Rerank: 處理 {len(response.points)} 個結果")
    
    documents = [p.payload.get("page_content", "") for p in response.points if p.payload]
    
    try:
        rerank_results = list(reranker.rerank(config.query_text, documents, rerank_top_n))
        
        # 重新排序並更新分數
        reranked_points = []
        for idx, score in rerank_results:
            point = response.points[idx]
            point.score = score
            reranked_points.append(point)
        
        response.points = reranked_points
        print(f"Rerank: 完成")
    except Exception as e:
        print(f"Rerank: 錯誤 - {e}")
    
    return response


# -------------------------
# Utilities
# -------------------------
def flatten_points(resp: models.QueryResponse) -> List[Dict[str, Any]]:
    """把 QueryResponse 轉成 [{id, score, payload}]"""
    out = []
    for p in resp.points or []:
        out.append({"id": p.id, "score": p.score, "payload": p.payload})
    return out


# -------------------------
# Examples (inline usage)
# -------------------------
def _example_functional(client: QdrantClient) -> List[Dict[str, Any]]:
    resp = search_with_json(
        client,
        "my_collection",
        {
            "mode": "hybrid",
            "query_text": "加班費計算標準",
            "filter": {"court": "最高法院", "year": 2024},
            "limit": 20,
        },
    )
    return flatten_points(resp)


def _example_oop(client: QdrantClient) -> List[Dict[str, Any]]:
    searcher = QdrantSearcher(
        client,
        collection="my_collection",
        dense_name="dense",
        sparse_name="bm25",
        use_branch_filters=False,
    )
    resp = searcher.search(
        mode="sparse",
        query_text="假扣押要件",
        filter={
            "must": [
                {"key": "year", "range": {"gte": 2020, "lte": 2024}}
            ],
            "must_not": [
                {"key": "status", "match": {"value": "已撤銷"}}
            ],
        },
        limit=50,
    )
    return flatten_points(resp)
