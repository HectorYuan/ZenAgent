"""
状态管理器

管理多个 Agent 的状态，提供批量操作和状态查询功能
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime
import threading

from .agent_lifecycle import AgentLifecycle, AgentState, LifecycleTransition
from .transitions import TransitionRule, TransitionValidator
from .exceptions import StateManagerError, InvalidTransitionError


@dataclass
class StateTransitionResult:
    """状态转换结果"""
    success: bool
    agent_id: str
    from_state: AgentState
    to_state: AgentState
    timestamp: datetime
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# 类型别名
TransitionCallback = Callable[['StateManager', str, AgentState, AgentState], None]


class StateManager:
    """
    Agent 状态管理器
    
    管理多个 Agent 的生命周期状态，提供统一的状态查询和转换接口
    """
    
    def __init__(
        self,
        global_rules: Optional[List[TransitionRule]] = None,
        enable_history: bool = True,
    ):
        """
        初始化状态管理器
        
        Args:
            global_rules: 全局转换规则
            enable_history: 是否记录历史
        """
        self._agents: Dict[str, AgentLifecycle] = {}
        self._global_rules = global_rules or []
        self._enable_history = enable_history
        self._transition_history: List[StateTransitionResult] = []
        self._lock = threading.RLock()
        
        # 全局回调
        self._on_transition: List[TransitionCallback] = []
        self._on_agent_registered: List[Callable[['StateManager', str], None]] = []
        self._on_agent_unregistered: List[Callable[['StateManager', str], None]] = []
    
    @property
    def agent_count(self) -> int:
        """获取管理的 Agent 数量"""
        return len(self._agents)
    
    @property
    def active_agents(self) -> List[str]:
        """获取活跃的 Agent ID 列表"""
        return [
            agent_id for agent_id, lifecycle in self._agents.items()
            if lifecycle.is_active
        ]
    
    @property
    def transition_history(self) -> List[StateTransitionResult]:
        """获取转换历史"""
        return self._transition_history.copy()
    
    def register_agent(
        self,
        agent_id: str,
        initial_state: AgentState = AgentState.CREATED,
        custom_rules: Optional[List[TransitionRule]] = None,
    ) -> AgentLifecycle:
        """
        注册 Agent
        
        Args:
            agent_id: Agent ID
            initial_state: 初始状态
            custom_rules: 自定义转换规则
            
        Returns:
            AgentLifecycle: Agent 生命周期对象
            
        Raises:
            StateManagerError: Agent 已存在
        """
        with self._lock:
            if agent_id in self._agents:
                raise StateManagerError(f"Agent {agent_id} already registered")
            
            # 合并规则
            rules = self._global_rules.copy()
            if custom_rules:
                rules.extend(custom_rules)
            
            lifecycle = AgentLifecycle(
                agent_id=agent_id,
                initial_state=initial_state,
                transition_rules=rules,
            )
            
            self._agents[agent_id] = lifecycle
            
            # 触发回调
            self._trigger_callbacks(self._on_agent_registered, agent_id)
            
            return lifecycle
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        注销 Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否成功注销
        """
        with self._lock:
            if agent_id not in self._agents:
                return False
            
            del self._agents[agent_id]
            
            # 触发回调
            self._trigger_callbacks(self._on_agent_unregistered, agent_id)
            
            return True
    
    def get_agent(self, agent_id: str) -> Optional[AgentLifecycle]:
        """
        获取 Agent 生命周期对象
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Optional[AgentLifecycle]: 生命周期对象
        """
        return self._agents.get(agent_id)
    
    def get_state(self, agent_id: str) -> Optional[AgentState]:
        """
        获取 Agent 状态
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Optional[AgentState]: 当前状态
        """
        lifecycle = self._agents.get(agent_id)
        return lifecycle.state if lifecycle else None
    
    def transition(
        self,
        agent_id: str,
        target_state: AgentState,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StateTransitionResult:
        """
        执行 Agent 状态转换
        
        Args:
            agent_id: Agent ID
            target_state: 目标状态
            reason: 转换原因
            metadata: 附加元数据
            
        Returns:
            StateTransitionResult: 转换结果
        """
        with self._lock:
            lifecycle = self._agents.get(agent_id)
            if not lifecycle:
                return StateTransitionResult(
                    success=False,
                    agent_id=agent_id,
                    from_state=AgentState.CREATED,  # 虚拟初始状态
                    to_state=target_state,
                    timestamp=datetime.now(),
                    error=f"Agent {agent_id} not found",
                )
            
            from_state = lifecycle.state
            
            try:
                success = lifecycle.transition_to(
                    target_state=target_state,
                    reason=reason,
                    metadata=metadata,
                )
                
                result = StateTransitionResult(
                    success=success,
                    agent_id=agent_id,
                    from_state=from_state,
                    to_state=target_state,
                    timestamp=datetime.now(),
                    metadata=metadata or {},
                )
                
                # 记录历史
                if self._enable_history:
                    self._transition_history.append(result)
                
                # 触发全局回调
                self._trigger_callbacks(
                    self._on_transition,
                    agent_id,
                    from_state,
                    target_state,
                )
                
                return result
                
            except InvalidTransitionError as e:
                return StateTransitionResult(
                    success=False,
                    agent_id=agent_id,
                    from_state=from_state,
                    to_state=target_state,
                    timestamp=datetime.now(),
                    error=str(e),
                )
    
    def batch_transition(
        self,
        transitions: Dict[str, AgentState],
        reason: str = "",
    ) -> Dict[str, StateTransitionResult]:
        """
        批量状态转换
        
        Args:
            transitions: Agent ID 到目标状态的映射
            reason: 统一转换原因
            
        Returns:
            Dict[str, StateTransitionResult]: 各 Agent 的转换结果
        """
        results = {}
        
        for agent_id, target_state in transitions.items():
            results[agent_id] = self.transition(
                agent_id=agent_id,
                target_state=target_state,
                reason=reason,
            )
        
        return results
    
    def get_agents_by_state(self, state: AgentState) -> List[str]:
        """
        获取处于指定状态的所有 Agent
        
        Args:
            state: 目标状态
            
        Returns:
            List[str]: Agent ID 列表
        """
        return [
            agent_id for agent_id, lifecycle in self._agents.items()
            if lifecycle.state == state
        ]
    
    def get_state_distribution(self) -> Dict[AgentState, int]:
        """
        获取状态分布统计
        
        Returns:
            Dict[AgentState, int]: 状态到数量的映射
        """
        distribution: Dict[AgentState, int] = {}
        for lifecycle in self._agents.values():
            distribution[lifecycle.state] = distribution.get(lifecycle.state, 0) + 1
        return distribution
    
    def register_transition_callback(
        self,
        callback: TransitionCallback,
    ) -> None:
        """
        注册状态转换回调
        
        Args:
            callback: 回调函数
        """
        self._on_transition.append(callback)
    
    def register_agent_callback(
        self,
        event: str,
        callback: Callable[..., None],
    ) -> None:
        """
        注册 Agent 事件回调
        
        Args:
            event: 事件类型 ('registered' 或 'unregistered')
            callback: 回调函数
        """
        if event == "registered":
            self._on_agent_registered.append(callback)
        elif event == "unregistered":
            self._on_agent_unregistered.append(callback)
    
    def _trigger_callbacks(
        self,
        callbacks: List[Callable[..., None]],
        *args: Any,
    ) -> None:
        """触发回调列表"""
        for callback in callbacks:
            try:
                callback(*args)
            except Exception:
                pass  # 不中断流程
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取 Agent 详细信息
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Optional[Dict[str, Any]]: Agent 信息字典
        """
        lifecycle = self._agents.get(agent_id)
        if not lifecycle:
            return None
        
        return lifecycle.to_dict()
    
    def get_all_agents_summary(self) -> Dict[str, Any]:
        """
        获取所有 Agent 的摘要信息
        
        Returns:
            Dict[str, Any]: 摘要信息
        """
        return {
            "total_agents": self.agent_count,
            "active_agents": len(self.active_agents),
            "state_distribution": {
                state.value: count
                for state, count in self.get_state_distribution().items()
            },
            "transition_count": len(self._transition_history),
        }
    
    def clear_history(self) -> int:
        """
        清除转换历史
        
        Returns:
            int: 清除的记录数
        """
        count = len(self._transition_history)
        self._transition_history.clear()
        return count
    
    def __contains__(self, agent_id: str) -> bool:
        """检查 Agent 是否存在"""
        return agent_id in self._agents
    
    def __len__(self) -> int:
        """获取 Agent 数量"""
        return self.agent_count
    
    def __repr__(self) -> str:
        return f"StateManager(agents={self.agent_count})"
