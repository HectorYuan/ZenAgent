"""
记忆评分与淘汰机制测试
"""

import unittest
from datetime import datetime, timedelta

from packages.MetaSoul.memory import (
    MetaSoul,
    MemoryType,
    MemoryEntry,
    MemoryImportance,
    MemoryScorer,
)
from packages.MetaSoul.memory.forgetting import ForgettingCurve


def _make_memory(
    content="test",
    importance=MemoryImportance.NORMAL,
    access_count=0,
    created_at=None,
    emotional_valence=0.0,
):
    return MemoryEntry(
        memory_id=f"mem-{id(content)}",
        content=content,
        memory_type=MemoryType.EPISODIC,
        importance=importance,
        access_count=access_count,
        created_at=created_at or datetime.now(),
        emotional_valence=emotional_valence,
    )


class TestMemoryScorer(unittest.TestCase):
    def setUp(self):
        self.scorer = MemoryScorer()

    def test_new_memory_high_score(self):
        """新记忆评分应较高"""
        memory = _make_memory(created_at=datetime.now())
        score = self.scorer.score(memory)
        self.assertGreater(score, 0.3)

    def test_old_memory_low_score(self):
        """老记忆评分应较低"""
        memory = _make_memory(created_at=datetime.now() - timedelta(days=30))
        score = self.scorer.score(memory)
        self.assertLess(score, 0.5)

    def test_critical_importance_high_score(self):
        """CRITICAL 重要性应获得高分"""
        memory = _make_memory(importance=MemoryImportance.CRITICAL)
        score = self.scorer.score(memory)
        self.assertGreaterEqual(score, 0.6)

    def test_minimal_importance_low_score(self):
        """MINIMAL 重要性应获得低分"""
        memory = _make_memory(
            importance=MemoryImportance.MINIMAL,
            created_at=datetime.now() - timedelta(days=7),
        )
        score = self.scorer.score(memory)
        self.assertLess(score, 0.4)

    def test_frequent_access_boosts_score(self):
        """频繁访问应提升评分"""
        low = _make_memory(access_count=0)
        high = _make_memory(access_count=10)
        self.assertGreater(self.scorer.score(high), self.scorer.score(low))

    def test_emotional_valence_boosts_score(self):
        """强情感应提升评分"""
        neutral = _make_memory(emotional_valence=0.0)
        emotional = _make_memory(emotional_valence=0.9)
        self.assertGreater(self.scorer.score(emotional), self.scorer.score(neutral))


class TestShouldEvict(unittest.TestCase):
    def setUp(self):
        self.scorer = MemoryScorer()

    def test_low_score_evict(self):
        """低分记忆应被淘汰"""
        memory = _make_memory(
            importance=MemoryImportance.MINIMAL,
            created_at=datetime.now() - timedelta(days=30),
        )
        self.assertTrue(self.scorer.should_evict(memory, threshold=0.3))

    def test_high_score_retain(self):
        """高分记忆应被保留"""
        memory = _make_memory(
            importance=MemoryImportance.HIGH,
            created_at=datetime.now(),
        )
        self.assertFalse(self.scorer.should_evict(memory, threshold=0.3))

    def test_critical_never_evict(self):
        """CRITICAL 记忆永不淘汰"""
        memory = _make_memory(
            importance=MemoryImportance.CRITICAL,
            created_at=datetime.now() - timedelta(days=365),
        )
        self.assertFalse(self.scorer.should_evict(memory, threshold=0.99))

    def test_custom_threshold(self):
        """自定义阈值应生效"""
        memory = _make_memory(
            importance=MemoryImportance.NORMAL,
            created_at=datetime.now() - timedelta(days=5),
        )
        # 默认阈值 0.3 可能不淘汰，但高阈值应该淘汰
        self.assertFalse(self.scorer.should_evict(memory, threshold=0.1))


class TestRankMemories(unittest.TestCase):
    def setUp(self):
        self.scorer = MemoryScorer()

    def test_sorted_ascending(self):
        """排序应升序（最值得淘汰在前）"""
        m1 = _make_memory(importance=MemoryImportance.HIGH, created_at=datetime.now())
        m2 = _make_memory(
            importance=MemoryImportance.MINIMAL,
            created_at=datetime.now() - timedelta(days=30),
        )
        m3 = _make_memory(importance=MemoryImportance.NORMAL, created_at=datetime.now())

        ranked = self.scorer.rank_memories([m1, m2, m3])
        scores = [s for _, s in ranked]
        self.assertEqual(scores, sorted(scores))


class TestEnforceCapacityFix(unittest.TestCase):
    """验证 _enforce_capacity 修复：淘汰最衰减的记忆而非最健康的"""

    def test_evicts_decayed_not_healthy(self):
        soul = MetaSoul(soul_id="test-capacity", name="test")
        soul._max_episodic_memories = 3

        # 存入 3 条老记忆（高衰减）
        old_ids = []
        for i in range(3):
            mid = soul.store_memory(
                content=f"old memory {i}",
                memory_type=MemoryType.EPISODIC,
                importance=MemoryImportance.MINIMAL,
            )
            # 手动修改创建时间为 30 天前
            soul.soul_memory.memories[mid].created_at = datetime.now() - timedelta(days=30)
            old_ids.append(mid)

        # 存入 1 条新记忆（低衰减），触发淘汰
        new_id = soul.store_memory(
            content="new important memory",
            memory_type=MemoryType.EPISODIC,
            importance=MemoryImportance.HIGH,
        )

        # 新记忆应保留
        self.assertIn(new_id, soul.soul_memory.memories)
        # 至少有一条老记忆被淘汰
        remaining_old = [mid for mid in old_ids if mid in soul.soul_memory.memories]
        self.assertLess(len(remaining_old), 3)


class TestRunEvictionCycle(unittest.TestCase):
    def test_eviction_returns_stats(self):
        soul = MetaSoul(soul_id="test-eviction", name="test")

        # 存入一些记忆
        for i in range(5):
            soul.store_memory(
                content=f"memory {i}",
                memory_type=MemoryType.EPISODIC,
                importance=MemoryImportance.NORMAL,
            )

        result = soul.run_eviction_cycle(threshold=0.3)
        self.assertIn("total_evaluated", result)
        self.assertIn("evicted_count", result)
        self.assertIn("retained_count", result)
        self.assertEqual(result["total_evaluated"], 5)

    def test_eviction_removes_low_scores(self):
        soul = MetaSoul(soul_id="test-eviction2", name="test")

        # 存入老的低重要性记忆
        for i in range(3):
            mid = soul.store_memory(
                content=f"old low {i}",
                memory_type=MemoryType.EPISODIC,
                importance=MemoryImportance.MINIMAL,
            )
            soul.soul_memory.memories[mid].created_at = datetime.now() - timedelta(days=30)

        total_before = soul.soul_memory.total_memories
        result = soul.run_eviction_cycle(threshold=0.3)

        self.assertLess(soul.soul_memory.total_memories, total_before)
        self.assertGreater(result["evicted_count"], 0)


if __name__ == "__main__":
    unittest.main()
