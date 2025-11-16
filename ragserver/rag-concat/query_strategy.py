"""
rag-concat 查詢策略開發檔案
在這裡寫你的查詢策略和測試程式碼
"""
import os
from typing import Dict, Any, List, Optional, Literal
from dotenv import load_dotenv
from qdrant_client import AsyncQdrantClient, models
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from zht_sparse_embed import ZHTSparseEmbed
# from openai import AsyncOpenAI  # TODO: 如果需要使用 OpenAI
# from pydantic import BaseModel, Field  # TODO: 如果需要定義 Filter 模型
# 載入環境變數
load_dotenv()


class QueryStrategy:
    """
    查詢策略類別
    在這裡實作你的查詢邏輯
    """
    
    def __init__(self):
        # 基本設定
        self.qdrant_url = os.getenv("QDRANT_CLIENT", "http://localhost:6333")
        self.collection_name = os.getenv("COLLECTION_NAME", "embedding-concat")
        self.client = AsyncQdrantClient(url=self.qdrant_url)
        self.dense_embeddings = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001",
            google_api_key=os.getenv("GENAI_EMBEDDING_API_KEY"),
        )
        self.sparse_embeddings = ZHTSparseEmbed()
        
        # LLM 提取解耦：提取邏輯請放在外部服務，這裡不負責提取
    
    def _get_dense_embedding(self, query_text: str):
        return self.dense_embeddings.embed_query(query_text)

    def _get_sparse_embedding(self, query_text: str):
        return self.sparse_embeddings.embed_query(query_text)
    
    # 注意：LLM 提取功能請由外部服務負責，這裡不處理提取
    
    def _build_filter(self, filter_dict: Dict[str, Any]) -> Optional[models.Filter]:
        """
        將 filter 字典轉換為 Qdrant Filter
        
        Args:
            filter_dict: 結構化的 filter 字典
        
        Returns:
            Qdrant Filter 物件，如果沒有條件則返回 None
        
        TODO: 實作轉換邏輯
        參考: rag-seperate/services/filter_service.py 的 to_qdrant_filter() 方法
        
        需要處理的欄位：
        1. doc_level: "case" 或 "defendant"（重要！rag-concat 特有）
        2. 基本欄位: jid, jyear, jcase, jno, case_type
        3. case_metadata: first_instance, second_instance, third_instance, jtitle_type
        4. defendants: 被告條件（簡化：只處理第一個）
        5. negated_fields: 否定條件（must_not）
        """
        # TODO: 實作轉換邏輯
        pass
    
    async def hybrid_search(
        self,
        query_text: str,
        limit: int = 100,
        filter: Optional[models.Filter] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        執行 Hybrid 搜尋（dense + sparse 混合檢索）。
        
        目前實作：
        - 使用 `GoogleGenerativeAIEmbeddings` 產生 dense 向量
        - 使用 `ZHTSparseEmbed` 產生 sparse 向量（BM25）
        - 透過 `langchain_qdrant.QdrantVectorStore` 以 `RetrievalMode.HYBRID` 做混合查詢
        
        Args:
            query_text: 查詢文本（會同時用於 dense 與 sparse embedding）
            limit: 要從 Qdrant 取回的結果數量（傳給 `similarity_search`）
            filter: Qdrant Filter 物件（可選，用於 metadata 過濾）
            score_threshold: 分數閾值（目前未使用，預留參數）
        
        Returns:
            搜尋結果列表（`QdrantVectorStore.similarity_search` 回傳的結果）
        """
        # 1. 生成 dense 和 sparse embeddings
        dense_vector = await self.dense_embeddings.embed_query(query_text)
        sparse_vector = await self.sparse_embeddings.embed_query(query_text)
        
        # 2. 建立 QdrantVectorStore（使用 HYBRID 模式）
        vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=dense_vector,
            sparse_embedding=sparse_vector,
            retrieval_mode=RetrievalMode.HYBRID,
            vector_name="dense",
            sparse_vector_name="bm25",
        )

        # 3. 執行 hybrid search（可選擇是否帶 filter）
        if filter:
            results = vector_store.similarity_search(query_text, limit=limit, filter=filter)
        else:
            results = vector_store.similarity_search(query_text, limit=limit)
        
        return results

    async def search(
        self,
        query_text: str,
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        執行搜尋（對外主要介面）。
        
        預期責任：
        - 接收前端或上層服務傳入的 `query_text` 與 `filter_dict`
        - 將 `filter_dict` 轉成 Qdrant Filter
        - 呼叫 `hybrid_search()` 實際執行混合檢索
        
        Args:
            query_text: 查詢文本
            limit: 最終希望返回的結果數量（可與 hybrid_search 的 limit 分開調整）
            filter_dict: Filter 字典（由外部服務產生並傳入，可為 None）
        
        Returns:
            搜尋結果列表
        """
        # TODO: 在這裡實作完整流程（由你填寫）
        # 建議流程：
        # 1. 使用 _build_filter() 將 filter_dict 轉成 Qdrant Filter（若 filter_dict 為 None 則略過）
        # 2. 呼叫 hybrid_search() 取得結果
        # 3. 視需要再做後處理（排序、截斷、格式轉換等）
        return []
    
    def test(self, query_text: str, filter_dict: Optional[Dict[str, Any]] = None):
        """
        測試方法 - 用於快速測試你的策略
        
        Args:
            query_text: 查詢文本
            filter_dict: Filter 字典（外部服務產生並傳入，可選）
        """
        import asyncio
        results = asyncio.run(self.search(query_text, filter_dict=filter_dict))
        print(f"查詢結果數量: {len(results)}")
        return results


# 開發和測試用
if __name__ == "__main__":
    strategy = QueryStrategy()
    
    # 測試你的查詢策略
    test_query = "測試查詢"
    strategy.test(test_query)

