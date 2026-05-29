from __future__ import annotations
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
        from .provider_chain import ProviderChain, create_default_chain
        from .precache import PreCacheWorker

        self.settings = settings or Settings()
        self.provider_factory = ProviderFactory(self.settings)
        self.cache_manager = CacheManager(self.settings.cache)
        self.token_budget = TokenBudgetManager(self.settings.token_budget)
        self.response_validator = ResponseValidator(self.settings.response)
        self.provider_chain = create_default_chain(self.provider_factory)
        self.enable_provider_chain = True

        # ModelNexusCore — 唯一 LLM 调用路径
        from .modelnexus_core import ModelNexusCore
        self._core = ModelNexusCore(self.provider_factory, self.settings)
        logger.info("ModelNexusCore initialized as sole LLM path")

        # M9b: 响应质量评分管道
        from .quality_pipeline import ResponseQualityPipeline
        self.quality_pipeline = ResponseQualityPipeline()
        self.enable_quality_check = True

        # M9d: 混合专家系统
        from .mixture_of_agents import MixtureOfAgents
        self.moe = MixtureOfAgents(llm_chat_fn=None)  # 延迟注入

        # 预缓存 Worker（使用自身作为 LLM 调用者）
        self.precache_worker = PreCacheWorker(
            cache_manager=self.cache_manager,
            llm_caller=self._llm_call_for_precache
        )
        self.enable_precache = True
    
    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        provider: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        聊天 — 统一通过 ModelNexusCore 管线
        """
        request = ChatRequest(model=model or "default", messages=messages, **kwargs)
        return await self._core.chat(request)
    
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

    async def chat_with_chain(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        使用 Provider 责任链聊天（自动容灾切换）

        Args:
            messages: 消息列表
            model: 模型名称
            use_cache: 是否使用缓存
            **kwargs: 其他参数

        Returns:
            LLMResponse
        """
        # Token 预算管理
        messages = self.token_budget.maybe_truncate(messages)
        caller_max_tokens = kwargs.pop("max_tokens", None)
        budget = self.token_budget.allocate(messages, caller_max_tokens)
        if budget.max_tokens is not None:
            kwargs["max_tokens"] = budget.max_tokens

        # 使用默认 Provider 的默认模型（责任链内部会按优先级尝试）
        selected_provider = self.settings.default_provider
        selected_model = model or self.settings.get_provider_model(selected_provider)

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

        # 使用责任链调用
        chain_result = await self.provider_chain.chat(request)

        if not chain_result.success or not chain_result.response:
            raise RuntimeError(
                f"All providers failed. Attempts: {len(chain_result.attempts)}. "
                f"Last error: {chain_result.error}"
            )

        response = chain_result.response

        # 响应完整性校验（不重试，责任链已处理重试/降级）
        validation = self.response_validator.validate(response, request)
        if not validation.is_valid:
            logger.warning(
                "Response validation failed after chain fallback: issue=%s",
                validation.issue
            )

        # 存入缓存
        if use_cache:
            await self.cache_manager.set(request, response.model_dump())

        return response

    def get_chain_health(self) -> dict:
        """获取责任链健康状态"""
        return {
            "provider_health": self.provider_chain.get_provider_health(),
            "circuit_breakers": self.provider_chain.get_circuit_breaker_stats(),
            "enabled": self.enable_provider_chain
        }

    def get_cache_health(self) -> dict:
        """获取缓存系统健康状态"""
        return {
            "hotspot": self.cache_manager.get_hotspot_stats(),
            "precache": self.precache_worker.get_stats() if self.precache_worker else {},
            "enabled": self.cache_manager.enabled,
            "precache_enabled": self.enable_precache
        }

    def get_core_health(self) -> dict:
        """获取 ModelNexusCore 管线状态"""
        return {
            "enabled": True,
            "pipeline": self._core.get_pipeline_info(),
            "stats": self._core.get_stats(),
        }

    async def _llm_call_for_precache(self, request: ChatRequest) -> LLMResponse:
        """预缓存用的 LLM 调用器（走 ModelNexusCore 管线）"""
        return await self._core.chat(request)

    # ====================
    # 路径执行方法（intent_router 引用，统一走管线）
    # ====================

    async def chat_fast(self, request: ChatRequest) -> LLMResponse:
        """FastPath: 通过 ModelNexusCore 管线"""
        return await self._core.chat(request)

    async def chat_deep(self, request: ChatRequest) -> LLMResponse:
        """
        DeepPath: CoT 增强后通过管线
        """
        cot_hint = Message(
            role=MessageRole.SYSTEM,
            content="Think step by step before answering. Break down the problem, "
                    "consider alternatives, and provide a reasoned response."
        )
        enhanced_messages = [cot_hint] + list(request.messages)
        enhanced_request = ChatRequest(
            model=request.model,
            messages=enhanced_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            stream=request.stream,
            stop=request.stop,
            tools=request.tools,
        )
        return await self._core.chat(enhanced_request)

    async def chat_rag(self, request: ChatRequest) -> LLMResponse:
        """
        RAGPath: 知识库检索增强

        当前降级到 DeepPath。接入向量知识库后启用。
        """
        logger.info("RAG path not available, degrading to DeepPath")
        return await self.chat_deep(request)

    async def chat_tool(self, request: ChatRequest) -> LLMResponse:
        """
        ToolPath: 工具调用流程

        当前降级到 DeepPath。接入工具调用框架后启用。
        """
        logger.info("Tool path not available, degrading to DeepPath")
        return await self.chat_deep(request)

    async def chat_fallback(self, request: ChatRequest) -> LLMResponse:
        """
        FallbackPath: 兜底响应
        """
        from datetime import datetime

        user_content = ""
        for msg in request.messages:
            if msg.role == MessageRole.USER:
                user_content = msg.content[:100]
                break

        return LLMResponse(
            provider="fallback",
            model="fallback",
            content=f"I apologize, but I'm unable to process your request at this moment. "
                    f"Please try again or rephrase your question.",
            messages=list(request.messages),
            usage={"prompt_tokens": 0, "completion_tokens": 0},
            cost=0.0,
            finish_reason="error"
        )

    async def start_precache(self):
        """启动预缓存后台 Worker"""
        if self.precache_worker:
            await self.precache_worker.start()
        self.cache_manager.start_background_tasks()

    async def stop_precache(self):
        """停止预缓存后台 Worker"""
        if self.precache_worker:
            await self.precache_worker.stop()
        await self.cache_manager.stop_background_tasks()
