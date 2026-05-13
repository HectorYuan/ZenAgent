"""
同步协议

定义内存同步的消息格式和操作类型
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import threading
import uuid


class SyncOperation(Enum):
    """同步操作枚举"""
    READ = "read"
    WRITE = "write"
    UPDATE = "update"
    DELETE = "delete"
    INVALIDATE = "invalidate"
    SYNC_REQUEST = "sync_request"
    SYNC_RESPONSE = "sync_response"


class SyncState(Enum):
    """同步状态枚举"""
    IDLE = "idle"
    SYNCING = "syncing"
    CONSISTENT = "consistent"
    INCONSISTENT = "inconsistent"
    ERROR = "error"


@dataclass
class SyncMessage:
    """
    同步消息
    
    表示节点间的同步消息
    """
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # 消息类型
    operation: SyncOperation = SyncOperation.READ
    source_node: str = ""
    target_node: Optional[str] = None  # None 表示广播
    
    # 资源信息
    resource_id: str = ""
    resource_type: str = ""
    
    # 数据
    data: Any = None
    version: int = 0
    
    # 时间戳
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 状态
    acknowledged: bool = False
    success: bool = True
    error: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_broadcast(self) -> bool:
        """是否为广播消息"""
        return self.target_node is None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "operation": self.operation.value,
            "source_node": self.source_node,
            "target_node": self.target_node,
            "resource_id": self.resource_id,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
            "success": self.success,
            "error": self.error,
        }


class SyncProtocol:
    """
    同步协议
    
    定义节点间的内存同步协议
    """
    
    def __init__(self, node_id: str):
        """
        初始化同步协议
        
        Args:
            node_id: 节点 ID
        """
        self.node_id = node_id
        self.state = SyncState.IDLE
        
        # 消息队列
        self._pending_messages: Dict[str, SyncMessage] = {}
        self._message_history: List[SyncMessage] = []
        self._max_history = 1000
        
        # 连接的对等节点
        self._peers: Set[str] = set()
        
        # 版本向量
        self._version_vector: Dict[str, int] = {}
        
        # 锁
        self._lock = threading.RLock()
        
        # 回调
        self._on_message_sent: List[callable] = []
        self._on_message_received: List[callable] = []
        self._on_sync_complete: List[callable] = []
    
    def register_peer(self, peer_id: str) -> None:
        """注册对等节点"""
        with self._lock:
            self._peers.add(peer_id)
            self._version_vector[peer_id] = 0
    
    def unregister_peer(self, peer_id: str) -> None:
        """注销对等节点"""
        with self._lock:
            self._peers.discard(peer_id)
            self._version_vector.pop(peer_id, None)
    
    def get_peers(self) -> Set[str]:
        """获取所有对等节点"""
        return self._peers.copy()
    
    def create_message(
        self,
        operation: SyncOperation,
        resource_id: str,
        data: Any = None,
        target_node: Optional[str] = None,
        version: int = 0,
    ) -> SyncMessage:
        """
        创建同步消息
        
        Args:
            operation: 操作类型
            resource_id: 资源 ID
            data: 数据
            target_node: 目标节点
            version: 版本号
            
        Returns:
            SyncMessage: 创建的消息
        """
        message = SyncMessage(
            operation=operation,
            source_node=self.node_id,
            target_node=target_node,
            resource_id=resource_id,
            data=data,
            version=version,
        )
        
        with self._lock:
            self._pending_messages[message.message_id] = message
        
        return message
    
    def send_message(self, message: SyncMessage) -> bool:
        """
        发送消息
        
        Args:
            message: 消息对象
            
        Returns:
            bool: 是否成功
        """
        # 更新版本向量
        with self._lock:
            self._version_vector[self.node_id] = self._version_vector.get(self.node_id, 0) + 1
        
        # 触发回调
        for callback in self._on_message_sent:
            try:
                callback(message)
            except Exception:
                pass
        
        return True
    
    def receive_message(self, message: SyncMessage) -> bool:
        """
        接收消息
        
        Args:
            message: 消息对象
            
        Returns:
            bool: 是否成功处理
        """
        with self._lock:
            # 更新版本向量
            source = message.source_node
            if source in self._version_vector:
                self._version_vector[source] = max(
                    self._version_vector[source],
                    message.version
                )
            
            # 记录历史
            self._message_history.append(message)
            if len(self._message_history) > self._max_history:
                self._message_history.pop(0)
            
            # 从待确认队列移除
            self._pending_messages.pop(message.message_id, None)
            
            # 标记为已确认
            message.acknowledged = True
        
        # 触发回调
        for callback in self._on_message_received:
            try:
                callback(message)
            except Exception:
                pass
        
        return True
    
    def acknowledge_message(self, message_id: str) -> bool:
        """
        确认消息
        
        Args:
            message_id: 消息 ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            message = self._pending_messages.get(message_id)
            if message:
                message.acknowledged = True
                return True
        return False
    
    def read(
        self,
        resource_id: str,
        version: int = 0,
    ) -> SyncMessage:
        """
        读取同步
        
        Args:
            resource_id: 资源 ID
            version: 版本号
            
        Returns:
            SyncMessage: 读取消息
        """
        return self.create_message(
            operation=SyncOperation.READ,
            resource_id=resource_id,
            version=version,
        )
    
    def write(
        self,
        resource_id: str,
        data: Any,
        target_node: Optional[str] = None,
    ) -> SyncMessage:
        """
        写入同步
        
        Args:
            resource_id: 资源 ID
            data: 数据
            target_node: 目标节点
            
        Returns:
            SyncMessage: 写入消息
        """
        with self._lock:
            version = self._version_vector.get(self.node_id, 0) + 1
            self._version_vector[self.node_id] = version
        
        return self.create_message(
            operation=SyncOperation.WRITE,
            resource_id=resource_id,
            data=data,
            target_node=target_node,
            version=version,
        )
    
    def update(
        self,
        resource_id: str,
        data: Any,
        target_node: Optional[str] = None,
    ) -> SyncMessage:
        """
        更新同步
        
        Args:
            resource_id: 资源 ID
            data: 数据
            target_node: 目标节点
            
        Returns:
            SyncMessage: 更新消息
        """
        with self._lock:
            version = self._version_vector.get(self.node_id, 0) + 1
            self._version_vector[self.node_id] = version
        
        return self.create_message(
            operation=SyncOperation.UPDATE,
            resource_id=resource_id,
            data=data,
            target_node=target_node,
            version=version,
        )
    
    def invalidate(
        self,
        resource_id: str,
        target_node: Optional[str] = None,
    ) -> SyncMessage:
        """
        失效同步
        
        Args:
            resource_id: 资源 ID
            target_node: 目标节点
            
        Returns:
            SyncMessage: 失效消息
        """
        return self.create_message(
            operation=SyncOperation.INVALIDATE,
            resource_id=resource_id,
            target_node=target_node,
        )
    
    def request_sync(
        self,
        resource_ids: List[str],
        target_node: Optional[str] = None,
    ) -> SyncMessage:
        """
        请求同步
        
        Args:
            resource_ids: 请求的资源 ID 列表
            target_node: 目标节点
            
        Returns:
            SyncMessage: 同步请求消息
        """
        with self._lock:
            version = self._version_vector.get(self.node_id, 0) + 1
        
        return self.create_message(
            operation=SyncOperation.SYNC_REQUEST,
            resource_id=",".join(resource_ids),
            data=resource_ids,
            target_node=target_node,
            version=version,
        )
    
    def get_version_vector(self) -> Dict[str, int]:
        """获取版本向量"""
        return self._version_vector.copy()
    
    def compare_versions(self, other_vector: Dict[str, int]) -> Dict[str, int]:
        """
        比较版本向量
        
        Args:
            other_vector: 另一个版本向量
            
        Returns:
            Dict[str, int]: 差异
        """
        diff = {}
        all_nodes = set(self._version_vector.keys()) | set(other_vector.keys())
        
        for node in all_nodes:
            self_ver = self._version_vector.get(node, 0)
            other_ver = other_vector.get(node, 0)
            diff[node] = self_ver - other_ver
        
        return diff
    
    def is_concurrent_with(self, other_vector: Dict[str, int]) -> bool:
        """
        检查是否与另一版本向量并发
        
        Args:
            other_vector: 另一个版本向量
            
        Returns:
            bool: 是否并发
        """
        diff = self.compare_versions(other_vector)
        # 如果存在正差异和负差异，则并发
        has_positive = any(v > 0 for v in diff.values())
        has_negative = any(v < 0 for v in diff.values())
        return has_positive and has_negative
    
    def register_callback(
        self,
        event: str,
        callback: callable,
    ) -> None:
        """注册回调"""
        if event == "message_sent":
            self._on_message_sent.append(callback)
        elif event == "message_received":
            self._on_message_received.append(callback)
        elif event == "sync_complete":
            self._on_sync_complete.append(callback)
    
    def get_pending_count(self) -> int:
        """获取待确认消息数"""
        return len(self._pending_messages)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "node_id": self.node_id,
            "state": self.state.value,
            "peer_count": len(self._peers),
            "pending_messages": len(self._pending_messages),
            "message_history_size": len(self._message_history),
            "version_vector": self._version_vector,
        }
