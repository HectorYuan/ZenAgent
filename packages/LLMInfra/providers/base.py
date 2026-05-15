"""
Provider 基类
"""

from abc import ABC, abstractmethod
from typing import List, Optional, AsyncIterator, Dict, Any
import logging
import time
from datetime import datetime

from ..core import ChatRequest, LLMResponse, Message
from ..config import Settings
from ..exceptions import ProviderError, RateLimitError, TimeoutError, ServiceUnavailableError

logger = logging.getLogger(__name__)


class BaseProvider(ABC):
    """LLM 提供商基类"""
    
    def __init__(self, provider_name: str, settings: Settings):
        self.provider_name = provider_name
        self.settings = settings
        self.provider_config = settings.get_provider_config(provider_name)
        self.api_key = self.provider_config.api_key
        self.base_url = self.provider_config.base_url
        self._request_count = 0
        self._token_count = 0
        self._last_reset = time.time()
    
    @abstractmethod
    async def chat(self, request: ChatRequest) -> LLMResponse:
        """
        聊天接口
        
        Args:
            request: 聊天请求
        
        Returns:
            LLMResponse
        """
        pass
    
    @abstractmethod
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """
        流式聊天接口
        
        Args:
            request: 聊天请求
        
        Yields:
            内容片段
        """
        pass
    
    @abstractmethod
    async def embed(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        文本嵌入
        
        Args:
            text: 文本
            model: 模型名称
        
        Returns:
            嵌入向量
        """
        pass
    
    @abstractmethod
    async def list_models(self) -> List[str]:
        """
        列出可用模型
        
        Returns:
            模型列表
        """
        pass
    
    def _update_usage(self, input_tokens: int, output_tokens: int):
        """更新使用统计"""
        self._request_count += 1
        self._token_count += input_tokens + output_tokens
        
        now = time.time()
        if now - self._last_reset > 60:
            self._request_count = 1
            self._token_count = input_tokens + output_tokens
            self._last_reset = now
    
    def _check_rate_limit(self, input_tokens: int = 0):
        """检查限流"""
        if not self.settings.rate_limit.enabled:
            return
        
        elapsed = time.time() - self._last_reset
        if elapsed > 60:
            return
        
        req_limit = self.settings.rate_limit.requests_per_minute
        token_limit = self.settings.rate_limit.tokens_per_minute
        
        if self._request_count >= req_limit:
            retry_after = int(60 - elapsed)
            raise RateLimitError(
                self.provider_name,
                f"Rate limit exceeded: {self._request_count}/{req_limit} requests",
                retry_after=retry_after
            )
        
        if self._token_count + input_tokens > token_limit:
            retry_after = int(60 - elapsed)
            raise RateLimitError(
                self.provider_name,
                f"Token limit exceeded: {self._token_count + input_tokens}/{token_limit}",
                retry_after=retry_after
            )
    
    def _create_response(
        self,
        content: str,
        messages: List[Message],
        model: str,
        usage: Dict[str, int],
        raw_response: Optional[Dict] = None
    ) -> LLMResponse:
        """创建响应对象"""
        cost = self.settings.calculate_cost(
            self.provider_name,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0)
        )
        
        self._update_usage(
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0)
        )
        
        return LLMResponse(
            provider=self.provider_name,
            model=model,
            content=content,
            messages=messages,
            usage=usage,
            cost=cost,
            raw_response=raw_response
        )
