"""
特质动态变化

人格特质随时间和经验的变化
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import threading


class EnvironmentalFactor(Enum):
    """环境因素"""
    SOCIAL_INTERACTION = "social"         # 社交互动
    ACHIEVEMENT = "achievement"         # 成就体验
    STRESS = "stress"                   # 压力
    SUPPORT = "support"                 # 支持
    CHALLENGE = "challenge"             # 挑战
    STABILITY = "stability"             # 稳定性


@dataclass
class TraitChange:
    """特质变化"""
    trait_name: str
    previous_value: float
    new_value: float
    delta: float
    
    # 原因
    cause: str
    experience_id: str = ""
    
    # 元数据
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TraitDynamicsConfig:
    """特质动态配置"""
    # 变化速率
    max_change_per_event: float = 0.05
    daily_max_change: float = 0.1
    
    # 环境敏感性
    social_sensitivity: float = 0.5
    stress_sensitivity: float = 0.6
    achievement_sensitivity: float = 0.7
    
    # 时间衰减
    change_decay_days: float = 7.0


class TraitDynamics:
    """
    特质动态变化
    
    管理人格特质随时间和经验的变化
    """
    
    def __init__(
        self,
        personality,
        config: Optional[TraitDynamicsConfig] = None,
    ):
        """
        初始化特质动态
        
        Args:
            personality: Personality 实例
            config: 配置
        """
        self.personality = personality
        self.config = config or TraitDynamicsConfig()
        
        # 变化历史
        self._change_history: List[TraitChange] = []
        
        # 环境因素强度
        self._environmental_intensity: Dict[EnvironmentalFactor, float] = {
            factor: 0.0 for factor in EnvironmentalFactor
        }
        
        # 累积变化
        self._daily_changes: Dict[str, float] = {}
        self._last_change_date: Optional[datetime] = None
        
        # 回调
        self._on_trait_change: List[Callable[[TraitChange], None]] = []
        
        self._lock = threading.RLock()
    
    def process_experience(
        self,
        experience: Dict[str, Any],
    ) -> List[TraitChange]:
        """
        处理经验并更新特质
        
        Args:
            experience: 经验数据
            
        Returns:
            List[TraitChange]: 变化列表
        """
        with self._lock:
            changes = []
            
            # 更新环境因素
            self._update_environmental_factors(experience)
            
            # 计算各特质变化
            outcome = experience.get("outcome", 0)
            sentiment = experience.get("sentiment", 0)
            social = experience.get("social", False)
            stressful = experience.get("stressful", False)
            achievement = experience.get("achievement", False)
            
            # 开放性变化
            if experience.get("novelty", 0) > 0.5:
                delta = self._calculate_delta(
                    experience.get("novelty", 0),
                    self.personality.state.traits.get("openness", 0.5),
                    self.config.achievement_sensitivity,
                )
                change = self._apply_change("openness", delta, "新奇体验")
                if change:
                    changes.append(change)
            
            # 尽责性变化
            if outcome != 0:
                delta = self._calculate_delta(
                    outcome,
                    self.personality.state.traits.get("conscientiousness", 0.5),
                    self.config.achievement_sensitivity,
                )
                change = self._apply_change("conscientiousness", delta, "任务结果")
                if change:
                    changes.append(change)
            
            # 外向性变化
            if social:
                sentiment_factor = 1 if sentiment > 0 else -0.5
                delta = self._calculate_delta(
                    sentiment_factor * 0.5,
                    self.personality.state.traits.get("extraversion", 0.5),
                    self.config.social_sensitivity,
                )
                change = self._apply_change("extraversion", delta, "社交互动")
                if change:
                    changes.append(change)
            
            # 宜人性变化
            if experience.get("cooperation", False):
                delta = self._calculate_delta(
                    sentiment * 0.3,
                    self.personality.state.traits.get("agreeableness", 0.5),
                    self.config.social_sensitivity,
                )
                change = self._apply_change("agreeableness", delta, "合作体验")
                if change:
                    changes.append(change)
            
            # 神经质变化
            if stressful or sentiment < -0.3:
                stress_intensity = abs(sentiment) if sentiment < 0 else 0.5
                delta = self._calculate_delta(
                    stress_intensity * 0.3,
                    self.personality.state.traits.get("neuroticism", 0.5),
                    self.config.stress_sensitivity,
                    increase=True,
                )
                change = self._apply_change("neuroticism", delta, "压力体验")
                if change:
                    changes.append(change)
            
            return changes
    
    def _calculate_delta(
        self,
        raw_value: float,
        current_trait: float,
        sensitivity: float,
        increase: bool = False,
    ) -> float:
        """计算特质变化量"""
        # 限制单次变化
        delta = raw_value * sensitivity * self.config.max_change_per_event
        
        # 远离中值更容易变化
        distance_from_mid = abs(current_trait - 0.5)
        adjustment = 1.0 + distance_from_mid
        delta *= adjustment
        
        # 应用每日限制
        if self._last_change_date:
            days_since = (datetime.now() - self._last_change_date).days
            if days_since > 0:
                self._daily_changes.clear()
                self._last_change_date = datetime.now()
        
        if delta > 0:
            current_daily = sum(max(0, d) for d in self._daily_changes.values())
            if current_daily >= self.config.daily_max_change:
                delta = 0
        
        if increase:
            return abs(delta)  # 总是增加
        else:
            return delta
    
    def _apply_change(
        self,
        trait_name: str,
        delta: float,
        cause: str,
    ) -> Optional[TraitChange]:
        """应用特质变化"""
        if abs(delta) < 0.001:
            return None
        
        current = self.personality.state.traits.get(trait_name, 0.5)
        new_value = max(0.0, min(1.0, current + delta))
        
        if new_value == current:
            return None
        
        # 更新人格
        from .personality import BigFiveTraits
        trait = None
        for t in BigFiveTraits:
            if t.value == trait_name:
                trait = t
                break
        
        if trait:
            self.personality.set_trait(trait, new_value)
        
        # 记录变化
        change = TraitChange(
            trait_name=trait_name,
            previous_value=current,
            new_value=new_value,
            delta=delta,
            cause=cause,
        )
        
        self._change_history.append(change)
        self._daily_changes[trait_name] = self._daily_changes.get(trait_name, 0) + delta
        self._last_change_date = datetime.now()
        
        # 触发回调
        for callback in self._on_trait_change:
            try:
                callback(change)
            except Exception:
                pass
        
        return change
    
    def _update_environmental_factors(
        self,
        experience: Dict[str, Any],
    ) -> None:
        """更新环境因素"""
        if experience.get("social"):
            self._environmental_intensity[
                EnvironmentalFactor.SOCIAL_INTERACTION
            ] = 0.8
        
        if experience.get("outcome", 0) > 0.5:
            self._environmental_intensity[
                EnvironmentalFactor.ACHIEVEMENT
            ] = 0.9
        
        if experience.get("stressful"):
            self._environmental_intensity[
                EnvironmentalFactor.STRESS
            ] = 0.7
        
        if experience.get("supportive"):
            self._environmental_intensity[
                EnvironmentalFactor.SUPPORT
            ] = 0.8
        
        # 时间衰减
        decay_rate = 0.1
        for factor in self._environmental_intensity:
            current = self._environmental_intensity[factor]
            if current > 0:
                self._environmental_intensity[factor] = max(0, current - decay_rate)
    
    def get_recent_changes(
        self,
        limit: int = 10,
    ) -> List[TraitChange]:
        """获取最近的特质变化"""
        return self._change_history[-limit:]
    
    def get_change_trend(
        self,
        trait_name: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """获取特质变化趋势"""
        cutoff = datetime.now() - timedelta(days=days)
        
        relevant_changes = [
            c for c in self._change_history
            if c.trait_name == trait_name and c.timestamp >= cutoff
        ]
        
        if not relevant_changes:
            return {"trend": "stable", "net_change": 0.0}
        
        net_change = sum(c.delta for c in relevant_changes)
        
        if net_change > 0.05:
            trend = "increasing"
        elif net_change < -0.05:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "net_change": net_change,
            "change_count": len(relevant_changes),
            "avg_magnitude": abs(net_change) / len(relevant_changes),
        }
    
    def get_environmental_factors(self) -> Dict[str, float]:
        """获取当前环境因素强度"""
        return {
            factor.value: intensity
            for factor, intensity in self._environmental_intensity.items()
        }
    
    def on_trait_change(
        self,
        callback: Callable[[TraitChange], None],
    ) -> None:
        """注册特质变化回调"""
        self._on_trait_change.append(callback)
