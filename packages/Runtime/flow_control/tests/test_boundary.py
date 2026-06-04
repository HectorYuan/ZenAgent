"""
Flow Control 边界测试

覆盖：零容量队列、负值输入、队列满时行为、stats 精度验证、大量任务压力测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pytest
import asyncio
from packages.Runtime.flow_control.priority_queue import (
    PriorityTaskQueue,
    BackpressureController,
    Priority,
    PriorityTask,
    QueueStats,
)
from packages.Runtime.flow_control.rate_limiter import (
    TokenBucketRateLimiter,
    PriorityRateLimiter,
    PriorityLimiterConfig,
)


# ============================================================
# 零容量 / 边界阈值测试
# ============================================================

class TestZeroCapacityBoundary:
    """零容量与边界阈值测试"""

    @pytest.mark.asyncio
    async def test_backpressure_zero_threshold_rejects_all(self):
        """warning_threshold=0 时所有任务都被拒绝（除 P0 在 critical 之前）"""
        bp = BackpressureController(warning_threshold=0.0, critical_threshold=0.0)
        # 任何非零深度都超过 0.0 阈值
        bp.update_depth(1, 100)
        # critical=0.0，所以 water_level(0.01) >= critical → 只接受 P0
        assert bp.can_accept(Priority.P0_REALTIME) is True
        assert bp.can_accept(Priority.P1_NORMAL) is False
        assert bp.can_accept(Priority.P2_BACKGROUND) is False

    @pytest.mark.asyncio
    async def test_backpressure_zero_depth_accepts_all(self):
        """深度为 0 时接受所有优先级"""
        bp = BackpressureController()
        bp.update_depth(0, 100)
        assert bp.can_accept(Priority.P0_REALTIME) is True
        assert bp.can_accept(Priority.P1_NORMAL) is True
        assert bp.can_accept(Priority.P2_BACKGROUND) is True

    def test_backpressure_max_depth_zero(self):
        """max_depth 为 0 时的水位计算"""
        bp = BackpressureController()
        bp.update_depth(0, 0)
        # max_depth 被 max(..., 1) 保护，水位应为 0
        assert bp.water_level == 0.0


# ============================================================
# 负值输入处理
# ============================================================

class TestNegativeInput:
    """负值输入处理"""

    @pytest.mark.asyncio
    async def test_rate_limiter_negative_tokens(self):
        """负 tokens 请求——应该成功（tokens >= 0 时检查通过）"""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=0)
        # 负 tokens 会使 _tokens 变大，属于意外但不崩溃
        result = await limiter.acquire(-1)
        # _tokens(10) >= -1 为 True，扣减后变为 11
        assert result is True

    def test_backpressure_negative_depth(self):
        """负深度输入——水位为负，低于所有阈值，全部接受"""
        bp = BackpressureController()
        bp.update_depth(-5, 100)
        assert bp.water_level == -0.05
        assert bp.can_accept(Priority.P0_REALTIME) is True
        assert bp.can_accept(Priority.P1_NORMAL) is True
        assert bp.can_accept(Priority.P2_BACKGROUND) is True


# ============================================================
# 队列满时的行为
# ============================================================

class TestQueueFullBehavior:
    """队列满时的行为测试"""

    @pytest.mark.asyncio
    async def test_enqueue_rejects_when_full(self):
        """队列满时入队返回 None"""
        q = PriorityTaskQueue()
        # 填满队列
        for i in range(q.TOTAL_CAPACITY):
            await q.enqueue(f"task_{i}", priority=Priority.P1_NORMAL)

        # 再入队应被拒绝
        result = await q.enqueue("overflow", priority=Priority.P1_NORMAL)
        assert result is None
        assert q.stats["rejected"] >= 1

    @pytest.mark.asyncio
    async def test_enqueue_with_timeout_on_full_queue(self):
        """满队列带 timeout 入队"""
        q = PriorityTaskQueue()
        for i in range(q.TOTAL_CAPACITY):
            await q.enqueue(f"task_{i}", priority=Priority.P0_REALTIME)

        result = await q.enqueue("timeout_task", priority=Priority.P0_REALTIME, timeout=0.01)
        assert result is None


# ============================================================
# stats 精度验证
# ============================================================

class TestStatsPrecision:
    """统计精度验证"""

    @pytest.mark.asyncio
    async def test_stats_reject_rate_zero_when_no_rejections(self):
        """无拒绝时拒绝率为 0"""
        q = PriorityTaskQueue()
        await q.enqueue("task", priority=Priority.P0_REALTIME)
        assert q.stats["reject_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_stats_reject_rate_calculation(self):
        """拒绝率精确计算"""
        bp = BackpressureController(panic_threshold=0.0)
        bp.update_depth(1, 1)  # 水位 1.0 >= panic → 拒绝全部
        q = PriorityTaskQueue(backpressure=bp)

        # 所有入队都会被背压拒绝
        for _ in range(5):
            await q.enqueue("task", priority=Priority.P0_REALTIME)

        stats = q.stats
        # rejected=5, total_enqueued=0 → reject_rate = 5/(5+0) = 1.0
        assert stats["reject_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_queue_stats_reset(self):
        """reset_stats 清零"""
        q = PriorityTaskQueue()
        for i in range(5):
            await q.enqueue(f"task_{i}", priority=Priority.P1_NORMAL)

        q.reset_stats()
        stats = q.stats
        assert stats["p0_enqueued"] == 0
        assert stats["p1_enqueued"] == 0
        assert stats["p2_enqueued"] == 0
        assert stats["rejected"] == 0

    @pytest.mark.asyncio
    async def test_rate_limiter_stats_precision(self):
        """令牌桶限流器统计精度"""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=10.0)

        await limiter.acquire(3)
        await limiter.acquire(2)
        await limiter.acquire(100)  # 拒绝

        stats = limiter.get_stats()
        assert stats["tokens_acquired"] == 5
        assert stats["tokens_rejected"] == 100
        assert stats["capacity"] == 10
        # available_tokens 应为 10 - 5 = 5
        assert stats["available_tokens"] == 5.0


# ============================================================
# 大量任务压力测试
# ============================================================

class TestStressPressure:
    """大量任务压力测试"""

    @pytest.mark.asyncio
    async def test_large_enqueue_dequeue_cycle(self):
        """大量入队出队循环"""
        q = PriorityTaskQueue()
        n = 200

        # 入队
        for i in range(n):
            pri = [Priority.P0_REALTIME, Priority.P1_NORMAL, Priority.P2_BACKGROUND][i % 3]
            await q.enqueue(f"task_{i}", priority=pri)

        assert q._queue.qsize() == n

        # 出队
        dequeued = []
        for _ in range(n):
            task = await q.dequeue(timeout=1.0)
            if task:
                dequeued.append(task)

        assert len(dequeued) == n
        # P0 应该排在前面
        p0_indices = [i for i, t in enumerate(dequeued) if t.priority == Priority.P0_REALTIME]
        p2_indices = [i for i, t in enumerate(dequeued) if t.priority == Priority.P2_BACKGROUND]
        if p0_indices and p2_indices:
            assert max(p0_indices) < min(p2_indices)

    @pytest.mark.asyncio
    async def test_rate_limiter_stress_acquire(self):
        """令牌桶大量 acquire 压力测试"""
        limiter = TokenBucketRateLimiter(capacity=500, refill_rate=0)
        results = []

        for _ in range(600):
            results.append(await limiter.acquire(1))

        assert sum(results) == 500
        assert limiter.get_stats()["tokens_acquired"] == 500
        assert limiter.get_stats()["tokens_rejected"] == 100

    @pytest.mark.asyncio
    async def test_backpressure_controller_water_level_accuracy(self):
        """背压控制器水位在高频更新下保持准确"""
        bp = BackpressureController()
        for depth in range(0, 101, 10):
            bp.update_depth(depth, 100)
            assert abs(bp.water_level - depth / 100) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
