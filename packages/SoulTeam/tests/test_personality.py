"""
Personality 模块测试
"""

import unittest
from datetime import datetime

from packages.SoulTeam.personality import (
    Personality,
    BigFiveTraits,
    TraitDynamics,
    BeliefSystem,
    Belief,
    BeliefStrength,
    ValueEvolution,
    Value,
    ValuePriority,
)


class TestPersonality(unittest.TestCase):
    """人格模型测试"""
    
    def setUp(self):
        self.personality = Personality()
    
    def test_initial_traits(self):
        """测试初始特质"""
        traits = self.personality.get_traits()
        
        self.assertIn("openness", traits)
        self.assertIn("conscientiousness", traits)
        self.assertEqual(len(traits), 5)
    
    def test_get_trait(self):
        """测试获取特质"""
        openness = self.personality.get_trait(BigFiveTraits.OPENNESS)
        self.assertGreaterEqual(openness, 0.0)
        self.assertLessEqual(openness, 1.0)
    
    def test_set_trait(self):
        """测试设置特质"""
        self.personality.set_trait(BigFiveTraits.OPENNESS, 0.8)
        openness = self.personality.get_trait(BigFiveTraits.OPENNESS)
        self.assertAlmostEqual(openness, 0.8)
    
    def test_evolve(self):
        """测试演化"""
        experience = {
            "id": "exp1",
            "outcome": 0.7,
            "sentiment": 0.5,
            "novelty": 0.8,
        }
        
        deltas = self.personality.evolve(experience)
        
        self.assertIsInstance(deltas, dict)
    
    def test_predict_behavior(self):
        """测试预测行为"""
        situation = {
            "social": True,
            "complex": True,
        }
        
        predictions = self.personality.predict_behavior(situation)
        
        self.assertIsInstance(predictions, dict)
    
    def test_reset(self):
        """测试重置"""
        self.personality.set_trait(BigFiveTraits.OPENNESS, 0.9)
        self.personality.reset()
        
        openness = self.personality.get_trait(BigFiveTraits.OPENNESS)
        self.assertAlmostEqual(openness, 0.5)


class TestTraitDynamics(unittest.TestCase):
    """特质动态测试"""
    
    def setUp(self):
        self.personality = Personality()
        self.dynamics = TraitDynamics(self.personality)
    
    def test_process_experience(self):
        """测试处理经验"""
        experience = {
            "id": "exp1",
            "outcome": 0.6,
            "sentiment": 0.4,
            "novelty": 0.5,
            "social": True,
        }
        
        changes = self.dynamics.process_experience(experience)
        
        self.assertIsInstance(changes, list)
    
    def test_get_recent_changes(self):
        """测试获取最近变化"""
        self.dynamics.process_experience({
            "outcome": 0.5,
            "sentiment": 0.3,
        })
        
        changes = self.dynamics.get_recent_changes()
        self.assertIsInstance(changes, list)
    
    def test_get_change_trend(self):
        """测试获取变化趋势"""
        # 处理多个经验
        for _ in range(5):
            self.dynamics.process_experience({
                "outcome": 0.6,
                "sentiment": 0.4,
            })
        
        trend = self.dynamics.get_change_trend("conscientiousness")
        
        self.assertIn("trend", trend)
    
    def test_environmental_factors(self):
        """测试环境因素"""
        self.dynamics.process_experience({
            "social": True,
            "stressful": True,
            "achievement": True,
        })
        
        factors = self.dynamics.get_environmental_factors()
        
        self.assertIsInstance(factors, dict)


class TestBeliefSystem(unittest.TestCase):
    """信念系统测试"""
    
    def setUp(self):
        self.belief_system = BeliefSystem()
    
    def test_create_belief(self):
        """测试创建信念"""
        belief_id = self.belief_system.create_belief(
            content="学习是重要的",
            strength=BeliefStrength.MODERATE,
            confidence=0.6,
        )
        
        self.assertIsNotNone(belief_id)
        self.assertIn(belief_id, self.belief_system._beliefs)
    
    def test_get_belief(self):
        """测试获取信念"""
        belief_id = self.belief_system.create_belief("测试信念")
        belief = self.belief_system.get_belief(belief_id)
        
        self.assertIsNotNone(belief)
        self.assertEqual(belief.content, "测试信念")
    
    def test_reinforce_belief(self):
        """测试强化信念"""
        belief_id = self.belief_system.create_belief("待强化信念")
        initial_confidence = self.belief_system.get_belief(belief_id).confidence
        
        self.belief_system.reinforce_belief(
            belief_id,
            evidence="支持证据",
            amount=0.2,
        )
        
        new_confidence = self.belief_system.get_belief(belief_id).confidence
        self.assertGreater(new_confidence, initial_confidence)
    
    def test_challenge_belief(self):
        """测试挑战信念"""
        belief_id = self.belief_system.create_belief("待挑战信念", confidence=0.8)
        
        self.belief_system.challenge_belief(
            belief_id,
            counter_evidence="反证",
            amount=0.3,
        )
        
        confidence = self.belief_system.get_belief(belief_id).confidence
        self.assertLess(confidence, 0.8)
    
    def test_create_contradiction(self):
        """测试创建矛盾"""
        id1 = self.belief_system.create_belief("信念1")
        id2 = self.belief_system.create_belief("信念2")
        
        result = self.belief_system.create_contradiction(id1, id2)
        self.assertTrue(result)
    
    def test_search_beliefs(self):
        """测试搜索信念"""
        self.belief_system.create_belief("Python 是编程语言")
        self.belief_system.create_belief("JavaScript 是编程语言")
        
        results = self.belief_system.search_beliefs("编程语言")
        self.assertEqual(len(results), 2)
    
    def test_get_strong_beliefs(self):
        """测试获取强信念"""
        self.belief_system.create_belief(
            "强信念", confidence=0.9
        )
        self.belief_system.create_belief(
            "弱信念", confidence=0.3
        )
        
        strong = self.belief_system.get_strong_beliefs(
            min_strength=BeliefStrength.STRONG
        )
        self.assertEqual(len(strong), 1)
    
    def test_get_stats(self):
        """测试获取统计"""
        self.belief_system.create_belief("信念1")
        self.belief_system.create_belief("信念2")
        
        stats = self.belief_system.get_stats()
        self.assertEqual(stats["total_beliefs"], 2)


class TestValueEvolution(unittest.TestCase):
    """价值观演化测试"""
    
    def setUp(self):
        self.evolution = ValueEvolution()
    
    def test_create_value(self):
        """测试创建价值观"""
        value_id = self.evolution.create_value(
            name="诚信",
            description="诚实守信的品质",
            priority=ValuePriority.HIGH,
        )
        
        self.assertIsNotNone(value_id)
    
    def test_get_value(self):
        """测试获取价值观"""
        value_id = self.evolution.create_value("测试价值")
        value = self.evolution.get_value(value_id)
        
        self.assertIsNotNone(value)
        self.assertEqual(value.name, "测试价值")
    
    def test_set_as_core(self):
        """测试设为核心价值观"""
        value_id = self.evolution.create_value("核心价值")
        
        result = self.evolution.set_as_core(value_id)
        self.assertTrue(result)
        
        core = self.evolution.get_core_values()
        self.assertEqual(len(core), 1)
    
    def test_update_from_experience(self):
        """测试从经验更新"""
        value_id = self.evolution.create_value("成长")
        
        delta = self.evolution.update_value_from_experience(
            value_id,
            experience={
                "id": "exp1",
                "outcome": 0.7,
                "sentiment": 0.5,
                "value_aligned": True,
            }
        )
        
        self.assertIsInstance(delta, (float, type(None)))
    
    def test_align_behavior(self):
        """测试行为对齐"""
        self.evolution.create_value("效率")
        
        result = self.evolution.align_behavior({
            "values": ["效率"],
            "success": True,
        })
        
        self.assertIn("aligned", result)
        self.assertIn("alignment_score", result)
    
    def test_get_prioritized_values(self):
        """测试获取优先级价值观"""
        self.evolution.create_value("价值1", priority=ValuePriority.LOW)
        self.evolution.create_value("价值2", priority=ValuePriority.HIGH)
        
        prioritized = self.evolution.get_prioritized_values()
        
        self.assertEqual(len(prioritized), 2)
        # 高优先级应该在前面
        self.assertEqual(
            prioritized[0].priority,
            ValuePriority.HIGH
        )
    
    def test_resolve_conflict(self):
        """测试解决冲突"""
        id1 = self.evolution.create_value("价值A")
        id2 = self.evolution.create_value("价值B")
        
        winner = self.evolution.resolve_value_conflict(
            id1, id2, "需要做出选择"
        )
        
        self.assertIn(winner, [id1, id2])
    
    def test_get_stats(self):
        """测试获取统计"""
        self.evolution.create_value("价值1")
        self.evolution.create_value("价值2")
        
        stats = self.evolution.get_stats()
        self.assertEqual(stats["total_values"], 2)


if __name__ == "__main__":
    unittest.main()
