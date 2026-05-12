"""
趋势分析器核心 (Trend Analyzer)

提供趋势识别的通用框架:
- 趋势数据模型
- 趋势聚合
- 趋势评分
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TrendType(Enum):
    """趋势类型"""
    RISING = "rising"          # 上升趋势
    FALLING = "falling"        # 下降趋势
    STABLE = "stable"         # 稳定趋势
    VOLATILE = "volatile"     # 波动趋势
    EMERGING = "emerging"     # 新兴趋势
    DECLINING = "declining"    # 衰退趋势


class TrendSource(Enum):
    """趋势来源"""
    SOCIAL_MEDIA = "social_media"
    NEWS = "news"
    TECHNICAL = "technical"
    MARKET = "market"
    INTERNAL = "internal"
    EXTERNAL_API = "external_api"


@dataclass
class Trend:
    """趋势对象"""
    trend_id: str
    name: str
    description: str
    trend_type: TrendType
    source: TrendSource
    score: float  # 0-100
    confidence: float  # 0-1
    volume: int  # 相关事件/讨论数量
    keywords: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)  # 相关实体
    start_date: Optional[datetime] = None
    peak_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    velocity: float = 0.0  # 变化速度
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def is_significant(self, threshold: float = 60.0) -> bool:
        """判断趋势是否显著"""
        return self.score >= threshold and self.confidence >= 0.6
    
    def get_lifespan(self) -> Optional[timedelta]:
        """获取趋势持续时间"""
        if self.start_date and self.end_date:
            return self.end_date - self.start_date
        return None


@dataclass
class TrendAnalysis:
    """趋势分析结果"""
    timestamp: datetime
    trends: List[Trend]
    summary: str
    top_trends: List[Trend] = field(default_factory=list)
    emerging_trends: List[Trend] = field(default_factory=list)
    declining_trends: List[Trend] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TrendAggregator:
    """趋势聚合器"""
    
    def __init__(self):
        self.weights = {
            'score': 0.4,
            'volume': 0.2,
            'velocity': 0.2,
            'confidence': 0.2
        }
    
    def aggregate_trends(
        self,
        trends: List[Trend],
        group_by: Optional[str] = None
    ) -> List[Trend]:
        """聚合相似趋势"""
        if not trends:
            return []
        
        # 按关键词或类型分组
        groups: Dict[str, List[Trend]] = {}
        
        for trend in trends:
            if group_by == 'type':
                key = trend.trend_type.value
            elif group_by == 'source':
                key = trend.source.value
            else:
                # 按关键词匹配
                key = ','.join(sorted(trend.keywords[:3]))
            
            if key not in groups:
                groups[key] = []
            groups[key].append(trend)
        
        # 聚合每组
        aggregated = []
        for group_trends in groups.values():
            if len(group_trends) > 1:
                agg = self._merge_trends(group_trends)
                aggregated.append(agg)
            else:
                aggregated.extend(group_trends)
        
        return aggregated
    
    def _merge_trends(self, trends: List[Trend]) -> Trend:
        """合并多个相似趋势"""
        # 取平均分
        avg_score = sum(t.score for t in trends) / len(trends)
        
        # 取最高置信度
        best_confidence = max(t.confidence for t in trends)
        
        # 合并关键词
        keywords = set()
        for t in trends:
            keywords.update(t.keywords)
        
        # 取最新的
        latest = max(trends, key=lambda t: t.updated_at)
        
        return Trend(
            trend_id=f"merged_{latest.trend_id}",
            name=latest.name,
            description=f"Merged from {len(trends)} trends",
            trend_type=latest.trend_type,
            source=latest.source,
            score=avg_score,
            confidence=best_confidence,
            volume=sum(t.volume for t in trends),
            keywords=list(keywords),
            metadata={'merged_from': len(trends)}
        )


class TrendScorer:
    """趋势评分器"""
    
    @staticmethod
    def calculate_score(
        volume: int,
        velocity: float,
        recency: float,  # 0-1, 越接近1越新
        engagement: float  # 0-1
    ) -> float:
        """计算趋势得分"""
        # 基础分数
        volume_score = min(30, volume / 100 * 30)  # 最多30分
        velocity_score = min(30, max(0, velocity) * 10)  # 最多30分
        recency_score = recency * 20  # 最多20分
        engagement_score = engagement * 20  # 最多20分
        
        return volume_score + velocity_score + recency_score + engagement_score
    
    @staticmethod
    def calculate_confidence(
        data_points: int,
        consistency: float  # 0-1
    ) -> float:
        """计算置信度"""
        data_factor = min(1.0, data_points / 100)
        return (data_factor * 0.6 + consistency * 0.4)


class TrendAnalyzer:
    """
    趋势分析器
    
    核心功能:
    - 趋势数据收集
    - 趋势识别
    - 趋势评分
    - 趋势聚合
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 子分析器
        self.analyzers: Dict[str, Any] = {}
        
        # 趋势存储
        self.trends: Dict[str, Trend] = {}
        self.trend_history: List[TrendAnalysis] = []
        
        # 组件
        self.aggregator = TrendAggregator()
        self.scorer = TrendScorer()
        
        # 配置
        self.significance_threshold = self.config.get('significance_threshold', 60.0)
        self.max_trends = self.config.get('max_trends', 100)
        self.retention_days = self.config.get('retention_days', 30)
    
    def add_analyzer(self, name: str, analyzer: Any):
        """添加子分析器"""
        self.analyzers[name] = analyzer
    
    def analyze(
        self,
        data: List[Dict[str, Any]],
        sources: Optional[List[TrendSource]] = None
    ) -> TrendAnalysis:
        """
        分析趋势
        
        Args:
            data: 原始数据
            sources: 数据来源
            
        Returns:
            TrendAnalysis: 分析结果
        """
        trends = []
        
        # 使用子分析器处理
        for name, analyzer in self.analyzers.items():
            try:
                if hasattr(analyzer, 'analyze'):
                    analyzer_trends = analyzer.analyze(data)
                    trends.extend(analyzer_trends)
            except Exception as e:
                logger.error(f"Analyzer {name} failed: {e}")
        
        # 过滤
        if sources:
            trends = [t for t in trends if t.source in sources]
        
        # 聚合相似趋势
        trends = self.aggregator.aggregate_trends(trends)
        
        # 排序并限制
        trends.sort(key=lambda t: t.score, reverse=True)
        trends = trends[:self.max_trends]
        
        # 更新存储
        for trend in trends:
            self.trends[trend.trend_id] = trend
        
        # 生成分析结果
        result = TrendAnalysis(
            timestamp=datetime.now(),
            trends=trends,
            summary=self._generate_summary(trends),
            top_trends=trends[:10],
            emerging_trends=[t for t in trends if t.trend_type == TrendType.EMERGING],
            declining_trends=[t for t in trends if t.trend_type == TrendType.DECLINING]
        )
        
        self.trend_history.append(result)
        
        return result
    
    def get_trends(
        self,
        trend_type: Optional[TrendType] = None,
        source: Optional[TrendSource] = None,
        min_score: float = 0.0,
        limit: int = 50
    ) -> List[Trend]:
        """获取趋势列表"""
        filtered = []
        
        for trend in self.trends.values():
            if trend_type and trend.trend_type != trend_type:
                continue
            if source and trend.source != source:
                continue
            if trend.score < min_score:
                continue
            filtered.append(trend)
        
        filtered.sort(key=lambda t: t.score, reverse=True)
        return filtered[:limit]
    
    def get_trend_by_id(self, trend_id: str) -> Optional[Trend]:
        """获取指定趋势"""
        return self.trends.get(trend_id)
    
    def _generate_summary(self, trends: List[Trend]) -> str:
        """生成趋势摘要"""
        if not trends:
            return "No significant trends detected."
        
        significant = [t for t in trends if t.is_significant(self.significance_threshold)]
        
        if not significant:
            return "Trends are below significance threshold."
        
        rising = [t for t in significant if t.trend_type == TrendType.RISING]
        emerging = [t for t in significant if t.trend_type == TrendType.EMERGING]
        
        parts = []
        if rising:
            parts.append(f"{len(rising)} rising trend(s)")
        if emerging:
            parts.append(f"{len(emerging)} emerging trend(s)")
        
        return f"Analysis of {len(significant)} significant trends: {', '.join(parts)}"
    
    def cleanup_old_trends(self, before_date: datetime):
        """清理过期趋势"""
        to_remove = []
        
        for trend_id, trend in self.trends.items():
            if trend.updated_at < before_date:
                to_remove.append(trend_id)
        
        for trend_id in to_remove:
            del self.trends[trend_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old trends")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_trends': len(self.trends),
            'by_type': {
                t.value: sum(1 for tr in self.trends.values() if tr.trend_type == t)
                for t in TrendType
            },
            'by_source': {
                s.value: sum(1 for tr in self.trends.values() if tr.source == s)
                for s in TrendSource
            },
            'analyses_performed': len(self.trend_history),
            'significant_trends': sum(
                1 for t in self.trends.values()
                if t.is_significant(self.significance_threshold)
            )
        }
