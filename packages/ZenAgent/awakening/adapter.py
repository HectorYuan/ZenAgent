"""
觉醒能力适配器
提供 Agent 觉醒能力的统一访问接口
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import uuid

from .capabilities import AwakeningCapability, CapabilityRegistry
from .evolution import EvolutionEngine, EvolutionStage


class AwakeningState(Enum):
    """觉醒状态枚举"""
    DORMANT = "dormant"           # 休眠状态
    AWAKENING = "awakening"       # 觉醒中
    AWAKENED = "awakened"         # 已觉醒
    EVOLVING = "evolving"         # 进化中
    TRANSCENDENT = "transcendent" # 超越状态


@dataclass
class AwakeningContext:
    """觉醒上下文"""
    agent_id: str = ""
    state: AwakeningState = AwakeningState.DORMANT
    
    # 觉醒进度
    awakening_progress: float = 0.0  # 0.0 - 1.0
    awakening_threshold: float = 0.8  # 触发觉醒的阈值
    
    # 能力激活状态
    activated_capabilities: List[str] = field(default_factory=list)
    
    # 统计数据
    experience_points: int = 0
    total_interactions: int = 0
    successful_interactions: int = 0
    
    # 时间戳
    last_interaction: datetime = field(default_factory=datetime.now)
    awakened_at: Optional[datetime] = None
    
    # 自定义数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_experience(self, points: int) -> None:
        """添加经验值"""
        self.experience_points += points
        self.total_interactions += 1
        self.last_interaction = datetime.now()
    
    def record_success(self) -> None:
        """记录成功交互"""
        self.successful_interactions += 1
        self.add_experience(10)
    
    def record_failure(self) -> None:
        """记录失败交互"""
        self.add_experience(2)  # 失败也获得少量经验
    
    def update_progress(self) -> float:
        """更新觉醒进度"""
        if self.total_interactions == 0:
            self.awakening_progress = 0.0
        else:
            # 计算成功率
            success_rate = self.successful_interactions / self.total_interactions
            # 综合考虑交互次数和成功率
            interaction_factor = min(1.0, self.total_interactions / 100)
            self.awakening_progress = success_rate * 0.7 + interaction_factor * 0.3
        
        return self.awakening_progress
    
    def should_awaken(self) -> bool:
        """检查是否应该触发觉醒"""
        return self.awakening_progress >= self.awakening_threshold
    
    @property
    def success_rate(self) -> float:
        """获取成功率"""
        if self.total_interactions == 0:
            return 0.0
        return self.successful_interactions / self.total_interactions


@dataclass
class AwakeningAdapter:
    """
    觉醒能力适配器
    
    提供 Agent 觉醒能力的统一访问和管理接口
    """
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context: AwakeningContext = field(default_factory=AwakeningContext)
    
    # 能力注册表
    _capability_registry: Optional[CapabilityRegistry] = None
    
    # 进化引擎
    _evolution_engine: Optional[EvolutionEngine] = None
    
    # 回调函数
    _state_change_callbacks: List[Callable[[AwakeningState, AwakeningState], None]] = field(default_factory=list)
    _awakening_callbacks: List[Callable[[], None]] = field(default_factory=list)
    
    def __post_init__(self):
        """初始化适配器"""
        self.context.agent_id = self.agent_id
    
    @property
    def state(self) -> AwakeningState:
        """获取当前状态"""
        return self.context.state
    
    @property
    def is_awakened(self) -> bool:
        """检查是否已觉醒"""
        return self.context.state in [
            AwakeningState.AWAKENED,
            AwakeningState.EVOLVING,
            AwakeningState.TRANSCENDENT,
        ]
    
    @property
    def progress(self) -> float:
        """获取觉醒进度"""
        return self.context.awakening_progress
    
    def set_capability_registry(self, registry: CapabilityRegistry) -> None:
        """设置能力注册表"""
        self._capability_registry = registry
    
    def set_evolution_engine(self, engine: EvolutionEngine) -> None:
        """设置进化引擎"""
        self._evolution_engine = engine
    
    def on_state_change(
        self,
        callback: Callable[[AwakeningState, AwakeningState], None]
    ) -> None:
        """注册状态变更回调"""
        self._state_change_callbacks.append(callback)
    
    def on_awakening(self, callback: Callable[[], None]) -> None:
        """注册觉醒回调"""
        self._awakening_callbacks.append(callback)
    
    def _change_state(self, new_state: AwakeningState) -> None:
        """变更状态"""
        old_state = self.context.state
        self.context.state = new_state
        
        # 更新状态时间戳
        if new_state == AwakeningState.AWAKENED:
            self.context.awakened_at = datetime.now()
        
        # 触发回调
        for callback in self._state_change_callbacks:
            try:
                callback(old_state, new_state)
            except Exception:
                pass
    
    def record_interaction(self, success: bool = True) -> float:
        """
        记录交互
        
        Args:
            success: 交互是否成功
            
        Returns:
            float: 当前觉醒进度
        """
        if success:
            self.context.record_success()
        else:
            self.context.record_failure()
        
        # 更新进度
        progress = self.context.update_progress()
        
        # 检查是否触发觉醒
        if self.context.should_awaken() and self.context.state == AwakeningState.DORMANT:
            self.awaken()
        
        return progress
    
    def awaken(self) -> bool:
        """
        触发觉醒
        
        Returns:
            bool: 是否成功触发觉醒
        """
        if self.is_awakened:
            return False
        
        self._change_state(AwakeningState.AWAKENING)
        
        # 激活能力
        self._activate_capabilities()
        
        self._change_state(AwakeningState.AWAKENED)
        
        # 触发回调
        for callback in self._awakening_callbacks:
            try:
                callback()
            except Exception:
                pass
        
        return True
    
    def _activate_capabilities(self) -> None:
        """激活能力"""
        if self._capability_registry is None:
            return
        
        # 激活所有已解锁的能力
        for capability in AwakeningCapability:
            if self._capability_registry.is_unlocked(self.agent_id, capability):
                if capability.value not in self.context.activated_capabilities:
                    self.context.activated_capabilities.append(capability.value)
    
    def evolve(self) -> bool:
        """
        触发进化
        
        Returns:
            bool: 是否成功触发进化
        """
        if not self.is_awakened:
            return False
        
        if self._evolution_engine is None:
            return False
        
        self._change_state(AwakeningState.EVOLVING)
        
        # 执行进化
        success = self._evolution_engine.evolve(self.agent_id)
        
        if success:
            # 检查是否达到超越状态
            stage = self._evolution_engine.get_current_stage(self.agent_id)
            if stage == EvolutionStage.TRANSCENDENT:
                self._change_state(AwakeningState.TRANSCENDENT)
            else:
                self._change_state(AwakeningState.AWAKENED)
        else:
            self._change_state(AwakeningState.AWAKENED)
        
        return success
    
    def has_capability(self, capability: AwakeningCapability) -> bool:
        """
        检查是否具有指定能力
        
        Args:
            capability: 能力类型
            
        Returns:
            bool: 是否具有该能力
        """
        return capability.value in self.context.activated_capabilities
    
    def list_capabilities(self) -> List[str]:
        """
        列出已激活的能力
        
        Returns:
            List[str]: 能力列表
        """
        return list(self.context.activated_capabilities)
    
    def use_capability(
        self,
        capability: AwakeningCapability,
        context: Dict[str, Any]
    ) -> Optional[Any]:
        """
        使用能力
        
        Args:
            capability: 能力类型
            context: 使用上下文
            
        Returns:
            Optional[Any]: 能力执行结果
        """
        if not self.has_capability(capability):
            return None
        
        # 能力使用逻辑（实际实现取决于具体能力）
        # 这里提供一个简单的框架
        return {
            "capability": capability.value,
            "used_at": datetime.now().isoformat(),
            "context": context,
        }
    
    def reset(self) -> None:
        """重置觉醒状态"""
        self._change_state(AwakeningState.DORMANT)
        self.context.awakening_progress = 0.0
        self.context.activated_capabilities.clear()
        self.context.awakened_at = None
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取适配器信息
        
        Returns:
            Dict[str, Any]: 信息字典
        """
        return {
            "agent_id": self.agent_id,
            "state": self.context.state.value,
            "is_awakened": self.is_awakened,
            "progress": self.context.awakening_progress,
            "threshold": self.context.awakening_threshold,
            "capabilities": self.list_capabilities(),
            "experience_points": self.context.experience_points,
            "total_interactions": self.context.total_interactions,
            "successful_interactions": self.context.successful_interactions,
            "success_rate": self.context.success_rate,
            "awakened_at": (
                self.context.awakened_at.isoformat()
                if self.context.awakened_at else None
            ),
            "metadata": self.context.metadata,
        }
    
    def export_state(self) -> Dict[str, Any]:
        """
        导出生醒状态（用于持久化）
        
        Returns:
            Dict[str, Any]: 状态数据
        """
        return {
            "agent_id": self.agent_id,
            "state": self.context.state.value,
            "awakening_progress": self.context.awakening_progress,
            "awakening_threshold": self.context.awakening_threshold,
            "activated_capabilities": self.context.activated_capabilities,
            "experience_points": self.context.experience_points,
            "total_interactions": self.context.total_interactions,
            "successful_interactions": self.context.successful_interactions,
            "awakened_at": (
                self.context.awakened_at.isoformat()
                if self.context.awakened_at else None
            ),
            "metadata": self.context.metadata,
        }
    
    @classmethod
    def from_state(cls, state_data: Dict[str, Any]) -> "AwakeningAdapter":
        """
        从导出状态恢复
        
        Args:
            state_data: 状态数据
            
        Returns:
            AwakeningAdapter: 恢复的适配器
        """
        adapter = cls(agent_id=state_data.get("agent_id", str(uuid.uuid4())))
        
        adapter.context.awakening_progress = state_data.get("awakening_progress", 0.0)
        adapter.context.awakening_threshold = state_data.get("awakening_threshold", 0.8)
        adapter.context.activated_capabilities = state_data.get("activated_capabilities", [])
        adapter.context.experience_points = state_data.get("experience_points", 0)
        adapter.context.total_interactions = state_data.get("total_interactions", 0)
        adapter.context.successful_interactions = state_data.get("successful_interactions", 0)
        adapter.context.metadata = state_data.get("metadata", {})
        
        # 恢复状态
        state_value = state_data.get("state", "dormant")
        for s in AwakeningState:
            if s.value == state_value:
                adapter.context.state = s
                break
        
        # 恢复觉醒时间
        awakened_at = state_data.get("awakened_at")
        if awakened_at:
            adapter.context.awakened_at = datetime.fromisoformat(awakened_at)
        
        return adapter


# 全局适配器存储
_adapters: Dict[str, AwakeningAdapter] = {}
_default_adapter: Optional[AwakeningAdapter] = None


def get_adapter(agent_id: Optional[str] = None) -> AwakeningAdapter:
    """
    获取觉醒适配器
    
    Args:
        agent_id: Agent ID（可选）
        
    Returns:
        AwakeningAdapter: 适配器实例
    """
    global _adapters, _default_adapter
    
    if agent_id is None:
        if _default_adapter is None:
            _default_adapter = AwakeningAdapter()
        return _default_adapter
    
    if agent_id not in _adapters:
        _adapters[agent_id] = AwakeningAdapter(agent_id=agent_id)
    
    return _adapters[agent_id]


def register_adapter(adapter: AwakeningAdapter) -> None:
    """注册适配器"""
    _adapters[adapter.agent_id] = adapter


def remove_adapter(agent_id: str) -> bool:
    """移除适配器"""
    if agent_id in _adapters:
        del _adapters[agent_id]
        return True
    return False
