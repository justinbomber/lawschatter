from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., description="使用者的問題")
    # collection: Optional[str] = Field(None, description="指定的集合名稱")
    # mode: Optional[str] = Field(None, description="搜尋模式：dense/sparse/hybrid")
    # limit: Optional[int] = Field(None, description="返回結果數量上限", ge=1, le=100)
    # score_threshold: Optional[float] = Field(None, description="最低分數閾值", ge=0, le=1)
    # temperature: Optional[float] = Field(None, description="LLM 溫度參數", ge=0, le=2)
    # max_tokens: Optional[int] = Field(None, description="LLM 最大生成 token 數", ge=1)
    conversation_id: Optional[str] = Field(None, description="對話 ID，為 null 時將自動創建新對話")
    streaming: bool = Field(False, description="是否使用 SSE 串流回復")


class RAGSearchRequest(BaseModel):
    query_text: str
    conversation_id: Optional[str] = None
    streaming: bool = False
    search_mode: str = "rrf"


class RAGSearchResult(BaseModel):
    page_content: str
    jid: str
    defendants: List[str] = []


class RAGSearchResponse(BaseModel):
    results: List[RAGSearchResult]
    total: int
    query: str
    mode: str
    collection: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    query: str
    total_sources: int
    model: str


class HealthStatus(BaseModel):
    status: str
    rag_server_connection: str
    llm_provider: str
    error: Optional[str] = None

