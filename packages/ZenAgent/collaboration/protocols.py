"""
协作协议定义
定义 Agent 间协作的通信协议
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid


class ProtocolType(Enum):
    """协议类型枚举"""
    DIRECT = "direct"                 # 直接通信
    BROADCAST = "broadcast"          # 广播
    ANYCAST = "anycast"              # 任播（任一合适节点）
    MULTICAST = "multicast"          # 多播（多个指定节点）
    HIERARCHICAL = "hierarchical"    # 层级协作


class MessagePriority(Enum):
    """消息优先级枚举"""
    LOW = 0      # 低优先级
    NORMAL = 1   # 普通优先级
    HIGH = 2    # 高优先级
    URGENT = 3  # 紧急


@dataclass
class CollaborationMessage:
    """
    协作消息
    
    Agent 间传递的协作消息
    """
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    protocol: ProtocolType = ProtocolType.DIRECT
    
    # 发送方
    sender_id: str = ""
    sender_name: str = ""
    
    # 接收方
    receiver_id: Optional[str] = None
    receiver_ids: List[str] = field(default_factory=list)  # 用于多播
    
    # 消息内容
    content_type: str = "text"  # text, json, binary
    content: str = ""
    
    # 元数据
    priority: MessagePriority = MessagePriority.NORMAL
    correlation_id: Optional[str] = None  # 用于关联请求和响应
    reply_to: Optional[str] = None  # 回复目标消息 ID
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    # 自定义数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_broadcast(self) -> bool:
        """是否广播消息"""
        return self.protocol == ProtocolType.BROADCAST
    
    @property
    def is_reply(self) -> bool:
        """是否是回复消息"""
        return self.reply_to is not None
    
    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def set_expiry(self, seconds: int) -> None:
        """设置过期时间"""
        from datetime import timedelta
        self.expires_at = datetime.now() + timedelta(seconds=seconds)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "protocol": self.protocol.value,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "receiver_id": self.receiver_id,
            "receiver_ids": self.receiver_ids,
            "content_type": self.content_type,
            "content": self.content,
            "priority": self.priority.value,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborationMessage":
        """从字典创建"""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
        
        expires_at = data.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            protocol=ProtocolType(data.get("protocol", "direct")),
            sender_id=data.get("sender_id", ""),
            sender_name=data.get("sender_name", ""),
            receiver_id=data.get("receiver_id"),
            receiver_ids=data.get("receiver_ids", []),
            content_type=data.get("content_type", "text"),
            content=data.get("content", ""),
            priority=MessagePriority(data.get("priority", 1)),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
            created_at=created_at,
            expires_at=expires_at,
            metadata=data.get("metadata", {}),
        )


@dataclass
class CollaborationRequest:
    """
    协作请求
    
    向其他 Agent 请求协作
    """
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # 请求者
    requester_id: str = ""
    requester_name: str = ""
    
    # 任务描述
    task_type: str = ""  # analysis, generation, review, etc.
    task_description: str = ""
    task_data: Dict[str, Any] = field(default_factory=dict)
    
    # 协作需求
    required_capabilities: List[str] = field(default_factory=list)
    max_participants: int = 1
    
    # 约束条件
    timeout_seconds: int = 60
    priority: MessagePriority = MessagePriority.NORMAL
    
    # 策略
    allow_partial_result: bool = True  # 允许部分结果
    fallback_enabled: bool = True      # 启用降级策略
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "requester_id": self.requester_id,
            "requester_name": self.requester_name,
            "task_type": self.task_type,
            "task_description": self.task_description,
            "task_data": self.task_data,
            "required_capabilities": self.required_capabilities,
            "max_participants": self.max_participants,
            "timeout_seconds": self.timeout_seconds,
            "priority": self.priority.value,
            "allow_partial_result": self.allow_partial_result,
            "fallback_enabled": self.fallback_enabled,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborationRequest":
        """从字典创建"""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
        
        expires_at = data.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        
        return cls(
            request_id=data.get("request_id", str(uuid.uuid4())),
            requester_id=data.get("requester_id", ""),
            requester_name=data.get("requester_name", ""),
            task_type=data.get("task_type", ""),
            task_description=data.get("task_description", ""),
            task_data=data.get("task_data", {}),
            required_capabilities=data.get("required_capabilities", []),
            max_participants=data.get("max_participants", 1),
            timeout_seconds=data.get("timeout_seconds", 60),
            priority=MessagePriority(data.get("priority", 1)),
            allow_partial_result=data.get("allow_partial_result", True),
            fallback_enabled=data.get("fallback_enabled", True),
            created_at=created_at,
            expires_at=expires_at,
        )


@dataclass
class CollaborationResponse:
    """
    协作响应
    
    对协作请求的响应
    """
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""  # 对应的请求 ID
    
    # 响应者
    responder_id: str = ""
    responder_name: str = ""
    
    # 响应状态
    accepted: bool = False
    status: str = "pending"  # pending, accepted, declined, completed, failed
    
    # 结果数据
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # 进度（用于长时间任务）
    progress: float = 0.0  # 0.0 - 1.0
    progress_message: str = ""
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "response_id": self.response_id,
            "request_id": self.request_id,
            "responder_id": self.responder_id,
            "responder_name": self.responder_name,
            "accepted": self.accepted,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborationResponse":
        """从字典创建"""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
        
        completed_at = data.get("completed_at")
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)
        
        return cls(
            response_id=data.get("response_id", str(uuid.uuid4())),
            request_id=data.get("request_id", ""),
            responder_id=data.get("responder_id", ""),
            responder_name=data.get("responder_name", ""),
            accepted=data.get("accepted", False),
            status=data.get("status", "pending"),
            result=data.get("result"),
            error=data.get("error"),
            progress=data.get("progress", 0.0),
            progress_message=data.get("progress_message", ""),
            created_at=created_at,
            completed_at=completed_at,
        )


class CollaborationProtocol:
    """
    协作协议
    
    定义 Agent 间协作的标准协议
    """
    
    # 协议版本
    VERSION = "1.0.0"
    
    # 支持的任务类型
    TASK_TYPES = [
        "analysis",      # 分析任务
        "generation",     # 生成任务
        "review",        # 审查任务
        "optimization",  # 优化任务
        "research",      # 研究任务
        "coordination",  # 协调任务
    ]
    
    @staticmethod
    def create_request(
        requester_id: str,
        requester_name: str,
        task_type: str,
        task_description: str,
        **kwargs
    ) -> CollaborationRequest:
        """
        创建协作请求
        
        Args:
            requester_id: 请求者 ID
            requester_name: 请求者名称
            task_type: 任务类型
            task_description: 任务描述
            **kwargs: 其他参数
            
        Returns:
            CollaborationRequest: 协作请求
        """
        return CollaborationRequest(
            requester_id=requester_id,
            requester_name=requester_name,
            task_type=task_type,
            task_description=task_description,
            **kwargs
        )
    
    @staticmethod
    def create_response(
        request_id: str,
        responder_id: str,
        responder_name: str,
        accepted: bool = True,
        **kwargs
    ) -> CollaborationResponse:
        """
        创建协作响应
        
        Args:
            request_id: 请求 ID
            responder_id: 响应者 ID
            responder_name: 响应者名称
            accepted: 是否接受
            **kwargs: 其他参数
            
        Returns:
            CollaborationResponse: 协作响应
        """
        return CollaborationResponse(
            request_id=request_id,
            responder_id=responder_id,
            responder_name=responder_name,
            accepted=accepted,
            **kwargs
        )
    
    @staticmethod
    def create_message(
        sender_id: str,
        sender_name: str,
        content: str,
        receiver_id: Optional[str] = None,
        **kwargs
    ) -> CollaborationMessage:
        """
        创建协作消息
        
        Args:
            sender_id: 发送者 ID
            sender_name: 发送者名称
            content: 消息内容
            receiver_id: 接收者 ID
            **kwargs: 其他参数
            
        Returns:
            CollaborationMessage: 协作消息
        """
        return CollaborationMessage(
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            receiver_id=receiver_id,
            **kwargs
        )
    
    @staticmethod
    def validate_task_type(task_type: str) -> bool:
        """验证任务类型是否有效"""
        return task_type in CollaborationProtocol.TASK_TYPES
    
    @staticmethod
    def get_supported_task_types() -> List[str]:
        """获取支持的任务类型"""
        return list(CollaborationProtocol.TASK_TYPES)
