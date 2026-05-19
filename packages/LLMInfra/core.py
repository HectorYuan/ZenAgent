"""
核心模块 - 数据模型和客户端
"""

from typing import List, Dict, Any, Optional, AsyncIterator
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
import asyncio
import uuid
import logging

logger = logging.getLogger(__name__)


class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class Message(BaseModel):
    """消息模型"""
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class LLMResponse(BaseModel):
    """LLM 响应模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: str
    model: str
    content: str
    messages: List[Message]
    usage: Dict[str, int]
    cost: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    raw_response: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None


class ChatRequest(BaseModel):
    """聊天请求模型"""
    model: str
    messages: List[Message]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    stream: bool = False
    stop: Optional[List[str]] = None
    tools: Optional[List[Dict[str, Any]]] = None


class LLMClient:
    """LLM 客户端 - 统一接口"""
    
    def __init__(self, settings=None):
        from .config import Settings
        from .providers import ProviderFactory
        from .cache import CacheManager
        from .token_budget import TokenBudgetManager
        from .response_validator import ResponseValidator

        self.settings = settings or Settings()
        self.provider_factory = ProviderFactory(self.settings)
        self.cache_manager = CacheManager(self.settings.cache)
        self.token_budget = TokenBudgetManager(self.settings.token_budget)
        self.response_validator = ResponseValidator(self.settings.response)
    
    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        provider: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        同步聊天
        
        Args:
            messages: 消息列表
            model: 模型名称
            provider: 提供商名称
            use_cache: 是否使用缓存
            **kwargs: 其他参数
        
        Returns:
            LLMResponse
        """
        selected_provider = provider or self.settings.default_provider
        selected_model = model or self.settings.get_provider_model(selected_provider)

        # Token 预算管理
        messages = self.token_budget.maybe_truncate(messages)
        caller_max_tokens = kwargs.pop("max_tokens", None)
        budget = self.token_budget.allocate(messages, caller_max_tokens)
        if budget.max_tokens is not None:
            kwargs["max_tokens"] = budget.max_tokens

        request = ChatRequest(
            model=selected_model,
            messages=messages,
            **kwargs
        )
        
        # 检查缓存
        if use_cache:
            cached = await self.cache_manager.get(request)
            if cached:
                return LLMResponse(**cached)
        
        # 获取 Provider 并调用
        provider_instance = self.provider_factory.get_provider(selected_provider)
        
        response = await provider_instance.chat(request)

        # 响应完整性校验 + 自动重试
        validation = self.response_validator.validate(response, request)
        if not validation.is_valid and self.settings.response.auto_retry_on_truncation:
            if validation.issue == "truncated":
                new_max = (request.max_tokens or 2000) * 2
                logger.warning(
                    "响应截断，自动重试: finish_reason=%s, 原 max_tokens=%s, 新 max_tokens=%d",
                    validation.finish_reason, request.max_tokens, new_max,
                )
                kwargs["max_tokens"] = new_max
                request = ChatRequest(
                    model=selected_model,
                    messages=messages,
                    **kwargs
                )
                response = await provider_instance.chat(request)

        # 存入缓存
        if use_cache:
            await self.cache_manager.set(request, response.model_dump())
        
        return response
    
    async def chat_stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式聊天
        
        Args:
            messages: 消息列表
            model: 模型名称
            provider: 提供商名称
            **kwargs: 其他参数
        
        Yields:
            内容片段
        """
        selected_provider = provider or self.settings.default_provider
        selected_model = model or self.settings.get_provider_model(selected_provider)

        # Token 预算管理
        messages = self.token_budget.maybe_truncate(messages)
        caller_max_tokens = kwargs.pop("max_tokens", None)
        budget = self.token_budget.allocate(messages, caller_max_tokens)
        if budget.max_tokens is not None:
            kwargs["max_tokens"] = budget.max_tokens

        provider_instance = self.provider_factory.get_provider(selected_provider)

        request = ChatRequest(
            model=selected_model,
            messages=messages,
            stream=True,
            **kwargs
        )
        
        async for chunk in provider_instance.chat_stream(request):
            yield chunk
    
    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
        provider: Optional[str] = None
    ) -> List[float]:
        """
        文本嵌入
        
        Args:
            text: 文本
            model: 模型名称
            provider: 提供商名称
        
        Returns:
            嵌入向量
        """
        selected_provider = provider or self.settings.default_provider
        provider_instance = self.provider_factory.get_provider(selected_provider)
        
        return await provider_instance.embed(text, model)
    
    async def get_available_models(
        self,
        provider: Optional[str] = None
    ) -> List[str]:
        """
        获取可用模型列表
        
        Args:
            provider: 提供商名称
        
        Returns:
            模型列表
        """
        if provider:
            provider_instance = self.provider_factory.get_provider(provider)
            return await provider_instance.list_models()
        
        all_models = []
        for prov in self.settings.providers.keys():
            try:
                provider_instance = self.provider_factory.get_provider(prov)
                models = await provider_instance.list_models()
                all_models.extend([f"{prov}:{m}" for m in models])
            except Exception:
                pass
        return all_models
