# Clean Architecture 架構準則

## 核心原則

### 1. 依賴規則（Dependency Rule）

**最重要的規則**：依賴只能由外向內，內層不得依賴外層。

```
外層 → 內層（允許）
內層 → 外層（禁止）
```

### 層級依賴圖

```
┌─────────────────────────────────────────┐
│  Controllers (最外層)                    │
│  - 依賴: Services, Entities, Config     │
│  - 職責: HTTP 請求處理                   │
└─────────────────────────────────────────┘
              ↓ 依賴方向
┌─────────────────────────────────────────┐
│  Services (應用層)                       │
│  - 依賴: Domain, Infrastructure,        │
│          Entities, Config               │
│  - 職責: 業務邏輯實作                    │
└─────────────────────────────────────────┘
              ↓ 依賴方向
┌─────────────────────────────────────────┐
│  Infrastructure (基礎設施層)             │
│  - 依賴: Domain, Entities, Config       │
│  - 職責: 外部系統適配                    │
└─────────────────────────────────────────┘
              ↓ 依賴方向
┌──────────────────┬──────────────────────┐
│  Domain (領域層) │  Entities (實體層)    │
│  - 依賴: 無      │  - 依賴: 無           │
│  - 職責: 抽象介面│  - 職責: 資料模型     │
└──────────────────┴──────────────────────┘
              ↓ 依賴方向
┌─────────────────────────────────────────┐
│  Config (配置層 - 最內層)                │
│  - 依賴: 無                              │
│  - 職責: 環境變數管理                    │
└─────────────────────────────────────────┘
```

## 分層詳細說明

### Layer 1: Config（配置層）

**位置**: 最內層  
**依賴**: 無  
**職責**: 
- 載入環境變數
- 提供配置物件
- 驗證必要配置

**規則**:
- ✅ 只讀取環境變數
- ✅ 提供不可變的配置物件
- ❌ 不依賴任何其他層
- ❌ 不包含業務邏輯

### Layer 2: Entities（實體層）

**位置**: 內層  
**依賴**: 無  
**職責**:
- 定義資料模型
- 定義業務規則（透過 Pydantic 驗證）

**規則**:
- ✅ 純資料類別
- ✅ 使用 Pydantic 驗證
- ❌ 不包含業務邏輯
- ❌ 不依賴外部套件（Pydantic 除外）

### Layer 3: Domain（領域層）

**位置**: 內層  
**依賴**: 無  
**職責**:
- 定義抽象介面（ABC）
- 定義業務契約

**規則**:
- ✅ 只包含抽象類別
- ✅ 定義業務契約
- ❌ 不包含實作
- ❌ 不依賴具體實作

### Layer 4: Infrastructure（基礎設施層）

**位置**: 外層  
**依賴**: Domain, Entities, Config  
**職責**:
- 實作 Domain 層定義的介面
- 與外部系統互動（RAG API、LLM API）

**規則**:
- ✅ 實作 Domain 層的抽象介面
- ✅ 可依賴第三方套件
- ✅ 可使用 Config
- ❌ 不包含業務邏輯
- ❌ 不直接被 Controllers 依賴

### Layer 5: Services（服務層）

**位置**: 外層  
**依賴**: Domain, Infrastructure, Entities, Config  
**職責**:
- 實作業務邏輯
- 協調 Infrastructure 層

**規則**:
- ✅ 實作 Domain 層的抽象介面
- ✅ 協調多個 Infrastructure 元件
- ✅ 可使用 Config
- ❌ 不包含 HTTP 邏輯
- ❌ 不直接處理環境變數

### Layer 6: Controllers（控制器層）

**位置**: 最外層  
**依賴**: Services, Entities, Config  
**職責**:
- 處理 HTTP 請求
- 調用 Services
- 返回 HTTP 回應

**規則**:
- ✅ 只處理 HTTP 相關邏輯
- ✅ 調用 Services 執行業務邏輯
- ✅ 可使用 Config
- ❌ 不包含業務邏輯
- ❌ 不直接使用 Infrastructure

## 依賴注入模式

### 建構子注入（推薦）

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
        self.rag_client = rag_client
        self.llm_provider = llm_provider
        self.settings = settings
```

### 依賴注入容器

在 `main.py` 中統一建立和注入：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 載入配置
    settings = Settings()
    
    # 2. 建立 Infrastructure
    rag_client = RAGClient(settings)
    llm_provider = OpenAIProvider(settings)
    
    # 3. 建立 Services
    chat_service = ChatService(rag_client, llm_provider, settings)
    
    # 4. 建立 Controllers
    chat_controller = ChatController(
        chat_service=chat_service,
        rag_client=rag_client,
        llm_provider=llm_provider,
        settings=settings
    )
    
    yield
```

## 錯誤處理策略

### 快速失敗原則

**禁止使用 try-catch**，讓錯誤自然傳播到最外層。

```python
# ❌ 錯誤示範
async def search(self, request):
    try:
        result = await self.client.post(url)
        return result
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

# ✅ 正確示範
async def search(self, request):
    result = await self.client.post(url)
    return result
```

## 配置管理規範

### 環境變數規範

所有配置必須透過環境變數：

```python
# ✅ 正確
settings = Settings()
api_key = settings.llm.api_key

# ❌ 錯誤
api_key = os.getenv("LLM_API_KEY")
```

## 擴展準則

### 新增功能

1. **定義介面** (domain/)
2. **建立實體** (entities/)
3. **實作 Infrastructure** (infrastructure/)
4. **實作 Service** (services/)
5. **建立 Controller** (controllers/)
6. **更新 main.py** 依賴注入

### 替換實作

只需修改 `main.py` 的依賴注入：

```python
# 替換前
llm_provider = OpenAIProvider(settings)

# 替換後
llm_provider = ClaudeProvider(settings)
```

## 程式碼審查檢查清單

### 依賴檢查

- [ ] 內層不依賴外層
- [ ] 使用抽象介面而非具體類別
- [ ] 透過建構子注入依賴

### 職責檢查

- [ ] 每個類別只有一個職責
- [ ] Controllers 不包含業務邏輯
- [ ] Services 不包含 HTTP 邏輯
- [ ] Infrastructure 不包含業務邏輯

### 配置檢查

- [ ] 所有配置透過 Settings
- [ ] 不直接使用 os.getenv()
- [ ] 必要配置有驗證

### 錯誤處理檢查

- [ ] 不使用 try-catch
- [ ] 錯誤向上傳播
- [ ] 在 FastAPI 層統一處理

