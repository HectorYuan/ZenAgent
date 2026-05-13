"""
Agent 生命周期状态机

定义 Agent 的完整生命周期状态和状态转换
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime
import uuid

from .exceptions import InvalidTransitionError, TransitionError
from .transitions import TransitionRule, get_default_rules, TransitionValidator


class AgentState(Enum):
    """Agent 生命周期状态枚举"""
    CREATED = "created"           # 已创建
    INITIALIZING = "initializing" # 初始化中
    READY = "ready"               # 就绪
    RUNNING = "running"           # 运行中
    PAUSED = "paused"            # 已暂停
    STOPPED = "stopped"          # 已停止
    DISPOSED = "disposed"        # 已释放
    ERROR = "error"              # 错误状态


@dataclass
class LifecycleTransition:
    """生命周期转换记录"""
    from_state: AgentState
    to_state: AgentState
    timestamp: datetime
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LifecycleCallbacks:
    """生命周期回调集合"""
    on_state_change: List[Callable[['AgentLifecycle', AgentState, AgentState], None]] = field(default_factory=list)
    on_created: List[Callable[['AgentLifecycle'], None]] = field(default_factory=list)
    on_initializing: List[Callable[['AgentLifecycle'], None]] = field(default_factory=list)
    on_ready: List[Callable[['AgentLifecycle'], None]] = field(default_factory=list)
    on_running: List[Callable[['AgentLifecycle'], None]] = field(default_factory=list)
    on_paused: List[Callable[['AgentLifecycle'], None]] = field(default_factory=list)
    on_stopped: List[Callable[['AgentLifecycle'], None]] = field(default_factory=list)
    on_disposed: List[Callable[['AgentLifecycle'], None]] = field(default_factory=list)
    on_error: List[Callable[['AgentLifecycle', Exception], None]] = field(default_factory=list)


class AgentLifecycle:
    """
    Agent 生命周期状态机
    
    管理 Agent 从创建到销毁的完整生命周期
    
    状态转换流程:
    Created → Initializing → Ready → Running ↔ Paused → Stopped → Disposed
                                  ↓
                                Error
    """
    
    def __init__(
        self,
        agent_id: str,
        initial_state: AgentState = AgentState.CREATED,
        transition_rules: Optional[List[TransitionRule]] = None,
        enable_callbacks: bool = True,
    ):
        """
        初始化 Agent 生命周期
        
        Args:
            agent_id: Agent 唯一标识
            initial_state: 初始状态
            transition_rules: 状态转换规则列表
            enable_callbacks: 是否启用回调
        """
        self.agent_id = agent_id
        self._state = initial_state
        self._transition_history: List[LifecycleTransition] = []
        self._created_at = datetime.now()
        self._last_updated = self._created_at
        
        # 加载转换规则
        self._rules = transition_rules or get_default_rules()
        self._validator = TransitionValidator(self._rules)
        
        # 回调
        self._callbacks = LifecycleCallbacks() if enable_callbacks else None
        self._error: Optional[Exception] = None
        
        # 状态锁（防止并发转换）
        self._lock = False
    
    @property
    def state(self) -> AgentState:
        """获取当前状态"""
        return self._state
    
    @property
    def is_active(self) -> bool:
        """Agent 是否处于活跃状态"""
        return self._state in {
            AgentState.READY,
            AgentState.RUNNING,
            AgentState.PAUSED,
            AgentState.INITIALIZING,
        }
    
    @property
    def is_terminal(self) -> bool:
        """Agent 是否处于终态"""
        return self._state in {
            AgentState.STOPPED,
            AgentState.DISPOSED,
        }
    
    @property
    def can_transition_to(self) -> List[AgentState]:
        """获取可转换到的目标状态列表"""
        return self._validator.get_valid_transitions(self._state)
    
    @property
    def transition_history(self) -> List[LifecycleTransition]:
        """获取转换历史"""
        return self._transition_history.copy()
    
    @property
    def created_at(self) -> datetime:
        """获取创建时间"""
        return self._created_at
    
    @property
    def last_updated(self) -> datetime:
        """获取最后更新时间"""
        return self._last_updated
    
    @property
    def error(self) -> Optional[Exception]:
        """获取最近错误"""
        return self._error
    
    def register_callback(
        self,
        event: str,
        callback: Callable[['AgentLifecycle', ...], None],
    ) -> None:
        """
        注册生命周期回调
        
        Args:
            event: 事件名称
            callback: 回调函数
        """
        if self._callbacks is None:
            return
            
        if hasattr(self._callbacks, f"on_{event}"):
            callback_list = getattr(self._callbacks, f"on_{event}")
            if isinstance(callback_list, list):
                callback_list.append(callback)
    
    def _execute_callbacks(
        self,
        from_state: AgentState,
        to_state: AgentState,
    ) -> None:
        """执行状态转换回调"""
        if self._callbacks is None:
            return
            
        # 通用状态变化回调
        for callback in self._callbacks.on_state_change:
            try:
                callback(self, from_state, to_state)
            except Exception:
                pass  # 不中断转换流程
        
        # 特定状态回调
        state_event_map = {
            AgentState.CREATED: "created",
            AgentState.INITIALIZING: "initializing",
            AgentState.READY: "ready",
            AgentState.RUNNING: "running",
            AgentState.PAUSED: "paused",
            AgentState.STOPPED: "stopped",
            AgentState.DISPOSED: "disposed",
        }
        
        if to_state in state_event_map:
            event_name = state_event_map[to_state]
            if hasattr(self._callbacks, f"on_{event_name}"):
                for callback in getattr(self._callbacks, f"on_{event_name}"):
                    try:
                        callback(self)
                    except Exception:
                        pass
    
    def transition_to(
        self,
        target_state: AgentState,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        执行状态转换
        
        Args:
            target_state: 目标状态
            reason: 转换原因
            metadata: 附加元数据
            
        Returns:
            bool: 转换是否成功
            
        Raises:
            InvalidTransitionError: 无效的状态转换
        """
        if self._lock:
            raise InvalidTransitionError(
                self._state.value,
                target_state.value,
                "Transition in progress"
            )
        
        # 验证转换是否合法
        if not self._validator.is_valid_transition(self._state, target_state):
            raise InvalidTransitionError(
                self._state.value,
                target_state.value,
                f"No valid transition from {self._state.value} to {target_state.value}"
            )
        
        self._lock = True
        try:
            from_state = self._state
            
            # 记录转换
            transition = LifecycleTransition(
                from_state=from_state,
                to_state=target_state,
                timestamp=datetime.now(),
                reason=reason,
                metadata=metadata or {},
            )
            self._transition_history.append(transition)
            
            # 更新状态
            self._state = target_state
            self._last_updated = datetime.now()
            self._error = None
            
            # 执行回调
            self._execute_callbacks(from_state, target_state)
            
            return True
            
        finally:
            self._lock = False
    
    def initialize(self, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        初始化 Agent
        
        Args:
            metadata: 初始化元数据
            
        Returns:
            bool: 是否成功
        """
        return self.transition_to(
            AgentState.INITIALIZING,
            reason="Agent initialization",
            metadata=metadata,
        )
    
    def ready(self, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        将 Agent 标记为就绪
        
        Args:
            metadata: 就绪元数据
            
        Returns:
            bool: 是否成功
        """
        return self.transition_to(
            AgentState.READY,
            reason="Agent ready",
            metadata=metadata,
        )
    
    def start(self, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        启动 Agent
        
        Args:
            metadata: 启动元数据
            
        Returns:
            bool: 是否成功
        """
        return self.transition_to(
            AgentState.RUNNING,
            reason="Agent started",
            metadata=metadata,
        )
    
    def pause(self, reason: str = "", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        暂停 Agent
        
        Args:
            reason: 暂停原因
            metadata: 暂停元数据
            
        Returns:
            bool: 是否成功
        """
        return self.transition_to(
            AgentState.PAUSED,
            reason=reason or "Agent paused",
            metadata=metadata,
        )
    
    def resume(self, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        恢复 Agent 运行
        
        Args:
            metadata: 恢复元数据
            
        Returns:
            bool: 是否成功
        """
        return self.transition_to(
            AgentState.RUNNING,
            reason="Agent resumed",
            metadata=metadata,
        )
    
    def stop(self, reason: str = "", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        停止 Agent
        
        Args:
            reason: 停止原因
            metadata: 停止元数据
            
        Returns:
            bool: 是否成功
        """
        return self.transition_to(
            AgentState.STOPPED,
            reason=reason or "Agent stopped",
            metadata=metadata,
        )
    
    def dispose(self, reason: str = "", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        释放 Agent 资源
        
        Args:
            reason: 释放原因
            metadata: 释放元数据
            
        Returns:
            bool: 是否成功
        """
        return self.transition_to(
            AgentState.DISPOSED,
            reason=reason or "Agent disposed",
            metadata=metadata,
        )
    
    def set_error(self, error: Exception, reason: str = "") -> bool:
        """
        设置错误状态
        
        Args:
            error: 异常对象
            reason: 错误原因
            
        Returns:
            bool: 是否成功
        """
        self._error = error
        return self.transition_to(
            AgentState.ERROR,
            reason=reason or str(error),
            metadata={"error_type": type(error).__name__},
        )
    
    def reset(self) -> bool:
        """
        重置 Agent 到创建状态
        
        Returns:
            bool: 是否成功
        """
        self._state = AgentState.CREATED
        self._error = None
        self._transition_history.clear()
        return True
    
    def add_rule(self, rule: TransitionRule) -> None:
        """
        添加转换规则
        
        Args:
            rule: 转换规则
        """
        self._rules.append(rule)
        self._validator = TransitionValidator(self._rules)
    
    def get_state_duration(self, state: AgentState) -> float:
        """
        获取 Agent 处于某个状态的时间（秒）
        
        Args:
            state: 目标状态
            
        Returns:
            float: 状态持续时间
        """
        if not self._transition_history:
            return 0.0
            
        total_duration = 0.0
        last_time = self._created_at
        
        for transition in self._transition_history:
            if transition.from_state == state:
                total_duration += (transition.timestamp - last_time).total_seconds()
            last_time = transition.timestamp
        
        # 当前状态
        if self._state == state:
            total_duration += (datetime.now() - last_time).total_seconds()
            
        return total_duration
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_id": self.agent_id,
            "state": self._state.value,
            "is_active": self.is_active,
            "is_terminal": self.is_terminal,
            "can_transition_to": [s.value for s in self.can_transition_to],
            "created_at": self._created_at.isoformat(),
            "last_updated": self._last_updated.isoformat(),
            "has_error": self._error is not None,
            "transition_count": len(self._transition_history),
        }
    
    def __repr__(self) -> str:
        return f"AgentLifecycle(id={self.agent_id}, state={self._state.value})"
