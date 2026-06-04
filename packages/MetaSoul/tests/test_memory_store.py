"""
记忆存储模块综合测试

覆盖 MemoryStore、MemoryEntry、WorkingMemory、EpisodicMemory、SemanticMemory、
记忆评分及淘汰机制。
"""

import pytest
from datetime import datetime, timedelta

from packages.MetaSoul.memory import (
    MemoryStore,
    MemoryStoreConfig,
    InMemoryStorageBackend,
    MemoryEntry,
    MemoryType,
    MemoryImportance,
    WorkingMemory,
    EpisodicMemory,
    SemanticMemory,
    MemoryScorer,
    ForgettingMechanism,
    ForgettingPolicy,
)
from packages.MetaSoul.memory.memory_hierarchy import (
    EpisodicMemoryEntry,
    SemanticMemoryEntry,
)
from packages.MetaSoul.memory.forgetting import ForgettingCurve
from packages.MetaSoul.memory.semantic_kb import SemanticKnowledgeBase, KnowledgeTriple


# ============================================================
# 辅助工厂
# ============================================================

def _make_store(**kwargs):
    """创建 MemoryStore 实例"""
    return MemoryStore(config=MemoryStoreConfig(**kwargs))


def _make_memory(
    content="测试内容",
    importance=MemoryImportance.NORMAL,
    access_count=0,
    created_at=None,
    emotional_valence=0.0,
    memory_type=MemoryType.EPISODIC,
):
    """创建 MemoryEntry 实例"""
    return MemoryEntry(
        memory_id=f"mem-{abs(hash(content))}",
        content=content,
        memory_type=memory_type,
        importance=importance,
        access_count=access_count,
        created_at=created_at or datetime.now(),
        emotional_valence=emotional_valence,
    )


# ============================================================
# 1. MemoryStore: store / retrieve / delete / query / stats
# ============================================================

class TestMemoryStoreCRUD:
    """MemoryStore 基本 CRUD 操作"""

    def setup_method(self):
        self.store = _make_store()

    def test_store_returns_true(self):
        """存储记忆应返回 True"""
        result = self.store.store(memory_id="m1", content="你好世界")
        assert result is True

    def test_retrieve_after_store(self):
        """存储后检索应返回正确内容"""
        self.store.store(
            memory_id="m1",
            content="Python 编程",
            memory_type="semantic",
            importance=4,
            tags=["python", "编程"],
        )
        data = self.store.retrieve("m1")
        assert data is not None
        assert data["content"] == "Python 编程"
        assert data["memory_type"] == "semantic"
        assert data["importance"] == 4
        assert "python" in data["tags"]

    def test_retrieve_nonexistent_returns_none(self):
        """检索不存在的记忆应返回空字典"""
        data = self.store.retrieve("不存在的ID")
        # InMemoryStorageBackend.load 返回 {} 而不是 None
        assert not data

    def test_delete_existing(self):
        """删除已存在的记忆应返回 True"""
        self.store.store(memory_id="m2", content="待删除")
        assert self.store.delete("m2") is True
        assert not self.store.retrieve("m2")

    def test_delete_nonexistent(self):
        """删除不存在的记忆应返回 False"""
        assert self.store.delete("ghost") is False

    def test_query_by_type(self):
        """按类型查询应只返回匹配类型"""
        self.store.store(memory_id="a", content="语义", memory_type="semantic")
        self.store.store(memory_id="b", content="情景", memory_type="episodic")
        self.store.store(memory_id="c", content="更多语义", memory_type="semantic")

        results = self.store.query_by_type("semantic")
        assert len(results) == 2

    def test_query_by_tags(self):
        """按标签查询应返回包含任一标签的记忆"""
        self.store.store(memory_id="t1", content="A", tags=["python", "ai"])
        self.store.store(memory_id="t2", content="B", tags=["rust"])
        self.store.store(memory_id="t3", content="C", tags=["python"])

        results = self.store.query_by_tags(["python"])
        ids = [r["memory_id"] for r in results]
        assert "t1" in ids
        assert "t3" in ids
        assert "t2" not in ids

    def test_query_by_importance_range(self):
        """按重要性范围查询"""
        self.store.store(memory_id="lo", content="低", importance=1)
        self.store.store(memory_id="mid", content="中", importance=3)
        self.store.store(memory_id="hi", content="高", importance=5)

        results = self.store.query_by_importance(min_importance=3, max_importance=5)
        ids = [r["memory_id"] for r in results]
        assert "lo" not in ids
        assert "mid" in ids
        assert "hi" in ids

    def test_count_and_clear(self):
        """count 和 clear 应正确反映状态"""
        self.store.store(memory_id="x1", content="A")
        self.store.store(memory_id="x2", content="B")
        assert self.store.count() == 2

        self.store.clear()
        assert self.store.count() == 0

    def test_get_stats(self):
        """get_stats 应返回正确统计"""
        self.store.store(memory_id="s1", content="A", memory_type="semantic", importance=3)
        self.store.store(memory_id="s2", content="B", memory_type="episodic", importance=5)

        stats = self.store.get_stats()
        assert stats["total_memories"] == 2
        assert stats["by_type"]["semantic"] == 1
        assert stats["by_type"]["episodic"] == 1
        assert stats["total_accesses"] == 0

    def test_retrieve_increments_access_count(self):
        """每次检索应增加访问计数"""
        self.store.store(memory_id="ac", content="访问测试")
        self.store.retrieve("ac")
        self.store.retrieve("ac")
        data = self.store.retrieve("ac")
        assert data["access_count"] == 3  # retrieve 内部先 +1 再保存

    def test_get_recent_sorted_descending(self):
        """get_recent 应按创建时间降序返回"""
        import time
        self.store.store(memory_id="r1", content="最早")
        time.sleep(0.01)
        self.store.store(memory_id="r2", content="其次")
        time.sleep(0.01)
        self.store.store(memory_id="r3", content="最新")

        recent = self.store.get_recent(limit=2)
        assert len(recent) == 2
        assert recent[0]["content"] == "最新"
        assert recent[1]["content"] == "其次"


# ============================================================
# 2. InMemoryStorageBackend 单独测试
# ============================================================

class TestInMemoryStorageBackend:
    """InMemoryStorageBackend 后端行为"""

    def setup_method(self):
        self.backend = InMemoryStorageBackend()

    def test_save_and_load(self):
        """保存后加载应返回相同数据"""
        self.backend.save("k1", {"value": 42})
        data = self.backend.load("k1")
        assert data["value"] == 42

    def test_load_nonexistent_returns_empty(self):
        """加载不存在的 key 应返回空字典"""
        data = self.backend.load("no_such_key")
        assert data == {}

    def test_exists(self):
        """exists 应正确反映存在性"""
        assert self.backend.exists("k1") is False
        self.backend.save("k1", {"x": 1})
        assert self.backend.exists("k1") is True

    def test_delete_existing(self):
        """删除已存在的 key 应返回 True"""
        self.backend.save("k1", {"x": 1})
        assert self.backend.delete("k1") is True
        assert self.backend.exists("k1") is False

    def test_delete_nonexistent(self):
        """删除不存在的 key 应返回 False"""
        assert self.backend.delete("ghost") is False

    def test_query_with_filters(self):
        """query 应按过滤条件匹配"""
        self.backend.save("a", {"type": "semantic", "val": 1})
        self.backend.save("b", {"type": "episodic", "val": 2})
        self.backend.save("c", {"type": "semantic", "val": 3})

        results = self.backend.query({"type": "semantic"})
        assert len(results) == 2

    def test_query_with_list_filter(self):
        """query 的 list 过滤应匹配列表中任一值"""
        self.backend.save("a", {"level": "high"})
        self.backend.save("b", {"level": "low"})

        results = self.backend.query({"level": ["high", "mid"]})
        assert len(results) == 1
        assert results[0]["level"] == "high"


# ============================================================
# 3. MemoryEntry (meta_soul) 构造与行为
# ============================================================

class TestMemoryEntry:
    """MemoryEntry 数据类测试"""

    def test_construct_with_defaults(self):
        """默认构造应有合理初始值"""
        entry = MemoryEntry(
            memory_id="e1",
            content="测试",
            memory_type=MemoryType.WORKING,
        )
        assert entry.importance == MemoryImportance.NORMAL
        assert entry.access_count == 0
        assert entry.emotional_valence == 0.0
        assert entry.associations == []

    def test_access_increments_count(self):
        """访问应增加计数并更新时间"""
        entry = _make_memory()
        old_count = entry.access_count
        entry.access()
        assert entry.access_count == old_count + 1

    def test_add_association_no_duplicate(self):
        """添加关联不应产生重复"""
        entry = _make_memory()
        entry.add_association("other1")
        entry.add_association("other1")
        assert entry.associations.count("other1") == 1

    def test_decay_score_new_memory_low(self):
        """新记忆衰减分数应较低"""
        entry = _make_memory(created_at=datetime.now())
        score = entry.get_decay_score()
        assert score < 0.3

    def test_decay_score_old_memory_high(self):
        """老记忆衰减分数应较高"""
        entry = _make_memory(created_at=datetime.now() - timedelta(days=7))
        score = entry.get_decay_score()
        assert score > 0.3

    def test_importance_enum_values(self):
        """MemoryImportance 枚举值应正确"""
        assert MemoryImportance.CRITICAL.value == 5
        assert MemoryImportance.MINIMAL.value == 1


# ============================================================
# 4. WorkingMemory: store / retrieve / eviction / TTL
# ============================================================

class TestWorkingMemory:
    """WorkingMemory 工作记忆测试"""

    def setup_method(self):
        self.wm = WorkingMemory(capacity=5)

    def test_store_and_retrieve(self):
        """存取应一致"""
        self.wm.store("k1", "value1")
        assert self.wm.retrieve("k1") == "value1"

    def test_retrieve_nonexistent(self):
        """检索不存在的条目应返回 None"""
        assert self.wm.retrieve("不存在") is None

    def test_capacity_eviction(self):
        """超过容量应淘汰最低注意力权重的条目"""
        for i in range(6):
            self.wm.store(f"item-{i}", f"内容-{i}")
            self.wm.update_attention(f"item-{i}", 1.0)

        # 把第 0 条权重调到最低
        self.wm.update_attention("item-0", 0.01)

        # 再存一条触发淘汰
        self.wm.store("overflow", "溢出内容", ttl=None)

        # item-0 应被淘汰
        assert self.wm.retrieve("item-0") is None
        assert self.wm.retrieve("overflow") == "溢出内容"

    def test_ttl_expiration(self):
        """TTL 过期后检索应返回 None"""
        # ttl=0 是 falsy，不会设置 expires_at；使用 ttl=1 并等待
        self.wm.store("ttl_key", "短暂内容", ttl=1)
        assert self.wm.retrieve("ttl_key") == "短暂内容"  # 未过期
        # 手动将 expires_at 设为过去
        for entry in self.wm.get_all():
            if entry.entry_id == "ttl_key":
                from datetime import datetime, timedelta
                entry.expires_at = datetime.now() - timedelta(seconds=1)
        assert self.wm.retrieve("ttl_key") is None

    def test_update_attention(self):
        """更新注意力权重应生效"""
        self.wm.store("att", "内容")
        self.wm.update_attention("att", 0.5)
        entries = self.wm.get_all()
        target = [e for e in entries if e.entry_id == "att"][0]
        assert target.attention_weight == 0.5

    def test_clear(self):
        """clear 应清空所有条目"""
        self.wm.store("c1", "A")
        self.wm.store("c2", "B")
        self.wm.clear()
        assert len(self.wm.get_all()) == 0


# ============================================================
# 5. EpisodicMemory: store_episode / retrieve / time_range / emotion
# ============================================================

class TestEpisodicMemory:
    """EpisodicMemory 情景记忆测试"""

    def setup_method(self):
        self.em = EpisodicMemory()

    def _add_episode(self, episode_id, title, start_time=None):
        ep = EpisodicMemoryEntry(
            episode_id=episode_id,
            title=title,
            narrative=f"{title} 的详细描述",
            start_time=start_time or datetime.now(),
            emotions=["开心"],
        )
        self.em.store_episode(ep)
        return ep

    def test_store_and_retrieve_episode(self):
        """存取情景记忆应一致"""
        self._add_episode("ep1", "第一次飞行")
        result = self.em.retrieve_episode("ep1")
        assert result is not None
        assert result.title == "第一次飞行"

    def test_retrieve_nonexistent_episode(self):
        """检索不存在的情景应返回 None"""
        assert self.em.retrieve_episode("不存在") is None

    def test_search_by_time_range(self):
        """按时间范围检索应只返回范围内的情景"""
        t1 = datetime(2025, 1, 1)
        t2 = datetime(2025, 6, 1)
        t3 = datetime(2025, 12, 1)

        self._add_episode("ep1", "一月", start_time=t1)
        self._add_episode("ep2", "六月", start_time=t2)
        self._add_episode("ep3", "十二月", start_time=t3)

        results = self.em.retrieve_by_time_range(
            start=datetime(2025, 3, 1),
            end=datetime(2025, 9, 1),
        )
        ids = [r.episode_id for r in results]
        assert "ep2" in ids
        assert "ep1" not in ids
        assert "ep3" not in ids

    def test_search_by_emotion(self):
        """按情感标签检索"""
        ep_happy = EpisodicMemoryEntry(
            episode_id="ep_h",
            title="开心的事",
            narrative="描述",
            start_time=datetime.now(),
            emotions=["开心", "兴奋"],
        )
        ep_sad = EpisodicMemoryEntry(
            episode_id="ep_s",
            title="难过的事",
            narrative="描述",
            start_time=datetime.now(),
            emotions=["悲伤"],
        )
        self.em.store_episode(ep_happy)
        self.em.store_episode(ep_sad)

        results = self.em.retrieve_by_emotion("开心")
        assert len(results) == 1
        assert results[0].episode_id == "ep_h"

    def test_get_recent_episodes(self):
        """get_recent_episodes 应按时间倒序返回"""
        self._add_episode("ep_old", "旧事件")
        self._add_episode("ep_new", "新事件")

        recent = self.em.get_recent_episodes(limit=2)
        assert len(recent) == 2
        # 最新的在前
        assert recent[0].title == "新事件"


# ============================================================
# 6. SemanticMemory: store_concept / retrieve / search / confidence
# ============================================================

class TestSemanticMemory:
    """SemanticMemory 语义记忆测试"""

    def setup_method(self):
        self.sm = SemanticMemory()

    def _add_concept(self, concept_id, concept, definition, confidence=1.0):
        entry = SemanticMemoryEntry(
            concept_id=concept_id,
            concept=concept,
            definition=definition,
            confidence=confidence,
        )
        self.sm.store_concept(entry)
        return entry

    def test_store_and_retrieve_concept(self):
        """存取概念应一致"""
        self._add_concept("c1", "Python", "一种编程语言")
        result = self.sm.retrieve_concept("c1")
        assert result is not None
        assert result.concept == "Python"
        assert result.definition == "一种编程语言"

    def test_retrieve_nonexistent_concept(self):
        """检索不存在的概念应返回 None"""
        assert self.sm.retrieve_concept("不存在") is None

    def test_search_concepts_by_keyword(self):
        """按关键词搜索应匹配概念名或定义"""
        self._add_concept("c1", "Python", "一种解释型编程语言")
        self._add_concept("c2", "Rust", "一种系统编程语言")
        self._add_concept("c3", "TensorFlow", "Python 深度学习框架")

        results = self.sm.search_concepts("Python")
        ids = [r.concept_id for r in results]
        assert "c1" in ids
        assert "c3" in ids
        assert "c2" not in ids

    def test_update_confidence(self):
        """更新置信度应在 [0, 1] 范围内"""
        self._add_concept("c1", "AI", "人工智能", confidence=0.5)
        self.sm.update_confidence("c1", 0.3)
        c = self.sm.retrieve_concept("c1")
        assert c.confidence == pytest.approx(0.8)

        # 上限 1.0
        self.sm.update_confidence("c1", 0.5)
        assert self.sm.retrieve_concept("c1").confidence == 1.0

    def test_update_confidence_floor(self):
        """置信度下限为 0"""
        self._add_concept("c1", "AI", "人工智能", confidence=0.1)
        self.sm.update_confidence("c1", -0.5)
        assert self.sm.retrieve_concept("c1").confidence == 0.0


# ============================================================
# 7. SemanticKnowledgeBase: SPO 三元组
# ============================================================

class TestSemanticKnowledgeBase:
    """SemanticKnowledgeBase SPO 三元组操作"""

    def setup_method(self):
        self.kb = SemanticKnowledgeBase()

    def test_upsert_new_triple(self):
        """新建三元组应成功"""
        t = self.kb.upsert("Python", "是一种", "编程语言")
        assert t.subject == "Python"
        assert t.predicate == "是一种"
        assert t.object == "编程语言"
        assert self.kb.total_triples == 1

    def test_upsert_confirms_existing(self):
        """重复 upsert 应确认已有三元组并增加 seen_count"""
        self.kb.upsert("Python", "是一种", "编程语言", source_id="src1")
        t2 = self.kb.upsert("Python", "是一种", "编程语言", source_id="src2")
        assert t2.seen_count == 2
        assert self.kb.total_triples == 1

    def test_multiple_objects_same_sp(self):
        """同 (s,p) 不同 object 应各自创建独立三元组"""
        self.kb.upsert("Python", "类型", "动态")
        self.kb.upsert("Python", "类型", "静态")

        # 两个三元组共存
        assert self.kb.total_triples == 2
        by_entity = self.kb.get_by_entity("Python")
        objects = {t.object for t in by_entity}
        assert "动态" in objects
        assert "静态" in objects

    def test_conflict_detection_via_add_conflict(self):
        """手动注入 pending_conflict 后，upsert 应触发冲突检测"""
        # 先创建一个三元组
        existing = self.kb.upsert("AI", "包含", "机器学习")
        # 手动将其加入 _pending_conflicts 以模拟冲突场景
        self.kb._pending_conflicts["AI::包含"] = [existing]

        # 再 upsert 同 (s,p) 不同 object → 应触发冲突
        result = self.kb.upsert("AI", "包含", "深度学习")
        # 冲突检测保留旧的
        assert result.object == "机器学习"
        assert len(self.kb.get_pending_conflicts()) > 0

    def test_get_by_entity(self):
        """按实体检索相关三元组"""
        self.kb.upsert("Python", "是一种", "编程语言")
        self.kb.upsert("Java", "是一种", "编程语言")
        self.kb.upsert("Python", "用于", "AI")

        results = self.kb.get_by_entity("Python")
        assert len(results) == 2

    def test_semantic_search(self):
        """语义检索应匹配关键词"""
        self.kb.upsert("机器学习", "是", "AI 子领域")
        self.kb.upsert("深度学习", "是", "机器学习子领域")

        results = self.kb.semantic_search("机器学习")
        assert len(results) >= 1

    def test_knowledge_triple_confirm(self):
        """confirm 应增加 seen_count 和 confidence"""
        t = KnowledgeTriple(subject="A", predicate="B", object="C", confidence=0.5)
        t.confirm("src1")
        assert t.seen_count == 2
        assert t.confidence > 0.5

    def test_knowledge_triple_is_stale(self):
        """低置信度三元组应被标记为 stale"""
        t = KnowledgeTriple(subject="X", predicate="Y", object="Z", confidence=0.1)
        assert t.is_stale(threshold=0.3) is True
        assert t.is_stale(threshold=0.05) is False


# ============================================================
# 8. MemoryScorer: 评分与淘汰判定
# ============================================================

class TestMemoryScorerComprehensive:
    """MemoryScorer 评分器综合测试"""

    def setup_method(self):
        self.scorer = MemoryScorer()

    def test_score_range_0_to_1(self):
        """评分应在 0-1 范围内"""
        memory = _make_memory(
            importance=MemoryImportance.NORMAL,
            created_at=datetime.now() - timedelta(days=3),
            access_count=5,
            emotional_valence=0.5,
        )
        score = self.scorer.score(memory)
        assert 0.0 <= score <= 1.0

    def test_critical_never_evicted(self):
        """CRITICAL 记忆永不被淘汰"""
        memory = _make_memory(
            importance=MemoryImportance.CRITICAL,
            created_at=datetime.now() - timedelta(days=365),
        )
        assert self.scorer.should_evict(memory, threshold=0.99) is False

    def test_high_access_boosts_score(self):
        """高访问频率应提升评分"""
        low = _make_memory(access_count=0, created_at=datetime.now())
        high = _make_memory(access_count=10, created_at=datetime.now())
        assert self.scorer.score(high) > self.scorer.score(low)


# ============================================================
# 9. ForgettingMechanism: 遗忘与保护
# ============================================================

class TestForgettingMechanism:
    """ForgettingMechanism 遗忘机制测试"""

    def setup_method(self):
        self.store = _make_store()
        self.fm = ForgettingMechanism(
            memory_store=self.store,
            policy=ForgettingPolicy.ADAPTIVE,
        )

    def test_protect_and_unprotect(self):
        """保护和取消保护应正确切换状态"""
        self.store.store(memory_id="p1", content="保护测试")
        self.fm.protect_memory("p1")
        assert self.fm.is_protected("p1") is True

        self.fm.unprotect_memory("p1")
        assert self.fm.is_protected("p1") is False

    def test_protected_memory_not_forgotten(self):
        """受保护的记忆不应被遗忘"""
        self.store.store(memory_id="p2", content="重要内容", importance=1)
        self.fm.protect_memory("p2")

        memory_data = self.store.retrieve("p2")
        # 即使衰减很高，受保护的记忆也不应被遗忘
        assert self.fm.should_forget(memory_data) is False

    def test_calculate_decay_in_range(self):
        """calculate_decay 应返回 0-1 范围内的值"""
        self.store.store(memory_id="d1", content="衰减测试", importance=3)
        memory_data = self.store.retrieve("d1")
        decay = self.fm.calculate_decay(memory_data)
        assert 0.0 <= decay <= 1.0

    def test_run_forgetting_cycle_returns_stats(self):
        """run_forgetting_cycle 应返回正确的统计结构"""
        self.store.store(memory_id="f1", content="A")
        self.store.store(memory_id="f2", content="B")

        result = self.fm.run_forgetting_cycle(batch_size=10)
        assert "forgotten" in result
        assert "preserved" in result
        assert isinstance(result["forgotten"], list)
        assert isinstance(result["preserved"], list)

    def test_consolidate_memories(self):
        """整合记忆应返回 consolidation_id"""
        self.store.store(memory_id="c1", content="片段1")
        self.store.store(memory_id="c2", content="片段2")

        cid = self.fm.consolidate_memories(
            memory_ids=["c1", "c2"],
            summary="整合后的摘要",
        )
        assert cid is not None
        consolidation = self.fm.get_consolidation(cid)
        assert consolidation is not None
        assert consolidation.consolidated_content == "整合后的摘要"


# ============================================================
# 10. ForgettingCurve: 保留率计算
# ============================================================

class TestForgettingCurve:
    """ForgettingCurve 遗忘曲线测试"""

    def setup_method(self):
        self.curve = ForgettingCurve()

    def test_zero_days_full_retention(self):
        """零天时保留率应接近 1.0"""
        r = self.curve.calculate_retention(days_elapsed=0)
        assert r >= 0.9

    def test_retention_decreases_over_time(self):
        """保留率应随时间递减"""
        r_early = self.curve.calculate_retention(days_elapsed=1)
        r_late = self.curve.calculate_retention(days_elapsed=30)
        assert r_early > r_late

    def test_high_importance_boosts_retention(self):
        """高重要性应提升保留率"""
        r_low = self.curve.calculate_retention(days_elapsed=7, importance=0.1)
        r_high = self.curve.calculate_retention(days_elapsed=7, importance=0.9)
        assert r_high > r_low
