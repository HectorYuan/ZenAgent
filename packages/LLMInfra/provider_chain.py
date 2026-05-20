"""
Provider 责任链模块

设计依据: E2E_OPTIMIZATION_DESIGN §模块1 - 多 Provider 容灾切换

降级链路: ModelNexus → OpenAI → Mock (自动切换)
每跳独立超时配置: 30s → 60s → 10s
"""

import asyncio
import time
import logging
from typing import List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass, field

from .providers.base import BaseProvider
from .providers.factory import ProviderFactory
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError
from .core import ChatRequest, LLMResponse
from .config import Settings
from .exceptions import ProviderError, RateLimitError, TimeoutError, ServiceUnavailableError

logger = logging.getLogger(__name__)


class ChainStrategy(Enum):
    """责任链策略"""
    FAILOVER = "failover"          # 顺序失败转移: 主 Provider 失败尝试下一个
    LOAD_BALANCE = "load_balance"  # 负载均衡: 在健康 Provider 间轮询
    PRIORITY = "priority"          # 优先级: 始终选择最高优先级的健康 Provider


@dataclass
class ProviderChainConfig:
    """Provider 责任链配置"""
    # Provider 优先级列表（顺序决定失败转移顺序）
    provider_priority: List[str] = field(default_factory=lambda: ["modelnexus", "openai", "mock"])

    # 每 Provider 独立超时配置（秒）
    provider_timeouts: dict[str, float] = field(default_factory=lambda: {
        "modelnexus": 30.0,
        "openai": 60.0,
        "mock": 10.0,
    })

    # 责任链策略
    strategy: ChainStrategy = ChainStrategy.FAILOVER

    # 失败重试次数（每个 Provider 内部）
    max_retries_per_provider: int = 2

    # 是否启用每个 Provider 的独立熔断器
    enable_individual_circuit_breakers: bool = True

    # 熔断器配置
    circuit_breaker_config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)


@dataclass
class ChainAttempt:
    """一次调用尝试记录"""
    provider_name: str
    success: bool
    duration: float
    error: Optional[str] = None


@dataclass
class ChainResult:
    """责任链调用结果"""
    response: Optional[LLMResponse]
    success: bool
    attempts: List[ChainAttempt] = field(default_factory=list)
    total_duration: float = 0.0
    final_provider: Optional[str] = None
    error: Optional[str] = None


class ProviderChain:
    """
    Provider 责任链

    功能:
    - 主 Provider 失败自动尝试下一个
    - 失败原因分类处理 (超时/限流/错误)
    - 每跳独立超时配置
    - 每个 Provider 独立熔断器保护
    """

    def __init__(
        self,
        factory: ProviderFactory,
        config: Optional[ProviderChainConfig] = None,
        settings: Optional[Settings] = None
    ):
        self._factory = factory
        self._config = config or ProviderChainConfig()
        self._settings = settings or Settings()
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._round_robin_index = 0
        self._lock = asyncio.Lock()

        # 为每个 Provider 创建独立熔断器
        if self._config.enable_individual_circuit_breakers:
            for provider_name in self._config.provider_priority:
                self._circuit_breakers[provider_name] = CircuitBreaker(
                    name=f"provider_{provider_name}",
                    config=self._config.circuit_breaker_config
                )

    def get_timeout(self, provider_name: str) -> float:
        """获取 Provider 的超时配置"""
        return self._config.provider_timeouts.get(provider_name, 30.0)

    async def _call_with_timeout(
        self,
        provider: BaseProvider,
        request: ChatRequest,
        timeout: float
    ) -> LLMResponse:
        """带超时的 Provider 调用"""
        start_time = time.monotonic()

        try:
            async with asyncio.timeout(timeout):
                return await provider.chat(request)
        except asyncio.TimeoutError:
            raise TimeoutError(
                provider.provider_name,
                int(timeout)
            )

    async def _call_provider(
        self,
        provider_name: str,
        request: ChatRequest
    ) -> tuple[bool, Optional[LLMResponse], Optional[str]]:
        """
        调用单个 Provider（带熔断和重试）

        Returns:
            (success, response, error_message)
        """
        provider = self._factory.get_provider(provider_name)
        timeout = self.get_timeout(provider_name)
        circuit_breaker = self._circuit_breakers.get(provider_name)

        for attempt in range(self._config.max_retries_per_provider):
            try:
                if circuit_breaker:
                    # 通过熔断器调用
                    response = await circuit_breaker.call(
                        self._call_with_timeout,
                        provider,
                        request,
                        timeout
                    )
                else:
                    # 直接调用
                    response = await self._call_with_timeout(provider, request, timeout)

                return True, response, None

            except CircuitBreakerOpenError as e:
                # 熔断器打开，跳过此 Provider
                return False, None, f"Circuit breaker OPEN: {str(e)}"

            except TimeoutError as e:
                # 超时 - 重试
                if attempt < self._config.max_retries_per_provider - 1:
                    logger.debug(f"{provider_name} timeout, retry {attempt + 1}/{self._config.max_retries_per_provider}")
                    await asyncio.sleep(0.5)
                    continue
                return False, None, f"Timeout: {str(e)}"

            except RateLimitError as e:
                # 限流 - 直接放弃此 Provider（下一轮再试）
                return False, None, f"Rate limited: {str(e)}"

            except ServiceUnavailableError as e:
                # 服务不可用 - 重试
                if attempt < self._config.max_retries_per_provider - 1:
                    logger.debug(f"{provider_name} unavailable, retry {attempt + 1}/{self._config.max_retries_per_provider}")
                    await asyncio.sleep(1.0)
                    continue
                return False, None, f"Service unavailable: {str(e)}"

            except ProviderError as e:
                # 其他 Provider 错误 - 重试
                if attempt < self._config.max_retries_per_provider - 1:
                    logger.debug(f"{provider_name} error, retry {attempt + 1}/{self._config.max_retries_per_provider}: {e}")
                    await asyncio.sleep(0.3)
                    continue
                return False, None, f"Provider error: {str(e)}"

            except Exception as e:
                # 未知错误 - 重试
                if attempt < self._config.max_retries_per_provider - 1:
                    logger.warning(f"{provider_name} unexpected error, retry {attempt + 1}/{self._config.max_retries_per_provider}: {e}")
                    await asyncio.sleep(0.5)
                    continue
                return False, None, f"Unexpected error: {type(e).__name__}: {str(e)}"

        return False, None, "Max retries exceeded"

    def _get_health_providers(self) -> List[str]:
        """获取所有健康状态的 Provider（熔断器未打开）"""
        healthy = []
        for provider_name in self._config.provider_priority:
            cb = self._circuit_breakers.get(provider_name)
            if cb and cb.state.value == "open":
                continue  # 跳过熔断的 Provider
            healthy.append(provider_name)
        return healthy

    async def chat(self, request: ChatRequest) -> ChainResult:
        """
        通过责任链发起聊天请求

        Args:
            request: 聊天请求

        Returns:
            ChainResult: 调用结果（包含所有尝试记录）
        """
        total_start = time.monotonic()
        attempts: List[ChainAttempt] = []

        if self._config.strategy == ChainStrategy.FAILOVER:
            return await self._chat_failover(request, total_start, attempts)
        elif self._config.strategy == ChainStrategy.LOAD_BALANCE:
            return await self._chat_load_balance(request, total_start, attempts)
        else:
            return await self._chat_failover(request, total_start, attempts)

    async def _chat_failover(
        self,
        request: ChatRequest,
        total_start: float,
        attempts: List[ChainAttempt]
    ) -> ChainResult:
        """Failover 策略：按优先级顺序失败转移"""
        for provider_name in self._config.provider_priority:
            attempt_start = time.monotonic()

            success, response, error = await self._call_provider(provider_name, request)

            duration = time.monotonic() - attempt_start
            attempts.append(ChainAttempt(
                provider_name=provider_name,
                success=success,
                duration=duration,
                error=error
            ))

            if success and response:
                return ChainResult(
                    response=response,
                    success=True,
                    attempts=attempts,
                    total_duration=time.monotonic() - total_start,
                    final_provider=provider_name
                )

            logger.warning(f"{provider_name} failed: {error}, trying next...")

        # 所有 Provider 都失败
        return ChainResult(
            response=None,
            success=False,
            attempts=attempts,
            total_duration=time.monotonic() - total_start,
            final_provider=None,
            error="All providers failed"
        )

    async def _chat_load_balance(
        self,
        request: ChatRequest,
        total_start: float,
        attempts: List[ChainAttempt]
    ) -> ChainResult:
        """Load Balance 策略：在健康 Provider 间轮询"""
        healthy_providers = self._get_health_providers()
        if not healthy_providers:
            # 没有健康 Provider，回退到 failover
            return await self._chat_failover(request, total_start, attempts)

        async with self._lock:
            # 轮询选择起始点
            start_index = self._round_robin_index % len(healthy_providers)
            self._round_robin_index += 1

        # 从起始点开始尝试
        for i in range(len(healthy_providers)):
            provider_name = healthy_providers[(start_index + i) % len(healthy_providers)]
            attempt_start = time.monotonic()

            success, response, error = await self._call_provider(provider_name, request)

            duration = time.monotonic() - attempt_start
            attempts.append(ChainAttempt(
                provider_name=provider_name,
                success=success,
                duration=duration,
                error=error
            ))

            if success and response:
                return ChainResult(
                    response=response,
                    success=True,
                    attempts=attempts,
                    total_duration=time.monotonic() - total_start,
                    final_provider=provider_name
                )

        # 所有健康 Provider 都失败，回退到全部列表
        return await self._chat_failover(request, total_start, attempts)

    def get_circuit_breaker_stats(self) -> dict[str, dict]:
        """获取所有熔断器状态"""
        return {
            name: cb.get_stats()
            for name, cb in self._circuit_breakers.items()
        }

    def get_provider_health(self) -> dict[str, bool]:
        """获取 Provider 健康状态"""
        return {
            name: cb.state.value != "open"
            for name, cb in self._circuit_breakers.items()
        }

    def reset_circuit_breakers(self):
        """重置所有熔断器"""
        for cb in self._circuit_breakers.values():
            cb.reset()


# 便捷函数
def create_default_chain(factory: ProviderFactory) -> ProviderChain:
    """创建默认配置的 Provider 责任链"""
    # 只使用已配置的 Provider
    configured_providers = list(factory.settings.providers.keys())

    # 按优先级过滤
    priority_order = ["modelnexus", "openai", "mock"]
    available_priority = [p for p in priority_order if p in configured_providers]

    # 如果没有配置的，至少保证有 mock
    if not available_priority:
        available_priority = ["mock"]

    config = ProviderChainConfig(
        provider_priority=available_priority,
        provider_timeouts={
            "modelnexus": 30.0,
            "openai": 60.0,
            "mock": 10.0,
        },
        strategy=ChainStrategy.FAILOVER,
        max_retries_per_provider=2
    )
    return ProviderChain(factory, config)
