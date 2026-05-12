"""
会话状态机 - Session State Machine

管理会话生命周期和状态转换
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, Any, Optional, List, Callable, Set
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import uuid


class SessionState(Enum):
    """会话状态"""
    INITIAL = "initial"           # 初始状态
    ACTIVE = "active"             # 活跃状态
    IDLE = "idle"                 # 空闲状态
    SUSPENDED = "suspended"       # 暂停状态
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败状态
    EXPIRED = "expired"           # 已过期
    TERMINATED = "terminated"     # 已终止


class SessionEvent(Enum):
    """会话事件"""
    START = "start"               # 开始会话
    RESUME = "resume"             # 恢复会话
    PAUSE = "pause"              # 暂停会话
    IDLE_TIMEOUT = "idle_timeout" # 空闲超时
    ACTIVITY = "activity"         # 活动
    COMPLETE = "complete"         # 完成会话
    FAIL = "fail"                # 会话失败
    EXPIRE = "expire"            # 会话过期
    TERMINATE = "terminate"      # 终止会话
    RESET = "reset"              # 重置会话
    CUSTOM = "custom"            # 自定义事件


@dataclass
class StateTransition:
    """状态转换"""
    from_state: SessionState
    to_state: SessionState
    event: SessionEvent
    condition: Optional[Callable[["Session"], bool]] = None
    action: Optional[Callable[["Session", SessionEvent], None]] = None
    timestamp: datetime = field(default_factory=datetime.now)


class Session:
    """
    会话
    
    代表一个完整的对话会话，包含状态管理和事件处理。
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        初始化会话
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            metadata: 元数据
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id
        self.state = SessionState.INITIAL
        self.metadata = metadata or {}
        
        self._created_at = datetime.now()
        self._updated_at = datetime.now()
        self._last_activity_at = datetime.now()
        self._history: List[StateTransition] = []
        self._context: Dict[str, Any] = {}
        self._listeners: Dict[SessionEvent, List[Callable]] = {e: [] for e in SessionEvent}
        self._error: Optional[str] = None
    
    @property
    def created_at(self) -> datetime:
        """创建时间"""
        return self._created_at
    
    @property
    def updated_at(self) -> datetime:
        """更新时间"""
        return self._updated_at
    
    @property
    def last_activity_at(self) -> datetime:
        """最后活动时间"""
        return self._last_activity_at
    
    @property
    def is_active(self) -> bool:
        """是否活跃"""
        return self.state == SessionState.ACTIVE
    
    @property
    def is_terminal(self) -> bool:
        """是否处于终态"""
        return self.state in [
            SessionState.COMPLETED,
            SessionState.FAILED,
            SessionState.EXPIRED,
            SessionState.TERMINATED
        ]
    
    def send_event(self, event: SessionEvent, data: Optional[Dict[str, Any]] = None) -> bool:
        """
        发送事件
        
        Args:
            event: 事件
            data: 事件数据
            
        Returns:
            bool: 是否成功
        """
        # 检查转换
        transition = self._get_valid_transition(event)
        
        if not transition:
            return False
        
        # 执行转换前检查
        if transition.condition and not transition.condition(self):
            return False
        
        # 记录历史
        self._history.append(StateTransition(
            from_state=self.state,
            to_state=transition.to_state,
            event=event
        ))
        
        # 更新状态
        old_state = self.state
        self.state = transition.to_state
        self._updated_at = datetime.now()
        
        # 执行转换动作
        if transition.action:
            transition.action(self, event)
        
        # 触发监听器
        self._trigger_listeners(event, old_state, transition.to_state)
        
        # 存储事件数据
        if data:
            self._context[f"last_event_{event.value}"] = data
        
        return True
    
    def start(self) -> bool:
        """开始会话"""
        return self.send_event(SessionEvent.START)
    
    def resume(self) -> bool:
        """恢复会话"""
        return self.send_event(SessionEvent.RESUME)
    
    def pause(self) -> bool:
        """暂停会话"""
        return self.send_event(SessionEvent.PAUSE)
    
    def complete(self) -> bool:
        """完成会话"""
        return self.send_event(SessionEvent.COMPLETE)
    
    def fail(self, error: str) -> bool:
        """会话失败"""
        self._error = error
        return self.send_event(SessionEvent.FAIL, {"error": error})
    
    def terminate(self) -> bool:
        """终止会话"""
        return self.send_event(SessionEvent.TERMINATE)
    
    def reset(self) -> bool:
        """重置会话"""
        return self.send_event(SessionEvent.RESET)
    
    def record_activity(self) -> None:
        """记录活动"""
        self._last_activity_at = datetime.now()
        if self.state == SessionState.IDLE:
            self.send_event(SessionEvent.ACTIVITY)
    
    def add_listener(
        self,
        event: SessionEvent,
        callback: Callable[[SessionEvent, SessionState, SessionState], None]
    ) -> None:
        """添加事件监听器"""
        self._listeners[event].append(callback)
    
    def remove_listener(
        self,
        event: SessionEvent,
        callback: Callable
    ) -> None:
        """移除事件监听器"""
        if callback in self._listeners[event]:
            self._listeners[event].remove(callback)
    
    def get_history(self) -> List[StateTransition]:
        """获取状态转换历史"""
        return self._history.copy()
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文"""
        return self._context.get(key, default)
    
    def set_context(self, key: str, value: Any) -> None:
        """设置上下文"""
        self._context[key] = value
        self._updated_at = datetime.now()
    
    def update_context(self, data: Dict[str, Any]) -> None:
        """更新上下文"""
        self._context.update(data)
        self._updated_at = datetime.now()
    
    def get_idle_duration(self) -> float:
        """获取空闲时长（秒）"""
        delta = datetime.now() - self._last_activity_at
        return delta.total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "state": self.state.value,
            "metadata": self.metadata,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
            "last_activity_at": self._last_activity_at.isoformat(),
            "context": self._context,
            "error": self._error,
            "history": [
                {
                    "from_state": t.from_state.value,
                    "to_state": t.to_state.value,
                    "event": t.event.value,
                    "timestamp": t.timestamp.isoformat()
                }
                for t in self._history
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """从字典创建"""
        session = cls(
            session_id=data["session_id"],
            user_id=data.get("user_id"),
            metadata=data.get("metadata", {})
        )
        session.state = SessionState(data["state"])
        session._context = data.get("context", {})
        session._error = data.get("error")
        # 恢复历史
        session._history = [
            StateTransition(
                from_state=SessionState(t["from_state"]),
                to_state=SessionState(t["to_state"]),
                event=SessionEvent(t["event"]),
                timestamp=datetime.fromisoformat(t["timestamp"])
            )
            for t in data.get("history", [])
        ]
        return session
    
    def _get_valid_transition(self, event: SessionEvent) -> Optional[StateTransition]:
        """获取有效的转换"""
        # 定义状态转换规则
        transitions = {
            (SessionState.INITIAL, SessionEvent.START): SessionState.ACTIVE,
            (SessionState.IDLE, SessionEvent.RESUME): SessionState.ACTIVE,
            (SessionState.SUSPENDED, SessionEvent.RESUME): SessionState.ACTIVE,
            (SessionState.ACTIVE, SessionEvent.PAUSE): SessionState.SUSPENDED,
            (SessionState.ACTIVE, SessionEvent.IDLE_TIMEOUT): SessionState.IDLE,
            (SessionState.ACTIVE, SessionEvent.COMPLETE): SessionState.COMPLETED,
            (SessionState.ACTIVE, SessionEvent.FAIL): SessionState.FAILED,
            (SessionState.IDLE, SessionEvent.ACTIVITY): SessionState.ACTIVE,
            (SessionState.IDLE, SessionEvent.IDLE_TIMEOUT): SessionState.EXPIRED,
            (SessionState.ACTIVE, SessionEvent.TERMINATE): SessionState.TERMINATED,
            (SessionState.IDLE, SessionEvent.TERMINATE): SessionState.TERMINATED,
            (SessionState.SUSPENDED, SessionEvent.TERMINATE): SessionState.TERMINATED,
            (SessionState.COMPLETED, SessionEvent.RESET): SessionState.INITIAL,
            (SessionState.FAILED, SessionEvent.RESET): SessionState.INITIAL,
            (SessionState.EXPIRED, SessionEvent.RESET): SessionState.INITIAL,
            (SessionState.TERMINATED, SessionEvent.RESET): SessionState.INITIAL,
        }
        
        target_state = transitions.get((self.state, event))
        if target_state:
            return StateTransition(
                from_state=self.state,
                to_state=target_state,
                event=event
            )
        
        return None
    
    def _trigger_listeners(
        self,
        event: SessionEvent,
        old_state: SessionState,
        new_state: SessionState
    ) -> None:
        """触发监听器"""
        for callback in self._listeners[event]:
            try:
                callback(event, old_state, new_state)
            except Exception:
                pass  # 忽略监听器执行错误


class SessionManager:
    """
    会话管理器
    
    管理多个会话的生命周期。
    """
    
    def __init__(
        self,
        idle_timeout: int = 300,
        max_sessions: int = 1000,
        auto_cleanup: bool = True
    ):
        """
        初始化会话管理器
        
        Args:
            idle_timeout: 空闲超时时间（秒）
            max_sessions: 最大会话数
            auto_cleanup: 是否自动清理
        """
        self.idle_timeout = idle_timeout
        self.max_sessions = max_sessions
        self.auto_cleanup = auto_cleanup
        
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[str, Set[str]] = {}
        self._session_listeners: Dict[str, List[Callable]] = {}
        self._global_listeners: List[Callable] = []
    
    def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        创建会话
        
        Args:
            user_id: 用户 ID
            metadata: 元数据
            
        Returns:
            Session: 创建的会话
        """
        # 检查会话数量限制
        if len(self._sessions) >= self.max_sessions:
            self._cleanup_expired_sessions()
            
            if len(self._sessions) >= self.max_sessions:
                raise RuntimeError("Maximum sessions reached")
        
        session = Session(user_id=user_id, metadata=metadata)
        
        self._sessions[session.session_id] = session
        
        if user_id:
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = set()
            self._user_sessions[user_id].add(session.session_id)
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self._sessions.get(session_id)
    
    def get_user_sessions(self, user_id: str) -> List[Session]:
        """获取用户的所有会话"""
        session_ids = self._user_sessions.get(user_id, set())
        return [
            self._sessions[sid]
            for sid in session_ids
            if sid in self._sessions
        ]
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        if session.user_id and session.user_id in self._user_sessions:
            self._user_sessions[session.user_id].discard(session_id)
        
        del self._sessions[session_id]
        return True
    
    def list_sessions(
        self,
        state: Optional[SessionState] = None,
        user_id: Optional[str] = None
    ) -> List[Session]:
        """
        列出会话
        
        Args:
            state: 状态过滤
            user_id: 用户 ID 过滤
            
        Returns:
            List[Session]: 会话列表
        """
        sessions = list(self._sessions.values())
        
        if state:
            sessions = [s for s in sessions if s.state == state]
        
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]
        
        return sessions
    
    def cleanup_idle_sessions(self) -> int:
        """
        清理空闲会话
        
        Returns:
            int: 清理的会话数
        """
        cleaned = 0
        
        for session in list(self._sessions.values()):
            if session.state == SessionState.IDLE:
                if session.get_idle_duration() > self.idle_timeout:
                    session.send_event(SessionEvent.EXPIRE)
                    cleaned += 1
        
        return cleaned
    
    def _cleanup_expired_sessions(self) -> None:
        """清理过期会话"""
        for session in list(self._sessions.values()):
            if session.state == SessionState.EXPIRED:
                self.delete_session(session.session_id)
    
    def register_session_listener(
        self,
        session_id: str,
        callback: Callable[[Session, SessionEvent], None]
    ) -> None:
        """注册会话监听器"""
        if session_id not in self._session_listeners:
            self._session_listeners[session_id] = []
        self._session_listeners[session_id].append(callback)
    
    def register_global_listener(
        self,
        callback: Callable[[Session, SessionEvent], None]
    ) -> None:
        """注册全局监听器"""
        self._global_listeners.append(callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        state_counts = {}
        for state in SessionState:
            state_counts[state.value] = sum(
                1 for s in self._sessions.values()
                if s.state == state
            )
        
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": state_counts.get("active", 0),
            "idle_sessions": state_counts.get("idle", 0),
            "total_users": len(self._user_sessions),
            "state_distribution": state_counts
        }
