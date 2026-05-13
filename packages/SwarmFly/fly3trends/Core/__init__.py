"""
SwarmFly FLY-3 势·趋势层 - 核心模块

实现SwarmFly智能体系统的趋势层核心功能:
- 趋势分析引擎
- 预测引擎
- 自适应控制器
- Convolv对接
"""

from .TrendAnalyzer import (
    TrendAnalyzer,
    TechTrendAnalyzer,
    MarketTrendAnalyzer,
    BehaviorAnalyzer
)
from .PredictionEngine import (
    PredictionEngine,
    TimeSeriesModel,
    AnomalyDetector
)
from .AdaptiveController import (
    AdaptiveController,
    StrategyOptimizer,
    ResourceScaler
)

__all__ = [
    'TrendAnalyzer',
    'TechTrendAnalyzer',
    'MarketTrendAnalyzer',
    'BehaviorAnalyzer',
    'PredictionEngine',
    'TimeSeriesModel',
    'AnomalyDetector',
    'AdaptiveController',
    'StrategyOptimizer',
    'ResourceScaler'
]
