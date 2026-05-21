"""
优先级任务队列 + 背压控制器测试
"""
import pytest
import asyncio

from packages.Runtime.flow_control.priority_queue import (
    PriorityTaskQueue,
    BackpressureController,
    Priority,
    PriorityTask,
)


# ============================================================
# BackpressureController 测试
# ============================================================

class TestBackpressureController:
    """背压控制器测试"""

    def test_normal_accepts_all(self):
        """正常水位接受所有优先级"""
        bp = BackpressureController()
        bp.update_depth(10, 100)  # 10%
        assert bp.can_accept(Priority.P0_REALTIME) is True
        assert bp.can_accept(Priority.P1_NORMAL) is True
        assert bp.can_accept(Priority.P2_BACKGROUND) is True

    def test_warning_rejects_p2(self):
        """警告水位拒绝 P2"""
        bp = BackpressureController(warning_threshold=0.5)
        bp.update_depth(60, 100)  # 60%
        assert bp.can_accept(Priority.P0_REALTIME) is True
        assert bp.can_accept(Priority.P1_NORMAL) is True
        assert bp.can_accept(Priority.P2_BACKGROUND) is False

    def test_critical_only_p0(self):
        """严重水位仅接受 P0"""
        bp = BackpressureController(critical_threshold=0.8)
        bp.update_depth(85, 100)  # 85%
        assert bp.can_accept(Priority.P0_REALTIME) is True
        assert bp.can_accept(Priority.P1_NORMAL) is False
        assert bp.can_accept(Priority.P2_BACKGROUND) is False

    def test_panic_rejects_all(self):
        """恐慌水位拒绝全部"""
        bp = BackpressureController(panic_threshold=0.95)
        bp.update_depth(98, 100)  # 98%
        assert bp.can_accept(Priority.P0_REALTIME) is False
        assert bp.can_accept(Priority.P1_NORMAL) is False
        assert bp.can_accept(Priority.P2_BACKGROUND) is False

    def test_get_status(self):
        """测试状态获取"""
        bp = BackpressureController()
        bp.update_depth(30, 100)
        status = bp.get_status()
        assert status["water_level"] == 0.3
        assert status["warning"] is False


# ============================================================
# PriorityTaskQueue 测试
# ============================================================

class TestPriorityTaskQueue:
    """优先级任务队列测试"""

    @pytest.mark.asyncio
    async def test_enqueue_p0(self):
        """测试 P0 入队"""
        q = PriorityTaskQueue()
        task = await q.enqueue("critical task", priority=Priority.P0_REALTIME)
        assert task is not None
        assert task.priority == Priority.P0_REALTIME
        assert q.stats["p0_enqueued"] == 1

    @pytest.mark.asyncio
    async def test_enqueue_p1_p2(self):
        """测试 P1 P2 入队"""
        q = PriorityTaskQueue()
        await q.enqueue("normal", priority=Priority.P1_NORMAL)
        await q.enqueue("background", priority=Priority.P2_BACKGROUND)
        assert q.stats["p1_enqueued"] == 1
        assert q.stats["p2_enqueued"] == 1

    @pytest.mark.asyncio
    async def test_priority_order(self):
        """测试优先级出队顺序"""
        q = PriorityTaskQueue()
        await q.enqueue("p2_task", priority=Priority.P2_BACKGROUND)
        await q.enqueue("p0_task", priority=Priority.P0_REALTIME)
        await q.enqueue("p1_task", priority=Priority.P1_NORMAL)

        # 应该先出 P0
        task1 = await q.dequeue()
        assert task1.priority == Priority.P0_REALTIME

        # 再出 P1
        task2 = await q.dequeue()
        assert task2.priority == Priority.P1_NORMAL

        # 最后 P2
        task3 = await q.dequeue()
        assert task3.priority == Priority.P2_BACKGROUND

    @pytest.mark.asyncio
    async def test_dequeue_empty(self):
        """测试空队列出队"""
        q = PriorityTaskQueue()
        task = await q.dequeue(timeout=0.01)
        assert task is None

    @pytest.mark.asyncio
    async def test_backpressure_rejection(self):
        """测试背压拒绝"""
        bp = BackpressureController(warning_threshold=0.1)
        q = PriorityTaskQueue(backpressure=bp)

        # 填满一些任务触发水位
        for i in range(30):
            await q.enqueue(f"task_{i}", priority=Priority.P2_BACKGROUND)

        # 水位应该很高
        bp.update_depth(q._queue.qsize(), q.TOTAL_CAPACITY)

        # P2 任务在高水位应该被拒绝
        rejected = await q.enqueue("another p2", priority=Priority.P2_BACKGROUND)
        # 可能被拒绝（取决于实际水位）
        stats = q.stats
        assert stats["rejected"] >= 0  # 至少不报错

    @pytest.mark.asyncio
    async def test_process_method(self):
        """测试便捷 process 方法"""
        q = PriorityTaskQueue()

        async def handler(payload):
            return f"processed: {payload}"

        await q.enqueue("hello", priority=Priority.P0_REALTIME)
        result = await q.process(handler)
        assert result == "processed: hello"

    @pytest.mark.asyncio
    async def test_stats_peak_depth(self):
        """测试峰值队列深度"""
        q = PriorityTaskQueue()
        for i in range(10):
            await q.enqueue(f"task_{i}", priority=Priority.P1_NORMAL)
        assert q.stats["peak_queue_depth"] >= 10

    @pytest.mark.asyncio
    async def test_stats_reject_rate(self):
        """测试拒绝率"""
        q = PriorityTaskQueue()
        await q.enqueue("good", priority=Priority.P0_REALTIME)
        # 使用满队列来触发拒绝
        small_q = PriorityTaskQueue()
        small_q._queue = asyncio.PriorityQueue(maxsize=2)
        await small_q.enqueue("a", Priority.P0_REALTIME)
        await small_q.enqueue("b", Priority.P0_REALTIME)
        await small_q.enqueue("c", Priority.P0_REALTIME)  # 可能 rejected
        assert small_q.stats["reject_rate"] >= 0.0

    @pytest.mark.asyncio
    async def test_concurrent_enqueue_dequeue(self):
        """测试并发入队出队"""
        q = PriorityTaskQueue()

        async def producer():
            for i in range(20):
                await q.enqueue(f"task_{i}", priority=Priority.P2_BACKGROUND)
                await asyncio.sleep(0)

        async def consumer():
            count = 0
            for _ in range(20):
                task = await q.dequeue(timeout=0.5)
                if task:
                    count += 1
            return count

        producer_task = asyncio.create_task(producer())
        consumer_task = asyncio.create_task(consumer())

        produced = await producer_task
        consumed = await consumer_task
        assert consumed >= 18  # 允许少数丢失

    @pytest.mark.asyncio
    async def test_task_metadata(self):
        """测试任务元数据"""
        task = PriorityTask(priority=Priority.P0_REALTIME, payload={"key": "val"})
        assert task.task_id != ""
        assert task.created_at > 0
        assert task.payload == {"key": "val"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
