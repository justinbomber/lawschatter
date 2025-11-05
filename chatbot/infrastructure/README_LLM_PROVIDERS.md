# LLM Provider 說明

本專案提供多種 LLM 服務用於生成聊天回應，所有服務均實作 `ILLMProvider` 介面，可輕鬆切換。

## 可用的 LLM Providers

### 1. OpenAILLMProvider
使用 OpenAI GPT 模型（預設：gpt-5）

**環境變數設定：**
```bash
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5
```

**特點：**
- 支援 reasoning_effort="high" 用於推理模型
- 適合需要深度推理的法律問答

### 2. GrokLLMProvider
使用 xAI Grok 模型（預設：grok-3）

**環境變數設定：**
```bash
XAI_API_KEY=your_xai_api_key
XAI_MODEL=grok-3
XAI_BASE_URL=https://api.x.ai/v1
```

**特點：**
- 使用 OpenAI-compatible API
- 支援 temperature 和 max_tokens 參數

## 如何切換 LLM Provider

### 在 main.py 中切換

目前預設使用 `OpenAILLMProvider`：

```python
from infrastructure.openai_llm_provider import OpenAILLMProvider
from infrastructure.grok_llm_provider import GrokLLMProvider

# 默認使用 OpenAI
llm_provider = OpenAILLMProvider(settings)

# 切換到 Grok：取消下面的註解，註解上面的
# llm_provider = GrokLLMProvider(settings)
```

### 環境變數配置

**使用 OpenAI：**
```bash
# .env 文件
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
```

**使用 Grok：**
```bash
# .env 文件
XAI_API_KEY=xai-...
XAI_MODEL=grok-3
XAI_BASE_URL=https://api.x.ai/v1
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
```

## 介面規範

所有 LLM Provider 必須實作：

```python
class ILLMProvider(ABC):
    @abstractmethod
    async def generate_response(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int
    ) -> str:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
```

### 方法說明

- `generate_response()`: 生成聊天回應
  - **輸入**: 消息列表、溫度、最大 token 數
  - **輸出**: 生成的回應文本

- `is_available()`: 檢查 provider 是否可用
  - **輸出**: 布林值，表示是否配置了有效的 API key

## 新增其他 LLM Provider

若要新增其他 LLM provider（如 Claude、Gemini 等）：

1. 創建新的 provider 檔案（如 `claude_llm_provider.py`）
2. 實作 `ILLMProvider` 介面
3. 在 `config/settings.py` 中加入對應的配置類別
4. 在 `infrastructure/__init__.py` 中加入匯出
5. 在 `main.py` 中即可切換使用

## 注意事項

- 所有 provider 使用相同的消息格式：`List[ChatMessage]`
- OpenAI provider 使用 `reasoning_effort` 參數（特定於推理模型）
- Grok provider 使用標準的 `temperature` 和 `max_tokens` 參數
- 切換 provider 不需要修改業務邏輯代碼

