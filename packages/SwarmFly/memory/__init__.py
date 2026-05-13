"""
SwarmFly 共享内存池模块

提供多 Agent 共享内存管理、锁机制和缓存一致性功能
"""

from .shared_pool import (
    SharedMemoryPool,
    MemoryPoolConfig,
    PoolStats,
)
from .segment import (
    MemorySegment,
    SegmentType,
    SegmentAccess,
    SegmentManager,
)
from .lock_manager import (
    LockManager,
    Lock,
    LockType,
    LockAcquisitionResult,
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
    InvalidationResult,
)

__all__ = [
    # Shared Pool
    "SharedMemoryPool",
    "MemoryPoolConfig",
    "PoolStats",
    # Segment
    "MemorySegment",
    "SegmentType",
    "SegmentAccess",
    "SegmentManager",
    # Lock Manager
    "LockManager",
    "Lock",
    "LockType",
    "LockAcquisitionResult",
    "ReadLock",
    "WriteLock",
    "FairLock",
    # Sync Protocol
    "SyncProtocol",
    "SyncMessage",
    "SyncOperation",
    "SyncState",
    # Coherence
    "CacheCoherence",
    "CoherenceProtocol",
    "CacheLine",
    "CacheLineState",
    "InvalidationResult",
]
