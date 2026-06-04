"""
Reflection 模块单元测试

覆盖 Reflector、ExperienceAnalyzer、InsightExtractor、PatternRecognizer
"""

import pytest
from datetime import datetime

from packages.MetaSoul.reflection.reflector import (
    Reflector,
    ReflectionResult,
    ReflectionDepth,
)
from packages.MetaSoul.reflection.experience_analyzer import (
    ExperienceAnalyzer,
    ExperiencePattern,
    TrendAnalysis,
)
from packages.MetaSoul.reflection.insight_extractor import (
    InsightExtractor,
    Insight,
    InsightType,
)
from packages.MetaSoul.reflection.pattern_recognizer import (
    PatternRecognizer,
    Pattern,
    PatternType,
)


class TestReflector:
    """反思引擎测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.reflector = Reflector()

    def test_reflect_surface_depth(self):
        """测试表面反思：只生成摘要，不分析因果"""
        experience = {
            "context": "学习 Python 装饰器",
            "action": "阅读文档并练习",
            "result": "掌握了基本用法",
            "outcome": 0.8,
        }
        result = self.reflector.reflect(experience, depth=ReflectionDepth.SURFACE)

        assert "reflection_id" in result
        assert result["depth"] == "surface"
        assert isinstance(result["insights"], list)
        # 表面反思不分析因果
        assert result["causes_identified"] == []
        assert result["effects_observed"] == []

    def test_reflect_causal_depth(self):
        """测试因果反思：分析原因和影响"""
        experience = {
            "context": "部署失败 because 配置错误",
            "action": "尝试回滚",
            "result": "error: 服务不可用",
            "outcome": -0.7,
            "learning": ["检查配置文件"],
        }
        result = self.reflector.reflect(experience, depth=ReflectionDepth.CAUSAL)

        assert result["depth"] == "causal"
        # 因果反思应识别原因
        assert isinstance(result["causes_identified"], list)
        assert isinstance(result["effects_observed"], list)

    def test_reflect_meaning_depth(self):
        """测试意义反思：提取深层含义"""
        experience = {
            "context": "第一次尝试新方法",
            "action": "大胆创新",
            "result": "成功了",
            "outcome": 0.9,
        }
        result = self.reflector.reflect(experience, depth=ReflectionDepth.MEANING)

        assert result["depth"] == "meaning"
        # 意义反思应包含洞察
        assert isinstance(result["insights"], list)

    def test_reflect_transformative_depth(self):
        """测试变革反思：最深层次"""
        experience = {
            "context": "重大决策",
            "action": "改变策略",
            "result": "获得突破",
            "outcome": 0.95,
        }
        result = self.reflector.reflect(experience, depth=ReflectionDepth.TRANSFORMATIVE)

        assert result["depth"] == "transformative"
        assert isinstance(result["lessons_learned"], list)
        assert isinstance(result["suggested_actions"], list)

    def test_reflect_stores_history(self):
        """测试反思历史存储"""
        self.reflector.reflect({"context": "经验1", "action": "做", "result": "完成"})
        self.reflector.reflect({"context": "经验2", "action": "做", "result": "完成"})

        recent = self.reflector.get_recent_reflections(limit=5)
        assert len(recent) == 2
        assert all(isinstance(r, ReflectionResult) for r in recent)

    def test_reflect_callback_triggered(self):
        """测试反思完成回调"""
        callback_results = []
        self.reflector.on_reflection_complete(lambda r: callback_results.append(r))

        self.reflector.reflect({"context": "test", "action": "do", "result": "done"})
        assert len(callback_results) == 1
        assert isinstance(callback_results[0], ReflectionResult)

    def test_get_insights_from_reflections(self):
        """测试从反思中提取洞察"""
        # 先进行深度反思
        self.reflector.reflect(
            {"context": "new 体验", "action": "探索", "result": "成功", "outcome": 0.8},
            depth=ReflectionDepth.MEANING,
        )

        insights = self.reflector.get_insights_from_reflections(min_confidence=0.5)
        assert isinstance(insights, list)


class TestExperienceAnalyzer:
    """经验分析器测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.analyzer = ExperienceAnalyzer()

    def test_analyze_positive_outcome(self):
        """测试分析正面结果"""
        experience = {"outcome": 0.8, "content": "成功完成任务"}
        result = self.analyzer.analyze(experience)

        assert result["outcome"]["label"] == "positive"
        assert result["outcome"]["value"] == 0.8

    def test_analyze_negative_outcome(self):
        """测试分析负面结果"""
        experience = {"outcome": -0.6, "content": "任务失败"}
        result = self.analyzer.analyze(experience)

        assert result["outcome"]["label"] == "negative"

    def test_analyze_neutral_outcome(self):
        """测试分析中性结果"""
        experience = {"outcome": 0.1, "content": "一般般"}
        result = self.analyzer.analyze(experience)

        assert result["outcome"]["label"] == "neutral"

    def test_analyze_sentiment_positive(self):
        """测试正面情感分析"""
        experience = {"outcome": 0.5, "content": "great success", "result": "excellent"}
        result = self.analyzer.analyze(experience)

        assert result["sentiment"]["label"] == "positive"
        assert result["sentiment"]["positive_signals"] > 0

    def test_analyze_sentiment_negative(self):
        """测试负面情感分析"""
        experience = {"outcome": -0.5, "content": "fail error", "result": "bad"}
        result = self.analyzer.analyze(experience)

        assert result["sentiment"]["label"] == "negative"

    def test_identify_success_pattern(self):
        """测试识别成功模式"""
        experience = {"outcome": 0.7, "tags": ["success"]}
        result = self.analyzer.analyze(experience)

        pattern_types = [p["type"] for p in result["patterns"]]
        assert "success" in pattern_types

    def test_identify_failure_pattern(self):
        """测试识别失败模式"""
        experience = {"outcome": -0.7, "tags": ["failure"]}
        result = self.analyzer.analyze(experience)

        pattern_types = [p["type"] for p in result["patterns"]]
        assert "failure" in pattern_types

    def test_identify_repetition_pattern(self):
        """测试识别重复模式"""
        experience = {"outcome": 0.5, "tags": ["repeated"]}
        result = self.analyzer.analyze(experience)

        pattern_types = [p["type"] for p in result["patterns"]]
        assert "repetition" in pattern_types

    def test_analyze_trends_increasing(self):
        """测试上升趋势分析"""
        experiences = [{"outcome": 0.3}, {"outcome": 0.5}, {"outcome": 0.7}]
        trend = self.analyzer.analyze_trends(experiences, "outcome")

        assert isinstance(trend, TrendAnalysis)
        assert trend.direction == "increasing"
        assert trend.slope > 0

    def test_analyze_trends_decreasing(self):
        """测试下降趋势分析"""
        experiences = [{"outcome": 0.8}, {"outcome": 0.5}, {"outcome": 0.2}]
        trend = self.analyzer.analyze_trends(experiences, "outcome")

        assert trend.direction == "decreasing"
        assert trend.slope < 0

    def test_analyze_trends_stable(self):
        """测试稳定趋势分析"""
        experiences = [{"outcome": 0.5}, {"outcome": 0.5}, {"outcome": 0.5}]
        trend = self.analyzer.analyze_trends(experiences, "outcome")

        assert trend.direction == "stable"

    def test_find_similar_experiences(self):
        """测试查找相似经验"""
        target = {"id": "exp1", "content": "Python 编程学习"}
        all_exp = [
            {"id": "exp2", "content": "Python 基础教程"},
            {"id": "exp3", "content": "JavaScript 学习"},
        ]

        similar = self.analyzer.find_similar_experiences(target, all_exp)
        assert isinstance(similar, list)
        # exp2 应该比 exp3 更相似
        if len(similar) >= 2:
            assert similar[0][1] >= similar[1][1]

    def test_assess_value_high(self):
        """测试高价值评估"""
        experience = {
            "outcome": 0.9,
            "novelty": 0.8,
            "learning": ["新知识1", "新知识2"],
        }
        result = self.analyzer.analyze(experience)

        assert result["value_assessment"]["label"] in ["high", "medium"]

    def test_generate_insights_report(self):
        """测试生成洞察报告"""
        experiences = [
            {"outcome": 0.8, "tags": ["success"]},
            {"outcome": 0.6, "tags": ["success"]},
            {"outcome": -0.5, "tags": ["failure"]},
        ]

        report = self.analyzer.generate_insights_report(experiences)

        assert report["experience_count"] == 3
        assert "trends" in report
        assert "patterns" in report
        assert "insights" in report


class TestInsightExtractor:
    """洞察提取器测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.extractor = InsightExtractor()

    def test_extract_causal_insights(self):
        """测试提取因果洞察"""
        experiences = [
            {"id": "exp1", "outcome": 0.8, "factors": ["专注", "练习"]},
            {"id": "exp2", "outcome": 0.9, "factors": ["专注", "练习"]},
        ]

        insight_ids = self.extractor.extract(experiences)
        assert isinstance(insight_ids, list)

        # 应该有因果洞察
        for insight_id in insight_ids:
            insight = self.extractor.get_insight(insight_id)
            assert insight is not None
            assert isinstance(insight, Insight)

    def test_extract_temporal_insights(self):
        """测试提取时间洞察（持续进步）"""
        experiences = [
            {"id": "exp1", "outcome": 0.3},
            {"id": "exp2", "outcome": 0.5},
            {"id": "exp3", "outcome": 0.7},
        ]

        insight_ids = self.extractor.extract(experiences)
        assert isinstance(insight_ids, list)

        # 检查是否有时间洞察
        temporal_insights = self.extractor.get_insights_by_tag("temporal")
        assert isinstance(temporal_insights, list)

    def test_get_top_insights(self):
        """测试获取评分最高的洞察"""
        # 先提取一些洞察
        experiences = [
            {"id": "exp1", "outcome": 0.8, "factors": ["专注"]},
            {"id": "exp2", "outcome": 0.9, "factors": ["专注", "练习"]},
        ]
        self.extractor.extract(experiences)

        top_insights = self.extractor.get_top_insights(limit=5)
        assert isinstance(top_insights, list)
        # 按评分降序排列
        if len(top_insights) >= 2:
            assert top_insights[0].get_score() >= top_insights[1].get_score()

    def test_update_insight_evaluation(self):
        """测试更新洞察评估"""
        # 先提取洞察
        experiences = [{"id": "exp1", "outcome": 0.8, "factors": ["专注"]}]
        insight_ids = self.extractor.extract(experiences)

        if insight_ids:
            insight_id = insight_ids[0]
            success = self.extractor.update_insight_evaluation(
                insight_id, novelty=0.9, utility=0.8
            )
            assert success is True

            insight = self.extractor.get_insight(insight_id)
            assert insight.novelty == 0.9
            assert insight.utility == 0.8

    def test_insight_score_calculation(self):
        """测试洞察评分计算"""
        insight = Insight(
            insight_id="test",
            insight_type=InsightType.CAUSAL,
            content="测试洞察",
            confidence=0.8,
            novelty=0.6,
            utility=0.7,
        )

        expected_score = (0.8 + 0.6 + 0.7) / 3
        assert abs(insight.get_score() - expected_score) < 0.01


class TestPatternRecognizer:
    """模式识别器测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.recognizer = PatternRecognizer()

    def test_register_event(self):
        """测试注册事件"""
        pattern_ids = self.recognizer.register_event(
            event_type="coding",
            elements=["编写", "测试", "部署"],
        )
        assert isinstance(pattern_ids, list)

    def test_sequential_pattern_detection(self):
        """测试序列模式检测"""
        # 注册多次相同序列
        for _ in range(3):
            self.recognizer.register_event(
                event_type="task",
                elements=["计划", "执行", "评估"],
            )

        patterns = self.recognizer.get_patterns_by_type(PatternType.SEQUENTIAL)
        assert isinstance(patterns, list)

    def test_habit_pattern_detection(self):
        """测试习惯模式检测"""
        # 注册多次包含相同元素的事件
        for _ in range(10):
            self.recognizer.register_event(
                event_type="routine",
                elements=["早起", "锻炼", "阅读"],
            )

        patterns = self.recognizer.get_patterns_by_type(PatternType.HABIT)
        assert isinstance(patterns, list)

    def test_anomaly_detection(self):
        """测试异常检测"""
        # 先注册正常事件
        for _ in range(5):
            self.recognizer.register_event(
                event_type="normal",
                elements=["A", "B", "C"],
            )

        # 检测异常事件
        anomalies = self.recognizer.detect_anomalies({
            "type": "anomaly",
            "elements": ["X", "Y", "Z"],
        })
        assert isinstance(anomalies, list)

    def test_pattern_statistics(self):
        """测试模式统计"""
        self.recognizer.register_event("test", ["1", "2"])
        stats = self.recognizer.get_pattern_statistics()

        assert "total_patterns" in stats
        assert "by_type" in stats
        assert "average_strength" in stats
        assert "average_confidence" in stats
        assert "recent_events" in stats

    def test_update_pattern_strength(self):
        """测试更新模式强度"""
        # 先注册事件创建模式
        for _ in range(3):
            self.recognizer.register_event(
                event_type="task",
                elements=["计划", "执行"],
            )

        patterns = self.recognizer.get_active_patterns()
        if patterns:
            pattern_id = patterns[0].pattern_id
            original_strength = patterns[0].strength

            success = self.recognizer.update_pattern_strength(pattern_id, 0.2)
            assert success is True

            updated = self.recognizer.get_pattern(pattern_id)
            assert updated.strength == min(1.0, original_strength + 0.2)

    def test_merge_patterns(self):
        """测试合并模式"""
        # 创建两个模式
        for _ in range(3):
            self.recognizer.register_event("task1", ["A", "B"])
            self.recognizer.register_event("task2", ["C", "D"])

        patterns = self.recognizer.get_active_patterns()
        if len(patterns) >= 2:
            p1_id = patterns[0].pattern_id
            p2_id = patterns[1].pattern_id

            merged_id = self.recognizer.merge_patterns(p1_id, p2_id)
            assert merged_id is not None

            merged = self.recognizer.get_pattern(merged_id)
            assert merged is not None

    def test_clear_old_patterns(self):
        """测试清除旧模式"""
        # 注册事件
        self.recognizer.register_event("test", ["A", "B"])

        # 清除旧模式（设置很短的时间）
        removed = self.recognizer.clear_old_patterns(max_age_days=0, min_strength=0.99)
        assert isinstance(removed, int)
        assert removed >= 0


class TestLearningCycle:
    """学习循环测试"""

    def setup_method(self):
        """每个测试前初始化"""
        from packages.MetaSoul.learning.learner import SelfLearner
        self.learner = SelfLearner(soul_id="test_soul")

    def test_learn_basic(self):
        """测试基本学习流程"""
        experience = {
            "content": "学习新技能",
            "source": "direct",
            "tags": ["success"],
        }

        result = self.learner.learn(experience)
        assert result.success is True
        assert isinstance(result.new_knowledge, list)

    def test_learn_with_feedback(self):
        """测试带反馈的学习"""
        experience = {
            "content": "尝试新方法",
            "tags": ["success"],
        }
        feedback = {
            "type": "reinforcement",
            "content": "做得好",
            "weight": 1.0,
        }

        result = self.learner.learn(experience, feedback)
        assert result.success is True
        assert result.confidence_delta > 0

    def test_learn_correction_feedback(self):
        """测试纠正反馈"""
        experience = {
            "content": "犯错",
            "tags": ["failure"],
        }
        feedback = {
            "type": "correction",
            "content": "需要改进",
        }

        result = self.learner.learn(experience, feedback)
        assert result.success is True
        assert result.confidence_delta < 0

    def test_learning_stats(self):
        """测试学习统计"""
        self.learner.learn({"content": "经验1", "tags": []})
        self.learner.learn({"content": "经验2", "tags": []})

        stats = self.learner.get_stats()
        assert stats["cycle_count"] == 2
        assert stats["total_learnings"] == 2
        assert stats["observations"] == 2

    def test_learning_callback(self):
        """测试学习完成回调"""
        callback_results = []
        self.learner.on_learning_complete(lambda r: callback_results.append(r))

        self.learner.learn({"content": "测试", "tags": []})
        assert len(callback_results) == 1
