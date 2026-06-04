"""PredictionEngine 单元测试"""

from datetime import datetime, timedelta
import pytest

from packages.SwarmFly.fly3trends.Core.PredictionEngine.prediction_engine import (
    Prediction,
    PredictionEngine,
    PredictionHorizon,
    PredictionModel,
    TimeSeriesPoint,
)


# ---------------------------------------------------------------------------
# 辅助工具
# ---------------------------------------------------------------------------

def _make_series(values, start=None):
    """从纯数值列表构造 TimeSeriesPoint 序列（每天一个点）。"""
    start = start or datetime(2025, 1, 1)
    return [
        TimeSeriesPoint(timestamp=start + timedelta(days=i), value=v)
        for i, v in enumerate(values)
    ]


LINEAR_VALUES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]


# ===========================================================================
# Prediction dataclass
# ===========================================================================

class TestPredictionDataclass:
    """Prediction 数据类测试"""

    def test_construct_with_all_fields(self):
        """构造 Prediction 并验证所有字段"""
        now = datetime.now()
        p = Prediction(
            metric_name="cpu",
            predicted_value=75.0,
            horizon=PredictionHorizon.SHORT,
            confidence=0.9,
            lower_bound=70.0,
            upper_bound=80.0,
            model=PredictionModel.LINEAR,
            accuracy=0.85,
            prediction_time=now,
            forecast_until=now + timedelta(days=7),
            trend_direction="rising",
            metadata={"key": "val"},
        )
        assert p.metric_name == "cpu"
        assert p.predicted_value == 75.0
        assert p.horizon == PredictionHorizon.SHORT
        assert p.confidence == 0.9
        assert p.lower_bound == 70.0
        assert p.upper_bound == 80.0
        assert p.model == PredictionModel.LINEAR
        assert p.accuracy == 0.85
        assert p.prediction_time is now
        assert p.trend_direction == "rising"
        assert p.metadata == {"key": "val"}

    def test_defaults(self):
        """验证 Prediction 的默认字段值"""
        p = Prediction(
            metric_name="m",
            predicted_value=1.0,
            horizon=PredictionHorizon.MEDIUM,
            confidence=0.5,
            lower_bound=0.0,
            upper_bound=2.0,
            model=PredictionModel.SIMPLE_TREND,
            accuracy=0.7,
        )
        assert p.prediction_time is not None
        assert p.forecast_until is None
        assert p.trend_direction == "stable"
        assert p.metadata == {}


# ===========================================================================
# TimeSeriesPoint
# ===========================================================================

class TestTimeSeriesPoint:
    """TimeSeriesPoint 数据类测试"""

    def test_construct(self):
        """构造并验证字段"""
        ts = datetime(2025, 6, 1, 12, 0)
        pt = TimeSeriesPoint(timestamp=ts, value=42.5)
        assert pt.timestamp == ts
        assert pt.value == 42.5
        assert pt.metadata == {}

    def test_construct_with_metadata(self):
        """带 metadata 构造"""
        pt = TimeSeriesPoint(
            timestamp=datetime(2025, 1, 1),
            value=10,
            metadata={"source": "sensor"},
        )
        assert pt.metadata["source"] == "sensor"


# ===========================================================================
# PredictionEngine — predict 各模型
# ===========================================================================

class TestPredictLinear:
    """线性回归预测"""

    def setup_method(self):
        self.engine = PredictionEngine({"min_data_points": 5})

    def test_linear_returns_prediction(self):
        """LINEAR 模型返回 Prediction 对象"""
        result = self.engine.predict(
            "cpu", _make_series(LINEAR_VALUES), model=PredictionModel.LINEAR
        )
        assert isinstance(result, Prediction)
        assert result.model == PredictionModel.LINEAR

    def test_linear_confidence_bounds(self):
        """LINEAR 置信区间 lower < predicted < upper"""
        result = self.engine.predict(
            "cpu", _make_series(LINEAR_VALUES), model=PredictionModel.LINEAR
        )
        assert result.lower_bound <= result.predicted_value <= result.upper_bound


class TestPredictExponential:
    """指数平滑预测"""

    def setup_method(self):
        self.engine = PredictionEngine({"min_data_points": 5})

    def test_exponential_returns_prediction(self):
        """EXPONENTIAL 模型返回 Prediction"""
        result = self.engine.predict(
            "mem", _make_series(LINEAR_VALUES), model=PredictionModel.EXPONENTIAL
        )
        assert isinstance(result, Prediction)
        assert result.model == PredictionModel.EXPONENTIAL

    def test_exponential_predicted_near_last(self):
        """指数平滑的预测值应接近最后几个值的平滑结果"""
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        result = self.engine.predict(
            "mem", _make_series(values), model=PredictionModel.EXPONENTIAL
        )
        # 最后平滑值应小于最后一个原始值（因为有平滑效果）
        assert result.predicted_value <= values[-1]


class TestPredictMovingAverage:
    """移动平均预测"""

    def setup_method(self):
        self.engine = PredictionEngine({"min_data_points": 5})

    def test_moving_average_returns_prediction(self):
        """MOVING_AVERAGE 模型返回 Prediction"""
        result = self.engine.predict(
            "disk", _make_series(LINEAR_VALUES), model=PredictionModel.MOVING_AVERAGE
        )
        assert isinstance(result, Prediction)
        assert result.model == PredictionModel.MOVING_AVERAGE

    def test_moving_average_equals_mean_of_window(self):
        """移动平均预测值应等于最后 window 个值的均值"""
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        result = self.engine.predict(
            "disk", _make_series(values), model=PredictionModel.MOVING_AVERAGE
        )
        expected = sum(values[-7:]) / 7
        assert abs(result.predicted_value - expected) < 1e-9


class TestPredictWeightedMovingAverage:
    """加权移动平均预测"""

    def setup_method(self):
        self.engine = PredictionEngine({"min_data_points": 5})

    def test_wma_returns_prediction(self):
        """WEIGHTED_MOVING_AVERAGE 模型返回 Prediction"""
        result = self.engine.predict(
            "net", _make_series(LINEAR_VALUES),
            model=PredictionModel.WEIGHTED_MOVING_AVERAGE,
        )
        assert isinstance(result, Prediction)
        assert result.model == PredictionModel.WEIGHTED_MOVING_AVERAGE

    def test_wma_value_manual_calc(self):
        """手动计算加权移动平均并与引擎结果对比"""
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        result = self.engine.predict(
            "net", _make_series(values),
            model=PredictionModel.WEIGHTED_MOVING_AVERAGE,
        )
        recent = values[-7:]
        weights = list(range(1, 8))
        expected = sum(w * v for w, v in zip(weights, recent)) / sum(weights)
        assert abs(result.predicted_value - expected) < 1e-9


class TestPredictSimpleTrend:
    """简单趋势预测"""

    def setup_method(self):
        self.engine = PredictionEngine({"min_data_points": 5})

    def test_simple_trend_returns_prediction(self):
        """SIMPLE_TREND 模型返回 Prediction"""
        result = self.engine.predict(
            "latency", _make_series(LINEAR_VALUES),
            model=PredictionModel.SIMPLE_TREND,
        )
        assert isinstance(result, Prediction)
        assert result.model == PredictionModel.SIMPLE_TREND

    def test_simple_trend_manual_calc(self):
        """手动计算简单趋势并与引擎结果对比"""
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        result = self.engine.predict(
            "latency", _make_series(values),
            horizon=PredictionHorizon.SHORT,
            model=PredictionModel.SIMPLE_TREND,
        )
        avg_change = sum(values[i] - values[i - 1] for i in range(1, len(values))) / (
            len(values) - 1
        )
        expected = values[-1] + avg_change * 7  # SHORT = 7 天
        assert abs(result.predicted_value - expected) < 1e-9


# ===========================================================================
# PredictionEngine — batch_predict / record_accuracy / get_model_stats
# ===========================================================================

class TestBatchPredict:
    """批量预测测试"""

    def setup_method(self):
        self.engine = PredictionEngine({"min_data_points": 5})

    def test_batch_returns_dict(self):
        """batch_predict 返回以 metric_name 为 key 的字典"""
        series = {
            "cpu": _make_series(LINEAR_VALUES),
            "mem": _make_series([5, 15, 25, 35, 45, 55, 65, 75, 85, 95]),
        }
        results = self.engine.batch_predict(series)
        assert isinstance(results, dict)
        assert "cpu" in results
        assert "mem" in results
        assert all(isinstance(v, Prediction) for v in results.values())

    def test_batch_skips_insufficient_data(self):
        """数据点不足时，batch_predict 静默跳过而不抛异常"""
        series = {
            "ok": _make_series(LINEAR_VALUES),
            "too_short": _make_series([1, 2]),
        }
        results = self.engine.batch_predict(series)
        assert "ok" in results
        assert "too_short" not in results


class TestRecordAccuracy:
    """预测准确度记录测试"""

    def setup_method(self):
        self.engine = PredictionEngine({"min_data_points": 5})

    def test_record_and_retrieve(self):
        """record_accuracy 后 _get_accuracy 返回更新值"""
        self.engine.record_accuracy("cpu", PredictionModel.LINEAR, 100.0, 95.0)
        acc = self.engine._get_accuracy("cpu", PredictionModel.LINEAR)
        # 1 - |100-95|/|95| ≈ 0.947
        assert 0.9 < acc < 1.0

    def test_record_with_zero_actual_skipped(self):
        """actual=0 时不记录，保持默认值"""
        self.engine.record_accuracy("m", PredictionModel.LINEAR, 100.0, 0.0)
        acc = self.engine._get_accuracy("m", PredictionModel.LINEAR)
        assert acc == 0.7  # 默认

    def test_history_capped_at_100(self):
        """历史记录上限 100"""
        for _ in range(110):
            self.engine.record_accuracy("x", PredictionModel.LINEAR, 100.0, 100.0)
        key = "x_linear"
        assert len(self.engine.prediction_accuracy[key]) == 100


class TestGetModelStats:
    """模型统计辅助测试"""

    def setup_method(self):
        self.engine = PredictionEngine({"min_data_points": 5})

    def test_default_accuracy_when_no_history(self):
        """无历史记录时返回默认准确度 0.7"""
        acc = self.engine._get_accuracy("new_metric", PredictionModel.LINEAR)
        assert acc == 0.7

    def test_accuracy_is_mean_of_recent_history(self):
        """准确度为最近记录的均值"""
        self.engine.prediction_accuracy["q_moving_average"] = [0.8, 0.9, 0.7]
        acc = self.engine._get_accuracy("q", PredictionModel.MOVING_AVERAGE)
        expected = (0.8 + 0.9 + 0.7) / 3
        assert abs(acc - expected) < 1e-9
