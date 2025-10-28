# Summary Extractor Clean Architecture

## 架構概述

本專案採用 Clean Architecture 設計原則，將系統分為四個主要層次，確保高度模組化、可測試性與可維護性。

## 核心設計原則

1. **依賴反轉原則（Dependency Inversion Principle）**
   - 高層模組不依賴低層模組，兩者皆依賴抽象
   - Domain Layer 定義介面，Infrastructure Layer 實作介面

2. **單一職責原則（Single Responsibility Principle）**
   - 每個模組只處理一個特定關注點
   - 清晰的邊界與職責劃分

3. **開放封閉原則（Open-Closed Principle）**
   - 對擴充開放，對修改封閉
   - 透過抽象介面輕鬆替換實作

4. **Fail Fast 原則**
   - 無 try-catch 錯誤處理
   - 讓錯誤直接浮現，便於偵錯

## 架構分層

### 1. Domain Layer（領域層）

**路徑**: `domain/`

**職責**: 定義核心業務邏輯與抽象介面

**組成**:
- `entities.py`: 業務實體
  - `JudgmentRecord`: 判決書記錄
  - `DefendantSummary`: 被告摘要
  - `SummaryExtractionResult`: Summary 提取結果
  - `SummaryRecord`: Summary 記錄
  
- `repositories.py`: Repository 抽象介面
  - `JudgmentRepository`: 判決書資料存取介面
  - `MetadataRepository`: Metadata 資料存取介面
  - `SummaryRepository`: Summary 資料存取介面
  
- `services.py`: 領域服務抽象介面
  - `SummaryExtractor`: Summary 提取服務介面
  - `SchemaProvider`: Schema 提供者介面
  - `HashGenerator`: Hash 產生器介面
  - `SummaryDecomposer`: Summary 分解器介面

**依賴**: 無外部依賴（純 Python）

### 2. Application Layer（應用層）

**路徑**: `application/`

**職責**: 實作業務用例與流程編排

**組成**:
- `use_cases.py`:
  - `ExtractSummaryUseCase`: Summary 提取用例
    - 執行完整提取流程
    - 協調各服務完成業務目標

**依賴**: Domain Layer

### 3. Infrastructure Layer（基礎設施層）

**路徑**: `infrastructure/`

**職責**: 實作外部服務與技術細節

**組成**:
- `database.py`: 資料庫實作
  - `SupabaseJudgmentRepository`: Supabase 判決書 Repository
  - `SupabaseMetadataRepository`: Supabase Metadata Repository
  - `SupabaseSummaryRepository`: Supabase Summary Repository
  
- `ai_service.py`: AI 服務實作
  - `OpenAISummaryExtractor`: OpenAI Summary 提取器
  
- `schema_loader.py`: Schema 載入器
  - `FileSchemaProvider`: 檔案 Schema 提供者
  
- `hash_service.py`: Hash 服務
  - `MD5HashGenerator`: MD5 Hash 產生器
  
- `decomposer.py`: Summary 分解器
  - `DefaultSummaryDecomposer`: 預設 Summary 分解器

**依賴**: Domain Layer + 外部套件（Supabase, OpenAI）

### 4. Presentation Layer（表現層）

**路徑**: `presentation/`

**職責**: 使用者介面與程式入口

**組成**:
- `cli.py`: 命令列介面
  - `CLI`: CLI 應用程式
    - 初始化所有服務
    - 依賴注入
    - 執行用例

**依賴**: Application Layer + Infrastructure Layer

## 配置管理

**路徑**: `config.py`

**職責**: 統一管理應用程式配置

**組成**:
- `DatabaseConfig`: 資料庫配置
- `AIServiceConfig`: AI 服務配置
- `SchemaConfig`: Schema 配置
- `ProcessConfig`: 處理流程配置
- `AppConfig`: 應用程式總配置

## 主程式入口

**路徑**: `__main__.py`

**職責**: 應用程式啟動點

**流程**:
1. 載入環境變數配置
2. 建立 CLI 實例
3. 執行主流程

## 依賴流向

```
__main__.py
  ↓
presentation/cli.py
  ↓
application/use_cases.py
  ↓
domain/ (interfaces)
  ↑
infrastructure/ (implementations)
```

## Summary 分解邏輯

本系統將 AI 提取的 Summary 分解為多筆記錄：

1. **案件事實摘要** (`case_fact_summary`)
   - 1 筆記錄
   - `point_id`: MD5(`{jid}_case_fact_summary`)

2. **被告欄位** (每位被告 6 個欄位)
   - `role`: 角色定位
   - `A_fact`: 行為事實
   - `B_claim`: 被告主張
   - `C_court_finding`: 法院認定
   - `D_court_reason`: 法院理由
   - `E_legal_eval`: 法律評價
   - `point_id`: MD5(`{jid}_{defendant_name}_{field_name}`)

3. **案件亮點** (`case_highlights`)
   - N 筆記錄（依 AI 產生數量）
   - `point_id`: MD5(`{jid}_case_highlights_{index}`)

## 擴充指南

### 替換資料庫

1. 實作 `JudgmentRepository`, `MetadataRepository`, `SummaryRepository` 介面
2. 在 `cli.py` 中替換實作

範例：替換為 PostgreSQL
```python
from .infrastructure.postgres_database import PostgresJudgmentRepository

judgment_repo = PostgresJudgmentRepository(connection_string)
```

### 替換 AI 服務

1. 實作 `SummaryExtractor` 介面
2. 在 `cli.py` 中替換實作

範例：替換為 Claude
```python
from .infrastructure.claude_service import ClaudeSummaryExtractor

extractor = ClaudeSummaryExtractor(api_key, model)
```

### 自訂 Hash 產生器

1. 實作 `HashGenerator` 介面
2. 在 `cli.py` 中替換實作

範例：使用 SHA256
```python
class SHA256HashGenerator(HashGenerator):
    def generate(self, unique_string: str) -> str:
        return hashlib.sha256(unique_string.encode('utf-8')).hexdigest()
```

### 自訂分解邏輯

1. 實作 `SummaryDecomposer` 介面
2. 在 `cli.py` 中替換實作

範例：加入額外欄位
```python
class CustomSummaryDecomposer(SummaryDecomposer):
    def decompose(self, jid, jdate, extraction):
        records = []
        # 自訂分解邏輯
        return records
```

## 測試策略

### 單元測試

- Domain Layer: 測試實體邏輯
- Application Layer: 使用 Mock Repository 測試用例
- Infrastructure Layer: 測試各實作與外部服務的整合

### 整合測試

- 測試完整流程，使用真實服務

## 環境變數

| 變數名稱 | 說明 | 預設值 |
|---------|------|--------|
| `SUPABASE_URL` | Supabase URL | `https://supalaw.mooo.com/` |
| `SUPABASE_KEY` | Supabase API Key | 必填 |
| `OPENAI_API_KEY` | OpenAI API Key | 必填 |
| `SCHEMA_NAME` | Database Schema 名稱 | `lawschatter` |
| `AI_MODEL` | AI 模型名稱 | `gpt-5` |
| `REASONING_EFFORT` | AI 推理強度 | `medium` |
| `AI_TIMEOUT` | AI 請求超時時間（秒） | `180` |
| `SCHEMA_FILE` | Schema 檔案路徑 | `judgment_summary_schema.json` |
| `SLEEP_INTERVAL` | 處理間隔時間（秒） | `60` |

## 執行方式

```bash
# 設定環境變數（建議使用 .env 檔案）
export SUPABASE_KEY="your_key"
export OPENAI_API_KEY="your_key"

# 執行程式
cd embedding/db_summary_extractor
python -m __main__
```

或使用模組執行：
```bash
python -m db_summary_extractor
```

## 優點總結

1. **高度模組化**: 每層職責清晰，易於理解與維護
2. **易於測試**: 透過介面可輕鬆 Mock 依賴
3. **低耦合**: 層間透過抽象介面通訊，降低耦合度
4. **易於擴充**: 新增功能無需修改現有程式碼
5. **易於替換**: 更換實作無需修改業務邏輯
6. **Fail Fast**: 無錯誤處理，問題立即顯現
7. **靈活分解**: 可自訂 Summary 分解邏輯
8. **可追蹤性**: 每筆記錄有唯一 Hash ID

