# Lawschatter Qdrant 判決搜尋重構完成總結

## 專案概述

本次重構將判決搜尋系統從 V1（一判決多 points）升級到 V2（一判決一 point、named vectors），並整合 Qdrant Query API 的 prefetch + fusion 能力，實現更精確的硬條件/軟條件分流與 judgment-level AND 過濾。

## 完成的工作

### 1. Schema 設計（✅ 完成）

**檔案**: `embedding/embedding-seperate/SCHEMA_V2.md`

- 設計了完整的 V2 Collection Schema
- 定義了 named vectors 命名規則（`{semantic_field}_{vector_type}`）
- 規劃了 payload 結構，包含結構化欄位用於 filter
- 提供了 collection 建立範例與查詢範例
- 說明了索引策略與效能考量

**關鍵設計**:
- `summary_dense` / `summary_sparse`: 當前實作的摘要向量
- 未來可擴充: `fact_dense/sparse`, `finding_dense/sparse` 等
- Payload 包含: `has_guilt`, `offense`, `used_messaging_app` 等結構化欄位

### 2. Embedding 模組重構（✅ 完成）

**修改檔案**:
- `domain/entities.py`: 新增 `JudgmentSearchDocument` 實體
- `domain/services.py`: 新增 `upsert_judgment()` 和 `create_v2_collection()` 介面
- `infrastructure/vector_store.py`: 實作 V2 collection 建立與 judgment 級別 upsert
- `application/use_cases.py`: 加入 V2 處理邏輯與雙軌支援
- `config.py`: 新增 `use_v2` 配置選項
- `presentation/cli.py`: 傳遞 V2 參數

**特色**:
- 支援 V1/V2 雙軌運行（透過環境變數 `USE_V2_SCHEMA` 控制）
- V2 自動建立 collection 與索引
- 將多個 summary 合併成單一 judgment point
- 產生 `summary_dense` 和 `summary_sparse` 兩個 named vectors

### 3. Query API 整合（✅ 完成）

**修改檔案**:
- `domain/interfaces.py`: 新增 `PrefetchSpec`, `QuerySpec` 資料類別與 `query_with_prefetch` 介面
- `infrastructure/qdrant_client_wrapper.py`: 實作 `query_with_prefetch` 方法
- `entities/models.py`: 新增 `QueryCondition` 和 `use_v2` 欄位

**特色**:
- 封裝 Qdrant Query API 的 prefetch + fusion 能力
- 支援 RRF 和 DBSF 兩種 fusion 策略
- 清晰的抽象介面，易於測試和替換

### 4. 硬條件/軟條件分流（✅ 完成）

**新增檔案**:
- `services/search_service_v2.py`: V2 搜尋服務
- `services/document_search_orchestrator_v2.py`: V2 協調器

**核心邏輯**:
- **硬條件**: `C_court_finding`, `D_court_reason`, `E_legal_eval`
  - 轉成 prefetch entries，限制候選集合
  - 每個硬條件都使用 dense + sparse 雙向量
  - limit 設為 2000，確保足夠的候選集合

- **軟條件**: `A_fact`, `B_claim`, `defendants_role`
  - 作為主 query，用於最終排序
  - 或使用 fusion 與 prefetch 結果合併

- **NAND 過濾**: 優先使用 payload filter（如 `used_messaging_app=false`）
  - 在第二階段對結果進行文字層級的否定過濾

### 5. 漸進式遷移機制（✅ 完成）

**修改檔案**:
- `ragserver/rag-seperate/config/settings.py`: 新增 `use_v2` 配置
- `ragserver/rag-seperate/main.py`: 根據配置選擇 V1 或 V2 路徑

**文檔**:
- `ragserver/rag-seperate/MIGRATION_GUIDE.md`: 完整的遷移指南

**遷移策略**:
1. **階段 0**: 準備工作（備份、測試環境）
2. **階段 1**: 建立 V2 collection（自動）
3. **階段 2**: 雙軌寫入（可選）
4. **階段 3**: 切換查詢路徑（環境變數）
5. **階段 4**: 驗證與調整
6. **階段 5**: 完全遷移
7. **階段 6**: 清理舊資料（可選）

**回滾機制**:
- 緊急回滾：同時切換兩個模組的環境變數
- 部分回滾：只切換 RAG 模組
- V1 collection 保留作為備份

## 環境變數配置

### Embedding 模組
```bash
USE_V2_SCHEMA=true|false  # 控制使用 V1 或 V2 schema
```

### RAG 模組
```bash
USE_V2_SEARCH=true|false  # 控制使用 V1 或 V2 搜尋路徑
```

## 架構優勢

### V2 相對於 V1 的改進

1. **減少資料冗餘**: 一判決一 point，而非多個 chunk points
2. **自然的 AND 條件**: 透過 prefetch 實作硬條件過濾
3. **更好的融合**: 使用 Qdrant 原生 RRF/DBSF
4. **簡化應用邏輯**: 不需要在應用層做 judgment_id 交集
5. **更好的擴充性**: 未來可輕鬆加入新的語義欄位
6. **Payload filter 優化**: 結構化欄位直接用於否定條件

### 保持的設計原則

- ✅ Clean Architecture 分層清晰
- ✅ 無 try-catch，快速失敗
- ✅ 模組邊界明確
- ✅ 依賴注入
- ✅ 介面抽象

## 檔案清單

### 新增檔案
```
embedding/embedding-seperate/
  └── SCHEMA_V2.md

ragserver/rag-seperate/
  ├── services/
  │   ├── search_service_v2.py
  │   └── document_search_orchestrator_v2.py
  └── MIGRATION_GUIDE.md

REFACTOR_SUMMARY.md (本檔案)
```

### 修改檔案
```
embedding/embedding-seperate/
  ├── domain/
  │   ├── entities.py          (+ JudgmentSearchDocument)
  │   └── services.py          (+ upsert_judgment, create_v2_collection)
  ├── infrastructure/
  │   └── vector_store.py      (+ V2 實作)
  ├── application/
  │   └── use_cases.py         (+ V2 處理邏輯)
  ├── presentation/
  │   └── cli.py               (+ use_v2 參數)
  └── config.py                (+ use_v2 欄位)

ragserver/rag-seperate/
  ├── domain/
  │   └── interfaces.py        (+ PrefetchSpec, QuerySpec, query_with_prefetch)
  ├── infrastructure/
  │   └── qdrant_client_wrapper.py (+ query_with_prefetch 實作)
  ├── entities/
  │   └── models.py            (+ QueryCondition, use_v2)
  ├── config/
  │   └── settings.py          (+ use_v2)
  └── main.py                  (+ V2 路徑選擇)
```

## 使用方式

### 啟用 V2 Embedding
```bash
cd embedding/embedding-seperate
export USE_V2_SCHEMA=true
python -m __main__
```

### 啟用 V2 搜尋
```bash
cd ragserver/rag-seperate
export USE_V2_SEARCH=true
python main.py
```

### 回滾到 V1
```bash
# Embedding
export USE_V2_SCHEMA=false

# RAG
export USE_V2_SEARCH=false
```

## 測試建議

### 功能測試
1. 測試相同查詢在 V1 和 V2 下的結果差異
2. 驗證硬條件/軟條件分流是否正確
3. 檢查 NAND 過濾是否符合預期
4. 測試 payload filter 的各種組合

### 效能測試
1. 比較 V1 和 V2 的查詢響應時間
2. 測量 prefetch 不同 limit 的影響
3. 監控 Qdrant 記憶體使用
4. 壓力測試併發查詢

### 品質測試
1. 比較搜尋結果的相關度
2. 評估 judgment-level AND 的準確性
3. 測試邊界情況（無結果、大量結果等）
4. 驗證否定條件的準確性

## 未來擴充方向

### 短期（1-2 個月）
1. 從 metadata 或 LLM 抽取更多結構化欄位補充到 payload
2. 優化硬條件/軟條件的判定邏輯
3. 調整 prefetch limit 以優化效能
4. 增加更多監控指標

### 中期（3-6 個月）
1. 將 Summary 拆分成多個語義欄位（fact, claim, finding, reason 等）
2. 為每個欄位產生獨立的 named vectors
3. 更精細的多欄位 prefetch 策略
4. 實作更複雜的 AND/OR/NAND 組合邏輯

### 長期（6-12 個月）
1. 支援動態權重調整（importance 欄位）
2. 機器學習模型優化硬/軟條件判定
3. 自動化的 A/B 測試框架
4. 更智慧的查詢重寫與擴充

## 注意事項

1. **不要同時修改兩個環境變數**: 建議先測試單一模組，確認無誤後再切換另一個
2. **保留 V1 collection**: 至少保留 2 週作為備份
3. **監控日誌**: 注意「使用 V1」或「使用 V2」的日誌訊息
4. **逐步遷移**: 建議先對少量資料測試 V2，再完全遷移

## 已知限制

1. V2 目前只支援 `summary_dense` 和 `summary_sparse`，語義欄位拆分需要後續實作
2. 硬條件/軟條件的判定邏輯是靜態的，未來可改為動態或基於 LLM
3. prefetch limit 是固定的 2000，未來可根據查詢複雜度動態調整
4. 目前只支援 RRF fusion，DBSF 尚未充分測試

## 結論

本次重構成功實現了：
- ✅ V2 Schema 設計與實作
- ✅ 一判決一 point 的架構轉換
- ✅ Qdrant Query API 整合
- ✅ 硬條件/軟條件分流機制
- ✅ 漸進式遷移與回滾機制
- ✅ 完整保持 Clean Architecture

系統現在支援 V1/V2 雙軌運行，可以安全地逐步遷移到新架構，同時保留隨時回滾的能力。新架構為未來的語義欄位擴充和更複雜的查詢邏輯打下了堅實基礎。

---

**文件建立日期**: 2025-01-XX  
**重構版本**: V2.0  
**維護者**: Lawschatter Team

