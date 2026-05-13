"""
锁管理器

提供读写锁、公平锁等多种锁机制
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import threading
import time
from contextlib import contextmanager


class LockType(Enum):
    """锁类型枚举"""
    READ = "read"           # 读锁
    WRITE = "write"         # 写锁
    FAIR = "fair"           # 公平锁
    RECURSIVE = "recursive" # 可重入锁


@dataclass
class Lock:
    """
    锁信息
    
    表示一个锁的状态
    """
    lock_id: str
    resource_id: str
    lock_type: LockType
    
    # 持有者
    holder_id: Optional[str] = None
    holders: Set[str] = field(default_factory=set)  # 支持多个持有者（读锁）
    
    # 状态
    is_held: bool = False
    hold_count: int = 0  # 重入计数
    
    # 时间信息
    acquired_at: Optional[datetime] = None
    waiters: List[str] = field(default_factory=list)  # 等待者队列
    
    # 优先级
    priority: int = 0
    
    @property
    def holder_count(self) -> int:
        """当前持有者数量"""
        return len(self.holders)
    
    @property
    def is_exclusive(self) -> bool:
        """是否为独占锁"""
        return self.lock_type == LockType.WRITE
    
    def add_holder(self, holder_id: str) -> None:
        """添加持有者"""
        self.holders.add(holder_id)
        self.holder_id = holder_id
        self.is_held = True
        self.hold_count += 1
        if self.acquired_at is None:
            self.acquired_at = datetime.now()
    
    def remove_holder(self, holder_id: str) -> bool:
        """移除持有者"""
        if holder_id in self.holders:
            self.holders.discard(holder_id)
            self.hold_count = max(0, self.hold_count - 1)
            
            if not self.holders:
                self.is_held = False
                self.holder_id = None
                self.acquired_at = None
            elif self.lock_type == LockType.READ:
                self.holder_id = next(iter(self.holders), None)
            
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "lock_id": self.lock_id,
            "resource_id": self.resource_id,
            "lock_type": self.lock_type.value,
            "is_held": self.is_held,
            "holder_count": self.holder_count,
            "holders": list(self.holders),
            "waiters": self.waiters,
            "acquired_at": self.acquired_at.isoformat() if self.acquired_at else None,
        }


@dataclass
class LockAcquisitionResult:
    """锁获取结果"""
    success: bool
    lock: Optional[Lock] = None
    acquired_at: Optional[datetime] = None
    wait_time: float = 0.0
    error: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        """持有时长（秒）"""
        if self.acquired_at:
            return (datetime.now() - self.acquired_at).total_seconds()
        return None


class ReadLock:
    """读锁上下文管理器"""
    
    def __init__(self, lock_manager: 'LockManager', resource_id: str, holder_id: str, timeout: Optional[float] = None):
        self._lock_manager = lock_manager
        self._resource_id = resource_id
        self._holder_id = holder_id
        self._timeout = timeout
        self._acquired = False
    
    def __enter__(self) -> bool:
        result = self._lock_manager.acquire_read(self._resource_id, self._holder_id, self._timeout)
        self._acquired = result.success
        return self._acquired
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._acquired:
            self._lock_manager.release_read(self._resource_id, self._holder_id)


class WriteLock:
    """写锁上下文管理器"""
    
    def __init__(self, lock_manager: 'LockManager', resource_id: str, holder_id: str, timeout: Optional[float] = None):
        self._lock_manager = lock_manager
        self._resource_id = resource_id
        self._holder_id = holder_id
        self._timeout = timeout
        self._acquired = False
    
    def __enter__(self) -> bool:
        result = self._lock_manager.acquire_write(self._resource_id, self._holder_id, self._timeout)
        self._acquired = result.success
        return self._acquired
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._acquired:
            self._lock_manager.release_write(self._resource_id, self._holder_id)


class FairLock:
    """公平锁上下文管理器"""
    
    def __init__(self, lock_manager: 'LockManager', resource_id: str, holder_id: str, timeout: Optional[float] = None):
        self._lock_manager = lock_manager
        self._resource_id = resource_id
        self._holder_id = holder_id
        self._timeout = timeout
        self._acquired = False
    
    def __enter__(self) -> bool:
        result = self._lock_manager.acquire_fair(self._resource_id, self._holder_id, self._timeout)
        self._acquired = result.success
        return self._acquired
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._acquired:
            self._lock_manager.release_fair(self._resource_id, self._holder_id)


class LockManager:
    """
    锁管理器
    
    管理资源的读写锁和公平锁
    """
    
    def __init__(self, enable_fairness: bool = True):
        """
        初始化锁管理器
        
        Args:
            enable_fairness: 是否启用公平性
        """
        self._locks: Dict[str, Lock] = {}
        self._read_counts: Dict[str, int] = {}  # resource_id -> read lock count
        self._lock = threading.RLock()
        self._enable_fairness = enable_fairness
        
        # 回调
        self._on_lock_acquired: List[callable] = []
        self._on_lock_released: List[callable] = []
    
    def _get_or_create_lock(self, resource_id: str, lock_type: LockType) -> Lock:
        """获取或创建锁"""
        key = f"{resource_id}:{lock_type.value}"
        if key not in self._locks:
            self._locks[key] = Lock(
                lock_id=key,
                resource_id=resource_id,
                lock_type=lock_type,
            )
        return self._locks[key]
    
    def _get_lock(self, resource_id: str, lock_type: LockType) -> Optional[Lock]:
        """获取锁"""
        key = f"{resource_id}:{lock_type.value}"
        return self._locks.get(key)
    
    def acquire_read(
        self,
        resource_id: str,
        holder_id: str,
        timeout: Optional[float] = None,
    ) -> LockAcquisitionResult:
        """
        获取读锁
        
        Args:
            resource_id: 资源 ID
            holder_id: 持有者 ID
            timeout: 超时时间
            
        Returns:
            LockAcquisitionResult: 获取结果
        """
        start_time = time.time()
        
        with self._lock:
            # 获取读锁
            read_lock = self._get_or_create_lock(resource_id, LockType.READ)
            write_lock = self._get_lock(resource_id, LockType.WRITE)
            
            # 检查写锁
            if write_lock and write_lock.is_held and holder_id not in write_lock.holders:
                if timeout is None or timeout <= 0:
                    return LockAcquisitionResult(
                        success=False,
                        error="Resource is held by writer",
                    )
            
            # 添加到等待队列
            if holder_id not in read_lock.waiters:
                read_lock.waiters.append(holder_id)
            
            # 获取锁
            while True:
                # 检查是否可以获取
                if write_lock and write_lock.is_held and holder_id not in write_lock.holders:
                    elapsed = time.time() - start_time
                    remaining = timeout - elapsed if timeout else 0
                    if timeout and remaining <= 0:
                        return LockAcquisitionResult(
                            success=False,
                            error="Timeout waiting for write lock",
                        )
                    time.sleep(0.01)
                    continue
                
                break
            
            # 获取锁
            read_lock.add_holder(holder_id)
            self._read_counts[resource_id] = self._read_counts.get(resource_id, 0) + 1
            
            # 从等待队列移除
            if holder_id in read_lock.waiters:
                read_lock.waiters.remove(holder_id)
            
            return LockAcquisitionResult(
                success=True,
                lock=read_lock,
                acquired_at=datetime.now(),
                wait_time=time.time() - start_time,
            )
    
    def release_read(self, resource_id: str, holder_id: str) -> bool:
        """
        释放读锁
        
        Args:
            resource_id: 资源 ID
            holder_id: 持有者 ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            read_lock = self._get_lock(resource_id, LockType.READ)
            if not read_lock:
                return False
            
            if read_lock.remove_holder(holder_id):
                self._read_counts[resource_id] = max(0, self._read_counts.get(resource_id, 0) - 1)
                return True
            
            return False
    
    def acquire_write(
        self,
        resource_id: str,
        holder_id: str,
        timeout: Optional[float] = None,
    ) -> LockAcquisitionResult:
        """
        获取写锁
        
        Args:
            resource_id: 资源 ID
            holder_id: 持有者 ID
            timeout: 超时时间
            
        Returns:
            LockAcquisitionResult: 获取结果
        """
        start_time = time.time()
        
        with self._lock:
            write_lock = self._get_or_create_lock(resource_id, LockType.WRITE)
            read_lock = self._get_lock(resource_id, LockType.READ)
            
            # 检查是否已持有写锁（重入）
            if write_lock.is_held and holder_id in write_lock.holders:
                write_lock.add_holder(holder_id)  # 增加重入计数
                return LockAcquisitionResult(
                    success=True,
                    lock=write_lock,
                    acquired_at=datetime.now(),
                    wait_time=0.0,
                )
            
            # 检查是否有其他读锁
            if read_lock and read_lock.holder_count > 0:
                if holder_id not in read_lock.holders:
                    if timeout is None or timeout <= 0:
                        return LockAcquisitionResult(
                            success=False,
                            error="Resource is held by readers",
                        )
            
            # 添加到等待队列
            if self._enable_fairness and holder_id not in write_lock.waiters:
                write_lock.waiters.append(holder_id)
            
            # 等待所有读锁释放
            while True:
                read_lock = self._get_lock(resource_id, LockType.READ)
                if read_lock and read_lock.holder_count > 0:
                    if holder_id not in (read_lock.holders if read_lock else set()):
                        elapsed = time.time() - start_time
                        remaining = timeout - elapsed if timeout else 0
                        if timeout and remaining <= 0:
                            return LockAcquisitionResult(
                                success=False,
                                error="Timeout waiting for read locks",
                            )
                        time.sleep(0.01)
                        continue
                break
            
            # 获取写锁
            write_lock.add_holder(holder_id)
            
            # 从等待队列移除
            if holder_id in write_lock.waiters:
                write_lock.waiters.remove(holder_id)
            
            return LockAcquisitionResult(
                success=True,
                lock=write_lock,
                acquired_at=datetime.now(),
                wait_time=time.time() - start_time,
            )
    
    def release_write(self, resource_id: str, holder_id: str) -> bool:
        """
        释放写锁
        
        Args:
            resource_id: 资源 ID
            holder_id: 持有者 ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            write_lock = self._get_lock(resource_id, LockType.WRITE)
            if not write_lock:
                return False
            
            return write_lock.remove_holder(holder_id)
    
    def acquire_fair(
        self,
        resource_id: str,
        holder_id: str,
        timeout: Optional[float] = None,
    ) -> LockAcquisitionResult:
        """
        获取公平锁
        
        Args:
            resource_id: 资源 ID
            holder_id: 持有者 ID
            timeout: 超时时间
            
        Returns:
            LockAcquisitionResult: 获取结果
        """
        # 公平锁本质上是排他写锁
        return self.acquire_write(resource_id, holder_id, timeout)
    
    def release_fair(self, resource_id: str, holder_id: str) -> bool:
        """
        释放公平锁
        
        Args:
            resource_id: 资源 ID
            holder_id: 持有者 ID
            
        Returns:
            bool: 是否成功
        """
        return self.release_write(resource_id, holder_id)
    
    def is_read_locked(self, resource_id: str) -> bool:
        """检查是否有读锁"""
        read_lock = self._get_lock(resource_id, LockType.READ)
        return read_lock is not None and read_lock.is_held
    
    def is_write_locked(self, resource_id: str) -> bool:
        """检查是否有写锁"""
        write_lock = self._get_lock(resource_id, LockType.WRITE)
        return write_lock is not None and write_lock.is_held
    
    def get_read_holders(self, resource_id: str) -> List[str]:
        """获取读锁持有者"""
        read_lock = self._get_lock(resource_id, LockType.READ)
        return list(read_lock.holders) if read_lock else []
    
    def get_write_holder(self, resource_id: str) -> Optional[str]:
        """获取写锁持有者"""
        write_lock = self._get_lock(resource_id, LockType.WRITE)
        return write_lock.holder_id if write_lock else None
    
    @contextmanager
    def read_lock(self, resource_id: str, holder_id: str, timeout: Optional[float] = None):
        """读锁上下文管理器"""
        result = self.acquire_read(resource_id, holder_id, timeout)
        try:
            yield result.success
        finally:
            if result.success:
                self.release_read(resource_id, holder_id)
    
    @contextmanager
    def write_lock(self, resource_id: str, holder_id: str, timeout: Optional[float] = None):
        """写锁上下文管理器"""
        result = self.acquire_write(resource_id, holder_id, timeout)
        try:
            yield result.success
        finally:
            if result.success:
                self.release_write(resource_id, holder_id)
    
    @contextmanager
    def fair_lock(self, resource_id: str, holder_id: str, timeout: Optional[float] = None):
        """公平锁上下文管理器"""
        result = self.acquire_fair(resource_id, holder_id, timeout)
        try:
            yield result.success
        finally:
            if result.success:
                self.release_fair(resource_id, holder_id)
    
    def get_lock_info(self, resource_id: str) -> Dict[str, Any]:
        """获取锁信息"""
        read_lock = self._get_lock(resource_id, LockType.READ)
        write_lock = self._get_lock(resource_id, LockType.WRITE)
        
        return {
            "resource_id": resource_id,
            "read_lock": read_lock.to_dict() if read_lock else None,
            "write_lock": write_lock.to_dict() if write_lock else None,
            "read_count": self._read_counts.get(resource_id, 0),
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_locks": len(self._locks),
            "read_locks": sum(1 for l in self._locks.values() if l.lock_type == LockType.READ and l.is_held),
            "write_locks": sum(1 for l in self._locks.values() if l.lock_type == LockType.WRITE and l.is_held),
            "total_read_count": sum(self._read_counts.values()),
        }
