"""
Agent 进化机制
提供 Agent 持续进化的框架
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import uuid


class EvolutionStage(Enum):
    """进化阶段枚举"""
    DORMANT = "dormant"           # 休眠
    AWAKENED = "awakened"         # 觉醒
    DEVELOPING = "developing"     # 发展中
    MATURED = "matured"           # 成熟
    TRANSCENDENT = "transcendent" # 超越


@dataclass
class EvolutionEvent:
    """进化事件"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    from_stage: EvolutionStage = EvolutionStage.DORMANT
    to_stage: EvolutionStage = EvolutionStage.DORMANT
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 进化详情
    experience_gained: int = 0
    capabilities_unlocked: List[str] = field(default_factory=list)
    
    # 统计数据
    total_interactions: int = 0
    success_rate: float = 0.0
    
    # 自定义数据
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvolutionConfig:
    """进化配置"""
    # 各阶段所需经验
    stage_thresholds: Dict[EvolutionStage, int] = field(default_factory=lambda: {
        EvolutionStage.DORMANT: 0,
        EvolutionStage.AWAKENED: 100,
        EvolutionStage.DEVELOPING: 300,
        EvolutionStage.MATURED: 600,
        EvolutionStage.TRANSCENDENT: 1000,
    })
    
    # 进化奖励
    evolution_rewards: Dict[EvolutionStage, List[str]] = field(default_factory=lambda: {
        EvolutionStage.AWAKENED: ["emotion_recognition", "context_adaptation"],
        EvolutionStage.DEVELOPING: ["deep_reasoning", "creative_generation", "empathy"],
        EvolutionStage.MATURED: ["metacognition", "novel_synthesis", "collaborative_reasoning"],
        EvolutionStage.TRANSCENDENT: ["wisdom_synthesis", "intuitive_judgment", "integrated_information"],
    })
    
    # 进化条件
    min_success_rate_for_evolution: float = 0.6  # 进化所需最低成功率
    min_interactions_for_evolution: int = 50     # 进化所需最少交互数


@dataclass
class AgentEvolution:
    """Agent 进化状态"""
    agent_id: str = ""
    current_stage: EvolutionStage = EvolutionStage.DORMANT
    experience: int = 0
    
    # 进度追踪
    progress_to_next_stage: float = 0.0
    
    # 进化历史
    evolution_history: List[EvolutionEvent] = field(default_factory=list)
    
    # 统计数据
    total_evolutions: int = 0
    total_interactions: int = 0
    successful_interactions: int = 0
    
    # 时间戳
    stage_entered_at: datetime = field(default_factory=datetime.now)
    last_interaction: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        """获取成功率"""
        if self.total_interactions == 0:
            return 0.0
        return self.successful_interactions / self.total_interactions
    
    def add_experience(self, amount: int) -> int:
        """
        添加经验值
        
        Args:
            amount: 经验值数量
            
        Returns:
            int: 新增的经验值
        """
        self.experience += amount
        self.total_interactions += 1
        self.last_interaction = datetime.now()
        return amount
    
    def record_interaction(self, success: bool) -> None:
        """记录交互"""
        self.total_interactions += 1
        if success:
            self.successful_interactions += 1
        self.last_interaction = datetime.now()


class EvolutionEngine:
    """
    进化引擎
    
    管理 Agent 的持续进化
    """
    
    def __init__(self, config: Optional[EvolutionConfig] = None):
        """
        初始化进化引擎
        
        Args:
            config: 进化配置
        """
        self.config = config or EvolutionConfig()
        
        # Agent 进化状态
        self._evolutions: Dict[str, AgentEvolution] = {}
        
        # 进化回调
        self._evolution_callbacks: List[Callable[[EvolutionEvent], None]] = []
    
    def register_agent(self, agent_id: str) -> AgentEvolution:
        """
        注册 Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            AgentEvolution: 进化状态对象
        """
        if agent_id in self._evolutions:
            return self._evolutions[agent_id]
        
        evolution = AgentEvolution(agent_id=agent_id)
        self._evolutions[agent_id] = evolution
        return evolution
    
    def get_evolution(self, agent_id: str) -> Optional[AgentEvolution]:
        """获取 Agent 进化状态"""
        return self._evolutions.get(agent_id)
    
    def get_current_stage(self, agent_id: str) -> EvolutionStage:
        """获取当前进化阶段"""
        evolution = self._evolutions.get(agent_id)
        if evolution is None:
            return EvolutionStage.DORMANT
        return evolution.current_stage
    
    def get_experience(self, agent_id: str) -> int:
        """获取经验值"""
        evolution = self._evolutions.get(agent_id)
        if evolution is None:
            return 0
        return evolution.experience
    
    def can_evolve(self, agent_id: str) -> bool:
        """
        检查是否可以进化
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否可以进化
        """
        evolution = self._evolutions.get(agent_id)
        if evolution is None:
            return False
        
        # 检查是否已达到最高阶段
        if evolution.current_stage == EvolutionStage.TRANSCENDENT:
            return False
        
        # 检查经验值是否达到下一阶段阈值
        next_stage = self._get_next_stage(evolution.current_stage)
        if next_stage is None:
            return False
        
        threshold = self.config.stage_thresholds.get(next_stage, 0)
        if evolution.experience < threshold:
            return False
        
        # 检查成功率
        if evolution.success_rate < self.config.min_success_rate_for_evolution:
            return False
        
        # 检查交互次数
        if evolution.total_interactions < self.config.min_interactions_for_evolution:
            return False
        
        return True
    
    def _get_next_stage(self, current: EvolutionStage) -> Optional[EvolutionStage]:
        """获取下一阶段"""
        stage_order = [
            EvolutionStage.DORMANT,
            EvolutionStage.AWAKENED,
            EvolutionStage.DEVELOPING,
            EvolutionStage.MATURED,
            EvolutionStage.TRANSCENDENT,
        ]
        
        try:
            idx = stage_order.index(current)
            if idx < len(stage_order) - 1:
                return stage_order[idx + 1]
        except ValueError:
            pass
        
        return None
    
    def evolve(self, agent_id: str) -> bool:
        """
        执行进化
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否成功进化
        """
        if not self.can_evolve(agent_id):
            return False
        
        evolution = self._evolutions[agent_id]
        old_stage = evolution.current_stage
        
        # 获取下一阶段
        next_stage = self._get_next_stage(old_stage)
        if next_stage is None:
            return False
        
        # 创建进化事件
        event = EvolutionEvent(
            agent_id=agent_id,
            from_stage=old_stage,
            to_stage=next_stage,
            experience_gained=evolution.experience,
            total_interactions=evolution.total_interactions,
            success_rate=evolution.success_rate,
        )
        
        # 获取进化奖励
        rewards = self.config.evolution_rewards.get(next_stage, [])
        event.capabilities_unlocked = rewards
        
        # 更新状态
        evolution.current_stage = next_stage
        evolution.total_evolutions += 1
        evolution.stage_entered_at = datetime.now()
        
        # 重置进度
        evolution.progress_to_next_stage = 0.0
        
        # 添加历史
        evolution.evolution_history.append(event)
        
        # 触发回调
        for callback in self._evolution_callbacks:
            try:
                callback(event)
            except Exception:
                pass
        
        return True
    
    def add_experience(self, agent_id: str, amount: int) -> int:
        """
        添加经验值并检查是否可进化
        
        Args:
            agent_id: Agent ID
            amount: 经验值数量
            
        Returns:
            int: 添加的经验值
        """
        if agent_id not in self._evolutions:
            self.register_agent(agent_id)
        
        evolution = self._evolutions[agent_id]
        
        # 添加经验
        actual_added = evolution.add_experience(amount)
        
        # 更新进度
        self._update_progress(agent_id)
        
        # 检查是否可以进化
        if self.can_evolve(agent_id):
            self.evolve(agent_id)
        
        return actual_added
    
    def record_interaction(self, agent_id: str, success: bool) -> None:
        """
        记录交互并检查进化
        
        Args:
            agent_id: Agent ID
            success: 是否成功
        """
        if agent_id not in self._evolutions:
            self.register_agent(agent_id)
        
        evolution = self._evolutions[agent_id]
        evolution.record_interaction(success)
        
        # 更新进度
        self._update_progress(agent_id)
        
        # 检查是否可以进化
        if self.can_evolve(agent_id):
            self.evolve(agent_id)
    
    def _update_progress(self, agent_id: str) -> float:
        """更新进化进度"""
        evolution = self._evolutions.get(agent_id)
        if evolution is None:
            return 0.0
        
        next_stage = self._get_next_stage(evolution.current_stage)
        if next_stage is None:
            evolution.progress_to_next_stage = 1.0
            return 1.0
        
        current_threshold = self.config.stage_thresholds.get(evolution.current_stage, 0)
        next_threshold = self.config.stage_thresholds.get(next_stage, 0)
        
        if next_threshold == current_threshold:
            evolution.progress_to_next_stage = 1.0
        else:
            progress = (evolution.experience - current_threshold) / (next_threshold - current_threshold)
            evolution.progress_to_next_stage = max(0.0, min(1.0, progress))
        
        return evolution.progress_to_next_stage
    
    def on_evolution(self, callback: Callable[[EvolutionEvent], None]) -> None:
        """注册进化回调"""
        self._evolution_callbacks.append(callback)
    
    def get_evolution_history(self, agent_id: str) -> List[EvolutionEvent]:
        """获取进化历史"""
        evolution = self._evolutions.get(agent_id)
        if evolution is None:
            return []
        return list(evolution.evolution_history)
    
    def get_progress(self, agent_id: str) -> Dict[str, Any]:
        """
        获取进化进度
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dict[str, Any]: 进度信息
        """
        evolution = self._evolutions.get(agent_id)
        if evolution is None:
            return {
                "current_stage": EvolutionStage.DORMANT.value,
                "progress": 0.0,
                "experience": 0,
            }
        
        next_stage = self._get_next_stage(evolution.current_stage)
        
        return {
            "agent_id": agent_id,
            "current_stage": evolution.current_stage.value,
            "next_stage": next_stage.value if next_stage else None,
            "progress": evolution.progress_to_next_stage,
            "experience": evolution.experience,
            "next_threshold": (
                self.config.stage_thresholds.get(next_stage, 0)
                if next_stage else None
            ),
            "success_rate": evolution.success_rate,
            "total_interactions": evolution.total_interactions,
            "total_evolutions": evolution.total_evolutions,
        }
    
    def get_all_progress(self) -> Dict[str, Dict[str, Any]]:
        """获取所有 Agent 的进化进度"""
        return {
            agent_id: self.get_progress(agent_id)
            for agent_id in self._evolutions.keys()
        }
    
    def reset(self, agent_id: str) -> bool:
        """
        重置进化状态
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否成功重置
        """
        if agent_id in self._evolutions:
            del self._evolutions[agent_id]
            return True
        return False


# 全局进化引擎
_default_engine: Optional[EvolutionEngine] = None


def get_evolution_engine() -> EvolutionEngine:
    """获取全局进化引擎"""
    global _default_engine
    if _default_engine is None:
        _default_engine = EvolutionEngine()
    return _default_engine
