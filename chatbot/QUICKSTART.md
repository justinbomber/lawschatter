# 快速開始指南

## 📁 專案結構

```
chatbot/
├── config/                 # ⚙️ 配置層（最內層）
│   ├── __init__.py
│   └── settings.py         # 環境變數管理
│
├── entities/               # 📦 實體層（資料模型）
│   ├── __init__.py
│   └── models.py           # ChatRequest, ChatResponse 等
│
├── domain/                 # 🎯 領域層（抽象介面）
│   ├── __init__.py
│   └── interfaces.py       # ILLMProvider, IRAGClient, IChatService
│
├── infrastructure/         # 🔧 基礎設施層（外部適配）
│   ├── __init__.py
│   ├── rag_client.py       # RAG 伺服器客戶端
│   └── llm_provider.py     # OpenAI LLM 提供者
│
├── services/               # 💼 服務層（業務邏輯）
│   ├── __init__.py
│   └── chat_service.py     # 聊天處理邏輯
│
├── controllers/            # 🎮 控制器層（HTTP 處理）
│   ├── __init__.py
│   ├── chat_controller.py  # 聊天控制器
│   └── api_router.py       # API 路由定義
│
├── main.py                 # 🚀 應用程式入口點
├── pyproject.toml          # 📋 專案配置
├── requirements.txt        # 📦 依賴清單
├── .env.example            # 📝 環境變數範本
├── .gitignore              # 🚫 Git 忽略規則
├── README.md               # 📖 完整說明文件
├── CLEAN_ARCHITECTURE_RULES.md  # 📐 架構規範
└── QUICKSTART.md           # ⚡ 本文件
```

## 🚀 五分鐘快速啟動

### 步驟 1: 安裝依賴

```bash
cd chatbot
pip install -r requirements.txt
```

### 步驟 2: 配置環境變數

```bash
# 複製範本
cp .env.example .env

# 編輯 .env，填入你的 OpenAI API Key
# 最少需要設定：LLM_API_KEY
```

`.env` 範例：
```env
LLM_API_KEY=sk-proj-xxxxxxxxxxxxx
RAG_SERVER_URL=http://localhost:8000
```

### 步驟 3: 確認 RAG 伺服器運行

確保 RAG 伺服器運行在 `http://localhost:8000`

```bash
# 測試 RAG 伺服器
curl http://localhost:8000/health
```

### 步驟 4: 啟動聊天機器人服務

```bash
python main.py
```

服務將運行在 `http://localhost:8001`

### 步驟 5: 測試 API

**方式 1: 使用瀏覽器**
訪問 http://localhost:8001/docs

**方式 2: 使用 curl**
```bash
curl -X POST http://localhost:8001/chat/completion \
  -H "Content-Type: application/json" \
  -d '{"question": "有沒有未認罪，但法院還是給予緩刑的詐欺車手案例"}'
```

**方式 3: 使用 Python**
```python
import requests

response = requests.post(
    "http://localhost:8001/chat/completion",
    json={"question": "詐欺車手的緩刑條件是什麼？"}
)

print(response.json()["answer"])
```

## 📊 API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/` | GET | 根路徑，顯示服務資訊 |
| `/chat/completion` | POST | 聊天完成端點 |
| `/health` | GET | 健康檢查 |
| `/docs` | GET | Swagger API 文件 |

## 💡 請求範例

### 最簡請求
```json
{
  "question": "詐欺車手的緩刑條件是什麼？"
}
```

### 完整參數
```json
{
  "question": "有沒有未認罪，但法院還是給予緩刑的詐欺車手案例",
  "collection": "embedding-seperate",
  "mode": "hybrid",
  "limit": 10,
  "score_threshold": 1,
  "temperature": 0.7,
  "max_tokens": 2000
}
```

## 🔧 環境變數說明

### 必填項目 ⚠️
```env
LLM_API_KEY=your_openai_api_key_here
```

### 選填項目
```env
# RAG 設定
RAG_SERVER_URL=http://localhost:8000
RAG_SERVER_TIMEOUT=30

# LLM 設定
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# API 設定
API_HOST=0.0.0.0
API_PORT=8001
API_RELOAD=true

# RAG 搜尋預設
RAG_COLLECTION=embedding-seperate
RAG_MODE=hybrid
RAG_LIMIT=10
RAG_SCORE_THRESHOLD=1
```

## 🏗️ 架構特色

### Clean Architecture
- ✅ **分層清晰**: Config → Entities/Domain → Infrastructure → Services → Controllers
- ✅ **依賴注入**: 所有依賴在 main.py 統一管理
- ✅ **介面抽象**: 易於替換 LLM 或 RAG 實作
- ✅ **模組化**: 每層職責單一，易於測試

### 工作流程
```
使用者請求 → Controller → Service → RAG Client (搜尋) → Service → LLM Provider (生成) → Controller → 回應
```

## 🔄 工作原理

1. **接收問題**: 使用者透過 `/chat/completion` 發送問題
2. **RAG 搜尋**: 系統呼叫 RAG 伺服器搜尋相關判決
3. **建立提示**: 將搜尋結果與問題組合成 LLM 提示
4. **生成回答**: LLM 根據相關判決生成回答
5. **返回結果**: 包含答案和引用來源

## 🛠️ 常見問題

### Q: RAG 伺服器連接失敗
```bash
# 檢查 RAG 伺服器狀態
curl http://localhost:8000/health

# 查看聊天機器人健康狀態
curl http://localhost:8001/health
```

### Q: OpenAI API Key 錯誤
確認 `.env` 中的 `LLM_API_KEY` 設定正確。

### Q: 修改回答風格
調整 `.env` 中的 `LLM_TEMPERATURE`：
- 0.0-0.3: 更保守、精確
- 0.4-0.7: 平衡
- 0.8-2.0: 更有創意

### Q: 搜尋結果不夠
增加 `.env` 中的 `RAG_LIMIT` 數值。

## 🎯 下一步

1. 閱讀 [README.md](README.md) 了解完整功能
2. 查看 [CLEAN_ARCHITECTURE_RULES.md](CLEAN_ARCHITECTURE_RULES.md) 理解架構規範
3. 訪問 http://localhost:8001/docs 探索 API

## 📞 需要幫助？

查看完整文件：[README.md](README.md)

