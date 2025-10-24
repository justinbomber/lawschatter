# Qdrant 搜尋 API 服務

這是一個完整的 Qdrant 向量資料庫搜尋 API 服務，提供混合嵌入搜尋的 REST API 介面。

## 功能特色

- 🔍 **多種搜尋模式**: 支援語意搜尋 (dense)、關鍵字搜尋 (sparse) 和混合搜尋 (hybrid)
- 🎯 **智慧過濾**: 自動從查詢文字中提取結構化過濾條件
- 📊 **集合管理**: 列出集合、取得詳細資訊
- 🛠️ **REST API**: 提供完整的 REST API 介面
- 🚀 **高性能**: 基於 FastAPI 的異步處理

## 技術架構

### Hybrid Embedding
- **Google Gemini Dense Embedding** (gemini-embedding-001) with **3072** dimensions
- **基於 Jieba tokenizer 的 BM25 Sparse Embedding**
- **Qdrant 向量資料庫**

## 📂 專案結構

```
.
├── 🔧 核心功能
│   ├── main.py                    # FastAPI 應用程式主檔
│   ├── qdrant_search.py           # Qdrant 搜尋功能
│   ├── hybrid_embed.py            # 混合嵌入配置
│   ├── zht_sparse_embed.py        # 中文 BM25 + Jieba tokenizer
│   ├── law_tokenize.py            # Jieba Tokenizer
│   └── filter_extractor.py        # 智慧過濾條件提取
├── ⚙️ 配置檔案
│   ├── pyproject.toml             # 專案配置
│   └── .python-version            # Python 版本
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
pip install -r requirements.txt
```

## 🔑 環境變數設定

請在專案目錄建立 `.env` 檔案，內容如下：

```env
GENAI_EMBEDDING_API_KEY=你的GoogleAPI金鑰
QDRANT_CLIENT=http://localhost:6333
COLLECTION_NAME=law_docs
API_HOST=0.0.0.0
API_PORT=8000
```

## 🚀 使用方式

### 1. 啟動 API 服務

```bash
# 方法 1: 直接執行
uv run python main.py

# 方法 2: 使用 uvicorn
uv run uvicorn main:app --reload

# 方法 3: 使用腳本命令
uv run qdrant-api
```

服務啟動後：
- API 文件: http://localhost:8000/docs
- 替代文件: http://localhost:8000/redoc
- 健康檢查: http://localhost:8000/health

### 2. API 端點

#### POST /search
主要搜尋端點，支援混合嵌入搜尋

**請求範例:**
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "law_docs",
    "query_text": "加班費計算標準",
    "mode": "hybrid",
    "limit": 10
  }'
```

**請求參數:**
- `collection` (必填): 集合名稱
- `query_text` (必填): 搜尋查詢文字
- `mode` (可選): 搜尋模式 (dense/sparse/hybrid，預設: hybrid)
- `limit` (可選): 結果數量上限 (1-100，預設: 10)
- `score_threshold` (可選): 最低分數閾值 (0-1)

#### GET /collections
列出所有可用的集合

**回應範例:**
```json
{
  "collections": ["law_docs", "judgments"],
  "count": 2
}
```

#### GET /collections/{collection}/info
取得指定集合的詳細資訊

**回應範例:**
```json
{
  "name": "law_docs",
  "vectors_count": 3072,
  "points_count": 15000,
  "status": "green"
}
```

#### GET /health
健康檢查端點

**回應範例:**
```json
{
  "status": "healthy",
  "qdrant_connection": "connected",
  "collections_count": 3
}
```

### 3. 錯誤回應

當 API 調用失敗時，返回標準的錯誤格式：

```json
{
  "detail": "搜尋執行錯誤: 集合不存在"
}
```

## 進階功能

### 智慧過濾條件提取

API 會自動從查詢文字中提取結構化的過濾條件，例如：
- 查詢 "最高法院 2024 年的民事案件" 會自動提取法院、年份、案類等條件
- 支援複雜的法律條件識別（罪名、法條、刑期等）

### 搜尋模式說明

- **dense**: 純語意搜尋，適合理解文意和概念
- **sparse**: 純關鍵字搜尋，適合精確匹配
- **hybrid**: 混合模式，平衡語意和關鍵字的優勢

## 注意事項

- 需要 Qdrant 服務運行在指定的 URL
- 所有請求和回應都使用 JSON 格式
- 支援繁體中文的搜尋和結果顯示
- 需要 Google API 金鑰用於 Gemini 嵌入
- 建議在生產環境中設定適當的限流和認證

## 錯誤處理

- API 會返回適當的 HTTP 狀態碼
- 錯誤訊息包含詳細的失敗原因
- 所有端點都有完整的異常處理機制

## 環境變數

| 變數名稱 | 描述 | 預設值 |
|---------|------|-------|
| `QDRANT_CLIENT` | Qdrant 服務 URL | `http://localhost:6333` |
| `API_HOST` | API 服務綁定地址 | `0.0.0.0` |
| `API_PORT` | API 服務端口 | `8000` |
| `GENAI_EMBEDDING_API_KEY` | Google Gemini API 金鑰 | 必填 |

## 開發說明

### 程式碼結構

- `main.py`: FastAPI 應用程式主檔
- `qdrant_search.py`: 核心搜尋功能
- `filter_extractor.py`: 智慧過濾條件提取
- `hybrid_embed.py`: 混合嵌入配置
- `zht_sparse_embed.py`: 中文稀疏嵌入
- `law_tokenize.py`: 法律專用分詞器

### 測試 API

```bash
# 健康檢查
curl http://localhost:8000/health

# 列出集合
curl http://localhost:8000/collections

# 搜尋測試
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"collection": "your_collection", "query_text": "測試查詢"}'
```