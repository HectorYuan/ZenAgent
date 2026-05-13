"""
Learning 模块测试
"""

import unittest
from datetime import datetime

from packages.SoulTeam.learning import (
    SelfLearner,
    LearningCycle,
    LearningResult,
    FeedbackProcessor,
    FeedbackType,
    Feedback,
    FeedbackSource,
    KnowledgeGraph,
    EntityType,
    RelationType,
    SkillAcquisition,
    SkillLevel,
    LearningOptimizer,
    CurriculumStage,
)


class TestSelfLearner(unittest.TestCase):
    """自学习器测试"""
    
    def setUp(self):
        self.learner = SelfLearner(soul_id="learner1")
    
    def test_learn(self):
        """测试学习"""
        experience = {
            "content": "学习 Python 基础",
            "source": "course",
            "reliability": 0.9,
        }
        
        result = self.learner.learn(experience)
        
        self.assertIsNotNone(result)
        self.assertIn("observation_id", result.metadata)
    
    def test_learning_cycle(self):
        """测试学习循环"""
        result = self.learner.learn({
            "content": "测试经验",
            "tags": ["test"],
        })
        
        self.assertIsInstance(result, LearningResult)
    
    def test_stats(self):
        """测试统计"""
        self.learner.learn({"content": "测试1"})
        self.learner.learn({"content": "测试2"})
        
        stats = self.learner.get_stats()
        
        self.assertEqual(stats["total_learnings"], 2)


class TestFeedbackProcessor(unittest.TestCase):
    """反馈处理器测试"""
    
    def setUp(self):
        self.learner = SelfLearner(soul_id="test")
        self.processor = FeedbackProcessor(learner=self.learner)
    
    def test_process_feedback(self):
        """测试处理反馈"""
        feedback = Feedback(
            source=FeedbackSource.EXTERNAL,
            feedback_type=FeedbackType.CORRECTION,
            content="需要改进",
            weight=1.0,
        )
        
        result = self.processor.process(feedback)
        
        self.assertIn("feedback_id", result)
        self.assertIn("confidence_delta", result)
    
    def test_create_internal_feedback(self):
        """测试创建内部反馈"""
        feedback = self.processor.create_internal_feedback(
            content="自我评估",
            feedback_type=FeedbackType.REINFORCEMENT,
            context="完成任务",
        )
        
        self.assertEqual(feedback.source, FeedbackSource.INTERNAL)
    
    def test_feedback_stats(self):
        """测试反馈统计"""
        feedback = Feedback(
            source=FeedbackSource.EXTERNAL,
            feedback_type=FeedbackType.NOVEL,
            content="新信息",
        )
        self.processor.process(feedback)
        
        stats = self.processor.get_stats()
        self.assertEqual(stats["total_feedback"], 1)


class TestKnowledgeGraph(unittest.TestCase):
    """知识图谱测试"""
    
    def setUp(self):
        self.kg = KnowledgeGraph()
    
    def test_add_entity(self):
        """测试添加实体"""
        entity_id = self.kg.add_entity(
            name="Python",
            entity_type=EntityType.CONCEPT,
            description="编程语言",
        )
        
        self.assertIsNotNone(entity_id)
        self.assertIn(entity_id, self.kg._entities)
    
    def test_add_relation(self):
        """测试添加关系"""
        id1 = self.kg.add_entity("Python", EntityType.CONCEPT)
        id2 = self.kg.add_entity("编程", EntityType.CONCEPT)
        
        relation_id = self.kg.add_relation(
            source_id=id1,
            target_id=id2,
            relation_type=RelationType.ENABLES,
        )
        
        self.assertIsNotNone(relation_id)
    
    def test_get_entity(self):
        """测试获取实体"""
        entity_id = self.kg.add_entity("Test", EntityType.OBJECT)
        entity = self.kg.get_entity(entity_id)
        
        self.assertIsNotNone(entity)
        self.assertEqual(entity.name, "Test")
    
    def test_traverse(self):
        """测试遍历"""
        id1 = self.kg.add_entity("A", EntityType.CONCEPT)
        id2 = self.kg.add_entity("B", EntityType.CONCEPT)
        self.kg.add_relation(id1, id2, RelationType.IS_A)
        
        results = self.kg.traverse(
            start_id=id1,
            relation_types=[RelationType.IS_A],
            max_depth=3,
        )
        
        self.assertIsInstance(results, list)
    
    def test_stats(self):
        """测试统计"""
        self.kg.add_entity("E1", EntityType.CONCEPT)
        self.kg.add_entity("E2", EntityType.OBJECT)
        
        stats = self.kg.get_stats()
        self.assertEqual(stats["total_entities"], 2)


class TestSkillAcquisition(unittest.TestCase):
    """技能获取测试"""
    
    def setUp(self):
        self.acquisition = SkillAcquisition()
    
    def test_register_skill(self):
        """测试注册技能"""
        skill_id = self.acquisition.register_skill(
            skill_name="Python编程",
            description="使用Python编程的能力",
        )
        
        self.assertIsNotNone(skill_id)
    
    def test_learn_from_demonstration(self):
        """测试从示范学习"""
        from packages.SoulTeam.learning.skill_acquisition import Demonstration
        
        skill_id = self.acquisition.register_skill("测试技能")
        
        demo = Demonstration(
            teacher_id="teacher1",
            content="如何做某事",
            steps=["步骤1", "步骤2", "步骤3"],
            success=True,
        )
        
        result_id = self.acquisition.learn_from_demonstration("测试技能", demo)
        self.assertEqual(result_id, skill_id)
    
    def test_reinforce_learning(self):
        """测试强化学习"""
        skill_id = self.acquisition.register_skill("强化技能")
        
        attempt = self.acquisition.reinforce_learning(
            skill_id=skill_id,
            outcome=0.8,
        )
        
        self.assertIsNotNone(attempt)
        self.assertTrue(attempt.success)
    
    def test_apply_skill(self):
        """测试应用技能"""
        skill_id = self.acquisition.register_skill("应用技能")
        
        result = self.acquisition.apply_skill(
            skill_id=skill_id,
            context={"task": "测试"},
        )
        
        self.assertIn("success", result)
    
    def test_distill_knowledge(self):
        """测试知识蒸馏"""
        id1 = self.acquisition.register_skill("源技能")
        id2 = self.acquisition.register_skill("目标技能")
        
        result = self.acquisition.distill_knowledge(id1, id2)
        self.assertTrue(result)


class TestLearningOptimizer(unittest.TestCase):
    """学习优化器测试"""
    
    def setUp(self):
        self.optimizer = LearningOptimizer()
    
    def test_create_curriculum(self):
        """测试创建课程"""
        from packages.SoulTeam.learning.learning_optimizer import CurriculumItem
        
        items = [
            CurriculumItem(
                item_id="item1",
                name="基础",
                description="基础知识",
                stage=CurriculumStage.FOUNDATION,
                difficulty=0.3,
            ),
        ]
        
        curriculum_id = self.optimizer.create_curriculum("编程", items)
        self.assertEqual(curriculum_id, "编程")
    
    def test_get_next_item(self):
        """测试获取下一个项目"""
        item = self.optimizer.get_next_learning_item("测试领域")
        # 首次可能没有项目
        self.assertTrue(item is None or isinstance(item, CurriculumItem))
    
    def test_update_progress(self):
        """测试更新进度"""
        completed, mastery = self.optimizer.update_progress("item1", 0.8)
        self.assertIsInstance(completed, bool)
        self.assertIsInstance(mastery, float)
    
    def test_analyze_transferability(self):
        """测试分析迁移能力"""
        self.optimizer.learn_in_domain("数学", "代数", 0.5)
        self.optimizer.learn_in_domain("物理", "力学", 0.3)
        
        transferability = self.optimizer.analyze_transferability(
            "数学", "物理"
        )
        
        self.assertGreaterEqual(transferability, 0.0)
        self.assertLessEqual(transferability, 1.0)


if __name__ == "__main__":
    unittest.main()
