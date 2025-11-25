# V1 到 V2 架構遷移指南

## 概述

本指南說明如何從 V1（一判決多 points）遷移到 V2（一判決一 point、named vectors）架構。

## 架構差異對比

### V1 架構
- 一份判決 → 多個 chunk points（約 16 個）
- 每個 point 有 `dense` 和 `bm25` 兩個向量
- 查詢時需要在應用層做 judgment_id 交集
- 使用 `DocumentSearchOrchestrator` 和 `SearchService`

### V2 架構
- 一份判決 → 一個 point
- 每個 point 有多個 named vectors（`summary_dense`, `summary_sparse`）
- 查詢使用 Qdrant Query API 的 prefetch + fusion
- 使用 `DocumentSearchOrchestratorV2` 和 `SearchServiceV2`
- 支援硬條件/軟條件分流
- 更好的 payload filter 支援

## 環境變數設定

### Embedding 模組（embedding-seperate）

```bash
# 使用 V2 schema 進行 embedding
USE_V2_SCHEMA=true

# 其他必要設定
QDRANT_SERVER=http://localhost:6333
COLLECTION_NAME=new_judgment_0915
GENAI_EMBEDDING_API_KEY=your_key
```

### RAG 模組（rag-seperate）

```bash
# 使用 V2 搜尋路徑
USE_V2_SEARCH=true

# 其他必要設定
QDRANT_CLIENT=http://localhost:6333
COLLECTION_NAME=new_judgment_0915
OPENAI_API_KEY=your_key
GENAI_EMBEDDING_API_KEY=your_key
```

## 遷移階段

### 階段 0：準備工作

1. 確保 Qdrant 服務正常運行
2. 備份現有資料庫和配置
3. 測試環境變數設定

### 階段 1：建立 V2 Collection

在 embedding 模組中，V2 collection 會在首次執行時自動建立：

```bash
# 設定環境變數
export USE_V2_SCHEMA=true

# 執行 embedding（會自動建立 new_judgment_0915_v2 collection）
cd embedding/embedding-seperate
python -m __main__
```

V2 collection 命名規則：`{原collection名稱}_v2`

例如：
- V1: `new_judgment_0915`
- V2: `new_judgment_0915_v2`

### 階段 2：雙軌寫入（可選）

如果需要同時維護 V1 和 V2，可以執行兩次 embedding：

```bash
# 寫入 V1
export USE_V2_SCHEMA=false
python -m __main__

# 寫入 V2
export USE_V2_SCHEMA=true
python -m __main__
```

### 階段 3：切換查詢路徑

RAG 模組透過環境變數控制使用哪個路徑：

```bash
# 測試 V2 路徑
export USE_V2_SEARCH=true
cd ragserver/rag-seperate
python main.py

# 如果需要回滾到 V1
export USE_V2_SEARCH=false
python main.py
```

### 階段 4：驗證與調整

1. **功能驗證**
   - 測試相同的查詢在 V1 和 V2 下的結果
   - 比較結果品質和相關度
   - 檢查 payload filter 是否正常工作

2. **效能驗證**
   - 測量查詢響應時間
   - 監控記憶體使用
   - 檢查 Qdrant 負載

3. **記錄觀察**
   - 檢查日誌輸出，確認使用正確路徑
   - 觀察硬條件/軟條件分流是否符合預期
   - 驗證 NAND 條件過濾是否正常

### 階段 5：完全遷移

確認 V2 穩定後：

1. 將所有服務切換到 V2
2. 保留 V1 collection 作為備份（至少 2 週）
3. 更新文檔和監控配置
4. 通知相關團隊

### 階段 6：清理（可選）

在 V2 運行穩定至少 1 個月後：

```python
# 刪除 V1 collection（謹慎操作！）
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")
client.delete_collection("new_judgment_0915")  # V1 collection
```

## 回滾策略

### 緊急回滾

如果 V2 出現問題，立即回滾到 V1：

```bash
# Embedding 模組
export USE_V2_SCHEMA=false

# RAG 模組
export USE_V2_SEARCH=false

# 重啟服務
```

### 部分回滾

只回滾查詢路徑，保留 V2 embedding：

```bash
# 只改 RAG 模組
export USE_V2_SEARCH=false
```

## 監控指標

### Embedding 階段

- V2 collection 點數增長
- Embedding 速度（點/秒）
- 錯誤率

### 查詢階段

- 平均響應時間
- P95/P99 延遲
- 結果相關度分數分布
- 硬條件/軟條件命中率

## 常見問題

### Q1: V2 collection 已經存在怎麼辦？

A: 系統會自動跳過建立步驟，直接使用現有 collection。如果需要重建：

```python
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")
client.delete_collection("new_judgment_0915_v2")
```

### Q2: 可以同時運行 V1 和 V2 嗎？

A: 可以。兩個版本使用不同的 collection，不會互相干擾。透過環境變數控制使用哪個版本。

### Q3: V2 查詢比 V1 慢怎麼辦？

A: 可能原因：
- prefetch limit 設定太大（調整 `search_service_v2.py` 中的 limit）
- 硬條件過多（檢查 `_determine_hard_soft_conditions` 邏輯）
- Payload filter 複雜度過高

### Q4: V2 結果數量比 V1 少很多？

A: 這是正常的，因為：
- V2 使用 judgment-level 返回（一判決一筆結果）
- V1 可能返回同一判決的多個 chunk
- V2 更嚴格的 AND 條件過濾

### Q5: 如何判斷硬條件和軟條件？

A: 在 `DocumentSearchOrchestratorV2._determine_hard_soft_conditions` 中定義：
- 硬條件：法院認定、判決理由、法律評價
- 軟條件：事實、主張、角色
- 可根據業務需求調整

## 技術細節

### V2 Query API 使用方式

```python
# 硬條件轉成 prefetch
prefetch = [
    Prefetch(query=fact_vector, using="summary_dense", limit=2000),
    Prefetch(query=finding_vector, using="summary_dense", limit=2000)
]

# 軟條件作為主 query
response = await client.query_points(
    collection_name="collection_v2",
    prefetch=prefetch,
    query=soft_condition_vector,
    using="summary_dense",
    limit=100
)
```

### NAND 過濾實作

V2 優先使用 payload filter：

```python
# 在 payload 中標記
payload = {
    "used_messaging_app": False  # 沒有使用通訊軟體
}

# 查詢時過濾
filter = models.Filter(
    must_not=[
        models.FieldCondition(
            key="used_messaging_app",
            match=models.MatchValue(value=True)
        )
    ]
)
```

## 未來擴充

當 Summary 拆分成多個語義欄位後：

1. 更新 `domain/entities.py` 的 `JudgmentSearchDocument`
2. 在 `vector_store.py` 中加入新的 named vectors
3. 更新 `SearchServiceV2` 支援新欄位
4. 調整 `_determine_hard_soft_conditions` 邏輯

## 支援

如有問題，請：
1. 檢查日誌輸出
2. 驗證環境變數設定
3. 確認 Qdrant collection 狀態
4. 參考 `SCHEMA_V2.md` 了解資料結構

## 變更記錄

- 2025-01-XX: 初版發布
- V2 架構支援 named vectors
- 實作硬條件/軟條件分流
- 加入漸進式遷移機制

