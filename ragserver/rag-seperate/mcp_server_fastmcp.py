#!/usr/bin/env python3
"""
使用 FastMCP 的 Qdrant 搜尋 MCP 伺服器
基於官方 Model Context Protocol Python SDK 的 FastMCP 實作
"""
import json
import logging
from typing import Any, Dict, List, Optional
from qdrant_client import QdrantClient
from qdrant_search import SearchConfig, search_qdrant, flatten_points
from filter_extractor import extract_filter_conditions, to_qdrant_filter_python
from mcp.server.fastmcp import FastMCP


# 創建 FastMCP 伺服器實例
mcp = FastMCP("Qdrant Search Tools")

# Qdrant 客戶端
client = QdrantClient(host="localhost", port=6333)

# 設定日誌記錄器
logger = logging.getLogger("qdrant_search")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler("qdrant_search.log", encoding="utf-8")
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

@mcp.tool()
def qdrant_search(
    collection: str,
    query_text: str,
    # mode: str = "hybrid",
    limit: int = 10,
    score_threshold: Optional[float] = None
) -> str:
    """
    在 Qdrant 向量資料庫中搜尋文件，支援語意搜尋、關鍵字搜尋和混合搜尋
    
    Args:
        collection: 要搜尋的集合名稱，例如：'judgments'、'laws' 等
        query_text: 要搜尋的查詢內容，必須要是完整的句子，不能是關鍵字，例如：'我想了解勞動契約的爭議該怎麼處理'、'民事訴訟的程序是什麼'、'如果對方違約，我可以要求多少違約金'、'公司無故解僱員工是否合法' 等
        limit: 返回結果數量上限 (1-100)
        score_threshold: 最低分數閾值 (0-1)，只返回分數高於此值的結果
    
    Returns:
        JSON 字串格式的搜尋結果
    """
# mode: 搜尋模式：dense(語意搜尋，適合理解文意)、sparse(關鍵字搜尋，適合精確匹配)、hybrid(混合搜尋，平衡語意和關鍵字)
    try:
        mode = "hybrid"
        # 從查詢文字中提取過濾條件
        structured_filter = extract_filter_conditions(query_text)
        qdrant_filter = to_qdrant_filter_python(structured_filter)
        qdrant_filter_str = str(qdrant_filter)

        # 請求日誌（含 query_text 與 structured_filter），多行縮排便於閱讀
        request_log = {
            "collection": collection,
            "query_text": query_text,
            "mode": mode,
            "limit": limit,
            "score_threshold": score_threshold,
            "structured_filter": structured_filter,
            "qdrant_filter": qdrant_filter_str,
        }
        logger.info("qdrant_search_request: %s", json.dumps(request_log, ensure_ascii=False, indent=2))

        config = SearchConfig(
            collection=collection,
            query_text=query_text,
            mode=mode,
            filter=qdrant_filter,  # 使用 Python 格式的 filter
            limit=limit,
            score_threshold=score_threshold
        )

        response = search_qdrant(client, config)
        results = flatten_points(response)

        # 產生可讀性較佳的結果日誌，僅預覽前 3 筆，避免過長
        preview_count = 3
        results_preview = results[:preview_count]

        result_log = {
            "collection": collection,
            "query_text": query_text,
            "mode": mode,
            "total": len(results),
            "results_preview": results_preview,
        }
        logger.info("qdrant_search_result: %s", json.dumps(result_log, ensure_ascii=False, indent=2))

        result_data = {
            "results": results,
            "total": len(results),
            "query": query_text,
            "mode": mode,
            "collection": collection,
        }

        return json.dumps(result_data, ensure_ascii=False, indent=2)

    except Exception as e:
        error_result = {
            "error": f"搜尋執行錯誤: {str(e)}",
            "query": query_text,
            "collection": collection
        }
        # 記錄錯誤堆疊至日誌（多行縮排）
        logger.exception("qdrant_search encountered an error")
        logger.info("qdrant_search_error_payload: %s", json.dumps(error_result, ensure_ascii=False, indent=2))
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool()
def list_collections() -> str:
    """
    列出 Qdrant 中所有可用的集合
    
    Returns:
        JSON 字串格式的集合列表
    """
    try:
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        result = {
            "collections": collection_names,
            "count": len(collection_names)
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "error": f"列出集合錯誤: {str(e)}"
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)

@mcp.tool()
def collection_info(collection: str) -> str:
    """
    取得指定集合的詳細資訊，包括點數、向量數量和狀態
    
    Args:
        collection: 集合名稱
    
    Returns:
        JSON 字串格式的集合詳細資訊
    """
    try:
        info = client.get_collection(collection)
        
        result = {
            "name": collection,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.value,
            "config": {
                "distance": info.config.params.vectors.get("dense", {}).get("distance", "Unknown") if hasattr(info.config.params, 'vectors') else "Unknown"
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "error": f"取得集合資訊錯誤: {str(e)}",
            "collection": collection
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)

# 主程式入口
if __name__ == "__main__":
    # 使用 FastMCP 的 run 方法啟動伺服器
    mcp.run()
