"""
OpenAI 兼容提供商实现
"""

from typing import List, Optional, AsyncIterator, Dict, Any
import aiohttp
import asyncio
import json
import logging

from .base import BaseProvider
from ..core import ChatRequest, LLMResponse, Message
from ..exceptions import (
    AuthenticationError,
    InvalidRequestError,
    ModelNotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    TimeoutError,
    ProviderError
)

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI 兼容提供商"""
    
    def __init__(self, provider_name: str, settings):
        super().__init__(provider_name, settings)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self):
        """获取 HTTP 会话"""
        if self._session is None or self._session.closed:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            self._session = aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=self.provider_config.timeout))
        return self._session
    
    async def chat(self, request: ChatRequest) -> LLMResponse:
        """聊天接口"""
        self._check_rate_limit()
        
        session = await self._get_session()
        
        payload = {
            "model": request.model,
            "messages": [msg.dict(exclude_none=True) for msg in request.messages],
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
        
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.stop:
            payload["stop"] = request.stop
        if request.tools:
            payload["tools"] = request.tools
        
        url = f"{self.base_url}/chat/completions"
        
        try:
            async with session.post(url, json=payload) as response:
                if response.status == 401:
                    raise AuthenticationError(self.provider_name, "Invalid API key")
                elif response.status == 404:
                    raise ModelNotFoundError(self.provider_name, request.model)
                elif response.status == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    raise RateLimitError(
                        self.provider_name,
                        "Rate limit exceeded",
                        retry_after=int(retry_after)
                    )
                elif response.status == 503:
                    raise ServiceUnavailableError(self.provider_name)
                elif response.status != 200:
                    error_text = await response.text()
                    raise ProviderError(self.provider_name, f"API error: {error_text}", response.status)
                
                data = await response.json()

                content = data["choices"][0]["message"]["content"]
                finish_reason = data["choices"][0].get("finish_reason")
                raw_usage = data.get("usage", {})

                # 兼容 MIMO 等提供商返回的扩展 usage 字段（如 *_tokens_details）
                # 只保留整数字段，避免 Pydantic 验证错误
                usage = {
                    "prompt_tokens": int(raw_usage.get("prompt_tokens", 0)),
                    "completion_tokens": int(raw_usage.get("completion_tokens", 0)),
                    "total_tokens": int(raw_usage.get("total_tokens", 0))
                }
                
                return self._create_response(
                    content=content,
                    messages=request.messages,
                    model=request.model,
                    usage=usage,
                    raw_response=data,
                    finish_reason=finish_reason
                )
        
        except asyncio.TimeoutError:
            raise TimeoutError(self.provider_name, self.provider_config.timeout)
    
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """流式聊天接口"""
        self._check_rate_limit()
        
        session = await self._get_session()
        
        payload = {
            "model": request.model,
            "messages": [msg.dict(exclude_none=True) for msg in request.messages],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": True
        }
        
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.stop:
            payload["stop"] = request.stop
        
        url = f"{self.base_url}/chat/completions"
        
        try:
            async with session.post(url, json=payload) as response:
                if response.status == 401:
                    raise AuthenticationError(self.provider_name, "Invalid API key")
                elif response.status == 404:
                    raise ModelNotFoundError(self.provider_name, request.model)
                elif response.status == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    raise RateLimitError(
                        self.provider_name,
                        "Rate limit exceeded",
                        retry_after=int(retry_after)
                    )
                elif response.status != 200:
                    error_text = await response.text()
                    raise ProviderError(self.provider_name, f"API error: {error_text}", response.status)
                
                async for line in response.content:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        
        except asyncio.TimeoutError:
            raise TimeoutError(self.provider_name, self.provider_config.timeout)
    
    async def embed(self, text: str, model: Optional[str] = None) -> List[float]:
        """文本嵌入"""
        embed_model = model or "text-embedding-ada-002"
        session = await self._get_session()
        
        payload = {
            "model": embed_model,
            "input": text
        }
        
        url = f"{self.base_url}/embeddings"
        
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise ProviderError(self.provider_name, f"Embed error: {error_text}", response.status)
            
            data = await response.json()
            return data["data"][0]["embedding"]
    
    async def list_models(self) -> List[str]:
        """列出可用模型"""
        if self.provider_config.models:
            return self.provider_config.models
        
        session = await self._get_session()
        url = f"{self.base_url}/models"
        
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return [model["id"] for model in data.get("data", [])]
            
            logger.warning(f"Failed to list models for {self.provider_name}")
            return [self.provider_config.default_model]
    
    async def close(self):
        """关闭会话"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def __del__(self):
        """析构函数 — 尝试同步关闭 session"""
        if self._session and not self._session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except RuntimeError:
                pass  # 没有运行中的事件循环，忽略
