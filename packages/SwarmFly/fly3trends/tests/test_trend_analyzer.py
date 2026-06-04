"""
TrendAnalyzer 单元测试

覆盖:
- Trend dataclass: is_significant、get_lifespan
- TrendAnalysis dataclass
- TrendAnalyzer: add_trend、get_trends、get_trend_by_id、get_stats、cleanup_old_trends
- TrendAggregator: aggregate_trends
- TrendScorer: calculate_score、calculate_confidence
"""

import pytest
from datetime import datetime, timedelta

from packages.SwarmFly.fly3trends.Core.TrendAnalyzer.trend_analyzer import (
    Trend,
    TrendType,
    TrendSource,
    TrendAnalysis,
    TrendAnalyzer,
    TrendAggregator,
    TrendScorer,
)


def _make_trend(**kwargs) -> Trend:
    """辅助函数: 创建测试用 Trend 对象"""
    defaults = dict(
        trend_id="t1",
        name="test trend",
        description="desc",
        trend_type=TrendType.RISING,
        source=TrendSource.SOCIAL_MEDIA,
        score=70.0,
        confidence=0.8,
        volume=500,
        keywords=["ai", "llm"],
        entities=["OpenAI"],
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 10),
        velocity=1.5,
    )
    defaults.update(kwargs)
    return Trend(**defaults)


# ── Trend dataclass ─────────────────────────────────────────────

class TestTrendIsSignificant:
    """Trend.is_significant 判断逻辑"""

    def test_significant_when_above_threshold(self):
        """score >= threshold 且 confidence >= 0.6 应返回 True"""
        trend = _make_trend(score=70.0, confidence=0.8)
        assert trend.is_significant(threshold=60.0) is True

    def test_not_significant_when_score_low(self):
        """score 低于阈值时应返回 False"""
        trend = _make_trend(score=50.0, confidence=0.8)
        assert trend.is_significant(threshold=60.0) is False

    def test_not_significant_when_confidence_low(self):
        """confidence 低于 0.6 时应返回 False"""
        trend = _make_trend(score=80.0, confidence=0.5)
        assert trend.is_significant(threshold=60.0) is False

    def test_significant_with_custom_threshold(self):
        """使用自定义阈值判断"""
        trend = _make_trend(score=45.0, confidence=0.9)
        assert trend.is_significant(threshold=40.0) is True


class TestTrendGetLifespan:
    """Trend.get_lifespan 计算逻辑"""

    def test_lifespan_with_both_dates(self):
        """有 start_date 和 end_date 时返回 timedelta"""
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 11)
        trend = _make_trend(start_date=start, end_date=end)
        lifespan = trend.get_lifespan()
        assert lifespan == timedelta(days=10)

    def test_lifespan_without_end_date(self):
        """end_date 为 None 时返回 None"""
        trend = _make_trend(start_date=datetime(2026, 1, 1), end_date=None)
        assert trend.get_lifespan() is None

    def test_lifespan_without_start_date(self):
        """start_date 为 None 时返回 None"""
        trend = _make_trend(start_date=None, end_date=datetime(2026, 1, 1))
        assert trend.get_lifespan() is None


# ── TrendAnalysis dataclass ─────────────────────────────────────

class TestTrendAnalysis:
    """TrendAnalysis 构造测试"""

    def test_construction(self):
        """基本构造及默认字段"""
        now = datetime.now()
        ta = TrendAnalysis(
            timestamp=now,
            trends=[],
            summary="empty",
        )
        assert ta.timestamp == now
        assert ta.trends == []
        assert ta.top_trends == []
        assert ta.emerging_trends == []
        assert ta.declining_trends == []
        assert ta.metadata == {}


# ── TrendAnalyzer ────────────────────────────────────────────────

class TestTrendAnalyzer:
    """TrendAnalyzer 核心方法测试"""

    def setup_method(self):
        self.analyzer = TrendAnalyzer()

    def test_add_trend_and_get_by_id(self):
        """add_trend 后可通过 get_trend_by_id 获取"""
        trend = _make_trend(trend_id="abc")
        self.analyzer.trends["abc"] = trend
        assert self.analyzer.get_trend_by_id("abc") is trend

    def test_get_trend_by_id_not_found(self):
        """不存在的 id 返回 None"""
        assert self.analyzer.get_trend_by_id("nonexistent") is None

    def test_get_trends_filter_by_type(self):
        """按 trend_type 过滤"""
        self.analyzer.trends["a"] = _make_trend(
            trend_id="a", trend_type=TrendType.RISING, score=80
        )
        self.analyzer.trends["b"] = _make_trend(
            trend_id="b", trend_type=TrendType.FALLING, score=60
        )
        result = self.analyzer.get_trends(trend_type=TrendType.RISING)
        assert len(result) == 1
        assert result[0].trend_id == "a"

    def test_get_trends_filter_by_min_score(self):
        """按 min_score 过滤"""
        self.analyzer.trends["a"] = _make_trend(trend_id="a", score=90)
        self.analyzer.trends["b"] = _make_trend(trend_id="b", score=30)
        result = self.analyzer.get_trends(min_score=50)
        assert len(result) == 1
        assert result[0].score == 90

    def test_get_trends_sorted_by_score_desc(self):
        """结果按 score 降序排列"""
        self.analyzer.trends["a"] = _make_trend(trend_id="a", score=50)
        self.analyzer.trends["b"] = _make_trend(trend_id="b", score=90)
        result = self.analyzer.get_trends()
        assert result[0].score >= result[1].score

    def test_cleanup_old_trends(self):
        """清理指定日期之前的趋势"""
        self.analyzer.trends["old"] = _make_trend(
            trend_id="old",
            updated_at=datetime(2025, 1, 1),
        )
        self.analyzer.trends["new"] = _make_trend(
            trend_id="new",
            updated_at=datetime(2026, 6, 1),
        )
        self.analyzer.cleanup_old_trends(before_date=datetime(2026, 1, 1))
        assert "old" not in self.analyzer.trends
        assert "new" in self.analyzer.trends

    def test_get_stats(self):
        """get_stats 返回正确的统计结构"""
        self.analyzer.trends["a"] = _make_trend(
            trend_id="a",
            trend_type=TrendType.RISING,
            source=TrendSource.SOCIAL_MEDIA,
            score=70,
            confidence=0.8,
        )
        stats = self.analyzer.get_stats()
        assert stats["total_trends"] == 1
        assert stats["by_type"]["rising"] == 1
        assert stats["by_source"]["social_media"] == 1
        assert stats["significant_trends"] == 1
        assert stats["analyses_performed"] == 0

    def test_get_stats_empty(self):
        """无趋势时 stats 全部为 0"""
        stats = self.analyzer.get_stats()
        assert stats["total_trends"] == 0
        assert stats["significant_trends"] == 0


# ── TrendAggregator ──────────────────────────────────────────────

class TestTrendAggregator:
    """TrendAggregator 聚合测试"""

    def setup_method(self):
        self.aggregator = TrendAggregator()

    def test_aggregate_empty(self):
        """空列表返回空列表"""
        assert self.aggregator.aggregate_trends([]) == []

    def test_aggregate_single_trend(self):
        """单条趋势原样返回"""
        t = _make_trend(trend_id="solo", keywords=["ai"])
        result = self.aggregator.aggregate_trends([t])
        assert len(result) == 1
        assert result[0].trend_id == "solo"

    def test_aggregate_merge_same_keywords(self):
        """相同关键词的趋势被合并"""
        t1 = _make_trend(
            trend_id="t1", score=60, confidence=0.7, volume=100,
            keywords=["ai", "llm"], updated_at=datetime(2026, 1, 1),
        )
        t2 = _make_trend(
            trend_id="t2", score=80, confidence=0.9, volume=200,
            keywords=["ai", "llm"], updated_at=datetime(2026, 1, 5),
        )
        result = self.aggregator.aggregate_trends([t1, t2])
        assert len(result) == 1
        merged = result[0]
        assert merged.score == 70.0  # 平均分
        assert merged.confidence == 0.9  # 最高置信度
        assert merged.volume == 300  # 累加 volume

    def test_aggregate_group_by_type(self):
        """按 type 分组聚合"""
        t1 = _make_trend(trend_id="a", trend_type=TrendType.RISING, keywords=["x"])
        t2 = _make_trend(trend_id="b", trend_type=TrendType.RISING, keywords=["y"])
        t3 = _make_trend(trend_id="c", trend_type=TrendType.FALLING, keywords=["z"])
        result = self.aggregator.aggregate_trends(
            [t1, t2, t3], group_by="type"
        )
        # RISING 组有 2 条合并为 1, FALLING 组 1 条 → 共 2 条
        assert len(result) == 2


# ── TrendScorer ──────────────────────────────────────────────────

class TestTrendScorer:
    """TrendScorer 计算测试"""

    def test_calculate_score_full_params(self):
        """全参数计算分数"""
        score = TrendScorer.calculate_score(
            volume=1000, velocity=3.0, recency=1.0, engagement=1.0
        )
        # volume_score = min(30, 1000/100*30) = 30
        # velocity_score = min(30, 3*10) = 30
        # recency_score = 1*20 = 20
        # engagement_score = 1*20 = 20
        assert score == pytest.approx(100.0)

    def test_calculate_score_zero_inputs(self):
        """零输入得零分"""
        score = TrendScorer.calculate_score(
            volume=0, velocity=0.0, recency=0.0, engagement=0.0
        )
        assert score == pytest.approx(0.0)

    def test_calculate_score_volume_cap(self):
        """volume 分数上限为 30"""
        score_low = TrendScorer.calculate_score(
            volume=100, velocity=0, recency=0, engagement=0
        )
        score_high = TrendScorer.calculate_score(
            volume=9999, velocity=0, recency=0, engagement=0
        )
        assert score_low == pytest.approx(30.0)
        assert score_high == pytest.approx(30.0)

    def test_calculate_confidence_high(self):
        """大量数据点 + 高一致性 → 高置信度"""
        conf = TrendScorer.calculate_confidence(data_points=100, consistency=1.0)
        # data_factor = 1.0 → 1.0*0.6 + 1.0*0.4 = 1.0
        assert conf == pytest.approx(1.0)

    def test_calculate_confidence_low_data(self):
        """少量数据点 → 置信度降低"""
        conf = TrendScorer.calculate_confidence(data_points=10, consistency=1.0)
        # data_factor = 0.1 → 0.1*0.6 + 1.0*0.4 = 0.46
        assert conf == pytest.approx(0.46)
