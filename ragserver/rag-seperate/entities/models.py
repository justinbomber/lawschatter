from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class SearchMode(str, Enum):
    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID = "hybrid"


class SearchRequest(BaseModel):
    collection: str = Field(..., description="要搜尋的集合名稱")
    query_text: str = Field(..., description="搜尋查詢文字")
    mode: str = Field("hybrid", description="搜尋模式：dense/sparse/hybrid")
    limit: int = Field(10, description="返回結果數量上限 (1-100)", ge=1, le=100)
    score_threshold: Optional[float] = Field(None, description="最低分數閾值 (0-1)", ge=0, le=1)
    streaming: bool = Field(False, description="是否使用 SSE 串流回復")


class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    query: str
    mode: str
    collection: str


class CollectionInfo(BaseModel):
    name: str
    vectors_count: int
    points_count: int
    status: str


class HealthStatus(BaseModel):
    status: str
    qdrant_connection: str
    collections_count: Optional[int] = None
    error: Optional[str] = None

