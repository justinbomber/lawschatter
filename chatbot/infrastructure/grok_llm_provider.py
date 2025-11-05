import logging
from typing import List
from openai import AsyncOpenAI
from domain.interfaces import ILLMProvider
from entities.models import ChatMessage
from config.settings import Settings

logger = logging.getLogger(__name__)


class GrokLLMProvider(ILLMProvider):
    """
    Grok LLM Provider implementation.
    
    Provides chat completion using xAI's Grok models through OpenAI-compatible API.
    Note: xAI Grok API is designed to be OpenAI-compatible.
    
    Reference: https://docs.x.ai/docs/guides/
    """
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AsyncOpenAI(
            api_key=settings.xai.api_key,
            base_url=settings.xai.base_url
        )
        self.model = settings.xai.model
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int
    ) -> str:
        logger.info(f"呼叫 Grok LLM: model={self.model}, temperature={temperature}")
        
        grok_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=grok_messages,
            # temperature=temperature,
            # max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    def is_available(self) -> bool:
        return bool(self.settings.xai.api_key)

