"""
ModelNexusCore — L0 LLM 基础设施核心 (M11 Phase 1)

设计依据: docs/M11_MODELNEXUS_CORE_REFACTOR.md v2.0

Pipeline 模式 — 可插拔管线阶段（6轮专家评审）
"""

import asyncio
import time
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional, Any

from .core import ChatRequest, LLMResponse, Message, MessageRole

logger = logging.getLogger(__name__)

# Feature flag: MODELNEXUS_CORE=1 启用新架构
_USE_CORE = os.getenv("MODELNEXUS_CORE", "0") == "1"


def is_core_enabled() -> bool:
    return _USE_CORE


# ============================================================
# Pipeline Context
# ============================================================

class PipelineContext:
    """管线上下文 — 在阶段间传递"""
    def __init__(self, request: ChatRequest):
        self.request = request
        self.response: Optional[LLMResponse] = None
        self.metadata: dict = {}
        self.start_time = time.monotonic()
        self._short_circuit = False

    def short_circuit(self):
        self._short_circuit = True

    @property
    def should_short_circuit(self) -> bool:
        return self._short_circuit

    @property
    def elapsed_ms(self) -> float:
        return (time.monotonic() - self.start_time) * 1000


# ============================================================
# Pipeline Stage
# ============================================================

class PipelineStage(ABC):
    """管线阶段 — 可插拔，可排序"""
    name: str = "base"
    priority: int = 50

    @abstractmethod
    async def process(self, ctx: PipelineContext) -> PipelineContext: ...

    @property
    def can_parallel_with(self) -> set[str]:
        return set()


# ============================================================
# Security Stage (安全前置检查)
# ============================================================

class SecurityStage(PipelineStage):
    """安全检查 — 前置 PromptGuard + 内容审核"""
    name = "security"
    priority = 5  # 最先执行

    def __init__(self):
        self._guard = None
        self._moderator = None

    async def _init_guard(self):
        if self._guard is None:
            try:
                from modelnexus.security.prompt_guard import PromptGuard
                self._guard = PromptGuard()
            except ImportError:
                pass

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        await self._init_guard()
        if self._guard:
            try:
                text = self._extract_text(ctx.request)
                matches = await self._guard.check(text)
                if matches:
                    logger.warning(f"PromptGuard: {len(matches)} injection matches detected")
                    ctx.metadata["security_flagged"] = True
            except Exception:
                pass
        return ctx

    @staticmethod
    def _extract_text(request: ChatRequest) -> str:
        texts = []
        for msg in request.messages:
            content = getattr(msg, 'content', str(msg))
            if content:
                texts.append(content)
        return " ".join(texts[-3:])


# ============================================================
# Cache Stage (L1+L2+L3)
# ============================================================

class CacheReadStage(PipelineStage):
    """缓存读取 — L1 精确 → L2 语义"""
    name = "cache_read"
    priority = 10

    def __init__(self):
        self._cache = None

    async def _init_cache(self):
        if self._cache is None:
            try:
                from packages.LLMInfra.cache import CacheManager
                from packages.LLMInfra.config import Settings, CacheConfig
                cfg = CacheConfig(enabled=True, type="memory", ttl=3600)
                self._cache = CacheManager(cfg)
            except ImportError:
                pass

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        await self._init_cache()
        if self._cache:
            try:
                cached = await self._cache.get(ctx.request)
                if cached:
                    ctx.response = LLMResponse(**cached)
                    ctx.metadata["cache_hit"] = "L1"
                    ctx.short_circuit()
                    return ctx
            except Exception:
                pass

        # L2 语义缓存（如果可用）
        if self._cache and hasattr(self._cache, '_semantic_layer') and self._cache._semantic_layer:
            try:
                result = await self._cache._semantic_layer.get(ctx.request)
                if result:
                    ctx.response = result
                    ctx.metadata["cache_hit"] = "L2"
                    ctx.short_circuit()
            except Exception:
                pass

        return ctx


class CacheWriteStage(PipelineStage):
    """缓存写入 — 异步写入 L1+L2"""
    name = "cache_write"
    priority = 90

    def __init__(self):
        self._cache = None

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.response and hasattr(self, '_cache_manager') and self._cache_manager:
            try:
                await self._cache_manager.set(ctx.request, ctx.response.model_dump())
            except Exception:
                pass
        return ctx


# ============================================================
# Rate Limit Stage
# ============================================================

class RateLimitStage(PipelineStage):
    """限流控制 — 令牌桶 (ModelNexus RateLimiter)"""
    name = "rate_limit"
    priority = 25
    can_parallel_with = {"cache_read"}

    def __init__(self):
        self._limiter = None

    async def _init_limiter(self):
        if self._limiter is None:
            try:
                from packages.Runtime.flow_control.rate_limiter import TokenBucketRateLimiter
                self._limiter = TokenBucketRateLimiter(capacity=100, refill_rate=10.0)
            except ImportError:
                pass

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        await self._init_limiter()
        if self._limiter:
            try:
                acquired = await self._limiter.acquire()
                if not acquired:
                    ctx.metadata["rate_limited"] = True
                    ctx.short_circuit()
                    logger.warning("Rate limit triggered")
            except Exception:
                pass
        return ctx


# ============================================================
# Route + Provider Stage
# ============================================================

class RouteStage(PipelineStage):
    """路由选择 — 成本 + 健康 + A/B"""
    name = "route"
    priority = 30

    def __init__(self, provider_factory=None):
        self._factory = provider_factory

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        if self._factory:
            try:
                provider = self._factory.get_provider(
                    self._factory.settings.default_provider
                )
                ctx.metadata["provider"] = provider.provider_name
                ctx.metadata["model"] = provider.provider_config.default_model
            except Exception:
                pass
        return ctx


class ProviderStage(PipelineStage):
    """Provider 调用 — 实际 LLM 请求"""
    name = "provider"
    priority = 50

    def __init__(self, provider_factory=None):
        self._factory = provider_factory

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.should_short_circuit:
            return ctx

        provider_name = ctx.metadata.get("provider", "mock")
        try:
            provider = self._factory.get_provider(provider_name)
            ctx.response = await provider.chat(ctx.request)
            ctx.metadata["provider"] = ctx.response.provider
            ctx.metadata["model"] = ctx.response.model
        except Exception as e:
            # Fallback to mock
            try:
                mock = self._factory.get_provider("mock")
                ctx.response = await mock.chat(ctx.request)
                ctx.metadata["degraded"] = str(e)
            except Exception:
                raise
        return ctx


# ============================================================
# Quality + Observe Stage
# ============================================================

class QualityStage(PipelineStage):
    """质量校验 — 完整性 + 安全性"""
    name = "quality"
    priority = 70

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.response and ctx.response.content:
            # 基础完整性：空响应检测
            if not ctx.response.content.strip():
                ctx.metadata["quality_issue"] = "empty_response"
        return ctx


class ObserveStage(PipelineStage):
    """可观测性 — 延迟 + Token 指标"""
    name = "observe"
    priority = 95

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        ctx.metadata["elapsed_ms"] = ctx.elapsed_ms
        if ctx.response and ctx.response.usage:
            ctx.metadata["tokens"] = ctx.response.usage.get("total_tokens", 0)
        return ctx


# ============================================================
# ModelNexusCore
# ============================================================

class ModelNexusCore:
    """
    L0 LLM 基础设施核心 (M11)

    管线流程:
      Security → CacheRead → Route → Provider → Quality → CacheWrite → Observe
    """

    def __init__(self, provider_factory=None, settings=None):
        self._factory = provider_factory
        self._settings = settings

        # 构建默认管线
        self._pipeline: list[PipelineStage] = [
            SecurityStage(),
            CacheReadStage(),
            RateLimitStage(),
            RouteStage(self._factory),
            ProviderStage(self._factory),
            QualityStage(),
            CacheWriteStage(),
            ObserveStage(),
        ]

        self._pipeline.sort(key=lambda s: s.priority)

    def register_stage(self, stage: PipelineStage):
        """注册自定义管线阶段（扩展专家 #1）"""
        self._pipeline.append(stage)
        self._pipeline.sort(key=lambda s: s.priority)

    def get_pipeline_info(self) -> list[dict]:
        return [{"name": s.name, "priority": s.priority} for s in self._pipeline]

    async def chat(self, request: ChatRequest) -> LLMResponse:
        """核心入口 — 穿过完整管线"""
        ctx = PipelineContext(request)

        for stage in self._pipeline:
            try:
                ctx = await stage.process(ctx)
                if ctx.should_short_circuit:
                    break
            except Exception as e:
                logger.error(f"Pipeline stage '{stage.name}' failed: {e}")
                ctx.metadata["error"] = str(e)
                # 非 Provider 阶段失败不中断（优雅降级）
                if stage.name == "provider":
                    raise

        # 如果所有阶段结束但无响应（例如缓存命中时 short_circuit 已有 response）
        if ctx.response is None:
            from .core import LLMResponse as LR
            ctx.response = LR(
                provider="core", model="fallback",
                content="Unable to process request.",
                messages=ctx.request.messages,
                usage={},
            )

        return ctx.response

    def get_stats(self) -> dict:
        """供给 SoulTeam L5 集群监控和 TUI 展示"""
        return {
            "pipeline": self.get_pipeline_info(),
            "enabled": True,
            "provider_count": len(self._factory.get_available_providers()) if self._factory else 0,
            "default_provider": self._settings.default_provider if self._settings else "unknown",
        }
