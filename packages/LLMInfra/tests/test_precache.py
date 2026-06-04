"""
precache 模块单元测试

覆盖: PreCacheTask, PreCacheStats, PreCacheWorker
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from packages.LLMInfra.precache import PreCacheTask, PreCacheStats, PreCacheWorker
from packages.LLMInfra.cache import HotLevel
from packages.LLMInfra.core import ChatRequest, Message, MessageRole


def _make_request(text: str = "hello") -> ChatRequest:
    """构造测试用 ChatRequest"""
    return ChatRequest(
        model="gpt-3.5-turbo",
        messages=[Message(role=MessageRole.USER, content=text)],
    )


def _make_mock_cache_manager():
    """构造 mock CacheManager"""
    cm = AsyncMock()
    cm.tracker = MagicMock()
    cm.tracker.get_level.return_value = HotLevel.COLD
    cm.tracker.record_precache = MagicMock()
    return cm


def _make_mock_llm_caller(response_content: str = "mock response"):
    """构造 mock LLM 调用器，返回固定 LLMResponse"""
    from packages.LLMInfra.core import LLMResponse

    async def _caller(request: ChatRequest) -> LLMResponse:
        return LLMResponse(
            provider="mock",
            model=request.model,
            content=response_content,
            messages=request.messages,
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            cost=0.0,
        )

    return _caller


# ── PreCacheTask ──────────────────────────────────────────────


class TestPreCacheTask:
    """PreCacheTask 构造与属性"""

    def test_construct_with_defaults(self):
        """使用默认值构造 PreCacheTask"""
        req = _make_request()
        task = PreCacheTask(cache_key="key-1", request=req)
        assert task.cache_key == "key-1"
        assert task.request is req
        assert task.priority == 0
        assert task.created_at == 0.0

    def test_construct_with_priority(self):
        """指定优先级构造"""
        req = _make_request()
        task = PreCacheTask(cache_key="key-2", request=req, priority=10)
        assert task.priority == 10


# ── PreCacheStats ─────────────────────────────────────────────


class TestPreCacheStats:
    """PreCacheStats 统计属性"""

    def test_success_rate_zero_when_no_tasks(self):
        """无任务时 success_rate 为 0"""
        stats = PreCacheStats()
        assert stats.success_rate == 0.0

    def test_success_rate_calculation(self):
        """success_rate = completed / (completed + failed)"""
        stats = PreCacheStats(completed_tasks=7, failed_tasks=3)
        assert abs(stats.success_rate - 0.7) < 1e-9

    def test_success_rate_all_success(self):
        """全部成功时 success_rate 为 1.0"""
        stats = PreCacheStats(completed_tasks=5, failed_tasks=0)
        assert stats.success_rate == 1.0


# ── PreCacheWorker ────────────────────────────────────────────


class TestPreCacheWorker:
    """PreCacheWorker 入队、统计、生命周期"""

    @pytest.mark.asyncio
    async def test_enqueue_increments_total_tasks(self):
        """入队增加 total_tasks 计数"""
        cm = _make_mock_cache_manager()
        worker = PreCacheWorker(cache_manager=cm, llm_caller=_make_mock_llm_caller())
        req = _make_request()

        await worker.enqueue("key-1", req)
        assert worker.stats.total_tasks == 1
        assert worker.stats.current_queue_size == 1

    @pytest.mark.asyncio
    async def test_enqueue_multiple(self):
        """多次入队累加计数"""
        cm = _make_mock_cache_manager()
        worker = PreCacheWorker(cache_manager=cm, llm_caller=_make_mock_llm_caller())

        for i in range(3):
            await worker.enqueue(f"key-{i}", _make_request(f"msg-{i}"))

        assert worker.stats.total_tasks == 3
        assert worker.stats.current_queue_size == 3

    @pytest.mark.asyncio
    async def test_enqueue_overflow_skips(self):
        """队列满时增加 skipped_tasks 计数"""
        cm = _make_mock_cache_manager()
        worker = PreCacheWorker(
            cache_manager=cm, llm_caller=_make_mock_llm_caller(), queue_size=2
        )

        for i in range(4):
            await worker.enqueue(f"key-{i}", _make_request(f"msg-{i}"))

        assert worker.stats.total_tasks == 2  # 只有 2 个成功入队
        assert worker.stats.skipped_tasks == 2  # 2 个被丢弃

    @pytest.mark.asyncio
    async def test_get_stats_returns_dict(self):
        """get_stats 返回完整统计字典"""
        cm = _make_mock_cache_manager()
        worker = PreCacheWorker(cache_manager=cm, llm_caller=_make_mock_llm_caller())
        await worker.enqueue("k1", _make_request())

        stats = worker.get_stats()
        assert stats["total_tasks"] == 1
        assert stats["completed_tasks"] == 0
        assert stats["failed_tasks"] == 0
        assert stats["skipped_tasks"] == 0
        assert stats["current_queue_size"] == 1
        assert stats["queue_max_size"] == 20

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self):
        """Worker 可正常启动和停止"""
        cm = _make_mock_cache_manager()
        worker = PreCacheWorker(cache_manager=cm, llm_caller=_make_mock_llm_caller())

        await worker.start()
        assert worker._running is True
        assert worker._worker_task is not None

        await worker.stop()
        assert worker._running is False
        assert worker._worker_task is None

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        """重复 start 不会创建多个 worker task"""
        cm = _make_mock_cache_manager()
        worker = PreCacheWorker(cache_manager=cm, llm_caller=_make_mock_llm_caller())

        await worker.start()
        task1 = worker._worker_task
        await worker.start()  # 重复启动
        assert worker._worker_task is task1

        await worker.stop()

    @pytest.mark.asyncio
    async def test_execute_task_success(self):
        """执行任务成功后 completed_tasks 递增，缓存被写入"""
        cm = _make_mock_cache_manager()
        caller = _make_mock_llm_caller("cached answer")
        worker = PreCacheWorker(cache_manager=cm, llm_caller=caller, queue_size=10)

        req = _make_request("what is AI?")
        task = PreCacheTask(cache_key="test-key", request=req)

        await worker._execute_task(task)

        assert worker.stats.completed_tasks == 1
        assert worker.stats.failed_tasks == 0
        cm.set.assert_called_once()
        cm.tracker.record_precache.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_task_failure(self):
        """执行任务失败后 failed_tasks 递增"""
        cm = _make_mock_cache_manager()

        async def failing_caller(request):
            raise RuntimeError("LLM 服务不可用")

        worker = PreCacheWorker(cache_manager=cm, llm_caller=failing_caller, queue_size=10)
        task = PreCacheTask(cache_key="fail-key", request=_make_request())

        await worker._execute_task(task)

        assert worker.stats.failed_tasks == 1
        assert worker.stats.completed_tasks == 0

    @pytest.mark.asyncio
    async def test_should_precache_delegates_to_tracker(self):
        """should_precache 委托给 tracker.get_level 判断"""
        cm = _make_mock_cache_manager()
        cm.tracker.get_level.return_value = HotLevel.HOT
        worker = PreCacheWorker(
            cache_manager=cm, llm_caller=_make_mock_llm_caller(),
            hot_level_trigger=HotLevel.HOT
        )
        assert worker.should_precache("hot-key") is True

        cm.tracker.get_level.return_value = HotLevel.COLD
        assert worker.should_precache("cold-key") is False
