"""
内存段管理

管理共享内存池中的内存段
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import threading
import uuid


class SegmentType(Enum):
    """内存段类型"""
    SHARED = "shared"           # 共享段
    PRIVATE = "private"         # 私有段
    PROTECTED = "protected"     # 保护段
    CACHED = "cached"           # 缓存段


class SegmentAccess(Enum):
    """内存段访问权限"""
    READ_ONLY = "read_only"
    WRITE_ONLY = "write_only"
    READ_WRITE = "read_write"
    EXCLUSIVE = "exclusive"


@dataclass
class MemorySegment:
    """
    内存段
    
    表示共享内存池中的一个内存区域
    """
    segment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    
    # 段类型
    segment_type: SegmentType = SegmentType.SHARED
    
    # 访问权限
    access: SegmentAccess = SegmentAccess.READ_WRITE
    
    # 所有者
    owner_id: Optional[str] = None
    allowed_agents: Set[str] = field(default_factory=set)
    
    # 数据
    data: Any = None
    schema: Optional[Dict[str, Any]] = None
    
    # 版本控制
    version: int = 0
    is_dirty: bool = False
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    
    # 访问追踪
    read_count: int = 0
    write_count: int = 0
    last_read_by: Optional[str] = None
    last_written_by: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 大小限制
    max_size: Optional[int] = None
    
    # 锁
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    
    @property
    def size(self) -> int:
        """获取数据大小"""
        if self.data is None:
            return 0
        if isinstance(self.data, (str, bytes)):
            return len(self.data)
        if isinstance(self.data, dict):
            return len(str(self.data))
        return 0
    
    @property
    def can_read(self) -> bool:
        """是否可以读取"""
        return self.access in {SegmentAccess.READ_ONLY, SegmentAccess.READ_WRITE}
    
    @property
    def can_write(self) -> bool:
        """是否可以写入"""
        return self.access in {SegmentAccess.WRITE_ONLY, SegmentAccess.READ_WRITE}
    
    def is_accessible_by(self, agent_id: str) -> bool:
        """
        检查 Agent 是否有权限访问
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否有权限
        """
        # 所有者总有权限
        if self.owner_id == agent_id:
            return True
        
        # 检查允许列表
        if self.allowed_agents and agent_id not in self.allowed_agents:
            return False
        
        return True
    
    def read(self, agent_id: str) -> Optional[Any]:
        """
        读取数据
        
        Args:
            agent_id: 读取者 ID
            
        Returns:
            Optional[Any]: 数据副本
        """
        with self._lock:
            if not self.can_read:
                return None
            
            self.read_count += 1
            self.last_read_by = agent_id
            
            # 返回数据副本
            if isinstance(self.data, (dict, list)):
                import copy
                return copy.deepcopy(self.data)
            return self.data
    
    def write(self, agent_id: str, data: Any) -> bool:
        """
        写入数据
        
        Args:
            agent_id: 写入者 ID
            data: 数据
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            if not self.can_write:
                return False
            
            # 检查大小限制
            if self.max_size is not None:
                import sys
                data_size = sys.getsizeof(data)
                if data_size > self.max_size:
                    return False
            
            self.data = data
            self.write_count += 1
            self.last_written_by = agent_id
            self.modified_at = datetime.now()
            self.version += 1
            self.is_dirty = True
            
            return True
    
    def acquire_read_lock(self, agent_id: str, timeout: Optional[float] = None) -> bool:
        """
        获取读锁
        
        Args:
            agent_id: Agent ID
            timeout: 超时时间
            
        Returns:
            bool: 是否成功
        """
        acquired = self._lock.acquire(timeout=timeout, blocking=True)
        return acquired
    
    def acquire_write_lock(self, agent_id: str, timeout: Optional[float] = None) -> bool:
        """
        获取写锁
        
        Args:
            agent_id: Agent ID
            timeout: 超时时间
            
        Returns:
            bool: 是否成功
        """
        acquired = self._lock.acquire(timeout=timeout, blocking=True)
        return acquired
    
    def release_lock(self) -> None:
        """释放锁"""
        try:
            self._lock.release()
        except RuntimeError:
            pass  # 锁未持有
    
    def mark_clean(self) -> None:
        """标记为干净"""
        self.is_dirty = False
    
    def mark_dirty(self) -> None:
        """标记为脏"""
        self.is_dirty = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "segment_id": self.segment_id,
            "name": self.name,
            "segment_type": self.segment_type.value,
            "access": self.access.value,
            "owner_id": self.owner_id,
            "allowed_agents": list(self.allowed_agents),
            "version": self.version,
            "is_dirty": self.is_dirty,
            "size": self.size,
            "read_count": self.read_count,
            "write_count": self.write_count,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
        }
    
    def __enter__(self) -> 'MemorySegment':
        """上下文管理器入口"""
        self._lock.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口"""
        self.release_lock()
    
    def __repr__(self) -> str:
        return f"MemorySegment(id={self.segment_id[:8]}, name={self.name}, type={self.segment_type.value})"


class SegmentManager:
    """
    内存段管理器
    
    管理多个内存段的创建、查询和销毁
    """
    
    def __init__(self):
        """初始化管理器"""
        self._segments: Dict[str, MemorySegment] = {}
        self._segments_by_name: Dict[str, MemorySegment] = {}
        self._segments_by_owner: Dict[str, List[str]] = {}  # owner_id -> segment_ids
        self._lock = threading.RLock()
    
    def create_segment(
        self,
        name: str,
        segment_type: SegmentType = SegmentType.SHARED,
        access: SegmentAccess = SegmentAccess.READ_WRITE,
        owner_id: Optional[str] = None,
        allowed_agents: Optional[Set[str]] = None,
        initial_data: Any = None,
        max_size: Optional[int] = None,
    ) -> MemorySegment:
        """
        创建内存段
        
        Args:
            name: 段名称
            segment_type: 段类型
            access: 访问权限
            owner_id: 所有者 ID
            allowed_agents: 允许访问的 Agent
            initial_data: 初始数据
            max_size: 最大大小
            
        Returns:
            MemorySegment: 创建的内存段
        """
        with self._lock:
            # 检查名称唯一性
            if name in self._segments_by_name:
                raise ValueError(f"Segment with name '{name}' already exists")
            
            segment = MemorySegment(
                name=name,
                segment_type=segment_type,
                access=access,
                owner_id=owner_id,
                allowed_agents=allowed_agents or set(),
                data=initial_data,
                max_size=max_size,
            )
            
            self._segments[segment.segment_id] = segment
            self._segments_by_name[name] = segment
            
            if owner_id:
                if owner_id not in self._segments_by_owner:
                    self._segments_by_owner[owner_id] = []
                self._segments_by_owner[owner_id].append(segment.segment_id)
            
            return segment
    
    def get_segment(self, segment_id: str) -> Optional[MemorySegment]:
        """获取内存段"""
        return self._segments.get(segment_id)
    
    def get_segment_by_name(self, name: str) -> Optional[MemorySegment]:
        """通过名称获取内存段"""
        return self._segments_by_name.get(name)
    
    def get_segments_by_owner(self, owner_id: str) -> List[MemorySegment]:
        """获取所有者的所有内存段"""
        segment_ids = self._segments_by_owner.get(owner_id, [])
        return [self._segments[sid] for sid in segment_ids if sid in self._segments]
    
    def get_segments_by_type(self, segment_type: SegmentType) -> List[MemorySegment]:
        """获取指定类型的所有内存段"""
        return [s for s in self._segments.values() if s.segment_type == segment_type]
    
    def delete_segment(self, segment_id: str) -> bool:
        """
        删除内存段
        
        Args:
            segment_id: 段 ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            segment = self._segments.get(segment_id)
            if not segment:
                return False
            
            # 从各索引中移除
            self._segments.pop(segment_id, None)
            self._segments_by_name.pop(segment.name, None)
            
            if segment.owner_id and segment.owner_id in self._segments_by_owner:
                if segment_id in self._segments_by_owner[segment.owner_id]:
                    self._segments_by_owner[segment.owner_id].remove(segment_id)
            
            return True
    
    def get_all_segments(self) -> List[MemorySegment]:
        """获取所有内存段"""
        return list(self._segments.values())
    
    def get_dirty_segments(self) -> List[MemorySegment]:
        """获取所有脏段"""
        return [s for s in self._segments.values() if s.is_dirty]
    
    def clear_dirty_flags(self) -> int:
        """清除所有脏标记"""
        count = 0
        for segment in self._segments.values():
            if segment.is_dirty:
                segment.mark_clean()
                count += 1
        return count
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_segments": len(self._segments),
            "by_type": {
                stype.value: len(self.get_segments_by_type(stype))
                for stype in SegmentType
            },
            "dirty_count": len(self.get_dirty_segments()),
            "total_owners": len(self._segments_by_owner),
        }
