# RAG / Embedding 強弱連接雙路線優化實作總結

## 完成狀態

✅ **所有計畫中的功能均已完成實作**

## 一、Embedding 模組：一判決一 point 的新 collection 設計

### 1.1 Domain 層擴充

**檔案：`embedding/embedding-seperate/domain/entities.py`**
- ✅ 新增 `JudgmentMultiVectorSpec` 輕量 helper 類別
- ✅ 維持既有 `EmbeddingDocument` 不變

**檔案：`embedding/embedding-seperate/domain/services.py`**
- ✅ 在 `VectorStore` 介面新增 `add_judgment_points()` 方法
- ✅ 擴充 `get_collection_count()` 和 `add_documents()` 支援可選的 `collection_name` 參數

### 1.2 Infrastructure 層實作

**檔案：`embedding/embedding-seperate/infrastructure/vector_store.py`**
- ✅ 在 `QdrantHybridVectorStore` 實作 `add_judgment_points()` 方法
- ✅ 對 `documents_by_jid` 分組，將同一 jid 的不同 `summary_type` 彙整成 named vectors
- ✅ point 的 payload 統一放 judgment-level metadata
- ✅ 支援寫入新的 collection

### 1.3 Application 層新增

**檔案：`embedding/embedding-seperate/application/use_cases.py`**
- ✅ 新增 `EmbedJudgmentPointsUseCase` 類別
- ✅ 重用現有資料讀取邏輯
- ✅ 呼叫 `vector_store.add_judgment_points()` 寫入新 collection
- ✅ 保留原有 `EmbedDocumentsUseCase` 不變

### 1.4 Presentation 層擴充

**檔案：`embedding/embedding-seperate/config.py`**
- ✅ 在 `VectorStoreConfig` 新增 `judgment_collection_name` 設定

**檔案：`embedding/embedding-seperate/presentation/cli.py`**
- ✅ 新增 `mode` 參數支援 `"judgment-point"` 模式
- ✅ 根據模式選擇不同的 use case

**檔案：`embedding/embedding-seperate/__main__.py`**
- ✅ 從環境變數讀取 `EMBEDDING_MODE` 來控制執行模式

### 使用方式

```bash
# 舊的 chunk-level 嵌入（預設）
python -m embedding.embedding-seperate

# 新的 judgment-level 嵌入
EMBEDDING_MODE=judgment-point python -m embedding.embedding-seperate

# 設定 judgment collection 名稱
JUDGMENT_COLLECTION_NAME=judgment_multivector
```

## 二、RAG 模組：新 collection 的強/弱連接搜尋

### 2.1 Domain 介面擴充

**檔案：`ragserver/rag-seperate/domain/interfaces.py`**
- ✅ 在 `IDocumentSearchOrchestrator.orchestrate_search()` 新增可選參數：
  - `hard_fields: Optional[List[str]]` - 強條件摘要欄位
  - `soft_fields: Optional[List[str]]` - 弱條件摘要欄位
  - `judgment_level: bool` - 是否走 judgment-level collection

### 2.2 Services 層新增

**檔案：`ragserver/rag-seperate/services/judgment_level_search_service.py`**
- ✅ 新增 `JudgmentLevelSearchService` 類別
- ✅ 封裝對 Qdrant Query API 的呼叫
- ✅ 針對 `hard_fields` 和 `soft_fields` 建立不同的 prefetch 策略
- ✅ 使用 `FusionQuery` (DBSF) 進行 rerank

**檔案：`ragserver/rag-seperate/services/judgment_level_orchestrator.py`**
- ✅ 新增 `JudgmentLevelSearchOrchestrator` 類別
- ✅ 實作強/弱欄位自動分類邏輯
- ✅ 呼叫 `JudgmentLevelSearchService` 執行搜尋
- ✅ 將結果轉換為簡化格式

**檔案：`ragserver/rag-seperate/services/chunk_strong_weak_orchestrator.py`**
- ✅ 新增 `ChunkStrongWeakSearchOrchestrator` 類別
- ✅ 為舊 chunk-level collection 實作強/弱連接邏輯
- ✅ Hard fields：必須全部有結果，使用 AND 邏輯
- ✅ Soft fields：允許部分匹配，使用加權評分（70% 閾值）

### 2.3 設定檔擴充

**檔案：`ragserver/rag-seperate/config/settings.py`**
- ✅ 在 `QdrantConfig` 新增 `judgment_collection_name` 設定

### 2.4 Entities 層擴充

**檔案：`ragserver/rag-seperate/entities/models.py`**
- ✅ 在 `SearchRequest` 新增：
  - `search_mode: Optional[str]` - 搜尋模式選擇

**檔案：`ragserver/rag-seperate/entities/filters.py`**
- ✅ 在 `Filter` 新增：
  - `hard_condition_fields: Optional[List[str]]` - 強條件欄位清單（由 LLM 分析問句後填寫）
  - `soft_condition_fields: Optional[List[str]]` - 弱條件欄位清單（由 LLM 分析問句後填寫）

### 2.5 Controllers 層擴充

**檔案：`ragserver/rag-seperate/controllers/search_controller.py`**
- ✅ 在 `SearchController` 注入新的 orchestrators
- ✅ 新增 `search_documents_advanced()` 方法
- ✅ 根據 `search_mode` 選擇對應的 orchestrator
- ✅ 保留原有 `search_documents()` 方法不變

**檔案：`ragserver/rag-seperate/controllers/api_router.py`**
- ✅ 新增 `POST /search/advanced` endpoint

**檔案：`ragserver/rag-seperate/main.py`**
- ✅ 初始化所有新的 services 和 orchestrators
- ✅ 注入到 controller

### 使用方式

#### 1. 標準 chunk-level 搜尋（舊方式，保持不變）

```bash
POST /search
{
  "query_text": "毒品案件",
  "conversation_id": null
}
```

#### 2. Judgment-level 搜尋

```bash
POST /search/advanced
{
  "query_text": "法院認定販賣毒品有罪的案件",
  "search_mode": "judgment-level"
}
```

LLM 會自動分析問句並在 Filter 中填寫：
- `hard_condition_fields`: `["C_court_finding", "E_legal_eval"]` - 因為問句中有「法院認定」和「有罪」的明確要求
- `soft_condition_fields`: `["A_fact"]` - 「販賣毒品」作為輔助條件

#### 3. Chunk-level 強/弱連接搜尋

```bash
POST /search/advanced
{
  "query_text": "被告主張不知情但法院不採信的詐欺案件",
  "search_mode": "chunk-strong-weak"
}
```

LLM 會自動分析問句並在 Filter 中填寫：
- `hard_condition_fields`: `["C_court_finding"]` - 「法院不採信」是核心判斷
- `soft_condition_fields`: `["B_claim", "A_fact"]` - 「被告主張」和案件類型作為輔助

#### 4. LLM 智慧分類機制

**強條件欄位（hard_condition_fields）通常包含：**
- `C_court_finding` - 法院認定（明確判斷）
- `E_legal_eval` - 法律評價（罪名、量刑）
- `defendants.is_conviction` - 有罪判決（明確結果）
- `defendants.crime_list` - 罪名（具體法律結論）

**弱條件欄位（soft_condition_fields）通常包含：**
- `A_fact` - 事實經過（描述性內容）
- `B_claim` - 被告主張（辯解理由）
- `defendants_role` - 被告角色（功能定位）
- `case_highlights` - 案件重點（綜合摘要）

**Fallback 機制：**
若 LLM 未填寫強弱分類，系統會使用預設邏輯自動分類：
- 根據 structured_filter 中有值的欄位，對照預設的 HARD/SOFT 候選清單進行分類

## 三、實作原則遵守情況

### ✅ 模組化設計
- 所有新功能以獨立 service 實作
- 舊 service 只增加可選參數，不改變原有邏輯

### ✅ 不破壞既有實體
- 沒有建立任何 v2 類別
- 在原實體新增可選欄位或建立獨立 helper

### ✅ Layer 抽換策略
- Embedding：透過 CLI mode 參數選擇不同 use case
- RAG：透過 endpoint 和 search_mode 參數選擇不同 orchestrator
- 舊 endpoint 完全不受影響

### ✅ LLM 智慧分類
- 強弱欄位分類由 LLM 在分析問句時決定
- 透過 Filter schema 的 `hard_condition_fields` 和 `soft_condition_fields` 傳遞
- 保留 fallback 機制：LLM 未分類時使用預設邏輯
- API 層面保持簡潔，不需要使用者手動指定強弱欄位

### ✅ 錯誤與日誌規範
- 遵守「無 try-catch、Fail Fast、最少日誌」原則
- 只在關鍵節點加入 INFO log

## 四、環境變數設定

### Embedding 模組

```bash
# 標準 collection
COLLECTION_NAME=new_judgment_0915

# Judgment-level collection
JUDGMENT_COLLECTION_NAME=judgment_multivector

# 執行模式：chunk（預設）或 judgment-point
EMBEDDING_MODE=chunk
```

### RAG 模組

```bash
# 標準 collection
COLLECTION_NAME=embedding-seperate

# Judgment-level collection
JUDGMENT_COLLECTION_NAME=judgment_multivector
```

## 五、架構亮點

### 🎯 LLM 驅動的強弱分類

**設計理念：**
將強弱欄位的分類決策交給 LLM，而不是在 API 層或程式碼中硬編碼。這樣的設計有以下優勢：

1. **語意理解**：LLM 可以根據問句的語意動態決定哪些是必要條件、哪些是輔助條件
2. **使用者友善**：API 使用者不需要了解系統內部的欄位結構，只需提供自然語言問句
3. **靈活適應**：當欄位定義變更時，只需調整 LLM prompt，不需修改程式碼
4. **降低耦合**：API 層與搜尋邏輯層解耦，中間透過 LLM 填寫的 Filter schema 傳遞資訊

**運作流程：**
```
用戶問句 
  → LLM 分析語意 
  → 填寫 Filter (含 hard/soft 分類) 
  → Orchestrator 讀取分類 
  → 執行強/弱連接搜尋
```

**Fallback 保障：**
即使 LLM 未能正確分類，系統仍會使用預設規則進行分類，確保功能可用性。

## 六、後續可優化項目

1. **Qdrant Collection Schema**：目前 named vector 名稱與 summary_type 直接對應，未來可以細化 schema 設計

2. **LLM Prompt 優化**：持續調整 Filter schema 的 description，提升 LLM 分類準確度

3. **Multi-chunk 聚合策略**：目前使用簡單字串 join，可以考慮更精緻的聚合演算法（平均、最大值等）

4. **Fallback 行為**：當 hard fields 無結果時的降級策略可以更細化

5. **效能監控**：可以新增 metrics 來追蹤不同搜尋模式的效能與準確度、LLM 分類的準確率

## 七、檔案清單

### 新增檔案

**Embedding 模組：**
- 無（都是擴充既有檔案）

**RAG 模組：**
- `ragserver/rag-seperate/services/judgment_level_search_service.py`
- `ragserver/rag-seperate/services/judgment_level_orchestrator.py`
- `ragserver/rag-seperate/services/chunk_strong_weak_orchestrator.py`

### 修改檔案

**Embedding 模組：**
- `embedding/embedding-seperate/domain/entities.py`
- `embedding/embedding-seperate/domain/services.py`
- `embedding/embedding-seperate/infrastructure/vector_store.py`
- `embedding/embedding-seperate/application/use_cases.py`
- `embedding/embedding-seperate/presentation/cli.py`
- `embedding/embedding-seperate/__main__.py`
- `embedding/embedding-seperate/config.py`

**RAG 模組：**
- `ragserver/rag-seperate/domain/interfaces.py`
- `ragserver/rag-seperate/config/settings.py`
- `ragserver/rag-seperate/entities/models.py`
- `ragserver/rag-seperate/controllers/search_controller.py`
- `ragserver/rag-seperate/controllers/api_router.py`
- `ragserver/rag-seperate/services/document_search_orchestrator.py`
- `ragserver/rag-seperate/main.py`

## 八、總結

所有計畫中的功能已全部實作完成，遵守以下原則：

1. ✅ 非必要不動到現有邏輯執行架構
2. ✅ 只增加功能，不修改舊功能
3. ✅ 透過 layer 抽換實現功能切換
4. ✅ 遵守 Clean Architecture 原則
5. ✅ 遵守 Fail Fast 與最少日誌原則
6. ✅ 所有新功能與舊功能並行，可獨立部署與測試

系統現在支援三種搜尋模式：
- **Chunk-level**（舊方式）：保持不變
- **Judgment-level**：一判決一 point，使用 named vectors
- **Chunk-strong-weak**：chunk-level 加入強/弱連接邏輯

可以透過環境變數和 API 參數靈活切換，方便進行灰度發布與效果對比。

