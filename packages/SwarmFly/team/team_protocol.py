"""
团队协议

定义团队成员间的通信协议
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable
from datetime import datetime
import threading
import uuid


class MessageType(Enum):
    """消息类型枚举"""
    # 协作消息
    TASK_ASSIGN = "task_assign"           # 任务分配
    TASK_COMPLETE = "task_complete"        # 任务完成
    TASK_REPORT = "task_report"            # 任务报告
    
    # 协调消息
    COORDINATE = "coordinate"              # 协调请求
    SYNC = "sync"                          # 同步请求
    HEARTBEAT = "heartbeat"                # 心跳
    
    # 角色消息
    ELECTION = "election"                  # 选举
    LEADERSHIP = "leadership"              # 领导权变更
    
    # 状态消息
    STATUS_UPDATE = "status_update"        # 状态更新
    ALERT = "alert"                        # 告警
    ERROR = "error"                        # 错误
    
    # 自定义
    CUSTOM = "custom"                       # 自定义消息


@dataclass
class ProtocolMessage:
    """
    协议消息
    
    表示团队成员间传输的消息
    """
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # 消息类型
    message_type: MessageType = MessageType.CUSTOM
    
    # 发送者和接收者
    sender_id: str = ""
    target_id: Optional[str] = None  # None 表示广播
    
    # 内容
    subject: str = ""
    content: Any = None
    
    # 上下文
    task_id: Optional[str] = None
    role: Optional[str] = None
    
    # 时间戳
    timestamp: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    # 状态
    acknowledged: bool = False
    processed: bool = False
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_broadcast(self) -> bool:
        """是否为广播消息"""
        return self.target_id is None
    
    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def acknowledge(self) -> None:
        """确认消息"""
        self.acknowledged = True
    
    def mark_processed(self) -> None:
        """标记为已处理"""
        self.processed = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "target_id": self.target_id,
            "subject": self.subject,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
            "processed": self.processed,
        }


class TeamProtocol:
    """
    团队协议
    
    定义团队成员间的通信和协作协议
    """
    
    def __init__(self, team_id: str, node_id: str):
        """
        初始化团队协议
        
        Args:
            team_id: 团队 ID
            node_id: 节点 ID
        """
        self.team_id = team_id
        self.node_id = node_id
        
        # 消息队列
        self._inbox: List[ProtocolMessage] = []
        self._outbox: List[ProtocolMessage] = []
        self._history: List[ProtocolMessage] = []
        self._max_history = 1000
        
        # 订阅者
        self._subscribers: Dict[MessageType, List[Callable]] = {
            msg_type: [] for msg_type in MessageType
        }
        self._subscribers[MessageType.CUSTOM] = []
        
        # 锁
        self._lock = threading.RLock()
        
        # 统计
        self._sent_count = 0
        self._received_count = 0
        self._processed_count = 0
    
    def send_message(
        self,
        message_type: MessageType,
        content: Any,
        target_id: Optional[str] = None,
        subject: str = "",
        task_id: Optional[str] = None,
        role: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> ProtocolMessage:
        """
        发送消息
        
        Args:
            message_type: 消息类型
            content: 内容
            target_id: 目标 ID（None 表示广播）
            subject: 主题
            task_id: 关联的任务 ID
            role: 关联的角色
            ttl: 生存时间（秒）
            
        Returns:
            ProtocolMessage: 发送的消息
        """
        expires_at = None
        if ttl:
            from datetime import timedelta
            expires_at = datetime.now() + timedelta(seconds=ttl)
        
        message = ProtocolMessage(
            message_type=message_type,
            sender_id=self.node_id,
            target_id=target_id,
            subject=subject,
            content=content,
            task_id=task_id,
            role=role,
            expires_at=expires_at,
        )
        
        with self._lock:
            self._outbox.append(message)
            self._history.append(message)
            self._sent_count += 1
            
            # 限制历史大小
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
        
        return message
    
    def receive_message(self, message: ProtocolMessage) -> bool:
        """
        接收消息
        
        Args:
            message: 消息对象
            
        Returns:
            bool: 是否接收成功
        """
        # 检查是否是广播或定向消息
        if message.target_id and message.target_id != self.node_id:
            return False
        
        # 检查是否过期
        if message.is_expired:
            return False
        
        with self._lock:
            self._inbox.append(message)
            self._received_count += 1
        
        # 触发订阅者
        self._notify_subscribers(message)
        
        return True
    
    def process_inbox(self) -> List[ProtocolMessage]:
        """
        处理收件箱
        
        Returns:
            List[ProtocolMessage]: 处理的消息列表
        """
        processed = []
        
        with self._lock:
            for message in self._inbox:
                if not message.processed:
                    message.mark_processed()
                    processed.append(message)
                    self._processed_count += 1
            
            # 清除已处理的消息
            self._inbox = [m for m in self._inbox if not m.processed]
        
        return processed
    
    def acknowledge_message(self, message_id: str) -> bool:
        """
        确认消息
        
        Args:
            message_id: 消息 ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            for message in self._history:
                if message.message_id == message_id:
                    message.acknowledge()
                    return True
        return False
    
    def subscribe(
        self,
        message_type: MessageType,
        callback: Callable[[ProtocolMessage], None],
    ) -> None:
        """
        订阅消息
        
        Args:
            message_type: 消息类型
            callback: 回调函数
        """
        with self._lock:
            if message_type not in self._subscribers:
                self._subscribers[message_type] = []
            self._subscribers[message_type].append(callback)
    
    def unsubscribe(
        self,
        message_type: MessageType,
        callback: Callable,
    ) -> bool:
        """
        取消订阅
        
        Args:
            message_type: 消息类型
            callback: 回调函数
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            if message_type in self._subscribers:
                try:
                    self._subscribers[message_type].remove(callback)
                    return True
                except ValueError:
                    pass
        return False
    
    def _notify_subscribers(self, message: ProtocolMessage) -> None:
        """通知订阅者"""
        with self._lock:
            # 先通知特定类型
            if message.message_type in self._subscribers:
                for callback in self._subscribers[message.message_type]:
                    try:
                        callback(message)
                    except Exception:
                        pass
            
            # 再通知通用订阅者
            for callback in self._subscribers[MessageType.CUSTOM]:
                try:
                    callback(message)
                except Exception:
                    pass
    
    def get_inbox_count(self) -> int:
        """获取收件箱消息数"""
        return len(self._inbox)
    
    def get_outbox_count(self) -> int:
        """获取发件箱消息数"""
        return len(self._outbox)
    
    def get_unprocessed_messages(self) -> List[ProtocolMessage]:
        """获取未处理的消息"""
        return [m for m in self._inbox if not m.processed]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "team_id": self.team_id,
            "node_id": self.node_id,
            "inbox_count": len(self._inbox),
            "outbox_count": len(self._outbox),
            "history_size": len(self._history),
            "sent_count": self._sent_count,
            "received_count": self._received_count,
            "processed_count": self._processed_count,
        }
    
    # ==================== 便捷方法 ====================
    
    def send_task_assignment(
        self,
        target_id: str,
        task_id: str,
        content: Dict[str, Any],
    ) -> ProtocolMessage:
        """发送任务分配"""
        return self.send_message(
            message_type=MessageType.TASK_ASSIGN,
            target_id=target_id,
            task_id=task_id,
            subject="Task Assignment",
            content=content,
        )
    
    def send_task_complete(
        self,
        target_id: str,
        task_id: str,
        result: Any,
    ) -> ProtocolMessage:
        """发送任务完成"""
        return self.send_message(
            message_type=MessageType.TASK_COMPLETE,
            target_id=target_id,
            task_id=task_id,
            subject="Task Complete",
            content=result,
        )
    
    def send_status_update(
        self,
        status: Dict[str, Any],
        broadcast: bool = True,
    ) -> ProtocolMessage:
        """发送状态更新"""
        return self.send_message(
            message_type=MessageType.STATUS_UPDATE,
            target_id=None if broadcast else self.node_id,
            subject="Status Update",
            content=status,
        )
    
    def send_heartbeat(
        self,
        health: Dict[str, Any],
    ) -> ProtocolMessage:
        """发送心跳"""
        return self.send_message(
            message_type=MessageType.HEARTBEAT,
            subject="Heartbeat",
            content=health,
            ttl=30,  # 30秒过期
        )
    
    def send_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "warning",
    ) -> ProtocolMessage:
        """发送告警"""
        return self.send_message(
            message_type=MessageType.ALERT,
            subject=f"Alert: {alert_type}",
            content={"alert_type": alert_type, "message": message, "severity": severity},
        )
    
    def broadcast_error(
        self,
        error: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ProtocolMessage:
        """广播错误"""
        return self.send_message(
            message_type=MessageType.ERROR,
            subject="Error Report",
            content={"error": error, "context": context or {}},
        )
