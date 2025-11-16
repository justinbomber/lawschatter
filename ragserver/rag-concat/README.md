# RAG Concat 查詢策略開發

## 簡介

這是 rag-concat 的查詢策略開發環境。目前保持最簡單的架構，方便你快速開發和測試。

## 檔案結構

```
rag-concat/
├── query_strategy.py    # 在這裡寫你的查詢策略和 filter 邏輯 ⭐
├── FILTER_ARCHITECTURE.md  # Filter 架構設計文件（參考）
└── README.md
```

## 使用方式

### 1. 編輯查詢策略

直接編輯 `query_strategy.py`，在 `QueryStrategy` 類別中實作你的查詢邏輯。

### 2. 測試

```bash
python query_strategy.py
```

或是在 Python 中：

```python
from query_strategy import QueryStrategy

strategy = QueryStrategy()
results = strategy.test("你的查詢")
```

## 環境變數（可選）

如果需要，可以在 `.env` 中設定：

```env
QDRANT_CLIENT=http://localhost:6333
COLLECTION_NAME=embedding-concat
```

## Filter 架構

Filter 功能設計詳見 `FILTER_ARCHITECTURE.md`。

### 設計原則

**簡單優先**：所有 filter 邏輯都在 `query_strategy.py` 中，方便開發和修改。

### 使用方式

在 `query_strategy.py` 中加入 `_build_filter()` 方法：

```python
def _build_filter(self, filter_dict: Dict[str, Any]) -> Optional[models.Filter]:
    """將 filter 字典轉換為 Qdrant Filter"""
    # TODO: 實作轉換邏輯
    pass

async def search(self, query_text: str, filter_dict: Dict = None, limit: int = 10):
    # 建立 filter
    qdrant_filter = self._build_filter(filter_dict) if filter_dict else None
    
    # 執行搜尋
    return await self.hybrid_search(query_text, filter=qdrant_filter, limit=limit)
```

### Filter 字典範例

```python
filter_dict = {
    "doc_level": "case",  # 或 "defendant"
    "jyear": 113,
    "case_type": "刑法",
    "case_metadata": {
        "first_instance": True,
        "jtitle_type": "詐欺"
    }
}
```

## 下一步

1. 研究 `rag-seperate/services/filter_service.py` 的 `to_qdrant_filter()` 方法
2. 在 `query_strategy.py` 中實作 `_build_filter()` 方法
3. 測試各種 filter 條件
4. [可選] 未來如果邏輯變複雜，再考慮抽成獨立檔案
