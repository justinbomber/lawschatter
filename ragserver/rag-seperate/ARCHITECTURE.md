# 系統架構文件

## 架構概覽

本專案採用分層架構（Layered Architecture），符合 Clean Code 原則。

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
│  - 錯誤處理與日誌                   │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│       Services (服務層)             │
│  - 核心業務邏輯                     │
│  - 搜尋、過濾、重新排序             │
│  - 不依賴 HTTP 層                   │
└─────────────────────────────────────┘
                  ↓
┌──────────────────┬──────────────────┐
│  Infrastructure  │    Entities      │
│  (基礎設施層)    │   (實體層)       │
│  - 外部依賴      │   - 資料模型     │
│  - Qdrant 客戶端 │   - 領域物件     │
│  - 嵌入模型      │   - Pydantic 模型│
│  - 分詞器        │                  │
└──────────────────┴──────────────────┘
```

## 層級詳細說明

### 1. Controllers（控制器層）

**職責**:
- 接收 HTTP 請求
- 驗證輸入資料
- 呼叫服務層
- 格式化回應
- 處理 HTTP 層級的錯誤

**檔案**:
- `controllers/search_controller.py`

**依賴**:
- Services 層
- Entities 層

### 2. Services（服務層）

**職責**:
- 實作核心業務邏輯
- 協調 Infrastructure 層
- 與 HTTP 無關的純邏輯
- 可獨立測試

**檔案**:
- `services/search_service.py`: 向量搜尋邏輯
- `services/filter_service.py`: 過濾條件處理
- `services/rerank_service.py`: 結果重新排序

**依賴**:
- Infrastructure 層
- Entities 層

### 3. Infrastructure（基礎設施層）

**職責**:
- 封裝外部依賴
- 提供技術實作細節
- 可替換的實作

**檔案**:
- `infrastructure/qdrant_client_wrapper.py`: Qdrant 客戶端
- `infrastructure/tokenizer.py`: 分詞器
- `infrastructure/embeddings/dense_embedding.py`: 語意向量
- `infrastructure/embeddings/sparse_embedding.py`: 稀疏向量

**依賴**:
- 第三方套件（Qdrant, Jieba, Google AI, FastEmbed）

### 4. Entities（實體層）

**職責**:
- 定義資料結構
- 領域模型
- 業務規則（通過 Pydantic 驗證）

**檔案**:
- `entities/models.py`: API 模型
- `entities/filters.py`: 過濾條件模型

**依賴**:
- 無（最內層）

## 資料流動

### 搜尋請求流程

```
1. 使用者發送 POST /search 請求
   ↓
2. FastAPI 驗證 SearchRequest（Entities）
   ↓
3. SearchController 接收請求
   ↓
4. Controller 調用 FilterService.extract_filter_conditions()
   ↓
5. FilterService 使用 OpenAI 提取結構化條件
   ↓
6. FilterService 轉換為 Qdrant 過濾格式
   ↓
7. Controller 調用 SearchService.search()
   ↓
8. SearchService 使用 EmbeddingProvider 生成向量
   ↓
9. SearchService 調用 Qdrant 客戶端執行搜尋
   ↓
10. SearchService 展平結果
   ↓
11. Controller 包裝為 SearchResponse
   ↓
12. FastAPI 返回 JSON 回應
```

## 依賴注入模式

在 `main.py` 的 `lifespan` 函式中初始化所有依賴：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 建立基礎設施
    qdrant_wrapper = QdrantClientWrapper()
    
    # 建立服務
    search_service = SearchService()
    filter_service = FilterService()
    
    # 建立控制器（注入依賴）
    search_controller = SearchController(
        qdrant_client=qdrant_wrapper.get_client(),
        search_service=search_service,
        filter_service=filter_service
    )
    
    yield
```

## 設計原則遵循

### 1. 單一職責原則（SRP）
每個類別只有一個改變的理由：
- `SearchController`: 處理 HTTP 請求
- `SearchService`: 執行搜尋邏輯
- `FilterService`: 處理過濾條件
- `RerankService`: 重新排序

### 2. 依賴反轉原則（DIP）
高層模組不依賴低層模組：
- Controllers 依賴 Services 抽象
- Services 依賴 Infrastructure 接口

### 3. 開放封閉原則（OCP）
對擴展開放，對修改封閉：
- 新增搜尋模式：擴展 `SearchService`
- 新增嵌入提供者：實作 `EmbeddingProvider` 接口

### 4. 介面隔離原則（ISP）
客戶端不應依賴它不使用的介面：
- 每個 Service 只暴露需要的方法
- Controller 只依賴必要的 Service 方法

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
│  - Qdrant                           │
│  - OpenAI                           │
│  - Google AI                        │
│  - Cohere                           │
└─────────────────────────────────────┘
```

## 錯誤處理策略

遵循「快速失敗」原則：

1. **不使用 try-catch**
2. **讓錯誤自然傳播**
3. **在最外層（FastAPI）統一處理**
4. **提供清晰的錯誤訊息**

## 日誌策略

遵循「最少日誌」原則：

1. **只記錄關鍵步驟**
2. **格式統一**: `時間 | 層級 | 訊息`
3. **不記錄詳細堆疊**
4. **避免冗餘資訊**

## 測試策略

1. **單元測試**: 測試每個 Service 的純邏輯
2. **整合測試**: 測試 Controller + Service
3. **E2E 測試**: 測試完整 API 流程

## 擴展性考量

### 新增搜尋模式
在 `SearchService` 中新增方法：
```python
def _search_custom(self, client, config):
    # 實作新模式
    pass
```

### 新增過濾器類型
在 `entities/filters.py` 中擴展模型：
```python
class NewFilter(BaseModel):
    # 新欄位
    pass
```

### 替換向量提供者
實作新的 `EmbeddingProvider`：
```python
class CustomEmbeddingProvider:
    def embed_query(self, text: str):
        # 自訂實作
        pass
```

## 效能考量

1. **向量快取**: 可在 `SearchService` 中加入快取層
2. **連線池**: `QdrantClientWrapper` 管理連線
3. **批次處理**: Service 層支援批次操作
4. **非同步處理**: 未來可擴展為 async/await

## 安全性考量

1. **API Key 管理**: 透過環境變數
2. **輸入驗證**: Pydantic 模型自動驗證
3. **錯誤訊息**: 不洩漏內部實作細節
