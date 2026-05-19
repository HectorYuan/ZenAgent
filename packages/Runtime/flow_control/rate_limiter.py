"""
令牌桶限流器

设计依据: E2E_OPTIMIZATION_DESIGN §模块4 - 全链路异步流控体系
"""

import asyncio
import time
import logging
from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class Priority(Enum):
    """请求优先级"""
    P0 = 0  # 实时 - 不限速
    P1 = 1  # 普通 - 标准限速
    P2 = 2  # 后台 - 严格限速


@dataclass
class RateLimiterStats:
    """限流器统计"""
    tokens_acquired: int = 0
    tokens_rejected: int = 0
    wait_count: int = 0
    total_wait_time: float = 0.0


class TokenBucketRateLimiter:
    """
    令牌桶限流器

    基于令牌桶算法的异步限流器，支持非阻塞获取和阻塞等待。
    """

    def __init__(self, capacity: int = 100, refill_rate: float = 10.0):
        """
        初始化令牌桶

        Args:
            capacity: 桶容量（最大令牌数）
            refill_rate: 每秒补充令牌数
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()
        self._stats = RateLimiterStats()

    def _refill(self):
        """补充令牌（非线程安全，需在锁内调用）"""
        now = time.monotonic()
        elapsed = now - self._last_refill
        new_tokens = elapsed * self.refill_rate
        self._tokens = min(self.capacity, self._tokens + new_tokens)
        self._last_refill = now

    async def acquire(self, tokens: int = 1) -> bool:
        """
        非阻塞获取令牌

        Args:
            tokens: 需要的令牌数

        Returns:
            是否获取成功
        """
        async with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                self._stats.tokens_acquired += tokens
                return True
            else:
                self._stats.tokens_rejected += tokens
                return False

    async def acquire_or_wait(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        阻塞等待获取令牌

        Args:
            tokens: 需要的令牌数
            timeout: 最大等待时间（秒），None 表示无限等待

        Returns:
            是否获取成功
        """
        start = time.monotonic()
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    self._stats.tokens_acquired += tokens
                    wait_time = time.monotonic() - start
                    if wait_time > 0.001:
                        self._stats.total_wait_time += wait_time
                    return True

            # 计算需要等待的时间
            async with self._lock:
                deficit = tokens - self._tokens
                wait_seconds = deficit / self.refill_rate if self.refill_rate > 0 else 1.0

            if timeout is not None:
                elapsed = time.monotonic() - start
                if elapsed + wait_seconds > timeout:
                    self._stats.tokens_rejected += tokens
                    return False

            self._stats.wait_count += 1
            await asyncio.sleep(min(wait_seconds, 0.1))

    @property
    def available_tokens(self) -> float:
        """当前可用令牌数"""
        return self._tokens

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "capacity": self.capacity,
            "refill_rate": self.refill_rate,
            "available_tokens": round(self._tokens, 2),
            "tokens_acquired": self._stats.tokens_acquired,
            "tokens_rejected": self._stats.tokens_rejected,
            "wait_count": self._stats.wait_count,
            "total_wait_time": round(self._stats.total_wait_time, 4),
        }

    def reset(self):
        """重置限流器"""
        self._tokens = float(self.capacity)
        self._last_refill = time.monotonic()
        self._stats = RateLimiterStats()


@dataclass
class PriorityLimiterConfig:
    """优先级限流器配置"""
    p0_capacity: int = 0        # P0 不限速
    p0_refill_rate: float = 0.0
    p1_capacity: int = 100      # P1 标准限速
    p1_refill_rate: float = 10.0
    p2_capacity: int = 30       # P2 严格限速
    p2_refill_rate: float = 3.0
    backpressure_threshold: float = 0.8  # 背压阈值


class PriorityRateLimiter:
    """
    优先级限流器

    三个独立令牌桶对应三个优先级：
    - P0: 实时请求，不限速
    - P1: 普通请求，标准限速
    - P2: 后台请求，严格限速，受背压影响
    """

    def __init__(self, config: Optional[PriorityLimiterConfig] = None):
        config = config or PriorityLimiterConfig()
        self._config = config

        # P0 不限速（容量为 0 表示不限制）
        self._p0_enabled = config.p0_capacity > 0
        if self._p0_enabled:
            self._p0 = TokenBucketRateLimiter(config.p0_capacity, config.p0_refill_rate)

        self._p1 = TokenBucketRateLimiter(config.p1_capacity, config.p1_refill_rate)
        self._p2 = TokenBucketRateLimiter(config.p2_capacity, config.p2_refill_rate)

        self._queue_depth = 0
        self._max_queue_depth = config.p1_capacity  # 用 P1 容量作为队列上限
        self._rejected_by_backpressure = 0

    async def acquire(self, priority: Priority = Priority.P1, tokens: int = 1) -> bool:
        """
        按优先级获取令牌

        Args:
            priority: 请求优先级
            tokens: 需要的令牌数

        Returns:
            是否获取成功
        """
        if priority == Priority.P0:
            # P0 不限速
            if self._p0_enabled:
                return await self._p0.acquire(tokens)
            return True

        if priority == Priority.P2:
            # P2 受背压影响
            if self._is_backpressure_active():
                self._rejected_by_backpressure += tokens
                logger.warning(f"Backpressure active, rejecting P2 request (queue_depth={self._queue_depth})")
                return False
            return await self._p2.acquire(tokens)

        # P1 标准限速
        return await self._p1.acquire(tokens)

    async def acquire_or_wait(self, priority: Priority = Priority.P1, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        按优先级阻塞等待获取令牌

        Args:
            priority: 请求优先级
            tokens: 需要的令牌数
            timeout: 最大等待时间

        Returns:
            是否获取成功
        """
        if priority == Priority.P0:
            if self._p0_enabled:
                return await self._p0.acquire_or_wait(tokens, timeout)
            return True

        if priority == Priority.P2:
            if self._is_backpressure_active():
                self._rejected_by_backpressure += tokens
                return False
            return await self._p2.acquire_or_wait(tokens, timeout)

        return await self._p1.acquire_or_wait(tokens, timeout)

    def _is_backpressure_active(self) -> bool:
        """检查背压是否激活"""
        if self._max_queue_depth <= 0:
            return False
        return (self._queue_depth / self._max_queue_depth) > self._config.backpressure_threshold

    def set_queue_depth(self, depth: int):
        """设置当前队列深度（由外部调用）"""
        self._queue_depth = depth

    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = {
            "p1": self._p1.get_stats(),
            "p2": self._p2.get_stats(),
            "queue_depth": self._queue_depth,
            "backpressure_active": self._is_backpressure_active(),
            "rejected_by_backpressure": self._rejected_by_backpressure,
        }
        if self._p0_enabled:
            stats["p0"] = self._p0.get_stats()
        return stats

    def reset(self):
        """重置所有限流器"""
        if self._p0_enabled:
            self._p0.reset()
        self._p1.reset()
        self._p2.reset()
        self._queue_depth = 0
        self._rejected_by_backpressure = 0
