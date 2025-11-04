# 法律聊天機器人 API

基於 Clean Architecture 架構的法律問答系統，整合 RAG（檢索增強生成）技術和大型語言模型。

## 系統架構

本專案採用 Clean Architecture 分層架構：

```
┌─────────────────────────────────────┐
│         FastAPI Application         │
│              (main.py)              │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│      Controllers (控制器層)         │
│  - 處理 HTTP 請求/回應              │
│  - 協調服務層                       │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│       Services (服務層)             │
│  - 核心業務邏輯                     │
│  - RAG 整合與 LLM 呼叫              │
└─────────────────────────────────────┘
                  ↓
┌──────────────────┬──────────────────┐
│  Infrastructure  │    Entities      │
│  (基礎設施層)    │   (實體層)       │
│  - RAG 客戶端    │   - 資料模型     │
│  - LLM 提供者    │   - Pydantic 模型│
└──────────────────┴──────────────────┘
                  ↓
┌──────────────────┬──────────────────┐
│     Domain       │     Config       │
│   (領域層)       │   (配置層)       │
│  - 抽象介面      │   - 環境變數     │
└──────────────────┴──────────────────┘
```

## 目錄結構

```
chatbot/
├── config/              # 配置層
│   └── settings.py      # 環境變數管理
├── entities/            # 實體層
│   └── models.py        # 資料模型
├── domain/              # 領域層
│   └── interfaces.py    # 抽象介面
├── infrastructure/      # 基礎設施層
│   ├── rag_client.py    # RAG 伺服器客戶端
│   └── llm_provider.py  # LLM 提供者
├── services/            # 服務層
│   └── chat_service.py  # 聊天業務邏輯
├── controllers/         # 控制器層
│   ├── chat_controller.py
│   └── api_router.py
├── main.py              # 應用程式入口
├── .env                 # 環境變數（需自行建立）
├── .env.example         # 環境變數範本
├── pyproject.toml       # 專案配置
├── requirements.txt     # 依賴套件
└── README.md            # 本文件
```

## 功能特色

- **Clean Architecture**: 嚴格遵循分層架構，易於維護和擴展
- **模組化設計**: 各層職責清晰，可獨立測試
- **依賴注入**: 在 `main.py` 中統一管理依賴
- **環境變數配置**: 所有設定透過 `.env` 管理
- **抽象介面**: 易於替換不同的 LLM 或 RAG 實作
- **錯誤快速失敗**: 遵循使用者規則，不使用 try-catch

## 快速開始

### 1. 安裝依賴

```bash
cd chatbot
pip install -r requirements.txt
```

或使用 `uv`：

```bash
uv pip install -r requirements.txt
```

### 2. 配置環境變數

複製 `.env.example` 為 `.env` 並填寫配置：

```bash
cp .env.example .env
```

編輯 `.env` 文件：

```env
# RAG 伺服器設定
RAG_SERVER_URL=http://localhost:8000
RAG_SERVER_TIMEOUT=30

# LLM 設定（必填）
LLM_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# API 服務設定
API_HOST=0.0.0.0
API_PORT=8001
API_RELOAD=true

# RAG 搜尋預設值
RAG_COLLECTION=embedding-seperate
RAG_MODE=hybrid
RAG_LIMIT=10
RAG_SCORE_THRESHOLD=1
```

### 3. 啟動服務

```bash
python main.py
```

或使用 uvicorn：

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 4. 訪問 API

- API 文檔: http://localhost:8001/docs
- 健康檢查: http://localhost:8001/health
- 根路徑: http://localhost:8001/

## API 端點

### POST /chat/completion

發送問題並獲取基於 RAG 的回答。

**請求範例**：

```bash
curl -X 'POST' \
  'http://localhost:8001/chat/completion' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "question": "有沒有未認罪，但法院還是給予緩刑的詐欺車手案例"
}'
```

**請求參數**：

```json
{
  "question": "使用者的問題（必填）",
  "collection": "指定的集合名稱（可選，預設使用環境變數）",
  "mode": "搜尋模式：dense/sparse/hybrid（可選）",
  "limit": 10,
  "score_threshold": 1,
  "temperature": 0.7,
  "max_tokens": 2000
}
```

**回應範例**：

```json
{
  "answer": "根據提供的判決資料，有以下幾個未認罪但仍獲得緩刑的詐欺車手案例：\n\n1. 【案號：TCDM,113,金訴,2174,20250630,1】...",
  "sources": [
    {
      "page_content": "被告19歲後續全額賠償獲緩刑量刑輕重考量因素",
      "jid": "TCDM,113,金訴,2174,20250630,1"
    }
  ],
  "query": "有沒有未認罪，但法院還是給予緩刑的詐欺車手案例",
  "total_sources": 10,
  "model": "gpt-4"
}
```

### GET /health

檢查服務健康狀態。

**回應範例**：

```json
{
  "status": "healthy",
  "rag_server_connection": "connected",
  "llm_provider": "available",
  "error": null
}
```

## 工作流程

1. **接收請求**: 使用者透過 `/chat/completion` 發送問題
2. **RAG 搜尋**: 系統將問題傳送到 RAG 伺服器（http://localhost:8000/search）
3. **獲取相關資料**: RAG 伺服器返回相關的法律判決資料
4. **建立提示**: 將 RAG 結果與使用者問題結合成 LLM 提示
5. **生成回答**: 呼叫 LLM（如 GPT-4）生成回答
6. **返回結果**: 將答案和相關來源返回給使用者

## Clean Architecture 設計原則

### 依賴規則

依賴只能由外向內：

```
Controllers → Services → Infrastructure/Domain/Entities → Config
```

### 各層職責

- **Config**: 環境變數管理，無依賴
- **Entities**: 資料模型，無業務邏輯
- **Domain**: 定義抽象介面，無具體實作
- **Infrastructure**: 實作外部系統適配（RAG、LLM）
- **Services**: 核心業務邏輯
- **Controllers**: HTTP 請求處理

### 擴展性

#### 替換 LLM 提供者

在 `infrastructure/` 下建立新的 provider：

```python
class ClaudeProvider(ILLMProvider):
    async def generate_response(self, messages, temperature, max_tokens):
        # 實作 Claude API 呼叫
        pass
```

在 `main.py` 中替換：

```python
llm_provider = ClaudeProvider(settings)
```

#### 新增自訂 Prompt

修改 `services/chat_service.py` 的 `build_prompt` 方法。

#### 新增新端點

在 `controllers/api_router.py` 中新增路由，並在 `ChatController` 中新增對應方法。

## 環境變數說明

| 變數名稱 | 說明 | 預設值 | 必填 |
|---------|------|--------|------|
| `RAG_SERVER_URL` | RAG 伺服器 URL | http://localhost:8000 | 否 |
| `RAG_SERVER_TIMEOUT` | RAG 請求超時（秒） | 30 | 否 |
| `LLM_API_KEY` | OpenAI API Key | - | **是** |
| `LLM_MODEL` | LLM 模型名稱 | gpt-4 | 否 |
| `LLM_TEMPERATURE` | LLM 溫度參數 | 0.7 | 否 |
| `LLM_MAX_TOKENS` | LLM 最大 token 數 | 2000 | 否 |
| `API_HOST` | API 服務主機 | 0.0.0.0 | 否 |
| `API_PORT` | API 服務端口 | 8001 | 否 |
| `API_RELOAD` | 開發模式自動重載 | true | 否 |
| `RAG_COLLECTION` | 預設集合名稱 | embedding-seperate | 否 |
| `RAG_MODE` | 預設搜尋模式 | hybrid | 否 |
| `RAG_LIMIT` | 預設搜尋結果數 | 10 | 否 |
| `RAG_SCORE_THRESHOLD` | 預設分數閾值 | 1 | 否 |

## 依賴項目

- **FastAPI**: Web 框架
- **Uvicorn**: ASGI 伺服器
- **Pydantic**: 資料驗證
- **httpx**: HTTP 客戶端（用於呼叫 RAG API）
- **OpenAI**: OpenAI Python SDK
- **python-dotenv**: 環境變數載入

## 開發指南

### 日誌格式

```
%(asctime)s | %(levelname)s | %(message)s
```

### 錯誤處理

遵循使用者規則，不使用 try-catch，讓錯誤自然傳播至 FastAPI 層統一處理。

### 程式碼風格

- 模組化：每個功能獨立模組
- 單一職責：每個類別只負責一件事
- 依賴注入：透過建構函數注入依賴
- 無交叉依賴：模組間透過介面互動

## 測試

### 健康檢查

```bash
curl http://localhost:8001/health
```

### 測試聊天

```bash
curl -X POST http://localhost:8001/chat/completion \
  -H "Content-Type: application/json" \
  -d '{"question": "詐欺車手的緩刑條件是什麼？"}'
```

## 常見問題

### Q: 如何更換 LLM 模型？

修改 `.env` 中的 `LLM_MODEL` 變數即可。

### Q: RAG 伺服器連接失敗怎麼辦？

1. 確認 RAG 伺服器是否運行在 `http://localhost:8000`
2. 檢查 `RAG_SERVER_URL` 環境變數設定
3. 查看 `/health` 端點檢查連接狀態

### Q: 如何調整回答的詳細程度？

調整 `.env` 中的 `LLM_TEMPERATURE` 和 `LLM_MAX_TOKENS` 參數。

## 版本資訊

- **版本**: 1.0.0
- **Python**: >= 3.12
- **架構**: Clean Architecture

## 授權

本專案遵循專案根目錄的授權條款。

