## 判決書嵌入系統（Clean Architecture 版本）

此模組用於將判決書 Summary 嵌入到 Qdrant 向量資料庫，支援混合檢索（密集嵌入 + 稀疏嵌入）。

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
embedding-seperate/
├── domain/                    # 領域層（核心業務邏輯與抽象）
│   ├── entities.py           # 業務實體
│   ├── repositories.py       # Repository 介面
│   └── services.py           # 領域服務介面
├── application/              # 應用層（用例與流程編排）
│   └── use_cases.py          # 業務用例
├── infrastructure/           # 基礎設施層（外部服務實作）
│   ├── database.py           # Supabase 資料庫實作
│   ├── vector_store.py       # Qdrant 向量資料庫實作
│   ├── tokenizer.py          # Jieba 分詞器
│   └── sparse_embedding.py   # BM25 稀疏嵌入
├── presentation/             # 表現層（使用者介面）
│   └── cli.py                # CLI 介面
├── config.py                 # 配置管理
├── __main__.py               # 主程式入口
├── ARCHITECTURE.md           # 架構文件
├── README.md                 # 本檔案
├── requirements.txt          # 依賴套件
├── zh-t.txt                  # 中文停用詞表
└── dict.txt.big              # Jieba 法律詞典
```

## 資料來源與條件

- **資料庫**: Supabase (`https://supalaw.mooo.com/`)
- **Schema**: `lawschatter`
- **來源表**: `judgment_summary`, `judgment_metadata`, `main_judgments`
- **向量資料庫**: Qdrant
- **處理條件**: 
  - 同時存在於 `main_judgments`, `judgment_metadata`, `judgment_summary`
  - `judgment_summary.embedded_1 = False`（未嵌入）

## 運作流程

1. 從 `judgment_metadata` 擷取所有獨特 `jdate`，以遞減排序（新到舊）
2. 逐日處理：
   - 撈出當日在三表交集且未嵌入的 `jid`
3. 逐 `jid` 處理：
   - 擷取該 `jid` 的所有 summary 記錄
   - 擷取該 `jid` 的 metadata 記錄
   - 結合兩者建立嵌入文件
   - 加入到 Qdrant 向量資料庫
   - 標記 `embedded_1 = True`
4. 程式中斷後重新啟動會自動接續處理

## 混合檢索技術

### 密集嵌入（Dense Embedding）

- **模型**: Google Generative AI `gemini-embedding-001`
- **向量名稱**: `dense`
- **用途**: 捕捉語義相似性
- **維度**: 768

### 稀疏嵌入（Sparse Embedding）

- **模型**: BM25 with Jieba 分詞
- **向量名稱**: `bm25`
- **用途**: 捕捉關鍵詞匹配
- **特色**: 
  - 使用法律專用詞典 (`dict.txt.big`)
  - 過濾中文停用詞 (`zh-t.txt`)
  - 文件分詞關閉 HMM（精確）
  - 查詢分詞開啟 HMM（容錯）

### 混合檢索模式

- 同時使用密集與稀疏嵌入
- 提升檢索準確度與召回率
- 適合法律文本的專業性與多樣性

## 環境變數設定

建立 `.env` 檔案並設定以下變數：

```env
# 必填
SUPABASE_KEY=your_supabase_key
GENAI_EMBEDDING_API_KEY=your_google_genai_key

# 可選（有預設值）
SUPABASE_URL=https://supalaw.mooo.com/
SCHEMA_NAME=lawschatter
QDRANT_SERVER=http://localhost:6333
COLLECTION_NAME=new_judgment_0915
EMBEDDING_MODEL=gemini-embedding-001
STOPWORDS_PATH=zh-t.txt
DICT_PATH=dict.txt.big
```

## 安裝與執行

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 準備詞典與停用詞

確保以下檔案存在於專案目錄：
- `dict.txt.big`: Jieba 繁體中文法律詞典
- `zh-t.txt`: 繁體中文停用詞表

### 3. 設定環境變數

建立 `.env` 檔案並填入必要的 API Keys

### 4. 啟動 Qdrant

```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 5. 執行程式

```bash
cd embedding/embedding-seperate
python -m __main__
```

## 如何擴充

### 替換向量資料庫

實作 `domain/services.py` 中的 `VectorStore` 介面：

```python
from infrastructure.pinecone_store import PineconeVectorStore

vector_store = PineconeVectorStore(api_key, index_name)
```

### 替換嵌入模型

修改配置：

```python
VectorStoreConfig(
    embedding_model="text-embedding-3-large",  # OpenAI
    embedding_api_key=openai_api_key
)
```

### 自訂分詞器

實作分詞器並在 `sparse_embedding.py` 中替換：

```python
class CustomTokenizer:
    def run_doc(self, text: str) -> List[str]:
        # 自訂分詞邏輯
        pass
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
2025-01-15 10:30:00 | INFO | 開始執行文件嵌入流程
2025-01-15 10:30:01 | INFO | 找到 365 個獨特日期
2025-01-15 10:30:02 | INFO | 處理日期: 2024-12-31
2025-01-15 10:30:03 | INFO | 找到 45 個待處理的判決
2025-01-15 10:30:04 | INFO | 處理判決: JID123456
2025-01-15 10:30:05 | INFO | 目前集合點數: 1000
2025-01-15 10:30:25 | INFO | 加入 15 個文件到向量資料庫
2025-01-15 10:30:26 | INFO | 完成處理判決 JID123456，共 15 個文件
...
```

## 效能考量

### 批次處理

- 逐日期處理，避免一次載入過多資料
- 逐判決處理，確保單筆失敗不影響其他

### 嵌入效能

- 密集嵌入：使用 Google GenAI，批次處理
- 稀疏嵌入：本地計算，速度快
- 向量儲存：Qdrant 高效能寫入

### 資料庫查詢

- 使用索引欄位（`jdate`, `jid`, `embedded_1`）
- 最小化資料傳輸

## 參考資料

- [Clean Architecture 概念](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Qdrant 文件](https://qdrant.tech/documentation/)
- [LangChain Qdrant](https://python.langchain.com/docs/integrations/vectorstores/qdrant)
- [Jieba 中文分詞](https://github.com/fxsjy/jieba)

## 版本歷史

### v2.0.0 (Clean Architecture)
- 重構為 Clean Architecture 架構
- 明確分層：Domain / Application / Infrastructure / Presentation
- 穩定抽象介面，降低替換成本
- 移除所有 try-catch，遵循 Fail Fast 原則
- 模組化分詞與嵌入邏輯

### v1.0.0 (Original)
- 原始版本，單一檔案實作
- 基本混合檢索功能

