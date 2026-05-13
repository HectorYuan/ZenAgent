"""
人格模型

Big Five 人格维度的实现
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import threading


class BigFiveTraits(Enum):
    """大五人格特质"""
    OPENNESS = "openness"              # 开放性
    CONSCIENTIOUSNESS = "conscientiousness"  # 尽责性
    EXTRAVERSION = "extraversion"      # 外向性
    AGREEABLENESS = "agreeableness"    # 宜人性
    NEUROTICISM = "neuroticism"         # 神经质


@dataclass
class PersonalityState:
    """人格状态"""
    traits: Dict[str, float] = field(default_factory=lambda: {
        BigFiveTraits.OPENNESS.value: 0.5,
        BigFiveTraits.CONSCIENTIOUSNESS.value: 0.5,
        BigFiveTraits.EXTRAVERSION.value: 0.5,
        BigFiveTraits.AGREEABLENESS.value: 0.5,
        BigFiveTraits.NEUROTICISM.value: 0.5,
    })
    
    # 稳定性
    stability: float = 0.8  # 人格稳定性
    adaptability: float = 0.5  # 适应能力
    
    # 元数据
    last_updated: datetime = field(default_factory=datetime.now)
    version: int = 1


@dataclass
class TraitProfile:
    """特质档案"""
    trait: BigFiveTraits
    value: float  # 0-1
    facets: Dict[str, float] = field(default_factory=dict)  # 子维度
    history: List[Tuple[datetime, float]] = field(default_factory=list)


class Personality:
    """
    人格模型
    
    实现 Big Five 人格维度及其演化
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, float]] = None,
    ):
        """
        初始化人格
        
        Args:
            config: 特质配置
        """
        self.state = PersonalityState()
        
        # 初始化特质
        if config:
            for trait, value in config.items():
                if trait in self.state.traits:
                    self.state.traits[trait] = max(0.0, min(1.0, value))
        
        # 特质档案
        self._trait_profiles: Dict[str, TraitProfile] = {}
        for trait in BigFiveTraits:
            self._init_trait_profile(trait)
        
        # 演化历史
        self._evolution_history: List[Dict[str, Any]] = []
        
        self._lock = threading.RLock()
    
    def _init_trait_profile(self, trait: BigFiveTraits) -> None:
        """初始化特质档案"""
        value = self.state.traits.get(trait.value, 0.5)
        
        self._trait_profiles[trait.value] = TraitProfile(
            trait=trait,
            value=value,
            facets={},
            history=[(datetime.now(), value)],
        )
    
    def get_trait(self, trait: BigFiveTraits) -> float:
        """
        获取特质值
        
        Args:
            trait: 特质类型
            
        Returns:
            float: 特质值 (0-1)
        """
        return self.state.traits.get(trait.value, 0.5)
    
    def get_traits(self) -> Dict[str, float]:
        """
        获取所有特质
        
        Returns:
            Dict[str, float]: 特质字典
        """
        return self.state.traits.copy()
    
    def set_trait(
        self,
        trait: BigFiveTraits,
        value: float,
    ) -> None:
        """
        设置特质值
        
        Args:
            trait: 特质类型
            value: 特质值 (0-1)
        """
        with self._lock:
            clamped_value = max(0.0, min(1.0, value))
            self.state.traits[trait.value] = clamped_value
            self.state.last_updated = datetime.now()
            self.state.version += 1
            
            # 更新档案
            self._update_trait_profile(trait, clamped_value)
    
    def _update_trait_profile(
        self,
        trait: BigFiveTraits,
        value: float,
    ) -> None:
        """更新特质档案"""
        profile = self._trait_profiles.get(trait.value)
        if profile:
            profile.value = value
            profile.history.append((datetime.now(), value))
    
    def evolve(
        self,
        experience: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        基于经验演化人格
        
        Args:
            experience: 经验数据
            
        Returns:
            Dict[str, float]: 更新的特质
        """
        with self._lock:
            deltas: Dict[str, float] = {}
            
            # 提取经验特征
            outcome = experience.get("outcome", 0)
            sentiment = experience.get("sentiment", 0)
            social = experience.get("social", False)
            novelty = experience.get("novelty", 0.5)
            
            # 基于经验调整特质
            
            # 开放性：处理新奇经验
            if novelty > 0.7:
                delta = 0.02 * novelty
                self._adjust_trait(BigFiveTraits.OPENNESS, delta)
                deltas[BigFiveTraits.OPENNESS.value] = delta
            
            # 尽责性：处理成功/失败
            if outcome != 0:
                # 成功增强尽责性，失败根据适应性调整
                delta = 0.01 * outcome * self.state.adaptability
                self._adjust_trait(BigFiveTraits.CONSCIENTIOUSNESS, delta)
                deltas[BigFiveTraits.CONSCIENTIOUSNESS.value] = delta
            
            # 外向性：处理社交经验
            if social:
                delta = 0.01 * (1 if sentiment > 0 else -0.5)
                self._adjust_trait(BigFiveTraits.EXTRAVERSION, delta)
                deltas[BigFiveTraits.EXTRAVERSION.value] = delta
            
            # 宜人性：处理情感倾向
            if sentiment != 0:
                delta = 0.01 * sentiment
                self._adjust_trait(BigFiveTraits.AGREEABLENESS, delta)
                deltas[BigFiveTraits.AGREEABLENESS.value] = delta
            
            # 神经质：处理负面经验
            if sentiment < 0 or outcome < -0.3:
                delta = 0.01 * abs(sentiment) if sentiment < 0 else 0.005
                self._adjust_trait(BigFiveTraits.NEUROTICISM, delta, increase=True)
                deltas[BigFiveTraits.NEUROTICISM.value] = delta
            
            # 记录演化
            if deltas:
                self._record_evolution(experience, deltas)
            
            return deltas
    
    def _adjust_trait(
        self,
        trait: BigFiveTraits,
        delta: float,
        increase: bool = False,
    ) -> None:
        """调整特质"""
        current = self.state.traits.get(trait.value, 0.5)
        
        if increase:
            new_value = current + abs(delta)
        else:
            new_value = current + delta
        
        # 应用稳定性限制
        adjustment = (new_value - current) * self.state.stability
        new_value = current + adjustment
        
        # 限制范围
        new_value = max(0.0, min(1.0, new_value))
        
        self.state.traits[trait.value] = new_value
        self.state.last_updated = datetime.now()
        self._update_trait_profile(trait, new_value)
    
    def _record_evolution(
        self,
        experience: Dict[str, Any],
        deltas: Dict[str, float],
    ) -> None:
        """记录演化历史"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "experience_id": experience.get("id", ""),
            "deltas": deltas.copy(),
            "traits_after": self.state.traits.copy(),
        }
        
        self._evolution_history.append(record)
        
        # 限制历史长度
        if len(self._evolution_history) > 100:
            self._evolution_history = self._evolution_history[-50:]
    
    def adjust_stability(self, delta: float) -> None:
        """调整稳定性"""
        self.state.stability = max(0.1, min(1.0, self.state.stability + delta))
    
    def adjust_adaptability(self, delta: float) -> None:
        """调整适应性"""
        self.state.adaptability = max(0.0, min(1.0, self.state.adaptability + delta))
    
    def get_trait_profile(self, trait: BigFiveTraits) -> TraitProfile:
        """获取特质档案"""
        return self._trait_profiles.get(trait.value)
    
    def get_evolution_history(
        self,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """获取演化历史"""
        return self._evolution_history[-limit:]
    
    def predict_behavior(
        self,
        situation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        预测行为
        
        基于人格特质预测在特定情境下的行为
        
        Args:
            situation: 情境描述
            
        Returns:
            Dict[str, Any]: 行为预测
        """
        openness = self.get_trait(BigFiveTraits.OPENNESS)
        conscientious = self.get_trait(BigFiveTraits.CONSCIENTIOUSNESS)
        extravert = self.get_trait(BigFiveTraits.EXTRAVERSION)
        agreeable = self.get_trait(BigFiveTraits.AGREEABLENESS)
        neurotic = self.get_trait(BigFiveTraits.NEUROTICISM)
        
        predictions = {}
        
        # 社交倾向
        if situation.get("social", False):
            if extravert > 0.6:
                predictions["social_engagement"] = "high"
            elif extravert < 0.4:
                predictions["social_engagement"] = "low"
        
        # 风险承担
        if situation.get("risky", False):
            if openness > 0.6:
                predictions["risk_taking"] = "likely"
            elif neurotic > 0.6:
                predictions["risk_taking"] = "unlikely"
        
        # 计划性
        if situation.get("complex", False):
            if conscientious > 0.6:
                predictions["planning"] = "detailed"
            elif conscientious < 0.4:
                predictions["planning"] = "minimal"
        
        return predictions
    
    def reset(self) -> None:
        """重置人格"""
        self.state = PersonalityState()
        self._evolution_history.clear()
        
        for trait in BigFiveTraits:
            self._init_trait_profile(trait)
