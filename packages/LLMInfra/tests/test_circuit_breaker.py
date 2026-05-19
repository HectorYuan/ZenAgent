"""
熔断器测试

设计依据: E2E_OPTIMIZATION_DESIGN §模块5
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import asyncio

from circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerOpenError,
)


class TestCircuitBreaker:
    """熔断器测试"""

    @pytest.mark.asyncio
    async def test_initial_state_closed(self):
        """初始状态为 CLOSED"""
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_success_keeps_closed(self):
        """成功调用保持 CLOSED"""
        cb = CircuitBreaker("test")
        result = await cb.call(asyncio.sleep, 0)
        assert result is None
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_consecutive_failures_opens(self):
        """连续失败触发 OPEN"""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)

        async def failing():
            raise ValueError("fail")

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(failing)

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_rejects_calls(self):
        """OPEN 状态拒绝调用"""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config)

        async def failing():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await cb.call(failing)

        assert cb.state == CircuitState.OPEN
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(asyncio.sleep, 0)

    @pytest.mark.asyncio
    async def test_open_to_half_open_recovery(self):
        """OPEN → HALF_OPEN 恢复"""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
        cb = CircuitBreaker("test", config)

        async def failing():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await cb.call(failing)

        assert cb.state == CircuitState.OPEN
        await asyncio.sleep(0.15)
        # 下一次调用应该进入 HALF_OPEN
        result = await cb.call(asyncio.sleep, 0)
        assert cb.state == CircuitState.CLOSED  # 成功后关闭

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self):
        """HALF_OPEN 失败重新打开"""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
        cb = CircuitBreaker("test", config)

        async def failing():
            raise ValueError("fail")

        # 触发熔断
        with pytest.raises(ValueError):
            await cb.call(failing)

        # 等待恢复
        await asyncio.sleep(0.15)

        # 半开状态下的失败
        with pytest.raises(ValueError):
            await cb.call(failing)

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_error_rate_threshold(self):
        """错误率阈值触发"""
        config = CircuitBreakerConfig(
            failure_threshold=100,  # 不用连续失败触发
            error_rate_threshold=0.35,  # 35% 阈值
            window_size=10,
        )
        cb = CircuitBreaker("test", config)

        async def failing():
            raise ValueError("fail")

        # 7 成功 + 3 失败 = 30% 错误率（不触发）
        for _ in range(7):
            await cb.call(asyncio.sleep, 0)
        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(failing)
        assert cb.state == CircuitState.CLOSED

        # 再加 1 失败 = 4/10 = 40% 错误率（≥35%，触发熔断）
        with pytest.raises(ValueError):
            await cb.call(failing)
        assert cb.state == CircuitState.OPEN

        # 后续调用被拒绝
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(failing)

    @pytest.mark.asyncio
    async def test_half_open_success_closes(self):
        """半开状态成功后关闭熔断器"""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1,
            half_open_max_calls=2,
        )
        cb = CircuitBreaker("test", config)

        async def failing():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await cb.call(failing)

        await asyncio.sleep(0.15)

        # 半开状态成功 → 熔断器关闭
        await cb.call(asyncio.sleep, 0)
        assert cb.state == CircuitState.CLOSED

        # 后续调用正常通过
        await cb.call(asyncio.sleep, 0)
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_manual_record(self):
        """手动记录成功/失败"""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_stats(self):
        """统计信息"""
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker("test", config)

        await cb.call(asyncio.sleep, 0)

        async def failing():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await cb.call(failing)

        stats = cb.get_stats()
        assert stats["total_calls"] == 2
        assert stats["success_calls"] == 1
        assert stats["failure_calls"] == 1
        assert stats["state"] == "closed"

    @pytest.mark.asyncio
    async def test_reset(self):
        """重置"""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config)

        async def failing():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await cb.call(failing)
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.get_stats()["total_calls"] == 0

    @pytest.mark.asyncio
    async def test_rejected_calls_counter(self):
        """拒绝计数"""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config)

        async def failing():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await cb.call(failing)

        for _ in range(5):
            with pytest.raises(CircuitBreakerOpenError):
                await cb.call(asyncio.sleep, 0)

        assert cb.get_stats()["rejected_calls"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
