"""
共享内存池核心

提供多 Agent 共享内存的统一管理
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import threading
import uuid

from .segment import (
    MemorySegment,
    SegmentType,
    SegmentAccess,
    SegmentManager,
)
from .lock_manager import (
    LockManager,
    LockType,
    ReadLock,
    WriteLock,
    FairLock,
)
from .sync_protocol import (
    SyncProtocol,
    SyncMessage,
    SyncOperation,
    SyncState,
)
from .coherence import (
    CacheCoherence,
    CoherenceProtocol,
    CacheLine,
    CacheLineState,
)


@dataclass
class MemoryPoolConfig:
    """
    内存池配置
    
    配置共享内存池的各项参数
    """
    # 缓存配置
    enable_cache: bool = True
    cache_size: int = 100
    coherence_protocol: CoherenceProtocol = CoherenceProtocol.MESI
    
    # 锁配置
    enable_fair_locks: bool = True
    default_lock_timeout: float = 30.0
    
    # 同步配置
    enable_sync: bool = True
    sync_interval: float = 1.0
    
    # 内存段配置
    max_segments: int = 1000
    default_segment_size: int = 1024 * 1024  # 1MB


@dataclass
class PoolStats:
    """内存池统计"""
    total_segments: int = 0
    valid_cache_lines: int = 0
    total_reads: int = 0
    total_writes: int = 0
    cache_hit_rate: float = 0.0
    lock_contention: float = 0.0
    pending_syncs: int = 0


class SharedMemoryPool:
    """
    共享内存池
    
    为多 Agent 提供共享内存访问的统一接口
    """
    
    def __init__(
        self,
        pool_id: str,
        node_id: str,
        config: Optional[MemoryPoolConfig] = None,
    ):
        """
        初始化共享内存池
        
        Args:
            pool_id: 内存池 ID
            node_id: 节点 ID
            config: 配置对象
        """
        self.pool_id = pool_id
        self.node_id = node_id
        self.config = config or MemoryPoolConfig()
        
        # 核心组件
        self.segment_manager = SegmentManager()
        self.lock_manager = LockManager(enable_fairness=self.config.enable_fair_locks)
        
        # 缓存一致性
        if self.config.enable_cache:
            self.cache = CacheCoherence(
                node_id=node_id,
                protocol=self.config.coherence_protocol,
                cache_size=self.config.cache_size,
            )
        else:
            self.cache = None
        
        # 同步协议
        if self.config.enable_sync:
            self.sync_protocol = SyncProtocol(node_id=node_id)
        else:
            self.sync_protocol = None
        
        # 锁
        self._lock = threading.RLock()
        
        # 注册的 Agent
        self._registered_agents: Set[str] = set()
        
        # 统计
        self._total_reads = 0
        self._total_writes = 0
    
    # ==================== Agent 管理 ====================
    
    def register_agent(self, agent_id: str) -> None:
        """注册 Agent"""
        with self._lock:
            self._registered_agents.add(agent_id)
            
            if self.sync_protocol:
                self.sync_protocol.register_peer(agent_id)
    
    def unregister_agent(self, agent_id: str) -> None:
        """注销 Agent"""
        with self._lock:
            self._registered_agents.discard(agent_id)
            
            if self.sync_protocol:
                self.sync_protocol.unregister_peer(agent_id)
    
    def get_registered_agents(self) -> Set[str]:
        """获取注册的 Agent"""
        return self._registered_agents.copy()
    
    # ==================== 内存段操作 ====================
    
    def create_segment(
        self,
        name: str,
        owner_id: Optional[str] = None,
        segment_type: SegmentType = SegmentType.SHARED,
        access: SegmentAccess = SegmentAccess.READ_WRITE,
        allowed_agents: Optional[Set[str]] = None,
        initial_data: Any = None,
    ) -> MemorySegment:
        """
        创建内存段
        
        Args:
            name: 段名称
            owner_id: 所有者 ID
            segment_type: 段类型
            access: 访问权限
            allowed_agents: 允许访问的 Agent
            initial_data: 初始数据
            
        Returns:
            MemorySegment: 创建的内存段
        """
        segment = self.segment_manager.create_segment(
            name=name,
            segment_type=segment_type,
            access=access,
            owner_id=owner_id,
            allowed_agents=allowed_agents,
            initial_data=initial_data,
        )
        
        return segment
    
    def get_segment(self, name: str) -> Optional[MemorySegment]:
        """获取内存段"""
        return self.segment_manager.get_segment_by_name(name)
    
    def delete_segment(self, name: str) -> bool:
        """删除内存段"""
        segment = self.segment_manager.get_segment_by_name(name)
        if segment:
            return self.segment_manager.delete_segment(segment.segment_id)
        return False
    
    # ==================== 带锁的读写操作 ====================
    
    def read_with_lock(
        self,
        segment_name: str,
        agent_id: str,
        timeout: Optional[float] = None,
    ) -> Optional[Any]:
        """
        带锁读取
        
        Args:
            segment_name: 内存段名称
            agent_id: Agent ID
            timeout: 超时时间
            
        Returns:
            Optional[Any]: 读取的数据
        """
        timeout = timeout or self.config.default_lock_timeout
        
        with self.lock_manager.read_lock(segment_name, agent_id, timeout):
            segment = self.get_segment(segment_name)
            if segment:
                data = segment.read(agent_id)
                self._total_reads += 1
                return data
        
        return None
    
    def write_with_lock(
        self,
        segment_name: str,
        agent_id: str,
        data: Any,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        带锁写入
        
        Args:
            segment_name: 内存段名称
            agent_id: Agent ID
            data: 数据
            timeout: 超时时间
            
        Returns:
            bool: 是否成功
        """
        timeout = timeout or self.config.default_lock_timeout
        
        with self.lock_manager.write_lock(segment_name, agent_id, timeout):
            segment = self.get_segment(segment_name)
            if segment:
                success = segment.write(agent_id, data)
                if success:
                    self._total_writes += 1
                    
                    # 如果启用了同步，发送同步消息
                    if self.sync_protocol:
                        msg = self.sync_protocol.write(segment_name, data)
                        self.sync_protocol.send_message(msg)
                    
                    # 如果启用了缓存，更新缓存
                    if self.cache:
                        self.cache.write(segment_name, data, agent_id)
                    
                    segment.mark_clean()
                
                return success
        
        return False
    
    def update_with_lock(
        self,
        segment_name: str,
        agent_id: str,
        updater: callable,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        带锁的原子更新
        
        Args:
            segment_name: 内存段名称
            agent_id: Agent ID
            updater: 更新函数，接收当前数据，返回新数据
            timeout: 超时时间
            
        Returns:
            bool: 是否成功
        """
        timeout = timeout or self.config.default_lock_timeout
        
        with self.lock_manager.write_lock(segment_name, agent_id, timeout):
            segment = self.get_segment(segment_name)
            if segment:
                current_data = segment.read(agent_id)
                new_data = updater(current_data)
                success = segment.write(agent_id, new_data)
                
                if success:
                    self._total_writes += 1
                    
                    if self.sync_protocol:
                        msg = self.sync_protocol.update(segment_name, new_data)
                        self.sync_protocol.send_message(msg)
                    
                    if self.cache:
                        self.cache.write(segment_name, new_data, agent_id)
                    
                    segment.mark_clean()
                
                return success
        
        return False
    
    # ==================== 批量操作 ====================
    
    def read_multiple(
        self,
        segment_names: List[str],
        agent_id: str,
    ) -> Dict[str, Any]:
        """
        批量读取
        
        Args:
            segment_names: 内存段名称列表
            agent_id: Agent ID
            
        Returns:
            Dict[str, Any]: 读取的数据
        """
        results = {}
        
        for name in segment_names:
            data = self.read_with_lock(name, agent_id)
            if data is not None:
                results[name] = data
        
        return results
    
    def write_multiple(
        self,
        writes: Dict[str, Any],
        agent_id: str,
    ) -> Dict[str, bool]:
        """
        批量写入
        
        Args:
            writes: 名称到数据的映射
            agent_id: Agent ID
            
        Returns:
            Dict[str, bool]: 写入结果
        """
        results = {}
        
        for name, data in writes.items():
            results[name] = self.write_with_lock(name, agent_id, data)
        
        return results
    
    # ==================== 缓存操作 ====================
    
    def read_from_cache(self, resource_id: str, agent_id: str) -> Optional[Any]:
        """从缓存读取"""
        if self.cache:
            return self.cache.read(resource_id, agent_id)
        return None
    
    def write_to_cache(
        self,
        resource_id: str,
        data: Any,
        agent_id: str,
    ) -> bool:
        """写入缓存"""
        if self.cache:
            return self.cache.write(resource_id, data, agent_id)
        return False
    
    def invalidate_cache(self, resource_id: str) -> None:
        """失效缓存"""
        if self.cache:
            self.cache.broadcast_invalidation(resource_id)
    
    # ==================== 同步操作 ====================
    
    def request_sync(
        self,
        segment_names: List[str],
        target_node: Optional[str] = None,
    ) -> SyncMessage:
        """请求同步"""
        if self.sync_protocol:
            return self.sync_protocol.request_sync(segment_names, target_node)
        return None
    
    def sync_all(self) -> None:
        """同步所有脏段"""
        dirty_segments = self.segment_manager.get_dirty_segments()
        
        for segment in dirty_segments:
            if self.sync_protocol:
                msg = self.sync_protocol.update(
                    segment.name,
                    segment.data,
                )
                self.sync_protocol.send_message(msg)
            
            segment.mark_clean()
    
    # ==================== 统计和监控 ====================
    
    def get_stats(self) -> PoolStats:
        """获取统计信息"""
        stats = PoolStats(
            total_segments=self.segment_manager.get_statistics()["total_segments"],
            total_reads=self._total_reads,
            total_writes=self._total_writes,
        )
        
        if self.cache:
            cache_stats = self.cache.get_statistics()
            stats.valid_cache_lines = cache_stats["valid_lines"]
            stats.cache_hit_rate = cache_stats["hit_rate"]
        
        if self.sync_protocol:
            stats.pending_syncs = self.sync_protocol.get_pending_count()
        
        return stats
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """获取详细统计"""
        return {
            "pool_id": self.pool_id,
            "node_id": self.node_id,
            "registered_agents": len(self._registered_agents),
            "segments": self.segment_manager.get_statistics(),
            "locks": self.lock_manager.get_statistics(),
            "cache": self.cache.get_statistics() if self.cache else None,
            "sync": self.sync_protocol.get_statistics() if self.sync_protocol else None,
            "total_reads": self._total_reads,
            "total_writes": self._total_writes,
        }
    
    def get_all_segments(self) -> List[MemorySegment]:
        """获取所有内存段"""
        return self.segment_manager.get_all_segments()
    
    def get_dirty_segments(self) -> List[MemorySegment]:
        """获取所有脏段"""
        return self.segment_manager.get_dirty_segments()
    
    def clear_dirty_flags(self) -> int:
        """清除所有脏标记"""
        return self.segment_manager.clear_dirty_flags()
