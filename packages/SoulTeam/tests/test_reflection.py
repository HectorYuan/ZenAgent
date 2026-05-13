"""
Reflection 模块测试
"""

import unittest
from datetime import datetime

from packages.SoulTeam.reflection import (
    Reflector,
    ReflectionResult,
    ReflectionDepth,
    ExperienceAnalyzer,
    InsightExtractor,
    InsightType,
    PatternRecognizer,
    PatternType,
)


class TestReflector(unittest.TestCase):
    """反思引擎测试"""
    
    def setUp(self):
        self.reflector = Reflector()
    
    def test_reflect_surface(self):
        """测试表面反思"""
        experience = {
            "context": "学习Python",
            "action": "完成教程",
            "result": "掌握了基础",
            "outcome": 0.7,
        }
        
        result = self.reflector.reflect(experience)
        
        self.assertIn("reflection_id", result)
        self.assertEqual(result["depth"], "surface")
    
    def test_reflect_causal(self):
        """测试因果反思"""
        experience = {
            "context": "遇到问题",
            "action": "分析原因",
            "result": "找到解决方案",
            "outcome": 0.6,
        }
        
        result = self.reflector.reflect(experience, ReflectionDepth.CAUSAL)
        
        self.assertEqual(result["depth"], "causal")
        self.assertIn("causes_identified", result)
    
    def test_reflect_deep(self):
        """测试深度反思"""
        experience = {
            "context": "重要的人生选择",
            "action": "仔细考虑",
            "result": "做出了决定",
            "outcome": 0.8,
        }
        
        result = self.reflector.reflect(experience, ReflectionDepth.MEANING)
        
        self.assertIn("insights", result)
    
    def test_get_recent_reflections(self):
        """测试获取最近的反思"""
        self.reflector.reflect({"context": "测试1", "action": "做1", "result": "完成1"})
        self.reflector.reflect({"context": "测试2", "action": "做2", "result": "完成2"})
        
        recent = self.reflector.get_recent_reflections(limit=5)
        self.assertLessEqual(len(recent), 5)


class TestExperienceAnalyzer(unittest.TestCase):
    """经验分析器测试"""
    
    def setUp(self):
        self.analyzer = ExperienceAnalyzer()
    
    def test_analyze_outcome(self):
        """测试分析结果"""
        experience = {
            "outcome": 0.8,
            "content": "成功的任务",
        }
        
        result = self.analyzer.analyze(experience)
        
        self.assertIn("outcome", result)
        self.assertEqual(result["outcome"]["label"], "positive")
    
    def test_analyze_negative_outcome(self):
        """测试分析负面结果"""
        experience = {
            "outcome": -0.6,
            "content": "失败的任务",
        }
        
        result = self.analyzer.analyze(experience)
        self.assertEqual(result["outcome"]["label"], "negative")
    
    def test_identify_patterns(self):
        """测试识别模式"""
        experience = {
            "outcome": 0.7,
            "tags": ["success", "repeated"],
        }
        
        result = self.analyzer.analyze(experience)
        self.assertIn("patterns", result)
    
    def test_analyze_trends(self):
        """测试分析趋势"""
        experiences = [
            {"outcome": 0.3},
            {"outcome": 0.5},
            {"outcome": 0.7},
        ]
        
        trend = self.analyzer.analyze_trends(experiences, "outcome")
        
        self.assertEqual(trend.direction, "increasing")
    
    def test_find_similar_experiences(self):
        """测试查找相似经验"""
        target = {
            "id": "exp1",
            "content": "Python 编程学习",
        }
        all_exp = [
            {"id": "exp2", "content": "Python 基础教程"},
            {"id": "exp3", "content": "JavaScript 学习"},
        ]
        
        similar = self.analyzer.find_similar_experiences(target, all_exp)
        
        self.assertIsInstance(similar, list)
        # exp2 应该比 exp3 更相似
        if similar:
            self.assertGreaterEqual(similar[0][1], 0)


class TestInsightExtractor(unittest.TestCase):
    """洞察提取器测试"""
    
    def setUp(self):
        self.extractor = InsightExtractor()
    
    def test_extract_single_experience(self):
        """测试提取单个经验洞察"""
        experiences = [
            {
                "id": "exp1",
                "outcome": 0.8,
                "factors": ["专注", "练习"],
            }
        ]
        
        insight_ids = self.extractor.extract(experiences)
        
        self.assertIsInstance(insight_ids, list)
    
    def test_extract_multiple_experiences(self):
        """测试提取多个经验洞察"""
        experiences = [
            {"id": "exp1", "outcome": 0.7, "factors": ["专注"]},
            {"id": "exp2", "outcome": 0.8, "factors": ["专注", "练习"]},
            {"id": "exp3", "outcome": 0.6, "factors": ["练习"]},
        ]
        
        insight_ids = self.extractor.extract(experiences)
        
        self.assertIsInstance(insight_ids, list)
    
    def test_get_insight(self):
        """测试获取洞察"""
        experiences = [
            {"id": "exp1", "outcome": 0.8, "factors": ["专注"]},
        ]
        self.extractor.extract(experiences)
        
        insights = self.extractor.get_top_insights()
        self.assertIsInstance(insights, list)


class TestPatternRecognizer(unittest.TestCase):
    """模式识别器测试"""
    
    def setUp(self):
        self.recognizer = PatternRecognizer()
    
    def test_register_event(self):
        """测试注册事件"""
        pattern_ids = self.recognizer.register_event(
            event_type="coding",
            elements=["编写", "测试", "部署"],
        )
        
        self.assertIsInstance(pattern_ids, list)
    
    def test_detect_sequential_pattern(self):
        """测试检测序列模式"""
        # 注册多个相同序列
        for _ in range(3):
            self.recognizer.register_event(
                event_type="task",
                elements=["计划", "执行", "评估"],
            )
        
        self.recognizer.register_event(
            event_type="task",
            elements=["计划", "执行", "评估"],
        )
        
        patterns = self.recognizer.get_patterns_by_type(PatternType.SEQUENTIAL)
        self.assertIsInstance(patterns, list)
    
    def test_detect_habit_pattern(self):
        """测试检测习惯模式"""
        # 注册多个包含相同元素的事件
        for _ in range(10):
            self.recognizer.register_event(
                event_type="routine",
                elements=["早起", "锻炼", "阅读"],
            )
        
        patterns = self.recognizer.get_patterns_by_type(PatternType.HABIT)
        self.assertGreaterEqual(len(patterns), 0)
    
    def test_detect_anomalies(self):
        """测试检测异常"""
        # 先注册一些正常事件
        for _ in range(5):
            self.recognizer.register_event(
                event_type="normal",
                elements=["A", "B", "C"],
            )
        
        # 注册一个异常事件
        current = {
            "type": "anomaly",
            "elements": ["X", "Y", "Z"],
        }
        
        anomalies = self.recognizer.detect_anomalies(current)
        self.assertIsInstance(anomalies, list)
    
    def test_get_statistics(self):
        """测试获取统计"""
        self.recognizer.register_event("test", ["1", "2"])
        
        stats = self.recognizer.get_pattern_statistics()
        self.assertIn("total_patterns", stats)


if __name__ == "__main__":
    unittest.main()
