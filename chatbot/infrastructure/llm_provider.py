import logging
from typing import List
from openai import AsyncOpenAI
from domain.interfaces import ILLMProvider
from entities.models import ChatMessage
from config.settings import Settings

logger = logging.getLogger(__name__)


class OpenAIProvider(ILLMProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.llm.api_key)
        self.model = settings.llm.model
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int
    ) -> str:
        logger.info(f"呼叫 LLM 生成回應: model={self.model}, temperature={temperature}")
        
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            reasoning_effort="high"
            # temperature=temperature,
            # max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    def is_available(self) -> bool:
        return bool(self.settings.llm.api_key)

