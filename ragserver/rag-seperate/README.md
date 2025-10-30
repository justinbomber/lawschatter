# Qdrant 搜尋 API 服務

## 專案架構 (Clean Architecture V2.0)

本專案採用嚴格的 Clean Architecture 設計，分為以下六個層級：

### 1. Config（配置層）- 最內層
- `config/settings.py`: 統一配置管理，所有環境變數集中載入

### 2. Entities（實體層）
- `entities/models.py`: API 請求與回應模型
- `entities/filters.py`: 法律判決過濾條件模型

### 3. Domain（領域層）- 抽象介面
- `domain/interfaces.py`: 定義所有服務的抽象介面（ABC）
  - `ISearchService`: 搜尋服務介面
  - `IFilterService`: 過濾服務介面
  - `IRerankService`: 重新排序服務介面
  - `IEmbeddingProvider`: 嵌入提供者介面
  - `IQdrantClient`: Qdrant 客戶端介面

### 4. Infrastructure（基礎設施層）
- `infrastructure/qdrant_client_wrapper.py`: Qdrant 客戶端封裝（實作 IQdrantClient）
- `infrastructure/tokenizer.py`: Jieba 法律文本分詞器
- `infrastructure/embeddings/dense_embedding.py`: 語意向量嵌入（實作 IEmbeddingProvider）
- `infrastructure/embeddings/sparse_embedding.py`: 稀疏向量（BM25）嵌入（實作 IEmbeddingProvider）

### 5. Services（服務層）
- `services/search_service.py`: 搜尋業務邏輯（實作 ISearchService）
- `services/filter_service.py`: 過濾條件提取與轉換（實作 IFilterService）
- `services/rerank_service.py`: 搜尋結果重新排序（實作 IRerankService）

### 6. Controllers（控制器層）- 最外層
- `controllers/search_controller.py`: API 端點處理
- `controllers/api_router.py`: API 路由定義

## 資料夾結構

```
rag-seperate/
├── config/               # 配置層（最內層）
│   ├── __init__.py
│   └── settings.py      # 統一配置管理
├── entities/             # 實體層
│   ├── __init__.py
│   ├── models.py
│   └── filters.py
├── domain/              # 領域層（抽象介面）
│   ├── __init__.py
│   └── interfaces.py    # 所有抽象介面定義
├── infrastructure/       # 基礎設施層
│   ├── __init__.py
│   ├── qdrant_client_wrapper.py
│   ├── tokenizer.py
│   └── embeddings/
│       ├── __init__.py
│       ├── dense_embedding.py
│       └── sparse_embedding.py
├── services/            # 服務層
│   ├── __init__.py
│   ├── search_service.py
│   ├── filter_service.py
│   └── rerank_service.py
├── controllers/         # 控制器層（最外層）
│   ├── __init__.py
│   ├── search_controller.py
│   └── api_router.py   # API 路由定義
├── main.py             # 應用程式入口（依賴注入）
├── requirements.txt
├── pyproject.toml
├── dict.txt.big       # Jieba 詞典
└── zh-t.txt          # 中文停用詞

[舊檔案保留]
├── filter_extractor.py  # 已重構至 services/filter_service.py
├── qdrant_search.py     # 已重構至 services/search_service.py
├── rerank.py            # 已重構至 services/rerank_service.py
├── law_tokenize.py      # 已重構至 infrastructure/tokenizer.py
├── zht_sparse_embed.py  # 已重構至 infrastructure/embeddings/
└── hybrid_embed.py      # 已重構至 infrastructure/embeddings/
```

## 環境變數設定

請在專案根目錄建立 `.env` 檔案，設定以下環境變數：

### 必要環境變數
```env
# Qdrant 設定
QDRANT_CLIENT=http://localhost:6333
COLLECTION_NAME=your_collection_name

# OpenAI 設定
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-5

# Google AI 設定
GENAI_EMBEDDING_API_KEY=your-key
GOOGLE_EMBEDDING_MODEL=gemini-embedding-001

# API 服務設定
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
```

### 可選環境變數
```env
# Cohere 設定（用於重新排序）
COHERE_API_KEY=your-key
COHERE_MODEL=rerank-v3.5

# 嵌入設定
DENSE_VECTOR_NAME=dense
SPARSE_VECTOR_NAME=bm25
STOPWORDS_PATH=zh-t.txt
```

## 啟動服務

```bash
python main.py
```

## API 端點

- `GET /`: 服務狀態檢查
- `GET /health`: 健康檢查
- `GET /collections`: 列出所有集合
- `GET /collections/{collection}/info`: 取得集合資訊
- `POST /search`: 執行搜尋

## 設計原則

### Clean Architecture 核心準則
- **依賴規則**: 依賴只能由外向內，內層不依賴外層
- **穩定抽象**: 透過 Domain 層定義抽象介面（ABC）
- **依賴注入**: 透過建構子注入所有依賴
- **配置分離**: 所有配置透過 Config 層統一管理

### 開發準則
- **模組化設計**: 每個功能在獨立模組中
- **單一職責**: 每個類別只負責一個功能
- **快速失敗**: 不使用 try-catch，錯誤直接拋出
- **最少日誌**: 只記錄關鍵資訊
- **簡潔程式碼**: 只寫必要的程式碼

### 可替換性
- **低替換成本**: 只需實作 Domain 介面，不影響其他層
- **易於測試**: 可注入 Mock 物件進行單元測試
- **明確契約**: 介面清楚定義行為預期
