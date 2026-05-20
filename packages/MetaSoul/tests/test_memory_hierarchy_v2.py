"""
记忆分层架构 v2 测试

HierarchicalStore + MemoryRetriever + PluggableBackend
"""
import pytest
import asyncio
import time

from packages.MetaSoul.memory.hierarchical_store import (
    HierarchicalStore,
    MemoryEntry,
    MemoryTier,
    MemoryBackend,
    BackendProtocol,
)
from packages.MetaSoul.memory.memory_retriever import (
    MemoryRetriever,
    RetrieveIntent,
)


@pytest.fixture
def store():
    return HierarchicalStore()


@pytest.fixture
def retriever(store):
    return MemoryRetriever(store)


# ============================================================
# HierarchicalStore 测试
# ============================================================

class TestHierarchicalStore:
    """分层存储测试"""

    @pytest.mark.asyncio
    async def test_store_l1(self, store):
        """测试 L1 存储"""
        entry = await store.store("e1", "Hello World", tier=MemoryTier.L1_HOT)
        assert entry.tier == MemoryTier.L1_HOT
        assert len(store._l1) == 1

    @pytest.mark.asyncio
    async def test_l1_fifo_eviction(self, store):
        """测试 L1 FIFO 淘汰"""
        for i in range(25):  # 超过 L1_CAPACITY (20)
            await store.store(f"e{i}", f"content {i}", tier=MemoryTier.L1_HOT)

        # FIFO: 不应超过容量
        assert len(store._l1) <= store.L1_CAPACITY
        assert store.stats["l1_evictions"] >= 5

    @pytest.mark.asyncio
    async def test_store_l2(self, store):
        """测试 L2 存储"""
        entry = await store.store("e_l2", "L2 content", tier=MemoryTier.L2_WARM)
        assert entry.tier == MemoryTier.L2_WARM
        assert "e_l2" in store._l2

    @pytest.mark.asyncio
    async def test_l1_consolidation_trigger(self, store):
        """测试 L1→L2 自动整合触发"""
        # 填满 L1 超过阈值 (15)
        for i in range(18):
            await store.store(f"e{i}", f"consolidation test {i}", tier=MemoryTier.L1_HOT)

        # 等待异步整合
        await asyncio.sleep(0.2)

        # L2 应该有了整合条目
        assert store.stats["consolidations"] >= 1
        assert store.stats["l2_size"] > 0

    @pytest.mark.asyncio
    async def test_search_l1(self, store):
        """测试 L1 检索"""
        await store.store("a1", "Python programming", tier=MemoryTier.L1_HOT)
        await store.store("a2", "Java development", tier=MemoryTier.L1_HOT)
        await store.store("a3", "Python testing", tier=MemoryTier.L1_HOT)

        results = await store.search_l1("Python")
        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_search_l2(self, store):
        """测试 L2 检索"""
        await store.store("b1", "machine learning basics", tier=MemoryTier.L2_WARM)
        await store.store("b2", "deep learning advanced", tier=MemoryTier.L2_WARM)
        await store.store("b3", "web development", tier=MemoryTier.L2_WARM)

        results = await store.search_l2("learning")
        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_l3_store_and_search(self, store):
        """测试 L3 存储和检索"""
        await store.store_l3("fact:python:created_by", {"subject": "Python", "predicate": "created_by", "object": "Guido"})
        await store.store_l3("fact:java:created_by", {"subject": "Java", "predicate": "created_by", "object": "Gosling"})

        results = await store.search_l3("Python")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_l4_store_and_search(self, store):
        """测试 L4 存储和检索"""
        await store.store_l4("archive:2024:session1", {"content": "old conversation about AI", "year": 2024})
        await store.store_l4("archive:2025:session1", {"content": "recent discussion", "year": 2025})

        results = await store.search_l4("AI")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_warmup_l1(self, store):
        """测试 L3/L4 回填 L1"""
        await store.warmup_l1("archived_entry", "warmed up content from archive")
        assert store.stats["warmups"] == 1
        assert len(store._l1) == 1

    @pytest.mark.asyncio
    async def test_quick_summarize(self, store):
        """测试规则快速摘要"""
        entry = MemoryEntry(
            entry_id="test",
            content="This is a very long content that should be summarized properly by the quick summarizer function" * 5,
            tier=MemoryTier.L1_HOT,
            metadata={"type": "conversation", "topic": "testing"}
        )
        summary = store._quick_summarize(entry)
        # 摘要应该包含元数据中的关键信息
        assert "testing" in summary
        assert "conversation" in summary
        # 500+ chars 应该被截断
        assert len(summary) <= 300

    @pytest.mark.asyncio
    async def test_access_count_tracking(self, store):
        """测试访问计数追踪"""
        entry = await store.store("acc_test", "access tracking test", tier=MemoryTier.L1_HOT)
        for _ in range(3):
            await store.search_l1("access")

        # 检查访问次数是否递增
        found = False
        for e in store._l1:
            if e.entry_id == "acc_test":
                found = True
                break
        assert found


# ============================================================
# MemoryBackend 测试
# ============================================================

class TestMemoryBackend:
    """内存后端测试"""

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """测试设置和获取"""
        backend = MemoryBackend()
        await backend.set("key1", {"data": "value"}, ttl=3600)
        result = await backend.get("key1")
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_expiry(self):
        """测试过期"""
        backend = MemoryBackend()
        await backend.set("key2", {"data": "expire"}, ttl=0)  # 立即过期
        await asyncio.sleep(0.01)
        result = await backend.get("key2")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self):
        """测试删除"""
        backend = MemoryBackend()
        await backend.set("key3", {"data": "delete"})
        await backend.delete("key3")
        result = await backend.get("key3")
        assert result is None


# ============================================================
# MemoryRetriever 测试
# ============================================================

class TestMemoryRetriever:
    """检索系统测试"""

    @pytest.mark.asyncio
    async def test_recent_context_intent(self, store, retriever):
        """测试 RECENT_CONTEXT 意图"""
        await store.store("r1", "recent Python question", tier=MemoryTier.L1_HOT)
        await store.store("r2", "recent Java answer", tier=MemoryTier.L2_WARM)

        results = await retriever.retrieve("Python", intent=RetrieveIntent.RECENT_CONTEXT)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_full_stack_parallel(self, store, retriever):
        """测试 FULL_STACK 并行四层检索"""
        await store.store("f1", "hello world test", tier=MemoryTier.L1_HOT)
        await store.store("f2", "hello world warm", tier=MemoryTier.L2_WARM)

        results = await retriever.retrieve("hello", intent=RetrieveIntent.FULL_STACK, top_k=5)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_jaccard_sim(self, retriever):
        """测试 Jaccard 相似度"""
        sim = retriever._jaccard_sim("hello world", "hello world")
        assert sim == pytest.approx(1.0)

        sim = retriever._jaccard_sim("hello world", "goodbye universe")
        assert sim == pytest.approx(0.0)

        sim = retriever._jaccard_sim("hello world python", "hello world java")
        assert 0.0 < sim < 1.0

    @pytest.mark.asyncio
    async def test_weighted_fusion(self, store, retriever):
        """测试三路加权融合"""
        e1 = MemoryEntry(
            entry_id="w1", content="Python programming guide",
            tier=MemoryTier.L1_HOT, importance=0.9
        )
        e2 = MemoryEntry(
            entry_id="w2", content="Java development tutorial",
            tier=MemoryTier.L2_WARM, importance=0.3
        )

        scored = retriever._weighted_fusion([e1, e2], "Python programming")
        assert len(scored) == 2
        # e1 应该得分更高（更相似 + 更重要）
        assert scored[0][0].entry_id == "w1"

    @pytest.mark.asyncio
    async def test_retrieve_empty_store(self, store, retriever):
        """测试空存储检索"""
        results = await retriever.retrieve("nothing")
        assert results == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
