"""
Memory 模块测试
"""

import unittest
from datetime import datetime, timedelta
import time

from packages.SoulTeam.memory import (
    MetaSoul,
    MemoryType,
    MemoryEntry,
    MemoryImportance,
    SoulExperience,
    MemoryHierarchy,
    MemoryTier,
    MemoryStore,
    MemoryStoreConfig,
    InMemoryStorageBackend,
    MemoryIndex,
    ForgettingMechanism,
    ForgettingPolicy,
)


class TestMetaSoul(unittest.TestCase):
    """MetaSoul 核心类测试"""
    
    def setUp(self):
        self.soul = MetaSoul(soul_id="test_soul", name="TestSoul")
    
    def test_store_memory(self):
        """测试存储记忆"""
        memory_id = self.soul.store_memory(
            content="这是一个测试记忆",
            memory_type=MemoryType.WORKING,
            importance=MemoryImportance.HIGH,
        )
        
        self.assertIsNotNone(memory_id)
        self.assertIn(memory_id, self.soul.soul_memory.memories)
    
    def test_retrieve_memory(self):
        """测试检索记忆"""
        # 存储测试记忆
        self.soul.store_memory(
            content="Python 编程语言",
            memory_type=MemoryType.SEMANTIC,
        )
        
        # 检索
        results = self.soul.retrieve(
            query="Python 编程",
            limit=5
        )
        
        self.assertIsInstance(results, list)
    
    def test_store_experience(self):
        """测试存储经验"""
        experience_id = self.soul.store_experience(
            context="学习 Python",
            action="完成了教程",
            result="掌握了基础语法",
            reflection="需要更多实践",
            outcome=0.8,
            learning=["基础语法", "函数定义"],
        )
        
        self.assertIsNotNone(experience_id)
        self.assertIn(experience_id, self.soul.soul_memory.experiences)
    
    def test_associate_memories(self):
        """测试关联记忆"""
        id1 = self.soul.store_memory(
            content="Python",
            memory_type=MemoryType.SEMANTIC,
        )
        id2 = self.soul.store_memory(
            content="编程语言",
            memory_type=MemoryType.SEMANTIC,
        )
        
        result = self.soul.associate_memories(id1, id2)
        self.assertTrue(result)
    
    def test_get_stats(self):
        """测试获取统计"""
        self.soul.store_memory(
            content="测试1",
            memory_type=MemoryType.WORKING,
        )
        self.soul.store_memory(
            content="测试2",
            memory_type=MemoryType.EPISODIC,
        )
        
        stats = self.soul.get_stats()
        
        self.assertEqual(stats["soul_id"], "test_soul")
        self.assertGreaterEqual(stats["total_memories"], 2)


class TestMemoryHierarchy(unittest.TestCase):
    """记忆层次结构测试"""
    
    def setUp(self):
        self.hierarchy = MemoryHierarchy(
            working_capacity=5,
            episodic_limit=100,
        )
    
    def test_working_memory(self):
        """测试工作记忆"""
        self.hierarchy.working_memory.store("key1", "value1")
        result = self.hierarchy.working_memory.retrieve("key1")
        self.assertEqual(result, "value1")
    
    def test_store_and_retrieve(self):
        """测试存储和检索"""
        self.hierarchy.store(
            tier=MemoryTier.EPISODIC,
            entry_id="ep1",
            content="测试情景",
        )
        
        result = self.hierarchy.retrieve(MemoryTier.EPISODIC, "ep1")
        self.assertIsNotNone(result)


class TestMemoryStore(unittest.TestCase):
    """记忆存储测试"""
    
    def setUp(self):
        self.store = MemoryStore()
    
    def test_store_and_retrieve(self):
        """测试存储和检索"""
        success = self.store.store(
            memory_id="mem1",
            content="测试内容",
            memory_type="semantic",
            importance=3,
        )
        
        self.assertTrue(success)
        
        result = self.store.retrieve("mem1")
        self.assertIsNotNone(result)
        self.assertEqual(result["content"], "测试内容")
    
    def test_delete(self):
        """测试删除"""
        self.store.store(memory_id="mem2", content="待删除")
        success = self.store.delete("mem2")
        self.assertTrue(success)
    
    def test_query_by_type(self):
        """测试按类型查询"""
        self.store.store(memory_id="mem3", content="内容1", memory_type="semantic")
        self.store.store(memory_id="mem4", content="内容2", memory_type="episodic")
        
        results = self.store.query_by_type("semantic")
        self.assertEqual(len(results), 1)


class TestMemoryIndex(unittest.TestCase):
    """记忆索引测试"""
    
    def setUp(self):
        self.index = MemoryIndex(vector_dim=64)
    
    def test_index(self):
        """测试索引"""
        self.index.index(
            memory_id="idx1",
            content="Python 编程",
            metadata={"keywords": ["Python", "编程"]},
        )
        
        results = self.index.search_by_keywords("Python")
        self.assertIn("idx1", results)
    
    def test_semantic_search(self):
        """测试语义搜索"""
        self.index.index(memory_id="sem1", content="机器学习是AI的分支")
        self.index.index(memory_id="sem2", content="深度学习是机器学习的分支")
        
        results = self.index.search_by_semantic("人工智能", limit=5)
        self.assertIsInstance(results, list)


class TestForgettingMechanism(unittest.TestCase):
    """遗忘机制测试"""
    
    def setUp(self):
        self.store = MemoryStore()
        self.forgetting = ForgettingMechanism(
            memory_store=self.store,
            policy=ForgettingPolicy.ADAPTIVE,
        )
    
    def test_protect_memory(self):
        """测试保护记忆"""
        self.store.store(memory_id="protect1", content="重要内容")
        self.forgetting.protect_memory("protect1")
        
        self.assertTrue(self.forgetting.is_protected("protect1"))
    
    def test_calculate_decay(self):
        """测试计算衰减"""
        self.store.store(
            memory_id="decay1",
            content="测试",
            importance=5,
        )
        
        memory = self.store.retrieve("decay1")
        decay = self.forgetting.calculate_decay(memory)
        
        self.assertGreaterEqual(decay, 0.0)
        self.assertLessEqual(decay, 1.0)


if __name__ == "__main__":
    unittest.main()
