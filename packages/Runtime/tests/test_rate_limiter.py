"""
令牌桶限流器测试

设计依据: E2E_OPTIMIZATION_DESIGN §模块4
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import asyncio

from flow_control.rate_limiter import (
    TokenBucketRateLimiter,
    PriorityRateLimiter,
    PriorityLimiterConfig,
    Priority,
)


class TestTokenBucketRateLimiter:
    """令牌桶限流器测试"""

    @pytest.mark.asyncio
    async def test_basic_acquire(self):
        """基本获取"""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=10.0)
        assert await limiter.acquire(1) is True
        assert limiter.available_tokens == 9.0

    @pytest.mark.asyncio
    async def test_acquire_exceeds_capacity(self):
        """获取超过容量"""
        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=10.0)
        assert await limiter.acquire(5) is True
        assert await limiter.acquire(1) is False

    @pytest.mark.asyncio
    async def test_refill(self):
        """令牌补充"""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=100.0)
        # 耗尽令牌
        await limiter.acquire(10)
        assert limiter.available_tokens == 0.0
        # 等待补充
        await asyncio.sleep(0.05)
        async with limiter._lock:
            limiter._refill()
        assert limiter.available_tokens > 0.0

    @pytest.mark.asyncio
    async def test_acquire_or_wait(self):
        """阻塞等待获取"""
        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=100.0)
        await limiter.acquire(5)
        # 桶空，等待补充
        result = await limiter.acquire_or_wait(1, timeout=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_acquire_or_wait_timeout(self):
        """阻塞等待超时"""
        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=0.1)  # 极慢补充
        await limiter.acquire(5)
        result = await limiter.acquire_or_wait(1, timeout=0.01)
        assert result is False

    @pytest.mark.asyncio
    async def test_stats(self):
        """统计信息"""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=10.0)
        await limiter.acquire(3)
        await limiter.acquire(100)  # 失败
        stats = limiter.get_stats()
        assert stats["tokens_acquired"] == 3
        assert stats["tokens_rejected"] == 100
        assert stats["capacity"] == 10

    @pytest.mark.asyncio
    async def test_reset(self):
        """重置"""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=10.0)
        await limiter.acquire(10)
        assert limiter.available_tokens == 0.0
        limiter.reset()
        assert limiter.available_tokens == 10.0

    @pytest.mark.asyncio
    async def test_concurrent_acquire(self):
        """并发安全"""
        limiter = TokenBucketRateLimiter(capacity=100, refill_rate=0)
        results = []

        async def try_acquire():
            r = await limiter.acquire(1)
            results.append(r)

        await asyncio.gather(*[try_acquire() for _ in range(150)])
        assert sum(results) == 100  # 只有 100 个成功


class TestPriorityRateLimiter:
    """优先级限流器测试"""

    @pytest.mark.asyncio
    async def test_p0_unlimited(self):
        """P0 不限速"""
        limiter = PriorityRateLimiter(PriorityLimiterConfig(p0_capacity=0))
        for _ in range(1000):
            assert await limiter.acquire(Priority.P0) is True

    @pytest.mark.asyncio
    async def test_p1_standard_limit(self):
        """P1 标准限速"""
        config = PriorityLimiterConfig(p1_capacity=5, p1_refill_rate=0)
        limiter = PriorityRateLimiter(config)
        for _ in range(5):
            assert await limiter.acquire(Priority.P1) is True
        assert await limiter.acquire(Priority.P1) is False

    @pytest.mark.asyncio
    async def test_p2_strict_limit(self):
        """P2 严格限速"""
        config = PriorityLimiterConfig(p2_capacity=3, p2_refill_rate=0)
        limiter = PriorityRateLimiter(config)
        for _ in range(3):
            assert await limiter.acquire(Priority.P2) is True
        assert await limiter.acquire(Priority.P2) is False

    @pytest.mark.asyncio
    async def test_backpressure(self):
        """背压机制"""
        config = PriorityLimiterConfig(
            p2_capacity=100,
            p2_refill_rate=100.0,
            backpressure_threshold=0.8,
        )
        limiter = PriorityRateLimiter(config)
        limiter.set_queue_depth(90)  # 超过 80% 阈值
        assert await limiter.acquire(Priority.P2) is False
        stats = limiter.get_stats()
        assert stats["rejected_by_backpressure"] == 1

    @pytest.mark.asyncio
    async def test_backpressure_does_not_affect_p1(self):
        """背压不影响 P1"""
        config = PriorityLimiterConfig(
            p1_capacity=100,
            p1_refill_rate=100.0,
            backpressure_threshold=0.8,
        )
        limiter = PriorityRateLimiter(config)
        limiter.set_queue_depth(90)  # 超过阈值
        assert await limiter.acquire(Priority.P1) is True

    @pytest.mark.asyncio
    async def test_stats(self):
        """统计信息"""
        limiter = PriorityRateLimiter()
        await limiter.acquire(Priority.P0)
        await limiter.acquire(Priority.P1)
        stats = limiter.get_stats()
        assert "p1" in stats
        assert "p2" in stats
        assert "queue_depth" in stats

    @pytest.mark.asyncio
    async def test_reset(self):
        """重置"""
        config = PriorityLimiterConfig(p1_capacity=5, p1_refill_rate=0)
        limiter = PriorityRateLimiter(config)
        await limiter.acquire(Priority.P1)
        await limiter.acquire(Priority.P1)
        limiter.reset()
        stats = limiter.get_stats()
        assert stats["p1"]["available_tokens"] == 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
