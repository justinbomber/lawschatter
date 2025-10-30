# Embedding System Clean Architecture

## 架構概述

本專案採用 Clean Architecture 設計原則，將判決書 Summary 嵌入到 Qdrant 向量資料庫的系統，分為四個主要層次，確保高度模組化、可測試性與可維護性。

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
  - `JudgmentSummary`: 判決書 Summary
  - `JudgmentMetadata`: 判決書 Metadata
  - `EmbeddingDocument`: 嵌入文件
  
- `repositories.py`: Repository 抽象介面
  - `SummaryRepository`: Summary 資料存取介面
  - `MetadataRepository`: Metadata 資料存取介面
  
- `services.py`: 領域服務抽象介面
  - `VectorStore`: 向量資料庫介面

**依賴**: 無外部依賴（純 Python）

### 2. Application Layer（應用層）

**路徑**: `application/`

**職責**: 實作業務用例與流程編排

**組成**:
- `use_cases.py`:
  - `EmbedDocumentsUseCase`: 文件嵌入用例
    - 執行完整嵌入流程
    - 協調各服務完成業務目標

**依賴**: Domain Layer

### 3. Infrastructure Layer（基礎設施層）

**路徑**: `infrastructure/`

**職責**: 實作外部服務與技術細節

**組成**:
- `database.py`: 資料庫實作
  - `SupabaseSummaryRepository`: Supabase Summary Repository
  - `SupabaseMetadataRepository`: Supabase Metadata Repository
  
- `vector_store.py`: 向量資料庫實作
  - `QdrantHybridVectorStore`: Qdrant 混合向量儲存
  
- `tokenizer.py`: 分詞器
  - `JiebaLawTokenizer`: 基於 Jieba 的法律文本分詞器
  
- `sparse_embedding.py`: 稀疏嵌入
  - `ZHTBm25Jieba`: 中文 BM25 稀疏嵌入
  - `ZHTSparseEmbed`: 中文稀疏嵌入包裝器

**依賴**: Domain Layer + 外部套件（Supabase, Qdrant, LangChain, Jieba）

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
- `VectorStoreConfig`: 向量資料庫配置
- `TokenizerConfig`: 分詞器配置
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

## 嵌入流程

1. **資料擷取**
   - 從 `judgment_metadata` 取得所有日期
   - 逐日處理未嵌入的判決

2. **文件建立**
   - 擷取判決的 Summary 記錄
   - 擷取判決的 Metadata 記錄
   - 結合 Summary 與 Metadata 建立嵌入文件

3. **向量嵌入**
   - 密集嵌入：使用 Google Generative AI (Gemini)
   - 稀疏嵌入：使用 BM25 with Jieba 分詞
   - 混合檢索：結合密集與稀疏嵌入

4. **資料更新**
   - 將文件加入 Qdrant
   - 標記 Summary 為已嵌入

## 技術特色

### 混合檢索（Hybrid Retrieval）

結合兩種嵌入方式：

1. **密集嵌入（Dense Embedding）**
   - 模型：`gemini-embedding-001`
   - 向量名稱：`dense`
   - 捕捉語義相似性

2. **稀疏嵌入（Sparse Embedding）**
   - 模型：BM25 with Jieba
   - 向量名稱：`bm25`
   - 捕捉關鍵詞匹配

### 中文法律文本處理

1. **法律專用詞典**
   - 使用 `dict.txt.big` 詞典
   - 提升法律術語分詞準確度

2. **停用詞過濾**
   - 使用 `zh-t.txt` 停用詞表
   - 過濾無意義詞彙

3. **分詞策略**
   - 文件：關閉 HMM（精確分詞）
   - 查詢：開啟 HMM（容錯分詞）

## 擴充指南

### 替換資料庫

1. 實作 `SummaryRepository`, `MetadataRepository` 介面
2. 在 `cli.py` 中替換實作

範例：替換為 PostgreSQL
```python
from .infrastructure.postgres_database import PostgresSummaryRepository

summary_repo = PostgresSummaryRepository(connection_string)
```

### 替換向量資料庫

1. 實作 `VectorStore` 介面
2. 在 `cli.py` 中替換實作

範例：替換為 Pinecone
```python
from .infrastructure.pinecone_store import PineconeVectorStore

vector_store = PineconeVectorStore(api_key, index_name)
```

### 替換嵌入模型

修改 `VectorStoreConfig`：
```python
VectorStoreConfig(
    embedding_model="text-embedding-3-large"  # 使用 OpenAI
)
```

### 自訂分詞器

1. 建立自訂分詞器類別
2. 在 `sparse_embedding.py` 中替換

範例：使用 CKIP
```python
class CKIPLawTokenizer:
    def run_doc(self, text: str) -> List[str]:
        # CKIP 分詞邏輯
        pass
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
| `SCHEMA_NAME` | Database Schema 名稱 | `lawschatter` |
| `QDRANT_SERVER` | Qdrant 伺服器 URL | `http://localhost:6333` |
| `COLLECTION_NAME` | Qdrant 集合名稱 | `new_judgment_0915` |
| `GENAI_EMBEDDING_API_KEY` | Google GenAI API Key | 必填 |
| `EMBEDDING_MODEL` | 嵌入模型名稱 | `gemini-embedding-001` |
| `STOPWORDS_PATH` | 停用詞檔案路徑 | `zh-t.txt` |
| `DICT_PATH` | Jieba 詞典路徑 | `dict.txt.big` |

## 執行方式

```bash
# 設定環境變數（建議使用 .env 檔案）
export SUPABASE_KEY="your_key"
export GENAI_EMBEDDING_API_KEY="your_key"

# 執行程式
cd embedding/embedding-seperate
python -m __main__
```

或使用模組執行：
```bash
python -m embedding-seperate
```

## 優點總結

1. **高度模組化**: 每層職責清晰，易於理解與維護
2. **易於測試**: 透過介面可輕鬆 Mock 依賴
3. **低耦合**: 層間透過抽象介面通訊，降低耦合度
4. **易於擴充**: 新增功能無需修改現有程式碼
5. **易於替換**: 更換實作無需修改業務邏輯
6. **Fail Fast**: 無錯誤處理，問題立即顯現
7. **混合檢索**: 結合密集與稀疏嵌入提升檢索品質
8. **法律專用**: 針對法律文本優化分詞與處理

