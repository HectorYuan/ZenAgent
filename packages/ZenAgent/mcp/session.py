"""
MCP 会话管理和上下文传递
提供会话生命周期管理和状态追踪
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import uuid
import asyncio


class MCPSessionState(Enum):
    """会话状态枚举"""
    INITIAL = "initial"           # 初始状态
    INITIALIZING = "initializing"  # 初始化中
    READY = "ready"               # 就绪
    BUSY = "busy"                 # 忙碌（处理请求）
    IDLE = "idle"                 # 空闲
    CLOSING = "closing"          # 关闭中
    CLOSED = "closed"             # 已关闭
    ERROR = "error"               # 错误状态


@dataclass
class MCPSessionContext:
    """
    会话上下文
    
    存储会话相关的状态和历史数据
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # 协议信息
    protocol_version: str = "1.0.0"
    client_info: Optional[Dict[str, str]] = None
    server_info: Optional[Dict[str, str]] = None
    
    # 能力协商
    capabilities: Dict[str, Any] = field(default_factory=dict)
    negotiated_capabilities: Dict[str, Any] = field(default_factory=dict)
    
    # 消息历史（用于上下文传递）
    message_history: List[Dict[str, Any]] = field(default_factory=list)
    max_history_size: int = 100
    
    # 自定义上下文数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, message: Dict[str, Any]) -> None:
        """添加消息到历史记录"""
        self.message_history.append({
            "timestamp": datetime.now().isoformat(),
            "message": message,
        })
        self.updated_at = datetime.now()
        
        # 限制历史大小
        if len(self.message_history) > self.max_history_size:
            self.message_history = self.message_history[-self.max_history_size:]
    
    def get_recent_messages(self, count: int = 10) -> List[Dict[str, Any]]:
        """获取最近的 N 条消息"""
        return self.message_history[-count:]
    
    def set_metadata(self, key: str, value: Any) -> None:
        """设置元数据"""
        self.metadata[key] = value
        self.updated_at = datetime.now()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取元数据"""
        return self.metadata.get(key, default)
    
    def age_seconds(self) -> float:
        """获取会话创建后的秒数"""
        return (datetime.now() - self.created_at).total_seconds()
    
    def idle_seconds(self) -> float:
        """获取上次更新后的空闲秒数"""
        return (datetime.now() - self.updated_at).total_seconds()


@dataclass
class MCPSession:
    """
    MCP 会话管理类
    
    管理单个 MCP 连接的会话生命周期
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: MCPSessionState = MCPSessionState.INITIAL
    context: MCPSessionContext = field(default_factory=MCPSessionContext)
    
    # 超时配置
    idle_timeout: int = 300  # 秒
    max_lifetime: int = 3600  # 秒
    
    # 回调函数
    _state_change_callbacks: List[Callable[[MCPSessionState, MCPSessionState], None]] = field(default_factory=list)
    _message_callbacks: List[Callable[[Dict[str, Any]], None]] = field(default_factory=list)
    
    def __post_init__(self):
        """初始化会话"""
        self.context.session_id = self.session_id
    
    @property
    def is_alive(self) -> bool:
        """检查会话是否存活"""
        return self.state not in [
            MCPSessionState.CLOSED,
            MCPSessionState.ERROR,
        ]
    
    @property
    def is_ready(self) -> bool:
        """检查会话是否就绪"""
        return self.state == MCPSessionState.READY
    
    @property
    def is_idle(self) -> bool:
        """检查会话是否空闲"""
        return self.state == MCPSessionState.IDLE
    
    def change_state(self, new_state: MCPSessionState) -> None:
        """
        变更会话状态
        
        Args:
            new_state: 新的会话状态
        """
        old_state = self.state
        self.state = new_state
        self.context.updated_at = datetime.now()
        
        # 触发回调
        for callback in self._state_change_callbacks:
            try:
                callback(old_state, new_state)
            except Exception:
                pass
    
    def on_state_change(
        self,
        callback: Callable[[MCPSessionState, MCPSessionState], None]
    ) -> None:
        """注册状态变更回调"""
        self._state_change_callbacks.append(callback)
    
    def on_message(
        self,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """注册消息回调"""
        self._message_callbacks.append(callback)
    
    def receive_message(self, message: Dict[str, Any]) -> None:
        """
        接收消息
        
        Args:
            message: 消息字典
        """
        self.context.add_message(message)
        self.context.updated_at = datetime.now()
        
        # 触发消息回调
        for callback in self._message_callbacks:
            try:
                callback(message)
            except Exception:
                pass
    
    def initialize(
        self,
        client_info: Dict[str, str],
        protocol_version: str = "1.0.0"
    ) -> Dict[str, Any]:
        """
        初始化会话
        
        Args:
            client_info: 客户端信息
            protocol_version: 协议版本
            
        Returns:
            Dict[str, Any]: 初始化结果
        """
        self.change_state(MCPSessionState.INITIALIZING)
        
        self.context.protocol_version = protocol_version
        self.context.client_info = client_info
        
        # 生成服务端信息
        self.context.server_info = {
            "name": "ZenAgent MCP Server",
            "version": "1.0.0",
        }
        
        # 协商能力
        self.context.negotiated_capabilities = {
            "tools": True,
            "resources": True,
            "prompts": True,
        }
        
        self.change_state(MCPSessionState.READY)
        
        return {
            "protocolVersion": self.context.protocol_version,
            "serverInfo": self.context.server_info,
            "capabilities": self.context.negotiated_capabilities,
        }
    
    def begin_processing(self) -> None:
        """开始处理请求（将会话状态设为忙碌）"""
        if self.state == MCPSessionState.READY:
            self.change_state(MCPSessionState.BUSY)
        elif self.state == MCPSessionState.IDLE:
            self.change_state(MCPSessionState.BUSY)
    
    def end_processing(self) -> None:
        """结束处理请求（将会话状态设为空闲）"""
        if self.state == MCPSessionState.BUSY:
            self.change_state(MCPSessionState.IDLE)
    
    def ping(self) -> bool:
        """
        心跳检测
        
        Returns:
            bool: 会话是否存活
        """
        if not self.is_alive:
            return False
        
        # 检查空闲超时
        if self.context.idle_seconds() > self.idle_timeout:
            self.change_state(MCPSessionState.ERROR)
            return False
        
        # 检查最大生命周期
        if self.context.age_seconds() > self.max_lifetime:
            self.change_state(MCPSessionState.ERROR)
            return False
        
        return True
    
    def close(self) -> None:
        """关闭会话"""
        self.change_state(MCPSessionState.CLOSING)
        self.change_state(MCPSessionState.CLOSED)
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取会话信息
        
        Returns:
            Dict[str, Any]: 会话详细信息
        """
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "created_at": self.context.created_at.isoformat(),
            "updated_at": self.context.updated_at.isoformat(),
            "age_seconds": self.context.age_seconds(),
            "idle_seconds": self.context.idle_seconds(),
            "client_info": self.context.client_info,
            "server_info": self.context.server_info,
            "message_count": len(self.context.message_history),
        }
    
    def export_context(self) -> Dict[str, Any]:
        """
        导出会话上下文（用于上下文传递）
        
        Returns:
            Dict[str, Any]: 上下文数据
        """
        return {
            "session_id": self.session_id,
            "protocol_version": self.context.protocol_version,
            "capabilities": self.context.negotiated_capabilities,
            "metadata": self.context.metadata,
            "recent_messages": self.context.get_recent_messages(20),
        }
    
    @classmethod
    def from_context(cls, context_data: Dict[str, Any]) -> "MCPSession":
        """
        从导出的上下文创建会话
        
        Args:
            context_data: 上下文数据
            
        Returns:
            MCPSession: 新建的会话对象
        """
        session = cls()
        session.session_id = context_data.get("session_id", session.session_id)
        session.context.session_id = session.session_id
        session.context.protocol_version = context_data.get("protocol_version", "1.0.0")
        session.context.negotiated_capabilities = context_data.get("capabilities", {})
        session.context.metadata = context_data.get("metadata", {})
        
        # 恢复历史消息
        recent_messages = context_data.get("recent_messages", [])
        for msg_data in recent_messages:
            session.context.add_message(msg_data.get("message", {}))
        
        session.change_state(MCPSessionState.READY)
        return session


class MCPSessionManager:
    """
    MCP 会话管理器
    
    管理多个会话的生命周期
    """
    
    def __init__(self):
        """初始化会话管理器"""
        self._sessions: Dict[str, MCPSession] = {}
        self._default_idle_timeout: int = 300
        self._default_max_lifetime: int = 3600
    
    def create_session(
        self,
        idle_timeout: Optional[int] = None,
        max_lifetime: Optional[int] = None
    ) -> MCPSession:
        """
        创建新会话
        
        Args:
            idle_timeout: 空闲超时时间（秒）
            max_lifetime: 最大生命周期（秒）
            
        Returns:
            MCPSession: 新建的会话
        """
        session = MCPSession(
            idle_timeout=idle_timeout or self._default_idle_timeout,
            max_lifetime=max_lifetime or self._default_max_lifetime,
        )
        self._sessions[session.session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[MCPSession]:
        """
        获取会话
        
        Args:
            session_id: 会话 ID
            
        Returns:
            Optional[MCPSession]: 会话对象，不存在返回 None
        """
        return self._sessions.get(session_id)
    
    def remove_session(self, session_id: str) -> bool:
        """
        移除会话
        
        Args:
            session_id: 会话 ID
            
        Returns:
            bool: 是否成功移除
        """
        session = self._sessions.pop(session_id, None)
        if session is not None:
            session.close()
            return True
        return False
    
    def list_sessions(self) -> List[MCPSession]:
        """
        列出所有会话
        
        Returns:
            List[MCPSession]: 会话列表
        """
        return list(self._sessions.values())
    
    def list_active_sessions(self) -> List[MCPSession]:
        """
        列出活跃会话
        
        Returns:
            List[MCPSession]: 活跃会话列表
        """
        return [s for s in self._sessions.values() if s.is_alive]
    
    def cleanup_expired(self) -> int:
        """
        清理过期会话
        
        Returns:
            int: 清理的会话数量
        """
        expired_ids = []
        for session_id, session in self._sessions.items():
            if not session.ping():
                expired_ids.append(session_id)
        
        for session_id in expired_ids:
            self.remove_session(session_id)
        
        return len(expired_ids)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取会话统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        total = len(self._sessions)
        active = len([s for s in self._sessions.values() if s.is_alive])
        ready = len([s for s in self._sessions.values() if s.is_ready])
        busy = len([s for s in self._sessions.values() if s.state == MCPSessionState.BUSY])
        
        return {
            "total_sessions": total,
            "active_sessions": active,
            "ready_sessions": ready,
            "busy_sessions": busy,
        }
