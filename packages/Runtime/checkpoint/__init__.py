# Checkpoint - 事件溯源与断点恢复模块
"""
Checkpoint 系统模块，提供任务状态保存与恢复功能

包含:
- event_store: 事件存储
- snapshot: 快照管理
- recovery: 恢复机制
"""

from .event_store import EventStore, Event, EventType
from .snapshot import SnapshotManager, Snapshot, SnapshotType
from .recovery import RecoveryManager, RecoveryStrategy, RecoveryResult, RecoveryPoint

__all__ = [
    "EventStore",
    "Event",
    "EventType",
    "SnapshotManager",
    "Snapshot",
    "SnapshotType",
    "RecoveryManager",
    "RecoveryStrategy",
    "RecoveryResult",
    "RecoveryPoint",
]
