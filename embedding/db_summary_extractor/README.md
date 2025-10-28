# 判決書 Summary 提取器（Clean Architecture 版本）

此模組用於從判決書中提取 Summary，並寫入 Supabase 中的 `lawschatter.judgment_summary`。

## 架構特色

本專案採用 **Clean Architecture** 設計，具備以下特點：

- ✅ **明確的分層與邊界**: Domain / Application / Infrastructure / Presentation
- ✅ **穩定的抽象介面**: 透過介面定義依賴，降低替換成本
- ✅ **高度模組化**: 每個模組單一職責，易於維護與擴充
- ✅ **依賴反轉**: 高層模組不依賴低層實作，皆依賴抽象
- ✅ **Fail Fast**: 無 try-catch，錯誤直接浮現便於偵錯

詳細架構說明請參考 [ARCHITECTURE.md](./ARCHITECTURE.md)

## 專案結構

```
db_summary_extractor/
├── domain/                    # 領域層（核心業務邏輯與抽象）
│   ├── entities.py           # 業務實體
│   ├── repositories.py       # Repository 介面
│   └── services.py           # 領域服務介面
├── application/              # 應用層（用例與流程編排）
│   └── use_cases.py          # 業務用例
├── infrastructure/           # 基礎設施層（外部服務實作）
│   ├── database.py           # Supabase 資料庫實作
│   ├── ai_service.py         # OpenAI 服務實作
│   ├── schema_loader.py      # Schema 載入器
│   ├── hash_service.py       # Hash 產生器
│   └── decomposer.py         # Summary 分解器
├── presentation/             # 表現層（使用者介面）
│   └── cli.py                # CLI 介面
├── config.py                 # 配置管理
├── __main__.py               # 主程式入口
├── ARCHITECTURE.md           # 架構文件
├── README.md                 # 本檔案
├── requirements.txt          # 依賴套件
└── judgment_summary_schema.json  # Summary Schema
```

## 資料來源與條件

- **連線**: `https://supalaw.mooo.com/`
- **Schema**: `lawschatter`
- **處理單位**: 以天為單位（`jdate`）
- **來源表**: `lawschatter.main_judgments`
- **判定表**: `lawschatter.judgment_metadata`
- **寫入表**: `lawschatter.judgment_summary`
- **處理條件**: 同時存在於 `main_judgments` 和 `judgment_metadata`，但不在 `judgment_summary` 的 `jid`

## 運作流程

1. 從 `judgment_metadata` 擷取所有獨特 `jdate`，以遞減排序（新到舊）
2. 逐日處理：
   - 撈出當日在 `main_judgments` 的 `jid`
   - 撈出當日在 `judgment_metadata` 的 `jid`
   - 撈出當日已存在於 `judgment_summary` 的 `jid`
   - 取得未處理的 `jid`（`main_judgments ∩ judgment_metadata - judgment_summary`）
3. 逐 `jid` 處理：
   - 讀取判決資料
   - 呼叫 OpenAI 產生結構化 summary
   - 分解 summary 為多筆記錄
   - 插入 `judgment_summary`
4. 程式中斷後重新啟動會自動接續處理

## Summary 結構

AI 提取的 Summary 包含三個主要部分：

### 1. 案件事實摘要 (case_fact_summary)
- 300字內事實概要
- 無法律評價
- 整體案件脈絡

### 2. 被告摘要 (defendants)
每位被告包含 6 個欄位：
- `name`: 被告姓名
- `role`: 角色定位
- `A_fact`: 行為事實
- `B_claim`: 被告主張
- `C_court_finding`: 法院認定
- `D_court_reason`: 法院理由
- `E_legal_eval`: 法律評價

### 3. 案件亮點 (case_highlights)
- 5-10 句短句
- 每句 20-40 字
- 獨立可讀

## 資料分解邏輯

Summary 會被分解為多筆記錄儲存：

| 類型 | 數量 | point_id 生成規則 |
|-----|------|-------------------|
| case_fact_summary | 1 | MD5(`{jid}_case_fact_summary`) |
| 被告欄位 | N × 6 | MD5(`{jid}_{defendant_name}_{field_name}`) |
| case_highlights | 5-10 | MD5(`{jid}_case_highlights_{index}`) |

## 環境變數設定

建立 `.env` 檔案並設定以下變數：

```env
# 必填
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_api_key

# 可選（有預設值）
SUPABASE_URL=https://supalaw.mooo.com/
SCHEMA_NAME=lawschatter
AI_MODEL=gpt-5
REASONING_EFFORT=medium
AI_TIMEOUT=180
SCHEMA_FILE=judgment_summary_schema.json
SLEEP_INTERVAL=60
```

## 安裝與執行

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

建立 `.env` 檔案並填入必要的 API Keys

### 3. 執行程式

```bash
cd embedding/db_summary_extractor
python -m __main__
```

## 如何擴充

### 替換資料庫

實作 `domain/repositories.py` 中的介面，並在 `presentation/cli.py` 替換實作：

```python
from infrastructure.postgres_database import PostgresJudgmentRepository

judgment_repo = PostgresJudgmentRepository(connection_params)
```

### 替換 AI 服務

實作 `domain/services.py` 中的 `SummaryExtractor` 介面：

```python
from infrastructure.claude_service import ClaudeSummaryExtractor

extractor = ClaudeSummaryExtractor(api_key, model)
```

### 自訂分解邏輯

實作 `domain/services.py` 中的 `SummaryDecomposer` 介面：

```python
class CustomDecomposer(SummaryDecomposer):
    def decompose(self, jid, jdate, extraction):
        # 自訂分解邏輯
        return records
```

詳細擴充指南請參考 [ARCHITECTURE.md](./ARCHITECTURE.md)

## Fail Fast 原則

本專案遵循 Fail Fast 原則：

- ❌ 不使用 try-catch 處理例外
- ✅ 讓錯誤直接拋出並顯示完整堆疊追蹤
- ✅ 透過資料庫狀態支援中斷後續跑
- ✅ 問題立即顯現，便於偵錯與修正

## 日誌輸出

日誌格式：`%(asctime)s | %(levelname)s | %(message)s`

範例輸出：
```
2025-01-15 10:30:00 | INFO | 開始執行 Summary 提取流程
2025-01-15 10:30:01 | INFO | 找到 365 個獨特日期
2025-01-15 10:30:02 | INFO | 處理日期: 2024-12-31
2025-01-15 10:30:03 | INFO | 找到 150 筆符合條件的判決
2025-01-15 10:30:04 | INFO | 找到 45 筆未處理的判決
2025-01-15 10:30:05 | INFO | 處理判決: JID123456
2025-01-15 10:30:25 | INFO | 分解完成，產生 21 筆記錄
...
```

## 參考資料

- [Clean Architecture 概念](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Supabase Python Client](https://supabase.com/docs/reference/python/introduction)
- [OpenAI Python SDK](https://github.com/openai/openai-python)

## 版本歷史

### v2.0.0 (Clean Architecture)
- 重構為 Clean Architecture 架構
- 明確分層：Domain / Application / Infrastructure / Presentation
- 穩定抽象介面，降低替換成本
- 移除所有 try-catch，遵循 Fail Fast 原則
- 模組化分解邏輯

### v1.0.0 (Original)
- 原始版本，單一檔案實作
