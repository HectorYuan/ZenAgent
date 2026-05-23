"""
自适应 Provider 负载均衡器

设计依据: E2E_OPTIMIZATION_DESIGN §模块13 (M9c)

增强 ProviderChain 的 LOAD_BALANCE 策略:
- 自适应评分: latency×0.3 + success_rate×0.4 + cost×0.3
- 并行请求: SIMPLE_QA 意图→并行调用 2 个 Provider, 取最快
- 成本感知: 按 Token 单价智能选择
"""

import asyncio
import time
import logging
from typing import Optional, List
from dataclasses import dataclass, field

from .providers.base import BaseProvider
from .core import ChatRequest
from .circuit_breaker import CircuitState

logger = logging.getLogger(__name__)


@dataclass
class ProviderMetrics:
    """Provider 性能指标"""
    provider_name: str
    total_calls: int = 0
    success_calls: int = 0
    failure_calls: int = 0
    total_latency_ms: float = 0.0
    latency_records: list[float] = field(default_factory=list)  # 最近 50 次
    cost_per_1k_input: float = 0.0015
    cost_per_1k_output: float = 0.002

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return self.success_calls / self.total_calls

    @property
    def p50_latency_ms(self) -> float:
        if not self.latency_records:
            return 0
        sorted_l = sorted(self.latency_records)
        return sorted_l[len(sorted_l) // 2]

    @property
    def avg_latency_ms(self) -> float:
        if self.total_calls == 0:
            return 0
        return self.total_latency_ms / self.total_calls

    def record(self, success: bool, latency_ms: float):
        self.total_calls += 1
        if success:
            self.success_calls += 1
        else:
            self.failure_calls += 1
        self.total_latency_ms += latency_ms
        self.latency_records.append(latency_ms)
        if len(self.latency_records) > 50:
            self.latency_records = self.latency_records[-50:]

    def estimated_cost(self, input_tokens: int = 100, output_tokens: int = 200) -> float:
        return (input_tokens / 1000) * self.cost_per_1k_input + (output_tokens / 1000) * self.cost_per_1k_output


class AdaptiveLoadBalancer:
    """
    自适应 Provider 选择器

    评分公式: latency_p50 × 0.3 + (1 - success_rate) × 0.4 × 100 + normalized_cost × 0.3
    分数越低越优先
    """

    LATENCY_WEIGHT = 0.3
    SUCCESS_WEIGHT = 0.4
    COST_WEIGHT = 0.3

    def __init__(self):
        self._metrics: dict[str, ProviderMetrics] = {}
        self._lock = asyncio.Lock()

    def get_or_create_metrics(self, provider: BaseProvider) -> ProviderMetrics:
        name = provider.provider_name
        if name not in self._metrics:
            self._metrics[name] = ProviderMetrics(
                provider_name=name,
                cost_per_1k_input=getattr(getattr(provider, 'provider_config', None), 'cost_per_1k_input_tokens', 0.0015),
                cost_per_1k_output=getattr(getattr(provider, 'provider_config', None), 'cost_per_1k_output_tokens', 0.002),
            )
        return self._metrics[name]

    def record_call(self, provider: BaseProvider, success: bool, latency_ms: float):
        metrics = self.get_or_create_metrics(provider)
        metrics.record(success, latency_ms)

    def select(
        self,
        providers: list[BaseProvider],
        request: Optional[ChatRequest] = None,
    ) -> BaseProvider:
        """
        自适应选择最优 Provider

        过滤: 熔断中的 Provider
        评分: latency + success_rate + cost
        """
        available = [p for p in providers if self._is_healthy(p)]
        if not available:
            return providers[0]  # fallback

        if len(available) == 1:
            return available[0]

        # 归一化评分
        scored = []
        for p in available:
            m = self.get_or_create_metrics(p)
            lat_score = min(m.p50_latency_ms / 5000.0, 1.0)  # 5s 为基准
            success_score = 1.0 - m.success_rate
            cost_model = m.estimated_cost(100, 200)
            cost_score = min(cost_model / 0.01, 1.0)  # $0.01/req 为基准

            score = (
                lat_score * self.LATENCY_WEIGHT +
                success_score * self.SUCCESS_WEIGHT +
                cost_score * self.COST_WEIGHT
            )
            scored.append((p, score))

        scored.sort(key=lambda x: x[1])
        return scored[0][0]

    async def parallel_best(
        self,
        providers: list[BaseProvider],
        request: ChatRequest,
        max_parallel: int = 2,
    ) -> BaseProvider:
        """
        并行请求: 同时调用 N 个 Provider，返回最快成功的

        适用于 SIMPLE_QA 意图（低延迟优先）
        """
        available = [p for p in providers if self._is_healthy(p)]
        if len(available) < 2:
            return self.select(available, request)

        # 选最快的 2 个
        candidates = available[:max_parallel]

        tasks = []
        for p in candidates:
            tasks.append(self._try_chat(p, request))

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        result_provider = None
        for task in done:
            try:
                provider_name, response = await task
                result_provider = provider_name
                self.record_call(
                    next(p for p in providers if p.provider_name == provider_name),
                    True, time.time() * 1000
                )
            except Exception:
                pass

        # 取消剩余
        for task in pending:
            task.cancel()

        if result_provider:
            return next(p for p in providers if p.provider_name == result_provider)

        return self.select(available, request)

    @staticmethod
    async def _try_chat(provider: BaseProvider, request: ChatRequest) -> tuple[str, any]:
        try:
            result = await provider.chat(request)
            return provider.provider_name, result
        except Exception as e:
            raise

    @staticmethod
    def _is_healthy(provider: BaseProvider) -> bool:
        """检查 Provider 是否健康（熔断器未打开）"""
        if hasattr(provider, '_circuit_breaker'):
            cb = provider._circuit_breaker
            if cb and cb.state == CircuitState.OPEN:
                return False
        return True

    def get_metrics(self) -> dict:
        return {
            name: {
                "total_calls": m.total_calls,
                "success_rate": round(m.success_rate, 3),
                "p50_latency_ms": round(m.p50_latency_ms, 1),
                "avg_latency_ms": round(m.avg_latency_ms, 1),
                "estimated_cost_per_req": round(m.estimated_cost(), 6),
            }
            for name, m in self._metrics.items()
        }

    def cost_optimize(
        self,
        providers: list[BaseProvider],
        max_cost: float = 0.01,
    ) -> Optional[BaseProvider]:
        """成本最优选择: 在预算内选最便宜的"""
        available = [p for p in providers if self._is_healthy(p)]
        best = None
        best_cost = float('inf')

        for p in available:
            m = self.get_or_create_metrics(p)
            cost = m.estimated_cost()
            if cost < best_cost and cost <= max_cost:
                best_cost = cost
                best = p

        return best or (available[0] if available else None)
