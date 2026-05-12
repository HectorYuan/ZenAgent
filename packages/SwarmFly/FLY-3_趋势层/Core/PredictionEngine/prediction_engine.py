"""
预测引擎 (Prediction Engine)

提供趋势预测能力:
- 时序预测
- 趋势外推
- 置信区间
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import statistics

logger = logging.getLogger(__name__)


class PredictionModel(Enum):
    """预测模型"""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    MOVING_AVERAGE = "moving_average"
    WEIGHTED_MOVING_AVERAGE = "weighted_moving_average"
    SIMPLE_TREND = "simple_trend"


class PredictionHorizon(Enum):
    """预测周期"""
    SHORT = "short"    # 1-7天
    MEDIUM = "medium"  # 7-30天
    LONG = "long"      # 30-90天


@dataclass
class Prediction:
    """预测结果"""
    metric_name: str
    predicted_value: float
    horizon: PredictionHorizon
    confidence: float  # 0-1
    lower_bound: float
    upper_bound: float
    model: PredictionModel
    accuracy: float  # 历史准确度 0-1
    prediction_time: datetime = field(default_factory=datetime.now)
    forecast_until: Optional[datetime] = None
    trend_direction: str = "stable"  # rising, falling, stable
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeSeriesPoint:
    """时间序列点"""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class PredictionEngine:
    """
    预测引擎
    
    提供多种预测模型:
    - 线性回归
    - 指数平滑
    - 移动平均
    - 简单趋势
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 默认模型
        self.default_model = PredictionModel(
            self.config.get('default_model', 'simple_trend')
        )
        
        # 预测配置
        self.confidence_level = self.config.get('confidence_level', 0.95)
        self.min_data_points = self.config.get('min_data_points', 10)
        self.max_forecast_days = self.config.get('max_forecast_days', 90)
        
        # 历史预测准确性
        self.prediction_accuracy: Dict[str, List[float]] = {}
    
    def predict(
        self,
        metric_name: str,
        data_points: List[TimeSeriesPoint],
        horizon: PredictionHorizon = PredictionHorizon.SHORT,
        model: Optional[PredictionModel] = None
    ) -> Prediction:
        """
        预测
        
        Args:
            metric_name: 指标名称
            data_points: 历史数据点
            horizon: 预测周期
            model: 预测模型
            
        Returns:
            Prediction: 预测结果
        """
        if len(data_points) < self.min_data_points:
            raise ValueError(
                f"Insufficient data points for metric '{metric_name}': "
                f"{len(data_points)} < {self.min_data_points}. "
                f"Please provide at least {self.min_data_points} historical data points "
                f"for accurate prediction. For {horizon.value} horizon forecasting, "
                f"a minimum of {self.min_data_points} data points is recommended."
            )
        
        model = model or self.default_model
        
        # 排序数据
        sorted_data = sorted(data_points, key=lambda p: p.timestamp)
        values = [p.value for p in sorted_data]
        timestamps = [p.timestamp for p in sorted_data]
        
        # 根据周期确定预测天数
        days_map = {
            PredictionHorizon.SHORT: 7,
            PredictionHorizon.MEDIUM: 30,
            PredictionHorizon.LONG: 90
        }
        forecast_days = min(days_map[horizon], self.max_forecast_days)
        
        # 执行预测
        if model == PredictionModel.LINEAR:
            predicted, bounds = self._linear_regression(values, forecast_days)
        elif model == PredictionModel.EXPONENTIAL:
            predicted, bounds = self._exponential_smoothing(values, forecast_days)
        elif model == PredictionModel.MOVING_AVERAGE:
            predicted, bounds = self._moving_average(values, forecast_days)
        elif model == PredictionModel.WEIGHTED_MOVING_AVERAGE:
            predicted, bounds = self._weighted_moving_average(values, forecast_days)
        else:
            predicted, bounds = self._simple_trend(values, forecast_days)
        
        # 计算置信度
        confidence = self._calculate_confidence(len(values), model)
        
        # 确定趋势方向
        trend = self._determine_trend(values, predicted)
        
        # 获取历史准确度
        accuracy = self._get_accuracy(metric_name, model)
        
        forecast_until = timestamps[-1] + timedelta(days=forecast_days)
        
        return Prediction(
            metric_name=metric_name,
            predicted_value=predicted,
            horizon=horizon,
            confidence=confidence,
            lower_bound=bounds[0],
            upper_bound=bounds[1],
            model=model,
            accuracy=accuracy,
            forecast_until=forecast_until,
            trend_direction=trend,
            metadata={
                'data_points': len(values),
                'forecast_days': forecast_days
            }
        )
    
    def _linear_regression(
        self,
        values: List[float],
        forecast_days: int
    ) -> Tuple[float, Tuple[float, float]]:
        """线性回归预测"""
        n = len(values)
        
        # 计算均值
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(values)
        
        # 计算斜率和截距
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        intercept = y_mean - slope * x_mean
        
        # 预测
        predicted = slope * (n - 1 + forecast_days) + intercept
        
        # 计算置信区间
        residuals = [
            values[i] - (slope * i + intercept)
            for i in range(n)
        ]
        std_err = statistics.stdev(residuals) if len(residuals) > 1 else 0
        
        margin = std_err * 1.96  # 95%置信区间
        
        return predicted, (predicted - margin, predicted + margin)
    
    def _exponential_smoothing(
        self,
        values: List[float],
        forecast_days: int
    ) -> Tuple[float, Tuple[float, float]]:
        """指数平滑预测"""
        alpha = 0.3  # 平滑系数
        
        # 计算平滑值
        smoothed = [values[0]]
        for i in range(1, len(values)):
            smoothed.append(alpha * values[i] + (1 - alpha) * smoothed[-1])
        
        # 使用最后一个平滑值作为预测
        predicted = smoothed[-1]
        
        # 计算置信区间
        std_dev = statistics.stdev(values)
        margin = std_dev * 1.96 * (1 + alpha * forecast_days / len(values))
        
        return predicted, (predicted - margin, predicted + margin)
    
    def _moving_average(
        self,
        values: List[float],
        forecast_days: int
    ) -> Tuple[float, Tuple[float, float]]:
        """移动平均预测"""
        window = min(7, len(values))
        
        # 使用最后window个值的平均
        recent = values[-window:]
        predicted = statistics.mean(recent)
        
        # 置信区间
        std_dev = statistics.stdev(recent)
        margin = std_dev * 1.96
        
        return predicted, (predicted - margin, predicted + margin)
    
    def _weighted_moving_average(
        self,
        values: List[float],
        forecast_days: int
    ) -> Tuple[float, Tuple[float, float]]:
        """加权移动平均预测"""
        window = min(7, len(values))
        recent = values[-window:]
        
        # 线性权重(越近权重越大)
        weights = list(range(1, window + 1))
        weight_sum = sum(weights)
        
        predicted = sum(w * v for w, v in zip(weights, recent)) / weight_sum
        
        # 置信区间
        std_dev = statistics.stdev(recent)
        margin = std_dev * 1.96
        
        return predicted, (predicted - margin, predicted + margin)
    
    def _simple_trend(
        self,
        values: List[float],
        forecast_days: int
    ) -> Tuple[float, Tuple[float, float]]:
        """简单趋势预测"""
        n = len(values)
        
        # 计算平均变化
        changes = [values[i] - values[i-1] for i in range(1, n)]
        avg_change = statistics.mean(changes) if changes else 0
        
        # 预测 = 最后一个值 + 平均变化 * 预测天数
        predicted = values[-1] + avg_change * forecast_days
        
        # 置信区间
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        margin = std_dev * 1.96 * (1 + forecast_days / n)
        
        return predicted, (predicted - margin, predicted + margin)
    
    def _calculate_confidence(
        self,
        data_points: int,
        model: PredictionModel
    ) -> float:
        """计算置信度"""
        base_confidence = min(0.95, data_points / 100 + 0.3)
        
        # 模型调整
        model_adjustments = {
            PredictionModel.LINEAR: 0.95,
            PredictionModel.EXPONENTIAL: 0.90,
            PredictionModel.MOVING_AVERAGE: 0.85,
            PredictionModel.WEIGHTED_MOVING_AVERAGE: 0.88,
            PredictionModel.SIMPLE_TREND: 0.80
        }
        
        return base_confidence * model_adjustments.get(model, 0.85)
    
    def _determine_trend(
        self,
        historical: List[float],
        predicted: float
    ) -> str:
        """确定趋势方向"""
        recent_avg = statistics.mean(historical[-5:])
        
        change_pct = (predicted - recent_avg) / recent_avg * 100 if recent_avg != 0 else 0
        
        if change_pct > 5:
            return "rising"
        elif change_pct < -5:
            return "falling"
        return "stable"
    
    def _get_accuracy(
        self,
        metric_name: str,
        model: PredictionModel
    ) -> float:
        """获取历史预测准确度"""
        key = f"{metric_name}_{model.value}"
        history = self.prediction_accuracy.get(key, [])
        
        if not history:
            return 0.7  # 默认准确度
        
        return statistics.mean(history[-10:])  # 最近10次的平均
    
    def record_accuracy(
        self,
        metric_name: str,
        model: PredictionModel,
        predicted: float,
        actual: float
    ):
        """记录预测准确度"""
        key = f"{metric_name}_{model.value}"
        
        if key not in self.prediction_accuracy:
            self.prediction_accuracy[key] = []
        
        # 计算准确度(预测误差百分比)
        if actual != 0:
            accuracy = 1 - abs(predicted - actual) / abs(actual)
            accuracy = max(0, min(1, accuracy))  # 限制在0-1
            self.prediction_accuracy[key].append(accuracy)
        
        # 保持历史记录数量
        if len(self.prediction_accuracy[key]) > 100:
            self.prediction_accuracy[key] = self.prediction_accuracy[key][-100:]
    
    def batch_predict(
        self,
        series: Dict[str, List[TimeSeriesPoint]],
        horizon: PredictionHorizon = PredictionHorizon.SHORT
    ) -> Dict[str, Prediction]:
        """批量预测"""
        results = {}
        
        for metric_name, data_points in series.items():
            try:
                prediction = self.predict(metric_name, data_points, horizon)
                results[metric_name] = prediction
            except Exception as e:
                logger.error(f"Prediction failed for {metric_name}: {e}")
        
        return results
