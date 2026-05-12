"""
FLY-3 趋势层 - 核心模块
Trend Layer Core Implementation
"""

from .Core.TrendAnalyzer import (
    TrendAnalyzer, TechTrendAnalyzer, MarketTrendAnalyzer,
    Trend, TrendType, TrendDirection
)
from .Core.PredictionEngine import (
    PredictionEngine, TimeSeriesModel, AnomalyDetector,
    PredictionResult
)
from .Core.AdaptiveController import (
    AdaptiveController, StrategyOptimizer, ResourceScaler
)
from .DataSources import (
    ExternalAPICollector, InternalDataCollector, RealTimeMonitor
)
from .Convolv import ConvolvEngine, EmergentPattern

__all__ = [
    "TrendAnalyzer",
    "TechTrendAnalyzer", 
    "MarketTrendAnalyzer",
    "Trend", "TrendType", "TrendDirection",
    "PredictionEngine",
    "TimeSeriesModel", 
    "AnomalyDetector",
    "PredictionResult",
    "AdaptiveController",
    "StrategyOptimizer",
    "ResourceScaler",
    "ExternalAPICollector",
    "InternalDataCollector",
    "RealTimeMonitor",
    "ConvolvEngine",
    "EmergentPattern",
]
