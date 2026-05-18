"""
行为趋势分析器 (Behavior Analyzer)

分析用户/智能体行为趋势:
- 使用模式
- 性能趋势
- 交互模式
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from .trend_analyzer import Trend, TrendType, TrendSource

logger = logging.getLogger(__name__)


@dataclass
class BehaviorEvent:
    """行为事件"""
    event_id: str
    agent_id: str
    event_type: str
    timestamp: datetime
    duration: Optional[float] = None  # 毫秒
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BehaviorPattern:
    """行为模式"""
    pattern_id: str
    agent_id: str
    pattern_type: str  # usage, performance, interaction
    frequency: float  # 每小时频率
    regularity: float  # 规律性 0-1
    description: str = ""


class BehaviorAnalyzer:
    """
    行为趋势分析器
    
    分析用户和智能体行为:
    - 使用模式
    - 性能趋势
    - 交互规律
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 事件存储
        self.events: List[BehaviorEvent] = []
        
        # 按智能体索引
        self.events_by_agent: Dict[str, List[BehaviorEvent]] = defaultdict(list)
        
        # 行为模式
        self.patterns: Dict[str, BehaviorPattern] = {}
        
        # 配置
        self.window_hours = self.config.get('window_hours', 24)
        self.min_events = self.config.get('min_events', 10)
    
    def record_event(self, event: BehaviorEvent):
        """记录行为事件"""
        self.events.append(event)
        self.events_by_agent[event.agent_id].append(event)
        
        # 保持大小限制
        max_events = self.config.get('max_events', 10000)
        if len(self.events) > max_events:
            self.events = self.events[-max_events:]
    
    def analyze_agent_behavior(self, agent_id: str) -> List[BehaviorPattern]:
        """分析智能体行为模式"""
        if agent_id not in self.events_by_agent:
            return []
        
        events = self.events_by_agent[agent_id]
        if len(events) < self.min_events:
            return []
        
        patterns = []
        
        # 分析事件类型分布
        type_distribution = defaultdict(int)
        for event in events:
            type_distribution[event.type] += 1
        
        # 生成使用模式
        for event_type, count in type_distribution.items():
            pattern = BehaviorPattern(
                pattern_id=f"pattern_{agent_id}_{event_type}",
                agent_id=agent_id,
                pattern_type="usage",
                frequency=count / self.window_hours,
                regularity=self._calculate_regularity(events, event_type),
                description=f"{event_type}: {count} events in {self.window_hours}h"
            )
            patterns.append(pattern)
            self.patterns[pattern.pattern_id] = pattern
        
        # 分析性能趋势
        durations = [e.duration for e in events if e.duration]
        if durations:
            performance_pattern = self._analyze_performance(agent_id, events)
            if performance_pattern:
                patterns.append(performance_pattern)
        
        return patterns
    
    def _calculate_regularity(self, events: List[BehaviorEvent], event_type: str) -> float:
        """计算规律性"""
        filtered = [e for e in events if e.event_type == event_type]
        if len(filtered) < 2:
            return 0.0
        
        # 计算时间间隔
        sorted_events = sorted(filtered, key=lambda e: e.timestamp)
        intervals = []
        
        for i in range(1, len(sorted_events)):
            delta = (sorted_events[i].timestamp - sorted_events[i-1].timestamp).total_seconds() / 3600
            intervals.append(delta)
        
        if not intervals:
            return 0.0
        
        # 标准差/均值作为规律性(越小越规律)
        mean_interval = statistics.mean(intervals)
        if mean_interval == 0:
            return 0.0
        
        stdev = statistics.stdev(intervals) if len(intervals) > 1 else 0
        cv = stdev / mean_interval  # 变异系数
        
        # 转换为规律性得分(1 - min(cv, 1))
        return max(0, 1 - min(cv, 1))
    
    def _analyze_performance(
        self,
        agent_id: str,
        events: List[BehaviorEvent]
    ) -> Optional[BehaviorPattern]:
        """分析性能趋势"""
        # 按时间窗口分组
        hourly_events: Dict[int, List[BehaviorEvent]] = defaultdict(list)
        
        for event in events:
            if event.duration:
                hour = event.timestamp.hour
                hourly_events[hour].append(event)
        
        if not hourly_events:
            return None
        
        # 计算每小时平均持续时间
        hourly_avg = {}
        for hour, hour_events in hourly_events.items():
            durations = [e.duration for e in hour_events if e.duration]
            if durations:
                hourly_avg[hour] = statistics.mean(durations)
        
        # 计算性能变化趋势
        sorted_hours = sorted(hourly_avg.keys())
        if len(sorted_hours) < 2:
            return None
        
        first_avg = hourly_avg[sorted_hours[0]]
        last_avg = hourly_avg[sorted_hours[-1]]
        
        change_pct = ((last_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0
        
        trend = "stable"
        if change_pct < -10:
            trend = "improving"  # 性能提升(时间减少)
        elif change_pct > 10:
            trend = "degrading"  # 性能下降
        
        return BehaviorPattern(
            pattern_id=f"performance_{agent_id}",
            agent_id=agent_id,
            pattern_type="performance",
            frequency=len(events) / self.window_hours,
            regularity=0.5,  # 简化
            description=f"Performance trend: {trend} ({change_pct:.1f}%)"
        )
    
    def analyze_all_agents(self) -> Dict[str, List[BehaviorPattern]]:
        """分析所有智能体行为"""
        results = {}
        
        for agent_id in self.events_by_agent:
            patterns = self.analyze_agent_behavior(agent_id)
            if patterns:
                results[agent_id] = patterns
        
        return results
    
    def detect_anomalous_behavior(
        self,
        agent_id: str,
        threshold: float = 2.0
    ) -> List[BehaviorEvent]:
        """检测异常行为"""
        if agent_id not in self.events_by_agent:
            return []
        
        events = self.events_by_agent[agent_id]
        if len(events) < 10:
            return []
        
        # 基于持续时间检测异常
        durations = [e.duration for e in events if e.duration]
        if len(durations) < 5:
            return []
        
        mean_duration = statistics.mean(durations)
        stdev_duration = statistics.stdev(durations)
        
        anomalies = []
        for event in events:
            if event.duration:
                z_score = abs((event.duration - mean_duration) / stdev_duration) if stdev_duration > 0 else 0
                if z_score > threshold:
                    anomalies.append(event)
        
        return anomalies
    
    def get_usage_trends(self) -> List[Trend]:
        """获取使用趋势"""
        trends = []
        
        # 按小时聚合事件数量
        hourly_counts: Dict[int, int] = defaultdict(int)
        
        for event in self.events:
            hour = event.timestamp.hour
            hourly_counts[hour] += 1
        
        # 生成趋势
        peak_hour = max(hourly_counts.items(), key=lambda x: x[1])
        low_hour = min(hourly_counts.items(), key=lambda x: x[1])
        
        if peak_hour[1] > low_hour[1] * 2:
            trend = Trend(
                trend_id="behavior_usage_pattern",
                name="Usage Pattern",
                description=f"Peak usage at hour {peak_hour[0]}, low at {low_hour[0]}",
                trend_type=TrendType.VOLATILE,
                source=TrendSource.INTERNAL,
                score=min(100, (peak_hour[1] - low_hour[1]) / 10),
                confidence=0.7,
                volume=len(self.events),
                keywords=["usage", "pattern"]
            )
            trends.append(trend)
        
        return trends
    
    def get_success_rate_trend(self, agent_id: str) -> Trend:
        """获取成功率趋势"""
        if agent_id not in self.events_by_agent:
            return None
        
        events = self.events_by_agent[agent_id]
        if not events:
            return None
        
        success_count = sum(1 for e in events if e.success)
        success_rate = success_count / len(events) * 100
        
        trend_type = TrendType.STABLE
        if success_rate > 90:
            trend_type = TrendType.RISING
        elif success_rate < 70:
            trend_type = TrendType.FALLING
        
        return Trend(
            trend_id=f"success_rate_{agent_id}",
            name=f"Success Rate: {agent_id}",
            description=f"Success rate: {success_rate:.1f}%",
            trend_type=trend_type,
            source=TrendSource.INTERNAL,
            score=success_rate,
            confidence=0.8,
            volume=len(events),
            keywords=["success", "reliability"]
        )
