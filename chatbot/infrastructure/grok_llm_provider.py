import logging
from typing import List, AsyncGenerator
from openai import AsyncOpenAI
from domain.interfaces import ILLMProvider, Message
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
        max_tokens: int,
        history_messages: List[Message] = None
    ) -> str:
        logger.info(f"呼叫 Grok LLM: model={self.model}, temperature={temperature}")
        
        grok_messages = []
        
        if history_messages:
            for msg in history_messages[-10:]:
                grok_messages.append({
                    "role": "user" if msg.sender_type == "user" else "assistant",
                    "content": msg.content
                })
        
        for msg in messages:
            grok_messages.append({"role": msg.role, "content": msg.content})
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=grok_messages,
            # temperature=temperature,
            # max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    async def generate_response_stream(
        self,
        messages: List[ChatMessage],
        temperature: float,
        max_tokens: int,
        history_messages: List[Message] = None
    ) -> AsyncGenerator[str, None]:
        logger.info(f"呼叫 Grok LLM (串流): model={self.model}, temperature={temperature}")
        
        grok_messages = []
        
        if history_messages:
            for msg in history_messages[-10:]:
                grok_messages.append({
                    "role": "user" if msg.sender_type == "user" else "assistant",
                    "content": msg.content
                })
        
        for msg in messages:
            grok_messages.append({"role": msg.role, "content": msg.content})
        
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=grok_messages,
            stream=True,
            # temperature=temperature,
            # max_tokens=max_tokens
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def is_available(self) -> bool:
        return bool(self.settings.xai.api_key)

