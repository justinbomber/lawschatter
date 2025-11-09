# RAG 搜尋服務整合歷史對話功能

## 功能概述

本次更新整合了 Supabase 歷史對話功能到 RAG 搜尋服務，使用 LangChain 的 ConversationChain 將歷史訊息與當前問題重組後進行搜尋。

## 主要變更

### 1. 資料模型層

#### `entities/filters.py`
- 新增 `limit` 欄位（Optional[int]，默認值 5）
- LLM 會根據問題複雜度決定返回結果數量（範圍 1-20）

#### `entities/models.py`
- `SearchRequest` 保留 `conversation_id` 和 `query_text` 欄位
- 移除已註解的 collection、mode、limit 欄位（這些參數現在寫死在 controller 中）

### 2. 配置層

#### `config/settings.py`
- 新增 `SupabaseConfig` dataclass（url, key, schema_name）
- 新增 `llm_provider` 配置（環境變數 `LLM_PROVIDER`，默認為 "grok"）
- 支援動態選擇 Grok 或 OpenAI extraction service

### 3. 領域層

#### `domain/interfaces.py`
- 新增 `Message` dataclass：表示單一對話訊息
- 新增 `IConversationRepository` 接口：
  - `get_conversation_messages()`: 查詢歷史訊息
  - `verify_user_conversation_access()`: 驗證使用者訪問權限
- 新增 `IQueryRewriteService` 接口：
  - `rewrite_query_with_history()`: 使用歷史對話重組當前問題

### 4. 基礎設施層

#### `infrastructure/supabase_repository.py` (新建)
- 實現 `IConversationRepository` 接口
- **使用前端傳入的 JWT token 創建 Supabase client**（支援 RLS policy）
- 每次請求動態創建帶有使用者 token 的 client
- 使用 `supabase-py` 客戶端查詢 `lawschatter.messages` 表
- 按 `created_at` 排序取得最近 10 筆訊息
- 驗證使用者對 conversation 的訪問權限

### 5. 服務層

#### `services/query_rewrite_service.py` (新建)
- 實現 `IQueryRewriteService` 接口
- 使用 LangChain 的 ChatOpenAI 或 ChatXAI（根據 LLM_PROVIDER 配置）
- 將歷史訊息格式化為 LangChain 對話歷史（HumanMessage 和 AIMessage）
- 結合當前問題讓 LLM 重組為更完整的查詢

#### `services/grok_extraction_service.py` & `services/openai_extraction_service.py`
- 更新 system prompt 強調 `limit` 欄位必填
- 提供根據問題複雜度填入 limit 的指引

### 6. 控制器層

#### `controllers/api_router.py`
- 新增 `get_token_and_user_id()` 依賴函數
- 解析 `Authorization` header 中的 JWT token（Bearer token）
- 提取 token 中的 user_id（sub claim）
- **同時返回完整 token 和 user_id**
- `/search` endpoint 新增 `token` 和 `user_id` 參數（通過 Depends）

#### `controllers/search_controller.py`
- 新增 `conversation_repository` 和 `query_rewrite_service` 依賴
- `search_documents()` 方法流程：
  1. 驗證使用者對 conversation 的訪問權限
  2. 查詢歷史訊息（最近 10 筆）
  3. 使用 query_rewrite_service 重組問題
  4. 使用寫死的參數進行搜尋：
     - collection = "embedding-seperate"
     - mode = "hybrid"
     - limit = 5 (從 LLM extraction 結果中獲取)
     - score_threshold = 0.95

### 7. 主程式

#### `main.py`
- **不再在初始化時創建 Supabase client**（改為每次請求動態創建）
- 建立 `SupabaseConversationRepository` 實例（只傳入 settings）
- 建立 `QueryRewriteService` 實例
- 根據環境變數 `LLM_PROVIDER` 動態選擇 extraction service
- 將新服務注入到 `SearchController`

## 環境變數配置

請在 `.env` 檔案中添加以下配置：

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here
SUPABASE_SCHEMA=lawschatter

# LLM Provider Selection (openai or grok)
LLM_PROVIDER=grok
```

## API 使用方式

### 請求格式

```http
POST /search
Authorization: Bearer <supabase_jwt_token>
Content-Type: application/json

{
  "conversation_id": "uuid-of-conversation",
  "query_text": "給我車手的判決",
  "streaming": false
}
```

### 回應格式

```json
{
  "results": [...],
  "total": 5,
  "query": "車手角色的詐欺罪判決",
  "mode": "hybrid",
  "collection": "embedding-seperate"
}
```

## 流程說明

1. 前端發送請求時在 `Authorization` header 中帶入 Supabase JWT token
2. API 解析 token 提取 user_id 並保留完整 token
3. **使用前端的 JWT token 創建 Supabase client**（確保 RLS policy 生效）
4. 驗證 user_id 是否有權訪問指定的 conversation_id
5. 從 Supabase 查詢該 conversation 的最近 10 筆歷史訊息
6. 使用 LangChain 將歷史訊息和當前問題傳給 LLM 重組為完整查詢
7. 使用重組後的查詢進行 RAG 搜尋
8. 返回搜尋結果

## 依賴套件

新增的依賴套件已添加到 `requirements.txt`：
- `supabase>=2.0.0`: Supabase Python 客戶端
- `PyJWT>=2.8.0`: JWT token 解析
- `langchain>=0.3.0`: LangChain 核心框架
- `langchain-core>=0.3.0`: LangChain 核心功能
- `langchain-openai>=0.2.0`: OpenAI LLM 整合
- `langchain-xai>=0.1.0`: XAI (Grok) LLM 整合
- `instructor>=1.0.0`: 結構化輸出處理

## 注意事項

1. JWT token 解析目前未驗證簽名（`verify_signature=False`），生產環境應啟用簽名驗證
2. Collection、mode、limit、score_threshold 等參數已寫死在 controller 中
3. **使用前端傳入的 JWT token 創建 Supabase client，確保 RLS (Row Level Security) 正確生效**
4. **環境變數中的 `SUPABASE_KEY` 僅用於初始化，實際查詢使用前端 token**
5. 每次請求動態創建 Supabase client 以支援不同使用者
6. 歷史訊息限制為最近 10 筆
7. 問題重組使用 temperature=0 確保輸出一致性

