# 系統架構文件

## 架構概覽

本專案採用 Clean Architecture 分層架構，符合 SOLID 原則和使用者的程式碼風格指南。

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
│  - 路由定義                         │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│       Services (服務層)             │
│  - 核心業務邏輯                     │
│  - RAG 整合與 LLM 呼叫              │
│  - Prompt 建構                      │
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

## 資料流動

### 完整聊天流程

```
1. 使用者發送 POST /chat/completion 請求
   ↓
2. FastAPI 驗證 ChatRequest（Entities）
   ↓
3. ChatController 接收請求
   ↓
4. Controller 調用 ChatService.process_chat()
   ↓
5. ChatService 建立 RAGSearchRequest
   ↓
6. 呼叫 RAGClient.search() → http://localhost:8000/search
   ↓
7. RAG 伺服器返回相關判決資料（RAGSearchResponse）
   ↓
8. ChatService 調用 build_prompt() 組合提示
   ↓
9. 呼叫 LLMProvider.generate_response()
   ↓
10. OpenAI API 返回生成的回答
   ↓
11. ChatService 組合結果（答案 + 來源）
   ↓
12. Controller 包裝為 ChatResponse
   ↓
13. FastAPI 返回 JSON 回應給使用者
```

## 層級詳細說明

### 1. Controllers（控制器層）

**職責**:
- 接收 HTTP 請求
- 驗證輸入資料（透過 Pydantic）
- 呼叫服務層
- 格式化回應
- 處理 HTTP 層級的錯誤

**檔案**:
- `controllers/chat_controller.py`: 聊天控制器
- `controllers/api_router.py`: API 路由定義

**依賴**:
- Services 層
- Entities 層
- Config 層

**範例**:
```python
class ChatController:
    def __init__(
        self,
        chat_service: IChatService,
        rag_client: IRAGClient,
        llm_provider: ILLMProvider,
        settings: Settings
    ):
        self.chat_service = chat_service
        # ...
```

### 2. Services（服務層）

**職責**:
- 實作核心業務邏輯
- 協調 Infrastructure 層（RAG + LLM）
- 建構 Prompt
- 與 HTTP 無關的純邏輯
- 可獨立測試

**檔案**:
- `services/chat_service.py`: 聊天處理邏輯

**依賴**:
- Infrastructure 層
- Domain 層
- Entities 層
- Config 層

**核心方法**:
```python
async def process_chat(
    question: str,
    collection: str,
    mode: str,
    limit: int,
    score_threshold: float,
    temperature: float,
    max_tokens: int
) -> Dict[str, Any]
```

### 3. Infrastructure（基礎設施層）

**職責**:
- 封裝外部依賴
- 實作 Domain 層定義的介面
- 與外部系統互動（RAG API、OpenAI API）
- 可替換的實作

**檔案**:
- `infrastructure/rag_client.py`: RAG 伺服器 HTTP 客戶端
- `infrastructure/llm_provider.py`: OpenAI LLM 提供者

**依賴**:
- Domain 層（實作介面）
- Entities 層
- Config 層
- 第三方套件（httpx, openai）

**RAG Client 範例**:
```python
class RAGClient(IRAGClient):
    async def search(self, request: RAGSearchRequest) -> RAGSearchResponse:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            return RAGSearchResponse(**response.json())
```

**LLM Provider 範例**:
```python
class OpenAIProvider(ILLMProvider):
    async def generate_response(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int
    ) -> str:
        response = await self.client.chat.completions.create(...)
        return response.choices[0].message.content
```

### 4. Domain（領域層）

**職責**:
- 定義抽象介面（ABC）
- 定義業務契約
- 不包含任何實作

**檔案**:
- `domain/interfaces.py`: 所有介面定義

**介面**:
- `IRAGClient`: RAG 客戶端介面
- `ILLMProvider`: LLM 提供者介面
- `IChatService`: 聊天服務介面

**範例**:
```python
class ILLMProvider(ABC):
    @abstractmethod
    async def generate_response(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int
    ) -> str:
        pass
```

### 5. Entities（實體層）

**職責**:
- 定義資料結構
- 領域模型
- 業務規則（通過 Pydantic 驗證）

**檔案**:
- `entities/models.py`: 所有資料模型

**主要模型**:
- `ChatRequest`: 聊天請求
- `ChatResponse`: 聊天回應
- `RAGSearchRequest`: RAG 搜尋請求
- `RAGSearchResponse`: RAG 搜尋回應
- `ChatMessage`: 聊天訊息
- `HealthStatus`: 健康狀態

**依賴**:
- 無（最內層之一）

### 6. Config（配置層）

**職責**:
- 載入環境變數
- 提供配置物件
- 驗證必要配置

**檔案**:
- `config/settings.py`: 環境變數管理

**配置類別**:
- `RAGServerConfig`: RAG 伺服器設定
- `LLMConfig`: LLM 設定
- `APIConfig`: API 服務設定
- `RAGSearchConfig`: RAG 搜尋預設值
- `Settings`: 統一配置管理

**依賴**:
- 無（最內層）

## 依賴注入模式

在 `main.py` 的 `lifespan` 函式中初始化所有依賴：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 載入配置（最內層）
    settings = Settings()
    
    # 2. 建立 Infrastructure（實作外部依賴）
    rag_client = RAGClient(settings)
    llm_provider = OpenAIProvider(settings)
    
    # 3. 建立 Services（業務邏輯）
    chat_service = ChatService(
        rag_client=rag_client,
        llm_provider=llm_provider,
        settings=settings
    )
    
    # 4. 建立 Controllers（HTTP 處理）
    chat_controller = ChatController(
        chat_service=chat_service,
        rag_client=rag_client,
        llm_provider=llm_provider,
        settings=settings
    )
    
    # 5. 建立路由
    router = create_router(chat_controller)
    app.include_router(router)
    
    yield
```

## 設計原則遵循

### 1. 單一職責原則（SRP）
每個類別只有一個改變的理由：
- `ChatController`: 處理 HTTP 請求
- `ChatService`: 執行業務邏輯
- `RAGClient`: 與 RAG API 互動
- `OpenAIProvider`: 與 OpenAI API 互動

### 2. 依賴反轉原則（DIP）
高層模組不依賴低層模組：
- Controllers 依賴 Services 介面（IChatService）
- Services 依賴 Infrastructure 介面（IRAGClient, ILLMProvider）

### 3. 開放封閉原則（OCP）
對擴展開放，對修改封閉：
- 新增 LLM 提供者：實作 `ILLMProvider` 介面
- 新增搜尋邏輯：擴展 `ChatService`
- 替換實作只需修改 `main.py` 的依賴注入

### 4. 介面隔離原則（ISP）
客戶端不應依賴它不使用的介面：
- 每個 Interface 只暴露必要的方法
- Controller 只依賴必要的 Service 方法

### 5. 里氏替換原則（LSP）
子類別可以替換父類別：
- 任何實作 `ILLMProvider` 的類別都可互換
- 任何實作 `IRAGClient` 的類別都可互換

## 模組邊界

```
┌─────────────────────────────────────┐
│           應用程式邊界               │
│                                     │
│  ┌─────────────────────────────┐   │
│  │      業務邏輯核心            │   │
│  │  (Services + Entities)      │   │
│  │  - 可獨立測試                │   │
│  │  - 不依賴框架                │   │
│  └─────────────────────────────┘   │
│              ↕                      │
│  ┌─────────────────────────────┐   │
│  │      基礎設施適配器          │   │
│  │  (Infrastructure)           │   │
│  │  - 可替換實作                │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
          ↕
┌─────────────────────────────────────┐
│         外部系統                     │
│  - RAG Server (http://localhost:8000)│
│  - OpenAI API                       │
└─────────────────────────────────────┘
```

## 錯誤處理策略

遵循「快速失敗」原則（使用者要求）：

1. **不使用 try-catch**
2. **讓錯誤自然傳播**
3. **在最外層（FastAPI）統一處理**
4. **提供清晰的錯誤訊息**

範例：
```python
# ✅ 正確
async def search(self, request):
    response = await self.client.post(url, json=payload)
    response.raise_for_status()
    return RAGSearchResponse(**response.json())

# ❌ 錯誤（使用者禁止）
async def search(self, request):
    try:
        response = await self.client.post(url, json=payload)
        return RAGSearchResponse(**response.json())
    except Exception as e:
        logger.error(f"Error: {e}")
        return None
```

## 日誌策略

遵循「最少日誌」原則（使用者要求）：

1. **只記錄關鍵步驟**
2. **格式統一**: `時間 | 層級 | 訊息`
3. **不記錄詳細堆疊**
4. **避免冗餘資訊**
5. **不使用 emoji**

範例：
```python
logger.info(f"處理聊天請求: {question}")
logger.info(f"RAG 搜尋完成，共 {total} 筆結果")
logger.info(f"LLM 生成回應完成")
```

## 擴展性考量

### 新增 LLM 提供者

在 `infrastructure/` 下新增實作：

```python
# infrastructure/claude_provider.py
class ClaudeProvider(ILLMProvider):
    async def generate_response(self, messages, temperature, max_tokens):
        # 實作 Claude API
        pass
```

在 `main.py` 中替換：
```python
llm_provider = ClaudeProvider(settings)
```

### 新增 RAG 後端

```python
# infrastructure/custom_rag_client.py
class CustomRAGClient(IRAGClient):
    async def search(self, request):
        # 實作自訂 RAG 邏輯
        pass
```

### 自訂 Prompt 模板

修改 `services/chat_service.py` 的 `build_prompt` 方法。

### 新增 API 端點

在 `controllers/api_router.py` 中新增路由：
```python
@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    return await controller.chat_stream(request)
```

在 `controllers/chat_controller.py` 中新增方法：
```python
async def chat_stream(self, request: ChatRequest):
    # 實作串流回應
    pass
```

## 效能考量

1. **非同步處理**: 所有 I/O 操作使用 async/await
2. **HTTP 連線池**: httpx 自動管理
3. **超時設定**: RAG_SERVER_TIMEOUT 控制請求超時
4. **快取機制**: 未來可在 Service 層加入

## 安全性考量

1. **API Key 管理**: 透過環境變數，不寫入程式碼
2. **輸入驗證**: Pydantic 模型自動驗證
3. **錯誤訊息**: 不洩漏內部實作細節
4. **HTTPS**: 生產環境建議使用 HTTPS

## 測試策略

### 單元測試
測試每個 Service 的純邏輯：
```python
def test_chat_service_build_prompt():
    service = ChatService(mock_rag, mock_llm, settings)
    messages = service.build_prompt(question, sources)
    assert len(messages) == 2
    assert messages[0].role == "system"
```

### 整合測試
測試 Controller + Service：
```python
async def test_chat_controller():
    controller = ChatController(...)
    response = await controller.chat_completion(request)
    assert response.answer is not None
```

### E2E 測試
測試完整 API 流程：
```python
async def test_chat_completion_endpoint():
    async with AsyncClient(app=app) as client:
        response = await client.post("/chat/completion", json=data)
        assert response.status_code == 200
```

## 版本控制

- **版本**: 1.0.0
- **最後更新**: 2025-11
- **Python**: >= 3.12
- **架構**: Clean Architecture

## 參考資料

- Clean Architecture by Robert C. Martin
- SOLID Principles
- Dependency Inversion Principle
- Domain-Driven Design

