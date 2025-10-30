#!/usr/bin/env python3
"""
Qdrant 搜尋 API 服務
提供 REST API 介面進行向量搜尋
"""
import os
import json
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from qdrant_search import search_qdrant, SearchConfig, flatten_points
from filter_extractor import extract_filter_conditions, to_qdrant_filter_python

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Qdrant 客戶端
qdrant_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    global qdrant_client

    # 啟動時初始化
    from qdrant_client import QdrantClient
    qdrant_url = os.getenv("QDRANT_CLIENT", "http://localhost:6333")
    qdrant_client = QdrantClient(url=qdrant_url)

    logger.info("Qdrant 搜尋 API 服務已啟動")

    yield

    # 關閉時清理
    logger.info("Qdrant 搜尋 API 服務已關閉")

# 建立 FastAPI 應用程式
app = FastAPI(
    title="Qdrant 搜尋 API",
    description="提供混合嵌入向量搜尋的 REST API 服務",
    version="1.0.0",
    lifespan=lifespan
)

# Pydantic 模型
class SearchRequest(BaseModel):
    collection: str = Field(..., description="要搜尋的集合名稱")
    query_text: str = Field(..., description="搜尋查詢文字")
    mode: str = Field("hybrid", description="搜尋模式：dense/sparse/hybrid")
    limit: int = Field(10, description="返回結果數量上限 (1-100)", ge=1, le=100)
    score_threshold: Optional[float] = Field(None, description="最低分數閾值 (0-1)", ge=0, le=1)

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    query: str
    mode: str
    collection: str

@app.get("/")
async def root():
    """API 服務狀態檢查"""
    return {"message": "Qdrant 搜尋 API 服務運行中", "status": "healthy"}

@app.get("/collections")
async def list_collections():
    """列出所有可用的集合"""
    try:
        collections = qdrant_client.get_collections()
        collection_names = [col.name for col in collections.collections]

        return {
            "collections": collection_names,
            "count": len(collection_names)
        }
    except Exception as e:
        logger.error(f"列出集合錯誤: {e}")
        raise HTTPException(status_code=500, detail=f"列出集合錯誤: {str(e)}")

@app.get("/collections/{collection}/info")
async def collection_info(collection: str):
    """取得指定集合的詳細資訊"""
    try:
        info = qdrant_client.get_collection(collection)

        return {
            "name": collection,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.value
        }
    except Exception as e:
        logger.error(f"取得集合資訊錯誤: {e}")
        raise HTTPException(status_code=500, detail=f"取得集合資訊錯誤: {str(e)}")

# TODO: 完成比較算法
# TODO: 解決case highlight
@app.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    在 Qdrant 向量資料庫中搜尋文件

    支援語意搜尋、關鍵字搜尋和混合搜尋
    """
    # try:
        # 從查詢文字中提取過濾條件
    structured_filter_lst = extract_filter_conditions(request.query_text)
    logger.info("=" * 50)
    logger.info(f"過濾條件: {structured_filter_lst}")
    logger.info("=" * 50)
    logger.info("---> 解析長度：structutred長度：" )
    for structured_filter in structured_filter_lst:
        qdrant_filter = to_qdrant_filter_python(structured_filter)

        # 請求日誌
        logger.info("=" * 50)
        logger.info(f"Qdrant 過濾條件: {qdrant_filter}")
        logger.info("=" * 50)
        logger.info(f"搜尋請求: collection={request.collection}, query='{request.query_text}', mode={request.mode}")
        logger.info("=" * 50)
        summary_fields = ["defendants_role", "A_fact", "B_claim", "C_court_finding", "D_court_reason", "E_legal_eval", "case_fact_summary"]
        reconstructed_query = ""
        for summary_field in summary_fields:
            if summary_field in structured_filter and structured_filter[summary_field]:
                reconstructed_query = structured_filter[summary_field]
                del structured_filter[summary_field]
                break

        # 建立搜尋配置
        config = SearchConfig(
            collection=request.collection,
            # query_text=request.query_text,
            query_text=reconstructed_query,
            mode=request.mode,
            filter=qdrant_filter,
            limit=request.limit,
            score_threshold=request.score_threshold
        )

        # 執行搜尋
        response = search_qdrant(qdrant_client, config)
        results = flatten_points(response)

        # 結果日誌
        logger.info(f"搜尋結果: 總共 {len(results)} 個結果")

    return SearchResponse(
        results=results,
        total=len(results),
        query=request.query_text,
        mode=request.mode,
        collection=request.collection
    )

    # except Exception as e:
    #     logger.error(f"搜尋執行錯誤: {e}")
    #     raise HTTPException(status_code=500, detail=f"搜尋執行錯誤: {str(e)}")

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    try:
        # 檢查 Qdrant 連線
        collections = qdrant_client.get_collections()
        return {
            "status": "healthy",
            "qdrant_connection": "connected",
            "collections_count": len(collections.collections)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "qdrant_connection": "disconnected",
            "error": str(e)
        }

def main():
    """啟動 API 服務"""
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    print("🚀 啟動 Qdrant 搜尋 API 服務...")
    print(f"📍 API 服務運行在: http://{host}:{port}")
    print(f"📚 API 文件: http://{host}:{port}/docs")
    print("=" * 50)

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
