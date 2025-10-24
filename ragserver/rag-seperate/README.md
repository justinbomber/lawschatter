# Qdrant 搜尋工具集

這是一個完整的 Qdrant 向量資料庫搜尋工具集，提供混合嵌入搜尋和 Model Context Protocol (MCP) 介面。

## 功能特色

- 🔍 **多種搜尋模式**: 支援語意搜尋 (dense)、關鍵字搜尋 (sparse) 和混合搜尋 (hybrid)
- 🎯 **靈活篩選**: 支援簡單和複雜的篩選條件
- 📊 **集合管理**: 列出集合、分析結構、取得詳細資訊
- 🛠️ **工具幫助**: 內建篩選條件建構幫助
- 🚀 **MCP 支援**: 使用 FastMCP 框架提供 Model Context Protocol 介面

## 技術架構

### Hybrid Embedding
- **Google Gemini Dense Embedding** (gemini-embedding-001) with **3072** dimensions
- **基於 Jieba tokenizer 的 BM25 Sparse Embedding**
- **Qdrant 向量資料庫**

## 📂 專案結構

```
.
├── 🔧 核心功能
│   ├── mcp_server_fastmcp.py      # FastMCP 伺服器實作
│   ├── qdrant_search.py           # Qdrant 搜尋功能
│   ├── hybrid_embed.py            # 建立 Qdrant Hybrid Vector Store
│   ├── zht_sparse_embed.py        # 中文 BM25 + Jieba tokenizer
│   └── law_tokenize.py            # Jieba Tokenizer
├── 🚀 啟動腳本
│   └── run_mcp_server.py          # MCP 伺服器啟動腳本
├── 🧪 測試檔案
│   ├── simple_test_fastmcp.py     # 簡單測試
│   └── test_fastmcp_server.py     # 完整測試
├── ⚙️ 配置檔案
│   ├── pyproject.toml             # 專案配置
│   ├── .python-version            # Python 版本
│   └── uv.lock                    # 依賴鎖定
└── 🔤 資源檔案
    ├── zh-t.txt                   # 中文停用詞表
    └── dict.txt.big               # Jieba 辭典
```

## ⚙️ 安裝需求

### 1. Python 版本
```bash
Python 3.12+
```

### 2. 安裝依賴
```bash
# 使用 uv (推薦)
uv sync

# 或使用 pip
pip install mcp[cli] qdrant-client fastembed jieba
```

## 🔑 環境變數設定

請在專案目錄建立 `.env` 檔案，內容如下：

```env
GENAI_EMBEDDING_API_KEY=你的GoogleAPI金鑰
QDRANT_CLIENT=http://localhost:6333
COLLECTION_NAME=law_docs
```

## 🚀 使用方式

### 1. MCP 伺服器模式 (推薦)

#### 啟動伺服器
```bash
# 方法 1: 直接執行
uv run python run_mcp_server.py

# 方法 2: 使用腳本命令
uv run mcp-server
```

#### 可用工具

**qdrant_search** - 在 Qdrant 向量資料庫中搜尋文件
- `collection` (必填): 集合名稱
- `query_text` (必填): 搜尋查詢文字
- `mode` (可選): 搜尋模式 (dense/sparse/hybrid，預設: hybrid)
- `filter` (可選): 篩選條件
- `limit` (可選): 結果數量上限 (1-100，預設: 10)
- `score_threshold` (可選): 最低分數閾值 (0-1)

**build_filter_help** - 協助建構篩選條件
- `filter_type` (可選): 篩選類型 (simple/range/multi_value/complex/examples，預設: examples)
- `field_name` (可選): 欄位名稱
- `data_type` (可選): 資料類型

**collection_schema** - 取得集合的資料結構和可用欄位
- `collection` (必填): 集合名稱
- `sample_size` (可選): 取樣數量 (1-20，預設: 5)

**list_collections** - 列出 Qdrant 中所有可用的集合

**collection_info** - 取得指定集合的詳細資訊
- `collection` (必填): 集合名稱

#### 測試工具
```bash
# 簡單測試
uv run python simple_test_fastmcp.py

# 完整測試
uv run python test_fastmcp_server.py
```

### 2. 直接使用 qdrant_search

#### 函式式用法
```python
from qdrant_client import QdrantClient
from qdrant_search import search_with_json, flatten_points

client = QdrantClient(host="localhost", port=6333)

resp = search_with_json(
    client,
    "my_collection",
    {
        "mode": "hybrid",  # "dense" | "sparse" | "hybrid"
        "query_text": "加班費計算標準",
        "filter": {"court": "最高法院", "year": 2024},  # 簡寫或完整規格皆可
        "limit": 20,
    },
)
print(flatten_points(resp))  # -> [{"id":..., "score":..., "payload":...}]
```

#### OOP 方式
```python
from qdrant_client import QdrantClient
from qdrant_search import QdrantSearcher, flatten_points

client = QdrantClient(host="localhost", port=6333)
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
print(flatten_points(resp))
```

### 3. 添加資料到 Qdrant

```python
from langchain_core.documents import Document
from hybrid_embed import qdrant_hybrid_vector_store

# 1. 轉換資料為 langchain Document 格式
document_1 = Document(
    page_content="I had chocolate chip pancakes and scrambled eggs for breakfast this morning.",
    metadata={"source": "tweet"},
)

document_2 = Document(
    page_content="The weather forecast for tomorrow is cloudy and overcast, with a high of 62 degrees Fahrenheit.",
    metadata={"source": "news"},
)

docs = [document_1, document_2]
ids = [id1, id2]  # uuid or db ids

# 2. 添加 Document
qdrant_hybrid_vector_store.add_documents(
    documents=docs, 
    ids=ids
)
```

## 篩選條件範例

### 簡單篩選
```json
{
  "court": "最高法院",
  "year": 2024
}
```

### 範圍查詢
```json
{
  "must": [
    {"key": "year", "range": {"gte": 2020, "lte": 2024}}
  ]
}
```

### 多值匹配
```json
{
  "must": [
    {"key": "court", "match": {"any": ["最高法院", "高等法院"]}}
  ]
}
```

### 複雜邏輯
```json
{
  "must": [
    {"key": "court", "match": {"value": "最高法院"}},
    {"key": "year", "range": {"gte": 2020}}
  ],
  "must_not": [
    {"key": "status", "match": {"value": "已撤銷"}}
  ],
  "should": [
    {"key": "case_type", "match": {"any": ["民事", "商事"]}}
  ]
}
```

## 篩選條件支援格式

filter 支援三種型式：
- **簡寫**: `{"year": 2024, "court": "最高法院"}`
- **完整規格**: `{"must":[...], "must_not":[...], "should":[...]}`
- **直接給**: `models.Filter`

欄位預設：`dense_name="dense"`、`sparse_name="bm25"`；`use_branch_filters=False`。

## FastMCP 的優勢

1. **簡化開發**: 使用 `@mcp.tool()` 裝飾器，無需手動實作 MCP 協定
2. **自動處理**: FastMCP 自動處理工具註冊、參數驗證和錯誤處理
3. **易於啟動**: 使用 `mcp.run()` 一行代碼啟動伺服器
4. **統一格式**: 工具函數直接返回 JSON 字串，格式統一
5. **內建功能**: 支援工具發現、參數完成等 MCP 標準功能

## 工具使用流程

1. **探索集合**: 使用 `list_collections` 查看可用集合
2. **分析結構**: 使用 `collection_schema` 了解資料欄位
3. **建構篩選**: 使用 `build_filter_help` 學習篩選語法
4. **執行搜尋**: 使用 `qdrant_search` 進行搜尋

## 注意事項

- 需要 Qdrant 服務運行在 `localhost:6333`
- 所有工具都返回 JSON 格式的結果
- 錯誤會以 JSON 格式返回，包含錯誤訊息
- 支援繁體中文的搜尋和結果顯示
- 需要 Google API 金鑰用於 Gemini 嵌入

## 配置

需要根據實際環境修改 Qdrant 連接設定：

```python
# 在相關檔案中
client = QdrantClient(host="localhost", port=6333)
```

## 錯誤處理

- 工具執行錯誤會在回應中包含錯誤資訊
- 連接失敗時會返回相應的錯誤訊息
- 所有函數都有完整的異常處理機制

## 優勢

1. **完整的篩選說明**: 詳細的 filter 參數說明，LLM 可以輕鬆理解如何構建篩選條件
2. **結構分析工具**: 自動分析集合資料結構，幫助了解可用欄位
3. **篩選輔助工具**: 提供範例和語法指導
4. **易於整合**: 可直接使用或輕鬆整合到任何 MCP 伺服器
5. **獨立測試**: 不依賴特定 MCP 實作，可獨立運行和測試
6. **混合搜尋**: 結合語意搜尋和關鍵字搜尋的優勢