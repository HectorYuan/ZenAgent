"""
市场趋势分析器 (Market Trend Analyzer)

分析市场数据趋势:
- 价格/量趋势
- 市场份额变化
- 竞争格局变化
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import statistics

from .trend_analyzer import Trend, TrendType, TrendSource

logger = logging.getLogger(__name__)


@dataclass
class MarketDataPoint:
    """市场数据点"""
    timestamp: datetime
    symbol: str  # 市场标的代码
    value: float
    volume: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketMetric:
    """市场指标"""
    name: str
    current: float
    previous: float
    change_pct: float
    trend: TrendType
    volatility: float  # 波动性


class MarketTrendAnalyzer:
    """
    市场趋势分析器
    
    分析市场数据和趋势:
    - 价格趋势识别
    - 波动性分析
    - 市场情绪
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 数据存储
        self.market_data: Dict[str, List[MarketDataPoint]] = {}
        
        # 配置
        self.trend_threshold = self.config.get('trend_threshold', 0.05)  # 5%变化阈值
        self.volatility_window = self.config.get('volatility_window', 20)
    
    def add_data(self, data_point: MarketDataPoint):
        """添加市场数据点"""
        symbol = data_point.symbol
        
        if symbol not in self.market_data:
            self.market_data[symbol] = []
        
        self.market_data[symbol].append(data_point)
        
        # 保持数据量限制
        max_points = self.config.get('max_data_points', 1000)
        if len(self.market_data[symbol]) > max_points:
            self.market_data[symbol] = self.market_data[symbol][-max_points:]
    
    def add_batch_data(self, data_points: List[MarketDataPoint]):
        """批量添加数据"""
        for point in data_points:
            self.add_data(point)
    
    def analyze_symbol(self, symbol: str) -> Optional[Trend]:
        """分析指定标的的趋势"""
        if symbol not in self.market_data or len(self.market_data[symbol]) < 2:
            return None
        
        points = self.market_data[symbol]
        
        # 计算基本统计
        values = [p.value for p in points]
        volumes = [p.volume for p in points if p.volume]
        
        current_value = values[-1]
        first_value = values[0]
        
        # 计算变化
        change = (current_value - first_value) / first_value if first_value != 0 else 0
        change_pct = change * 100
        
        # 确定趋势类型
        trend_type = self._determine_trend(change_pct)
        
        # 计算波动性
        volatility = self._calculate_volatility(values)
        
        # 计算趋势得分
        score = self._calculate_score(change_pct, volatility, len(values))
        
        return Trend(
            trend_id=f"market_{symbol}_{datetime.now().date()}",
            name=f"Market: {symbol}",
            description=f"Market trend for {symbol}: {change_pct:.2f}%",
            trend_type=trend_type,
            source=TrendSource.MARKET,
            score=score,
            confidence=self._calculate_confidence(len(values)),
            volume=sum(volumes) if volumes else len(values),
            keywords=[symbol],
            velocity=change_pct,
            metadata={
                'current': current_value,
                'change_pct': change_pct,
                'volatility': volatility
            }
        )
    
    def analyze_all(self) -> List[Trend]:
        """分析所有市场数据"""
        trends = []
        
        for symbol in self.market_data:
            trend = self.analyze_symbol(symbol)
            if trend:
                trends.append(trend)
        
        return trends
    
    def _determine_trend(self, change_pct: float) -> TrendType:
        """判断趋势类型"""
        threshold = self.trend_threshold * 100  # 转换为百分比
        
        if change_pct > threshold:
            return TrendType.RISING
        elif change_pct < -threshold:
            return TrendType.FALLING
        else:
            return TrendType.STABLE
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """计算波动性(标准差/均值)"""
        if len(values) < 2:
            return 0.0
        
        mean = statistics.mean(values)
        if mean == 0:
            return 0.0
        
        stdev = statistics.stdev(values)
        return (stdev / mean) * 100  # 百分比
    
    def _calculate_score(
        self,
        change_pct: float,
        volatility: float,
        data_points: int
    ) -> float:
        """计算趋势得分"""
        # 变化得分
        change_score = min(50, abs(change_pct) * 2)
        
        # 反波动性得分(低波动=高得分)
        volatility_score = max(0, 30 - volatility * 10)
        
        # 数据量得分
        data_score = min(20, data_points * 0.5)
        
        return change_score + volatility_score + data_score
    
    def _calculate_confidence(self, data_points: int) -> float:
        """计算置信度"""
        if data_points >= 100:
            return 0.9
        elif data_points >= 50:
            return 0.75
        elif data_points >= 20:
            return 0.6
        elif data_points >= 10:
            return 0.4
        return 0.2
    
    def get_metrics(self, symbol: str) -> Optional[List[MarketMetric]]:
        """获取市场指标"""
        if symbol not in self.market_data:
            return None
        
        points = self.market_data[symbol]
        if len(points) < 2:
            return None
        
        # 当前和之前值
        current = points[-1].value
        previous = points[-2].value
        
        # 计算变化
        change_pct = ((current - previous) / previous * 100) if previous != 0 else 0
        
        # 计算波动性
        values = [p.value for p in points[-self.volatility_window:]]
        volatility = self._calculate_volatility(values)
        
        return [
            MarketMetric(
                name=f"{symbol}_price",
                current=current,
                previous=previous,
                change_pct=change_pct,
                trend=self._determine_trend(change_pct),
                volatility=volatility
            )
        ]
    
    def detect_anomalies(
        self,
        symbol: str,
        threshold_std: float = 2.0
    ) -> List[MarketDataPoint]:
        """检测异常数据点"""
        if symbol not in self.market_data:
            return []
        
        points = self.market_data[symbol]
        if len(points) < 10:
            return []
        
        values = [p.value for p in points]
        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        
        anomalies = []
        for point in points:
            z_score = abs((point.value - mean) / stdev) if stdev > 0 else 0
            if z_score > threshold_std:
                anomalies.append(point)
        
        return anomalies
    
    def get_top_movers(self, limit: int = 10) -> List[Trend]:
        """获取涨幅/跌幅最大的标的"""
        trends = self.analyze_all()
        
        # 按涨幅排序
        trends.sort(key=lambda t: t.velocity, reverse=True)
        
        movers = []
        
        # 获取涨幅最大的
        movers.extend(trends[:limit])
        
        # 获取跌幅最大的
        movers.extend(trends[-limit:])
        
        return movers
