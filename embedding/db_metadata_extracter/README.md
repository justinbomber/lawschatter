# 判決書 Metadata 提取器（Clean Architecture 版本）

此模組用於從判決書中提取 Metadata，並寫入 Supabase 中的 `lawschatter.judgment_metadata`。

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
db_metadata_extracter/
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
│   └── filter_service.py     # 過濾服務
├── presentation/             # 表現層（使用者介面）
│   └── cli.py                # CLI 介面
├── config.py                 # 配置管理
├── main.py                   # 主程式入口
├── ARCHITECTURE.md           # 架構文件
├── README.md                 # 本檔案
├── requirements.txt          # 依賴套件
├── judgment_metadata_schema.json  # Metadata Schema
└── create_rpc_function.sql   # RPC 函數 SQL
```

## 資料來源與條件

- **連線**: `https://supalaw.mooo.com/`
- **Schema**: `lawschatter`
- **處理單位**: 以天為單位（`jdate`）
- **來源表**: `lawschatter.main_judgments`
- **寫入表**: `lawschatter.judgment_metadata`
- **過濾條件**: 僅處理 `jtitle` 為以下任一的資料：
  - `詐欺等`
  - `詐欺`
  - `洗錢防制法等`
  - `洗錢防制法`
- **過濾邏輯**: 僅處理不存在於 `judgment_metadata` 的 `jid`

## 運作流程

1. 擷取 `main_judgments` 的所有獨特 `jdate`，以遞減排序（新到舊）
2. 逐日處理：
   - 撈出當日符合 `jtitle` 條件的 `jid`
   - 撈出已存在於 `judgment_metadata` 的 `jid`
   - 取得未處理的 `jid`（差集）
3. 逐 `jid` 處理：
   - 讀取判決資料
   - 過濾裁定案件（前 20 字包含「裁定」）
   - 呼叫 OpenAI 產生結構化 metadata
   - 插入 `judgment_metadata`
4. 程式中斷後重新啟動會自動接續處理

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
SCHEMA_FILE=judgment_metadata_schema.json
INCLUDE_ADJUDICATE=false
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
cd embedding/db_metadata_extracter
python main.py
```

## 如何擴充

### 替換資料庫

實作 `domain/repositories.py` 中的介面，並在 `presentation/cli.py` 替換實作：

```python
from infrastructure.postgres_database import PostgresJudgmentRepository

judgment_repo = PostgresJudgmentRepository(connection_params)
```

### 替換 AI 服務

實作 `domain/services.py` 中的 `MetadataExtractor` 介面：

```python
from infrastructure.claude_service import ClaudeMetadataExtractor

extractor = ClaudeMetadataExtractor(api_key, model)
```

### 新增過濾規則

實作 `domain/services.py` 中的 `JudgmentFilter` 介面：

```python
class CustomFilter(JudgmentFilter):
    def should_ignore(self, judgment: JudgmentRecord) -> bool:
        # 自訂過濾邏輯
        return False
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
2025-01-15 10:30:00 | INFO | 開始執行 Metadata 提取流程
2025-01-15 10:30:01 | INFO | 找到 365 個獨特日期
2025-01-15 10:30:02 | INFO | 處理日期: 2024-12-31
2025-01-15 10:30:03 | INFO | 找到 150 筆符合條件的判決
2025-01-15 10:30:04 | INFO | 找到 45 筆未處理的判決
2025-01-15 10:30:05 | INFO | 處理判決: JID123456
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

### v1.0.0 (Original)
- 原始版本，單一檔案實作
