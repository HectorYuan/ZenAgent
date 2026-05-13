"""
缓存一致性

实现缓存一致性协议（MESI 等）
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import threading


class CoherenceProtocol(Enum):
    """一致性协议枚举"""
    MESI = "mesi"           # MESI 协议
    MOESI = "moesi"         # MOESI 协议
    MSI = "msi"             # MSI 协议
    WRITE_INVALIDATE = "write_invalidate"  # 写失效
    WRITE_UPDATE = "write_update"          # 写更新


class CacheLineState(Enum):
    """缓存行状态枚举 (MESI)"""
    MODIFIED = "M"    # 已修改
    EXCLUSIVE = "E"   # 独占
    SHARED = "S"      # 共享
    INVALID = "I"     # 无效


@dataclass
class CacheLine:
    """
    缓存行
    
    表示缓存中的一个行
    """
    line_id: str
    resource_id: str
    
    # 状态
    state: CacheLineState = CacheLineState.INVALID
    
    # 数据
    data: Any = None
    
    # 版本
    version: int = 0
    
    # 持有者
    sharers: Set[str] = field(default_factory=set)  # 共享者列表
    exclusive_owner: Optional[str] = None  # 独占持有者
    
    # 时间戳
    last_modified: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    
    # 统计
    access_count: int = 0
    miss_count: int = 0
    hit_count: int = 0
    
    @property
    def is_valid(self) -> bool:
        """是否有效"""
        return self.state != CacheLineState.INVALID
    
    @property
    def is_modified(self) -> bool:
        """是否已修改"""
        return self.state == CacheLineState.MODIFIED
    
    @property
    def is_shared(self) -> bool:
        """是否共享"""
        return self.state == CacheLineState.SHARED
    
    @property
    def is_exclusive(self) -> bool:
        """是否独占"""
        return self.state == CacheLineState.EXCLUSIVE
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "line_id": self.line_id,
            "resource_id": self.resource_id,
            "state": self.state.value,
            "version": self.version,
            "sharers": list(self.sharers),
            "exclusive_owner": self.exclusive_owner,
            "last_modified": self.last_modified.isoformat(),
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
        }


@dataclass
class InvalidationResult:
    """失效结果"""
    success: bool
    invalidated_nodes: List[str] = field(default_factory=list)
    failed_nodes: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class CacheCoherence:
    """
    缓存一致性管理器
    
    实现 MESI 等缓存一致性协议
    """
    
    def __init__(
        self,
        node_id: str,
        protocol: CoherenceProtocol = CoherenceProtocol.MESI,
        cache_size: int = 100,
    ):
        """
        初始化缓存一致性管理器
        
        Args:
            node_id: 节点 ID
            protocol: 一致性协议
            cache_size: 缓存大小
        """
        self.node_id = node_id
        self.protocol = protocol
        self._cache_size = cache_size
        
        # 缓存行
        self._cache: Dict[str, CacheLine] = {}  # resource_id -> CacheLine
        
        # 全局状态（模拟总线）
        self._global_states: Dict[str, CacheLineState] = {}
        self._global_owners: Dict[str, str] = {}  # resource -> owner
        self._global_sharers: Dict[str, Set[str]] = {}  # resource -> sharers
        
        # 锁
        self._lock = threading.RLock()
        
        # 统计
        self._total_hits = 0
        self._total_misses = 0
        self._invalidations_sent = 0
        self._invalidations_received = 0
        
        # 回调
        self._on_cache_miss: List[callable] = []
        self._on_cache_hit: List[callable] = []
        self._on_invalidation: List[callable] = []
    
    def read(self, resource_id: str, requester_id: str) -> Optional[Any]:
        """
        读取缓存
        
        Args:
            resource_id: 资源 ID
            requester_id: 请求者 ID
            
        Returns:
            Optional[Any]: 缓存数据
        """
        with self._lock:
            line = self._cache.get(resource_id)
            
            if line and line.is_valid:
                # 缓存命中
                line.access_count += 1
                line.last_accessed = datetime.now()
                line.hit_count += 1
                self._total_hits += 1
                
                # 触发回调
                for callback in self._on_cache_hit:
                    try:
                        callback(resource_id, line.data)
                    except Exception:
                        pass
                
                return line.data
            else:
                # 缓存未命中
                self._total_misses += 1
                
                if line:
                    line.miss_count += 1
                
                # 触发回调
                for callback in self._on_cache_miss:
                    try:
                        callback(resource_id)
                    except Exception:
                        pass
                
                return None
    
    def write(
        self,
        resource_id: str,
        data: Any,
        requester_id: str,
    ) -> bool:
        """
        写入缓存
        
        Args:
            resource_id: 资源 ID
            data: 数据
            requester_id: 请求者 ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            line = self._cache.get(resource_id)
            
            if line is None:
                # 创建新行
                line = CacheLine(
                    line_id=f"{resource_id}:{self.node_id}",
                    resource_id=resource_id,
                )
                self._cache[resource_id] = line
                
                # 如果缓存满了，驱逐一行
                if len(self._cache) > self._cache_size:
                    self._evict_one()
            
            # 根据协议更新状态
            if self.protocol == CoherenceProtocol.MESI:
                self._mesi_write(line, data, requester_id)
            elif self.protocol == CoherenceProtocol.MSI:
                self._msi_write(line, data, requester_id)
            else:
                # 默认：直接写入
                line.data = data
                line.version += 1
                line.state = CacheLineState.MODIFIED
                line.exclusive_owner = requester_id
            
            line.last_modified = datetime.now()
            line.last_accessed = datetime.now()
            line.access_count += 1
            
            # 更新全局状态
            self._global_states[resource_id] = CacheLineState.MODIFIED
            self._global_owners[resource_id] = requester_id
            self._global_sharers[resource_id] = {requester_id}
            
            return True
    
    def _mesi_write(self, line: CacheLine, data: Any, requester_id: str) -> None:
        """MESI 协议的写操作"""
        if line.state == CacheLineState.MODIFIED:
            # 已是修改状态，直接写入
            line.data = data
            line.version += 1
            
        elif line.state == CacheLineState.EXCLUSIVE:
            # 独占状态，转换到修改状态
            line.data = data
            line.version += 1
            line.state = CacheLineState.MODIFIED
            line.exclusive_owner = requester_id
            
        elif line.state == CacheLineState.SHARED:
            # 共享状态，需要失效其他副本
            line.data = data
            line.version += 1
            line.state = CacheLineState.MODIFIED
            line.exclusive_owner = requester_id
            line.sharers = {requester_id}
            
        else:  # INVALID
            # 无效状态，直接设置
            line.data = data
            line.version = 1
            line.state = CacheLineState.MODIFIED
            line.exclusive_owner = requester_id
            line.sharers = {requester_id}
    
    def _msi_write(self, line: CacheLine, data: Any, requester_id: str) -> None:
        """MSI 协议的写操作"""
        # MSI 没有 EXCLUSIVE 状态
        if line.state == CacheLineState.INVALID:
            line.data = data
            line.version = 1
            line.state = CacheLineState.MODIFIED
            line.exclusive_owner = requester_id
        else:
            line.data = data
            line.version += 1
            line.state = CacheLineState.MODIFIED
            line.exclusive_owner = requester_id
    
    def upgrade_to_modified(self, resource_id: str, requester_id: str) -> bool:
        """
        将共享行升级为修改状态
        
        Args:
            resource_id: 资源 ID
            requester_id: 请求者 ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            line = self._cache.get(resource_id)
            
            if not line or not line.is_valid:
                return False
            
            if line.state == CacheLineState.SHARED:
                line.state = CacheLineState.MODIFIED
                line.exclusive_owner = requester_id
                line.sharers = {requester_id}
                return True
            
            return False
    
    def invalidate(
        self,
        resource_id: str,
        target_nodes: Optional[List[str]] = None,
    ) -> InvalidationResult:
        """
        失效缓存行
        
        Args:
            resource_id: 资源 ID
            target_nodes: 目标节点列表
            
        Returns:
            InvalidationResult: 失效结果
        """
        with self._lock:
            result = InvalidationResult(success=True)
            
            # 如果没有指定目标，失效所有共享者
            sharers = self._global_sharers.get(resource_id, set())
            targets = target_nodes or list(sharers)
            
            for node_id in targets:
                if node_id in sharers:
                    # 失效该节点的缓存行
                    line = self._cache.get(resource_id)
                    if line and node_id in line.sharers:
                        line.sharers.discard(node_id)
                        line.state = CacheLineState.INVALID
                        result.invalidated_nodes.append(node_id)
                        self._invalidations_sent += 1
                        
                        # 触发回调
                        for callback in self._on_invalidation:
                            try:
                                callback(resource_id, node_id)
                            except Exception:
                                pass
            
            # 更新全局状态
            if self._global_owners.get(resource_id) in targets:
                self._global_owners.pop(resource_id, None)
                self._global_states[resource_id] = CacheLineState.INVALID
            
            return result
    
    def broadcast_invalidation(self, resource_id: str) -> InvalidationResult:
        """
        广播失效
        
        Args:
            resource_id: 资源 ID
            
        Returns:
            InvalidationResult: 失效结果
        """
        return self.invalidate(resource_id, None)
    
    def handle_invalidation(self, resource_id: str, sender_id: str) -> bool:
        """
        处理失效请求
        
        Args:
            resource_id: 资源 ID
            sender_id: 发送者 ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            line = self._cache.get(resource_id)
            
            if line and line.is_valid:
                # 如果是修改状态，需要写回
                if line.is_modified:
                    # 写回逻辑（这里简单处理）
                    pass
                
                line.state = CacheLineState.INVALID
                line.sharers.discard(self.node_id)
                self._invalidations_received += 1
                
                # 触发回调
                for callback in self._on_invalidation:
                    try:
                        callback(resource_id, sender_id)
                    except Exception:
                        pass
                
                return True
            
            return False
    
    def upgrade_from_shared(self, resource_id: str, requester_id: str) -> bool:
        """
        从共享状态升级（读锁转写锁）
        
        Args:
            resource_id: 资源 ID
            requester_id: 请求者 ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            line = self._cache.get(resource_id)
            
            if not line or not line.is_valid:
                return False
            
            if line.state == CacheLineState.SHARED:
                # 需要广播失效其他共享者
                sharers = line.sharers.copy()
                sharers.discard(requester_id)
                
                # 失效其他节点
                for other in sharers:
                    self._invalidations_sent += 1
                
                # 更新状态
                line.state = CacheLineState.MODIFIED
                line.exclusive_owner = requester_id
                line.sharers = {requester_id}
                
                return True
            
            return False
    
    def _evict_one(self) -> Optional[str]:
        """驱逐一个缓存行"""
        # 简单的驱逐策略：驱逐最早的
        if not self._cache:
            return None
        
        oldest = min(
            self._cache.values(),
            key=lambda l: l.last_accessed
        )
        
        evicted_id = oldest.resource_id
        
        # 如果是修改状态，需要写回
        if oldest.is_modified:
            # 写回逻辑（这里简化处理）
            pass
        
        del self._cache[evicted_id]
        return evicted_id
    
    def get_cache_line(self, resource_id: str) -> Optional[CacheLine]:
        """获取缓存行"""
        return self._cache.get(resource_id)
    
    def get_state(self, resource_id: str) -> Optional[CacheLineState]:
        """获取全局状态"""
        return self._global_states.get(resource_id)
    
    def is_shared(self, resource_id: str) -> bool:
        """检查资源是否被共享"""
        sharers = self._global_sharers.get(resource_id, set())
        return len(sharers) > 1
    
    def register_callback(
        self,
        event: str,
        callback: callable,
    ) -> None:
        """注册回调"""
        if event == "cache_miss":
            self._on_cache_miss.append(callback)
        elif event == "cache_hit":
            self._on_cache_hit.append(callback)
        elif event == "invalidation":
            self._on_invalidation.append(callback)
    
    def get_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self._total_hits + self._total_misses
        if total == 0:
            return 0.0
        return self._total_hits / total
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "node_id": self.node_id,
            "protocol": self.protocol.value,
            "cache_size": len(self._cache),
            "max_cache_size": self._cache_size,
            "total_hits": self._total_hits,
            "total_misses": self._total_misses,
            "hit_rate": self.get_hit_rate(),
            "invalidations_sent": self._invalidations_sent,
            "invalidations_received": self._invalidations_received,
            "valid_lines": sum(1 for l in self._cache.values() if l.is_valid),
            "modified_lines": sum(1 for l in self._cache.values() if l.is_modified),
            "shared_lines": sum(1 for l in self._cache.values() if l.is_shared),
        }
    
    def clear(self) -> int:
        """清空缓存"""
        count = len(self._cache)
        self._cache.clear()
        return count
