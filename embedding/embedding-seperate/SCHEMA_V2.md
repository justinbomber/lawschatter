# Qdrant Collection Schema V2 設計

## 概述

V2 Schema 採用「一判決一 point、多 named vectors」的設計，取代舊版「一判決多 point」的結構。這樣可以：
- 更自然地支援 judgment-level AND 條件
- 利用 Qdrant Query API 的 prefetch + fusion 能力
- 減少應用層的 group by 與交集運算

## Collection 設計

### Collection 命名
- 新版 collection：`judgments_v2`
- 舊版 collection：`new_judgment_0915`（保留作為 fallback）

### Named Vectors 架構

每個 point 包含多個 named vectors，分為：

#### 1. Summary 相關向量（當前階段實作）
- `summary_dense`: 判決摘要的稠密向量
  - 維度: 768
  - 距離: Cosine
  - 模型: gemini-embedding-001
  
- `summary_sparse`: 判決摘要的稀疏向量
  - 類型: Sparse
  - 模型: BM25 + Jieba

#### 2. 語義欄位向量（未來擴充）

當未來 Summary 拆分成多個語義欄位後，每個欄位都有 dense + sparse 版本：

- `fact_dense` / `fact_sparse`: 事實摘要（A_fact）
  - 內容：被告做了什麼、案件事實經過
  
- `claim_dense` / `claim_sparse`: 主張摘要（B_claim）
  - 內容：原告/檢察官的主張
  
- `finding_dense` / `finding_sparse`: 法院認定（C_court_finding）
  - 內容：法院對事實的認定
  
- `reason_dense` / `reason_sparse`: 法院理由（D_court_reason）
  - 內容：法院判決的理由
  
- `legal_eval_dense` / `legal_eval_sparse`: 法律評價（E_legal_eval）
  - 內容：法律適用與評價
  
- `highlight_dense`: 案件重點（case_highlights）
  - 內容：判決的關鍵亮點（通常不需要 sparse）

- `role_dense` / `role_sparse`: 被告角色（defendants_role）
  - 內容：被告在案件中的角色定位

### Payload 結構

```json
{
  "jid": "string",              // 判決 ID（短版）
  "jid_full": "string",         // 判決 ID（完整版）
  "jyear": "string",            // 判決年份
  "jcase": "string",            // 案由
  "jno": "string",              // 案號
  "jdate": "string",            // 判決日期 (YYYY-MM-DD)
  "jtitle": "string",           // 判決標題
  "case_type": "string",        // 案件類型
  
  // 結構化欄位（用於 filter）
  "has_guilt": boolean,         // 是否有罪 (true/false/null)
  "offense": ["string"],        // 罪名列表
  "court_level": "string",      // 法院層級（地方/高等/最高）
  "used_messaging_app": boolean,// 是否使用通訊軟體 (true/false/null)
  "has_recidivism": boolean,    // 是否再犯 (true/false/null)
  "sentence_months": integer,   // 刑期（月）
  
  // 被告資訊（可能是列表）
  "defendants": [
    {
      "defendant_name": "string",
      "defendant_role": "string",
      // 其他被告資訊...
    }
  ],
  
  // 原始摘要內容（用於返回結果）
  "summary_content": "string",  // 當前階段：完整 summary
  // 未來：可能拆成 fact_content, finding_content 等
  
  // 元數據
  "case_metadata": {}           // 其他案件元數據
}
```

## 命名約定

### Named Vector 命名規則
格式：`{semantic_field}_{vector_type}`

- `semantic_field`: 語義欄位名稱（summary, fact, claim, finding, reason, legal_eval, highlight, role）
- `vector_type`: 向量類型（dense 或 sparse）

### Payload Key 命名規則
- 使用 snake_case
- 布林值欄位使用 `has_*` 或 `is_*` 前綴
- 列表欄位使用複數形式（如 `defendants`, `offenses`）
- 日期欄位使用 `*_date` 後綴

## 索引策略

### HNSW 索引（Dense Vectors）
- M: 16（平衡搜尋速度與記憶體）
- ef_construct: 100
- 適用於所有 `*_dense` 向量

### Sparse 向量索引
- 使用 Qdrant 內建的 sparse vector index
- 適用於所有 `*_sparse` 向量

### Payload 索引
建議對以下欄位建立索引以加速 filter：
- `jid` (keyword)
- `jdate` (keyword)
- `has_guilt` (bool)
- `offense` (keyword array)
- `court_level` (keyword)
- `used_messaging_app` (bool)
- `has_recidivism` (bool)
- `sentence_months` (integer)

## 遷移策略

### 階段一：建立新 Collection
- 建立 `judgments_v2` collection
- 使用當前 summary 資料，產生 `summary_dense` 和 `summary_sparse`
- Payload 補充結構化欄位（從 metadata 或 LLM 抽取）

### 階段二：雙軌運行
- 新資料同時寫入 v1 和 v2
- 查詢路徑可透過環境變數切換
- 驗證 v2 效能與準確度

### 階段三：完全遷移
- 將所有查詢切換到 v2
- 保留 v1 作為備份一段時間
- 確認穩定後移除 v1

### 階段四：語義欄位拆分（未來）
- 將 summary 拆分成多個語義欄位
- 逐步增加 `fact_dense/sparse`, `finding_dense/sparse` 等
- 更新查詢邏輯以支援多欄位 prefetch

## Collection 建立範例

```python
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")

# 建立 V2 Collection
client.create_collection(
    collection_name="judgments_v2",
    vectors_config={
        "summary_dense": models.VectorParams(
            size=768,
            distance=models.Distance.COSINE,
        ),
        # 未來擴充其他 dense vectors
        # "fact_dense": models.VectorParams(...),
        # "finding_dense": models.VectorParams(...),
    },
    sparse_vectors_config={
        "summary_sparse": models.SparseVectorParams(),
        # 未來擴充其他 sparse vectors
        # "fact_sparse": models.SparseVectorParams(),
        # "finding_sparse": models.SparseVectorParams(),
    },
)

# 建立 Payload 索引
client.create_payload_index(
    collection_name="judgments_v2",
    field_name="jid",
    field_schema=models.PayloadSchemaType.KEYWORD,
)

client.create_payload_index(
    collection_name="judgments_v2",
    field_name="has_guilt",
    field_schema=models.PayloadSchemaType.BOOL,
)

# ... 其他索引
```

## 查詢範例

### 單一欄位查詢
```python
# 使用 summary_dense 查詢
response = await client.query_points(
    collection_name="judgments_v2",
    query=query_vector,
    using="summary_dense",
    query_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="has_guilt",
                match=models.MatchValue(value=True)
            )
        ]
    ),
    limit=100
)
```

### 混合查詢（dense + sparse fusion）
```python
response = await client.query_points(
    collection_name="judgments_v2",
    prefetch=[
        models.Prefetch(
            query=dense_vector,
            using="summary_dense",
            limit=500
        ),
        models.Prefetch(
            query=sparse_vector,
            using="summary_sparse",
            limit=500
        )
    ],
    query=models.FusionQuery(fusion=models.Fusion.RRF),
    limit=100
)
```

### 多欄位 prefetch（未來）
```python
# 硬條件：fact 與 finding 都要匹配
response = await client.query_points(
    collection_name="judgments_v2",
    prefetch=[
        models.Prefetch(
            query=fact_vector,
            using="fact_dense",
            filter=payload_filter,
            limit=2000
        )
    ],
    query=finding_vector,
    using="finding_dense",
    limit=500
)
```

## 優點總結

### V2 相對於 V1 的改進
1. **減少資料量**：一判決一 point 而非多個 chunk points
2. **自然的 AND 條件**：透過 prefetch 實作多欄位硬條件
3. **更好的融合**：使用 Qdrant 原生 fusion（RRF/DBSF）
4. **簡化應用邏輯**：不需要在應用層做 judgment_id 交集
5. **更好的擴充性**：未來可輕鬆加入新的語義欄位
6. **payload filter 優化**：結構化欄位直接用於 NAND 條件

## 效能考量

### 寫入效能
- V2 寫入量減少（一判決一次 upsert vs 多次）
- 但單次 upsert 的向量數增加（多個 named vectors）

### 查詢效能
- Prefetch 階段可能需要較大的 limit（如 2000）
- 但最終只返回少量結果（如 500）
- Payload filter 可以有效減少候選集合

### 記憶體使用
- Named vectors 共享 point ID，記憶體效率較高
- Payload 只儲存一份，減少冗餘

## 備註

- 本設計向後相容，可逐步遷移
- 環境變數控制使用 v1 或 v2 路徑
- 保留 v1 collection 作為 rollback 選項

