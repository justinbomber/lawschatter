# LLM 抽取服務說明

本專案提供多種 LLM 服務用於結構化過濾條件抽取，所有服務均實作 `ILLMExtractionService` 介面，輸入輸出完全一致。

## 可用服務

### 1. OpenAIExtractionService
使用 OpenAI GPT 模型（預設：gpt-5）

**環境變數設定：**
```bash
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5
```

### 2. GrokExtractionService
使用 xAI Grok 模型（預設：grok-3）

**為什麼使用 OpenAI library？**
- xAI Grok API 設計為 OpenAI-compatible
- 官方推薦使用 OpenAI 客戶端 + 不同的 base_url
- 這樣可以使用 OpenAI 的 `responses.parse()` 實現 structured output
- 參考：https://docs.x.ai/docs/guides/structured-outputs

**環境變數設定：**
```bash
XAI_API_KEY=your_xai_api_key
XAI_MODEL=grok-3
XAI_BASE_URL=https://api.x.ai/v1
```

## 如何切換服務

### 在 main.py 中切換

目前預設使用 `OpenAIExtractionService`：

```python
from services.openai_extraction_service import OpenAIExtractionService

llm_extraction_service = OpenAIExtractionService(settings)
filter_service = FilterService(settings, llm_extraction_service)
```

**切換到 Grok：**

```python
from services.grok_extraction_service import GrokExtractionService

llm_extraction_service = GrokExtractionService(settings)
filter_service = FilterService(settings, llm_extraction_service)
```

## 介面規範

所有 LLM 抽取服務必須實作：

```python
class ILLMExtractionService(ABC):
    @abstractmethod
    async def extract_structured_filter(self, user_question: str) -> Dict[str, Any]:
        pass
```

### 輸入
- `user_question: str` - 使用者的法律判決查詢問題

### 輸出
- `Dict[str, Any]` - 結構化的過濾條件字典，符合 `Filter` Pydantic 模型

## 新增其他 LLM 服務

若要新增其他 LLM 服務（如 Claude、Gemini 等），請：

1. 創建新的 service 檔案（如 `claude_extraction_service.py`）
2. 實作 `ILLMExtractionService` 介面
3. 確保輸入輸出與現有服務一致
4. 使用相同的 system prompt 以維持行為一致性
5. 在 `services/__init__.py` 中加入匯出

## 注意事項

- 所有服務使用相同的 system prompt，確保抽取邏輯一致
- 所有服務輸出必須符合 `entities.filters.Filter` 的 Pydantic 模型定義
- 建議在切換服務前先測試輸出格式是否正確

