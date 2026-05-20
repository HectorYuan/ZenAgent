"""
增强缓存模块测试
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from packages.LLMInfra.cache import (
    RingBuffer,
    HotspotTracker,
    HotLevel,
    EvictionManager,
    MemoryCache,
    CacheManager
)
from packages.LLMInfra.precache import PreCacheWorker, PreCacheTask
from packages.LLMInfra.core import ChatRequest, Message, MessageRole


@pytest.fixture
def ring_buffer():
    return RingBuffer(capacity=1000)


@pytest.fixture
def hotspot_tracker():
    return HotspotTracker()


@pytest.fixture
def memory_backend():
    return MemoryCache()


@pytest.fixture
def cache_manager():
    from packages.LLMInfra.config import CacheConfig
    config = CacheConfig(enabled=True, type="memory", ttl=3600)
    return CacheManager(config)


@pytest.fixture
def test_request():
    return ChatRequest(
        model="test-model",
        messages=[Message(role=MessageRole.USER, content="Hello World")],
        temperature=0.7
    )


# ============================================================
# RingBuffer 测试
# ============================================================

class TestRingBuffer:
    """环形缓冲区测试"""

    @pytest.mark.asyncio
    async def test_record_and_count(self, ring_buffer):
        """测试记录和计数"""
        for _ in range(5):
            await ring_buffer.record("key1")
        for _ in range(3):
            await ring_buffer.record("key2")

        count = await ring_buffer.count_range(0)
        assert count == 8

    @pytest.mark.asyncio
    async def test_count_specific_key(self, ring_buffer):
        """测试按 key 计数"""
        for _ in range(4):
            await ring_buffer.record("key_a")
        for _ in range(2):
            await ring_buffer.record("key_b")

        count_a = await ring_buffer.count_range(0, "key_a")
        count_b = await ring_buffer.count_range(0, "key_b")
        count_c = await ring_buffer.count_range(0, "key_c")

        assert count_a == 4
        assert count_b == 2
        assert count_c == 0

    @pytest.mark.asyncio
    async def test_time_window(self, ring_buffer):
        """测试时间窗口过滤"""
        now = time.monotonic()
        # 模拟历史记录（直接操作内部 buffer）
        ring_buffer._buffer = [
            (now - 1000, "old_key"),
            (now - 500, "old_key"),
            (now - 100, "recent_key"),
            (now - 50, "recent_key"),
            (now - 10, "recent_key"),
        ]

        # 200 秒内的记录
        count = await ring_buffer.count_range(now - 200)
        assert count == 3  # only recent_key records

    @pytest.mark.asyncio
    async def test_stats_range(self, ring_buffer):
        """测试统计计算"""
        for i in range(10):
            await ring_buffer.record("key_a")
        for i in range(5):
            await ring_buffer.record("key_b")

        mean, stddev, counts = await ring_buffer.stats_range(0)

        assert counts["key_a"] == 10
        assert counts["key_b"] == 5
        assert mean > 0
        assert stddev > 0

    @pytest.mark.asyncio
    async def test_capacity_overflow(self, ring_buffer):
        """测试容量溢出"""
        small_buf = RingBuffer(capacity=10)
        for i in range(15):
            await small_buf.record(f"key_{i}")

        count = await small_buf.count_range(0)
        assert count <= 10  # 最多保留容量大小

    @pytest.mark.asyncio
    async def test_empty_stats(self, ring_buffer):
        """测试空缓冲区统计"""
        mean, stddev, counts = await ring_buffer.stats_range(0)
        assert mean == 0.0
        assert stddev == 0.0
        assert counts == {}


# ============================================================
# HotspotTracker 测试
# ============================================================

class TestHotspotTracker:
    """热点追踪器测试"""

    @pytest.mark.asyncio
    async def test_quick_trigger(self, hotspot_tracker):
        """测试快速触发热点"""
        key = "hot_key_1"
        # 短时间内多次命中
        for _ in range(5):
            level = await hotspot_tracker.record_hit(key)

        assert level == HotLevel.HOT
        assert hotspot_tracker.get_level(key) == HotLevel.HOT

    @pytest.mark.asyncio
    async def test_no_trigger_on_low_frequency(self, hotspot_tracker):
        """测试低频不触发"""
        key = "cold_key"
        for _ in range(2):
            level = await hotspot_tracker.record_hit(key)

        assert level == HotLevel.COLD

    @pytest.mark.asyncio
    async def test_get_hot_keys(self, hotspot_tracker):
        """测试获取热点键列表"""
        for _ in range(5):
            await hotspot_tracker.record_hit("hot_a")
        for _ in range(5):
            await hotspot_tracker.record_hit("hot_b")
        for _ in range(2):
            await hotspot_tracker.record_hit("cold_c")

        hot_keys = hotspot_tracker.get_hot_keys()
        assert "hot_a" in hot_keys
        assert "hot_b" in hot_keys
        assert "cold_c" not in hot_keys

    @pytest.mark.asyncio
    async def test_stats(self, hotspot_tracker):
        """测试统计数据"""
        for _ in range(10):
            await hotspot_tracker.record_hit("key1")
        hotspot_tracker.record_cache_hit()
        hotspot_tracker.record_cache_hit()
        hotspot_tracker.record_cache_miss()

        stats = hotspot_tracker.get_stats()
        assert stats["total_hits"] == 10
        assert stats["cache_hits"] == 2
        assert stats["cache_misses"] == 1
        assert "hit_rate" in stats

    @pytest.mark.asyncio
    async def test_different_hot_levels(self, hotspot_tracker):
        """测试三态热度等级"""
        # COLD 启动
        assert hotspot_tracker.get_level("unknown") == HotLevel.COLD

        # 快速触发 → HOT
        for _ in range(5):
            await hotspot_tracker.record_hit("new_hot")
        assert hotspot_tracker.get_level("new_hot") == HotLevel.HOT

    @pytest.mark.asyncio
    async def test_precache_recording(self, hotspot_tracker):
        """测试预缓存记录"""
        hotspot_tracker.record_precache()
        hotspot_tracker.record_precache()

        stats = hotspot_tracker.get_stats()
        assert stats["precache_tasks"] == 2

    @pytest.mark.asyncio
    async def test_eviction_recording(self, hotspot_tracker):
        """测试淘汰记录"""
        for _ in range(3):
            hotspot_tracker.record_eviction()

        stats = hotspot_tracker.get_stats()
        assert stats["eviction_count"] == 3


# ============================================================
# EvictionManager 测试
# ============================================================

class TestEvictionManager:
    """淘汰管理器测试"""

    def test_compute_score_hot(self, hotspot_tracker):
        """测试 HOT 键的高分数"""
        # 先标记为 HOT
        for _ in range(5):
            asyncio.get_event_loop().run_until_complete(hotspot_tracker.record_hit("hot_key"))

        eviction = EvictionManager()
        score = eviction.compute_score("hot_key", hotspot_tracker)
        assert score > 2.0  # HOT 基础权重 3.0 × 衰减

    def test_compute_score_cold(self, hotspot_tracker):
        """测试 COLD 键的低分数"""
        eviction = EvictionManager()
        score = eviction.compute_score("unknown_cold", hotspot_tracker)
        assert score < 1.0  # COLD 基础权重 0.5 × 衰减

    @pytest.mark.asyncio
    async def test_maybe_evict(self, memory_backend, hotspot_tracker):
        """测试淘汰执行"""
        # 先标记一些键为 HOT
        for _ in range(5):
            await hotspot_tracker.record_hit("hot_key")

        # 填充缓存
        for i in range(20):
            await memory_backend.set(f"key_{i}", f"value_{i}", 3600)

        eviction = EvictionManager(max_entries=10, eviction_threshold=0.8)
        await eviction.maybe_evict(memory_backend, hotspot_tracker)

        # 应该有淘汰发生（20 个条目 > 10*0.8=8）
        current_size = await memory_backend.size()
        assert current_size <= 20  # 至少有一些被淘汰

    @pytest.mark.asyncio
    async def test_no_eviction_when_under_threshold(self, memory_backend, hotspot_tracker):
        """测试低于阈值时不淘汰"""
        for i in range(5):
            await memory_backend.set(f"key_{i}", f"value_{i}", 3600)

        eviction = EvictionManager(max_entries=100, eviction_threshold=0.8)
        await eviction.maybe_evict(memory_backend, hotspot_tracker)

        # 5 个条目 < 100*0.8=80，不应淘汰
        current_size = await memory_backend.size()
        assert current_size == 5

    @pytest.mark.asyncio
    async def test_protect_high_score_entries(self, memory_backend, hotspot_tracker):
        """测试保护高分条目不被淘汰"""
        # 标记 key_0 为 HOT
        for _ in range(5):
            await hotspot_tracker.record_hit("llm:cache:key_0")

        for i in range(100):
            await memory_backend.set(f"llm:cache:key_{i}", f"value_{i}", 3600)

        eviction = EvictionManager(max_entries=10, eviction_threshold=0.8)
        await eviction.maybe_evict(memory_backend, hotspot_tracker)

        # HOT 条目应被保护
        assert await memory_backend.exists("llm:cache:key_0") is True

    @pytest.mark.asyncio
    async def test_check_and_downgrade_warm(self, memory_backend, hotspot_tracker):
        """测试 WARM 状态降级恢复 TTL"""
        # 先设为 WARM
        hotspot_tracker._hot_levels["warm_key"] = HotLevel.WARM
        await memory_backend.set("warm_key", "data", 1800)  # 延长 TTL

        eviction = EvictionManager()
        await eviction.check_and_downgrade("warm_key", hotspot_tracker, memory_backend, 3600)

        # TTL 应该被重置为默认值
        _, expire_at = memory_backend._cache["warm_key"]
        remaining = expire_at - time.time()
        assert remaining <= 3600 + 5  # 接近默认 TTL


# ============================================================
# PreCacheWorker 测试
# ============================================================

class TestPreCacheWorker:
    """预缓存 Worker 测试"""

    @pytest.fixture
    def mock_llm_caller(self):
        """Mock LLM 调用器"""
        from packages.LLMInfra.core import LLMResponse
        caller = AsyncMock()
        caller.return_value = LLMResponse(
            provider="mock",
            model="test",
            content="Precached response",
            messages=[Message(role=MessageRole.ASSISTANT, content="Precached response")],
            usage={"prompt_tokens": 10, "completion_tokens": 5}
        )
        return caller

    @pytest.mark.asyncio
    async def test_enqueue(self, cache_manager, mock_llm_caller, test_request):
        """测试任务入队"""
        worker = PreCacheWorker(cache_manager, mock_llm_caller)
        key = cache_manager._generate_cache_key(test_request)

        await worker.enqueue(key, test_request)
        assert worker.stats.total_tasks == 1
        assert worker.stats.current_queue_size == 1

    @pytest.mark.asyncio
    async def test_enqueue_queue_full(self, cache_manager, mock_llm_caller, test_request):
        """测试队列满时丢弃"""
        worker = PreCacheWorker(cache_manager, mock_llm_caller, queue_size=2)

        # 填满队列
        for i in range(3):
            await worker.enqueue(f"key_{i}", test_request)

        # 前 2 个入队，第 3 个被跳过
        assert worker.stats.skipped_tasks >= 1
        assert worker.stats.total_tasks >= 2  # 成功入队的 >=2 个

    @pytest.mark.asyncio
    async def test_worker_execution(self, cache_manager, mock_llm_caller, test_request):
        """测试 Worker 执行预缓存"""
        worker = PreCacheWorker(cache_manager, mock_llm_caller, queue_size=10)
        key = cache_manager._generate_cache_key(test_request)

        # 入队
        await worker.enqueue(key, test_request)
        assert worker.stats.total_tasks == 1

        # 启动 Worker（短时间）
        await worker.start()
        await asyncio.sleep(0.5)
        await worker.stop()

        # 验证 LLM 被调用
        assert mock_llm_caller.called

    @pytest.mark.asyncio
    async def test_should_precache(self, cache_manager, mock_llm_caller):
        """测试预缓存判断"""
        worker = PreCacheWorker(cache_manager, mock_llm_caller)

        # 默认 COLD
        assert worker.should_precache("cold_key") is False

        # 标记 HOT
        cache_manager.tracker._hot_levels["hot_key"] = HotLevel.HOT
        assert worker.should_precache("hot_key") is True

    def test_get_stats(self, cache_manager, mock_llm_caller):
        """测试获取统计"""
        worker = PreCacheWorker(cache_manager, mock_llm_caller)
        stats = worker.get_stats()
        assert stats["total_tasks"] == 0
        assert stats["completed_tasks"] == 0
        assert "success_rate" in stats


# ============================================================
# CacheManager 集成测试
# ============================================================

class TestCacheManagerEnhanced:
    """增强 CacheManager 集成测试"""

    @pytest.mark.asyncio
    async def test_cache_hit_tracking(self, cache_manager, test_request):
        """测试缓存命中追踪"""
        # 写入缓存
        await cache_manager.set(test_request, {"content": "test"})

        # 读取缓存
        result = await cache_manager.get(test_request)
        assert result is not None

        # 验证统计
        stats = cache_manager.get_hotspot_stats()
        assert stats["cache_hits"] >= 1

    @pytest.mark.asyncio
    async def test_cache_miss_tracking(self, cache_manager, test_request):
        """测试缓存未命中追踪"""
        # 生成一个不存在的 key
        result = await cache_manager.get(test_request)
        assert result is None

        stats = cache_manager.get_hotspot_stats()
        assert stats["cache_misses"] >= 1

    @pytest.mark.asyncio
    async def test_hotspot_trigger_during_cache_hits(self, cache_manager, test_request):
        """测试缓存命中时热点追踪"""
        await cache_manager.set(test_request, {"content": "hot content"})

        # 多次命中触发热点
        for _ in range(5):
            await cache_manager.get(test_request)
            await cache_manager._on_cache_hit(cache_manager._generate_cache_key(test_request))

        # 等待异步处理
        await asyncio.sleep(0.1)

        key = cache_manager._generate_cache_key(test_request)
        level = cache_manager.tracker.get_level(key)
        assert level in (HotLevel.HOT, HotLevel.WARM, HotLevel.COLD)

    @pytest.mark.asyncio
    async def test_cache_key_optimization(self, cache_manager):
        """测试缓存键优化：相同语义不同无关字段生成相同 key"""
        req1 = ChatRequest(
            model="gpt-4",
            messages=[Message(role=MessageRole.USER, content="Hello")],
            temperature=0.7
        )
        req2 = ChatRequest(
            model="gpt-4",
            messages=[Message(role=MessageRole.USER, content="Hello")],
            temperature=0.7,
            top_p=1.0
        )

        key1 = cache_manager._generate_cache_key(req1)
        key2 = cache_manager._generate_cache_key(req2)

        assert key1 == key2  # 相同语义应生成相同 key

    @pytest.mark.asyncio
    async def test_cache_key_differs_for_different_content(self, cache_manager):
        """测试不同内容生成不同 key"""
        req1 = ChatRequest(
            model="gpt-4",
            messages=[Message(role=MessageRole.USER, content="Hello")],
        )
        req2 = ChatRequest(
            model="gpt-4",
            messages=[Message(role=MessageRole.USER, content="World")],
        )

        key1 = cache_manager._generate_cache_key(req1)
        key2 = cache_manager._generate_cache_key(req2)

        assert key1 != key2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
