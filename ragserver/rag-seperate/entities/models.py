from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class SearchMode(str, Enum):
    CHUNK = "chunk"
    RRF = "rrf"


class SearchRequest(BaseModel):
    query_text: str = Field(..., description="搜尋查詢文字")
    conversation_id: Optional[str] = Field(None, description="對話 ID，為 null 時不使用歷史對話")
    streaming: bool = Field(False, description="是否使用 SSE 串流回復")
    search_mode: SearchMode = Field(..., description="搜尋模式：chunk 或 rrf (必填)")


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

