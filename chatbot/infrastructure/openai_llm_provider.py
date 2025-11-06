import logging
from typing import List, AsyncGenerator
from openai import AsyncOpenAI
from domain.interfaces import ILLMProvider
from entities.models import ChatMessage
from config.settings import Settings

logger = logging.getLogger(__name__)


class OpenAILLMProvider(ILLMProvider):
    """
    OpenAI LLM Provider implementation.
    
    Provides chat completion using OpenAI's models (GPT-4, GPT-5, etc.)
    """
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai.api_key)
        self.model = settings.openai.model
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int
    ) -> str:
        logger.info(f"呼叫 OpenAI LLM: model={self.model}, temperature={temperature}")
        
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
    
    async def generate_response_stream(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[str, None]:
        logger.info(f"呼叫 OpenAI LLM (串流): model={self.model}, temperature={temperature}")
        
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            stream=True,
            reasoning_effort="high"
            # temperature=temperature,
            # max_tokens=max_tokens
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def is_available(self) -> bool:
        return bool(self.settings.openai.api_key)

