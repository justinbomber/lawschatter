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
│  - 依賴: Domain, Entities, Config       │
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

**範例**:
```python
# config/settings.py
@dataclass
class Settings:
    qdrant: QdrantConfig
    openai: OpenAIConfig
```

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

**範例**:
```python
# entities/models.py
class SearchRequest(BaseModel):
    collection: str
    query_text: str
```

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

**範例**:
```python
# domain/interfaces.py
class ISearchService(ABC):
    @abstractmethod
    def search(self, client, config):
        pass
```

### Layer 4: Infrastructure（基礎設施層）

**位置**: 外層  
**依賴**: Domain, Entities, Config  
**職責**:
- 實作 Domain 層定義的介面
- 與外部系統互動（資料庫、API）

**規則**:
- ✅ 實作 Domain 層的抽象介面
- ✅ 可依賴第三方套件
- ✅ 可使用 Config
- ❌ 不包含業務邏輯
- ❌ 不直接被 Controllers 依賴

**範例**:
```python
# infrastructure/embeddings/dense_embedding.py
class DenseEmbeddingProvider(IEmbeddingProvider):
    def embed_query(self, text: str):
        return self.embeddings.embed_query(text)
```

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

**範例**:
```python
# services/search_service.py
class SearchService(ISearchService):
    def __init__(self, dense_provider, sparse_provider):
        self.dense = dense_provider
        self.sparse = sparse_provider
```

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

**範例**:
```python
# controllers/search_controller.py
class SearchController:
    def __init__(self, search_service: ISearchService):
        self.search_service = search_service
```

## 介面隔離原則

### 為什麼需要介面？

1. **降低耦合**: 高層模組只依賴抽象，不依賴具體實作
2. **易於測試**: 可注入 Mock 物件
3. **易於替換**: 替換實作不影響使用者
4. **明確契約**: 清楚定義行為預期

### 介面定義規範

```python
# domain/interfaces.py
class IServiceName(ABC):
    """服務說明
    
    職責：
    - 職責1
    - 職責2
    
    依賴：
    - 依賴1
    """
    
    @abstractmethod
    def method_name(self, param: Type) -> ReturnType:
        """方法說明
        
        Args:
            param: 參數說明
            
        Returns:
            返回值說明
        """
        pass
```

## 依賴注入模式

### 建構子注入（推薦）

```python
class SearchController:
    def __init__(
        self,
        search_service: ISearchService,
        filter_service: IFilterService
    ):
        self.search_service = search_service
        self.filter_service = filter_service
```

### 依賴注入容器

在 `main.py` 中統一建立和注入：

```python
def create_app():
    # 1. 載入配置
    settings = Settings()
    
    # 2. 建立 Infrastructure
    qdrant_client = QdrantClientWrapper(settings)
    dense_provider = DenseEmbeddingProvider(settings)
    sparse_provider = SparseEmbeddingProvider(settings)
    
    # 3. 建立 Services
    search_service = SearchService(dense_provider, sparse_provider)
    filter_service = FilterService(settings)
    
    # 4. 建立 Controllers
    search_controller = SearchController(
        search_service=search_service,
        filter_service=filter_service
    )
    
    return app, search_controller
```

## 錯誤處理策略

### 快速失敗原則

**禁止使用 try-catch**，讓錯誤自然傳播到最外層。

```python
# ❌ 錯誤示範
def search(self, query):
    try:
        result = self.client.query(query)
        return result
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

# ✅ 正確示範
def search(self, query):
    result = self.client.query(query)
    return result
```

### 錯誤處理位置

只在 **FastAPI 層級** 統一處理錯誤：

```python
# main.py
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)}
    )
```

## 配置管理規範

### 環境變數規範

所有配置必須透過環境變數：

```python
# ✅ 正確
settings = Settings()
api_key = settings.openai.api_key

# ❌ 錯誤
api_key = os.getenv("OPENAI_API_KEY")
```

### 配置驗證

在 Settings 初始化時驗證：

```python
class Settings:
    def __init__(self):
        self.api_key = self._get_required_env("API_KEY")
    
    @staticmethod
    def _get_required_env(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise EnvironmentError(f"{key} is required")
        return value
```

## 測試策略

### 單元測試

測試每個 Service 的純邏輯：

```python
def test_search_service():
    # Arrange
    mock_provider = Mock(spec=IEmbeddingProvider)
    service = SearchService(mock_provider, mock_provider)
    
    # Act
    result = service.search(mock_client, config)
    
    # Assert
    assert result is not None
```

### 整合測試

測試 Controller + Service：

```python
def test_search_controller():
    # Arrange
    settings = Settings()
    service = SearchService(...)
    controller = SearchController(service, ...)
    
    # Act
    response = controller.search_documents(request)
    
    # Assert
    assert response.total > 0
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
search_service = SearchService(dense_provider, sparse_provider)

# 替換後
search_service = NewSearchService(custom_provider)
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

## 常見錯誤與解決方案

### 錯誤 1: 跨層直接調用

```python
# ❌ 錯誤：Controller 直接使用 Infrastructure
class SearchController:
    def __init__(self):
        self.client = QdrantClient()  # 錯誤

# ✅ 正確：透過 Service 層
class SearchController:
    def __init__(self, search_service: ISearchService):
        self.search_service = search_service
```

### 錯誤 2: 內層依賴外層

```python
# ❌ 錯誤：Entity 依賴 Service
class SearchRequest(BaseModel):
    def execute(self):
        service = SearchService()  # 錯誤

# ✅ 正確：Entity 只定義資料
class SearchRequest(BaseModel):
    collection: str
    query_text: str
```

### 錯誤 3: 直接讀取環境變數

```python
# ❌ 錯誤
class SearchService:
    def __init__(self):
        self.api_key = os.getenv("API_KEY")

# ✅ 正確
class SearchService:
    def __init__(self, settings: Settings):
        self.api_key = settings.openai.api_key
```

## 版本控制

- **版本**: 2.0
- **最後更新**: 2025-01
- **負責人**: Architecture Team

## 參考資料

- Clean Architecture by Robert C. Martin
- Dependency Inversion Principle
- SOLID Principles

