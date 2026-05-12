"""
恢复机制 - Recovery Manager

提供系统故障恢复和状态重建能力
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import List, Dict, Any, Optional, Callable, TypeVar, Generic
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import logging

from .event_store import EventStore, Event
from .snapshot import SnapshotManager, Snapshot

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RecoveryStrategy(Enum):
    """恢复策略"""
    FROM_SNAPSHOT = "from_snapshot"           # 从快照恢复
    FROM_EVENTS = "from_events"               # 从事件重放恢复
    SNAPSHOT_THEN_EVENTS = "snapshot_then_events"  # 快照+事件
    BEST_EFFORT = "best_effort"               # 尽力恢复


@dataclass
class RecoveryPoint:
    """恢复点"""
    aggregate_id: str
    snapshot_id: Optional[str]
    last_event_id: Optional[str]
    version: int
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "aggregate_id": self.aggregate_id,
            "snapshot_id": self.snapshot_id,
            "last_event_id": self.last_event_id,
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecoveryPoint":
        """从字典创建"""
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class RecoveryResult:
    """恢复结果"""
    success: bool
    aggregate_id: str
    recovered_state: Optional[Dict[str, Any]]
    recovery_point: Optional[RecoveryPoint]
    events_replayed: int
    snapshot_used: bool
    error_message: Optional[str] = None
    recovery_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "aggregate_id": self.aggregate_id,
            "recovered_state": self.recovered_state,
            "recovery_point": self.recovery_point.to_dict() if self.recovery_point else None,
            "events_replayed": self.events_replayed,
            "snapshot_used": self.snapshot_used,
            "error_message": self.error_message,
            "recovery_time": self.recovery_time
        }


class RecoveryManager:
    """
    恢复管理器
    
    负责从故障中恢复系统状态，支持多种恢复策略。
    """
    
    def __init__(
        self,
        event_store: Optional[EventStore] = None,
        snapshot_manager: Optional[SnapshotManager] = None,
        default_strategy: RecoveryStrategy = RecoveryStrategy.SNAPSHOT_THEN_EVENTS
    ):
        """
        初始化恢复管理器
        
        Args:
            event_store: 事件存储
            snapshot_manager: 快照管理器
            default_strategy: 默认恢复策略
        """
        self.event_store = event_store or EventStore()
        self.snapshot_manager = snapshot_manager or SnapshotManager()
        self.default_strategy = default_strategy
        
        self._recovery_points: Dict[str, RecoveryPoint] = {}
        self._recovery_handlers: Dict[str, Callable] = {}
        self._state_reducers: Dict[str, Callable[[Any, Event], Any]] = {}
        self._recovery_hooks: Dict[str, List[Callable]] = {
            "before_recovery": [],
            "after_recovery": [],
            "recovery_failed": []
        }
    
    def register_state_reducer(
        self,
        aggregate_id: str,
        reducer: Callable[[Any, Event], Any],
        initial_state: Any = None
    ) -> None:
        """
        注册状态 reducer
        
        Args:
            aggregate_id: 聚合 ID
            reducer: 状态 reducer 函数
            initial_state: 初始状态
        """
        self._state_reducers[aggregate_id] = reducer
        if initial_state is not None:
            self._recovery_handlers[aggregate_id] = lambda: initial_state
    
    def recover(
        self,
        aggregate_id: str,
        strategy: Optional[RecoveryStrategy] = None,
        reducer: Optional[Callable] = None
    ) -> RecoveryResult:
        """
        执行恢复
        
        Args:
            aggregate_id: 聚合 ID
            strategy: 恢复策略
            reducer: 状态 reducer
            
        Returns:
            RecoveryResult: 恢复结果
        """
        import time
        start_time = time.time()
        
        strategy = strategy or self.default_strategy
        reducer = reducer or self._state_reducers.get(aggregate_id)
        
        # 触发前置钩子
        for hook in self._recovery_hooks["before_recovery"]:
            hook(aggregate_id, strategy)
        
        try:
            if strategy == RecoveryStrategy.FROM_SNAPSHOT:
                result = self._recover_from_snapshot(aggregate_id, start_time)
            elif strategy == RecoveryStrategy.FROM_EVENTS:
                result = self._recover_from_events(aggregate_id, reducer, start_time)
            elif strategy == RecoveryStrategy.SNAPSHOT_THEN_EVENTS:
                result = self._recover_snapshot_then_events(aggregate_id, reducer, start_time)
            elif strategy == RecoveryStrategy.BEST_EFFORT:
                result = self._recover_best_effort(aggregate_id, reducer, start_time)
            else:
                result = self._recover_snapshot_then_events(aggregate_id, reducer, start_time)
            
            # 触发后置钩子
            for hook in self._recovery_hooks["after_recovery"]:
                hook(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Recovery failed for {aggregate_id}: {e}")
            
            result = RecoveryResult(
                success=False,
                aggregate_id=aggregate_id,
                recovered_state=None,
                recovery_point=None,
                events_replayed=0,
                snapshot_used=False,
                error_message=str(e),
                recovery_time=time.time() - start_time
            )
            
            for hook in self._recovery_hooks["recovery_failed"]:
                hook(result)
            
            return result
    
    def _recover_from_snapshot(
        self,
        aggregate_id: str,
        start_time: float
    ) -> RecoveryResult:
        """从快照恢复"""
        snapshot = self.snapshot_manager.get_latest_snapshot(aggregate_id)
        
        if not snapshot:
            return RecoveryResult(
                success=False,
                aggregate_id=aggregate_id,
                recovered_state=None,
                recovery_point=None,
                events_replayed=0,
                snapshot_used=False,
                error_message="No snapshot found",
                recovery_time=time.time() - start_time
            )
        
        recovery_point = RecoveryPoint(
            aggregate_id=aggregate_id,
            snapshot_id=snapshot.snapshot_id,
            last_event_id=None,
            version=snapshot.version,
            timestamp=datetime.now()
        )
        
        return RecoveryResult(
            success=True,
            aggregate_id=aggregate_id,
            recovered_state=snapshot.state,
            recovery_point=recovery_point,
            events_replayed=0,
            snapshot_used=True,
            recovery_time=time.time() - start_time
        )
    
    def _recover_from_events(
        self,
        aggregate_id: str,
        reducer: Optional[Callable],
        start_time: float
    ) -> RecoveryResult:
        """从事件重放恢复"""
        events = self.event_store.get_event_stream(aggregate_id)
        
        if not events:
            return RecoveryResult(
                success=False,
                aggregate_id=aggregate_id,
                recovered_state=None,
                recovery_point=None,
                events_replayed=0,
                snapshot_used=False,
                error_message="No events found",
                recovery_time=time.time() - start_time
            )
        
        state = None
        if reducer:
            state = reducer(None, None)  # 获取初始状态
            for event in events:
                state = reducer(state, event)
        else:
            # 使用事件数据作为状态
            state = {"events": [e.to_dict() for e in events]}
        
        recovery_point = RecoveryPoint(
            aggregate_id=aggregate_id,
            snapshot_id=None,
            last_event_id=events[-1].event_id if events else None,
            version=len(events),
            timestamp=datetime.now()
        )
        
        return RecoveryResult(
            success=True,
            aggregate_id=aggregate_id,
            recovered_state=state,
            recovery_point=recovery_point,
            events_replayed=len(events),
            snapshot_used=False,
            recovery_time=time.time() - start_time
        )
    
    def _recover_snapshot_then_events(
        self,
        aggregate_id: str,
        reducer: Optional[Callable],
        start_time: float
    ) -> RecoveryResult:
        """先从快照恢复，再重放事件"""
        snapshot = self.snapshot_manager.get_latest_snapshot(aggregate_id)
        events = self.event_store.get_event_stream(aggregate_id)
        
        # 确定起始状态
        start_version = 0
        start_state = None
        snapshot_used = False
        
        if snapshot:
            start_state = snapshot.state
            start_version = snapshot.version
            snapshot_used = True
        
        # 筛选需要重放的事件
        events_to_replay = [e for e in events if e.aggregate_id == aggregate_id]
        if snapshot:
            events_to_replay = [
                e for e in events_to_replay
                if e.event_id > (snapshot.parent_snapshot_id or "")
            ]
        
        # 重放事件
        if reducer and events_to_replay:
            if start_state is None:
                start_state = reducer(None, None)
            for event in events_to_replay:
                start_state = reducer(start_state, event)
        
        recovery_point = RecoveryPoint(
            aggregate_id=aggregate_id,
            snapshot_id=snapshot.snapshot_id if snapshot else None,
            last_event_id=events_to_replay[-1].event_id if events_to_replay else None,
            version=start_version + len(events_to_replay),
            timestamp=datetime.now()
        )
        
        return RecoveryResult(
            success=True,
            aggregate_id=aggregate_id,
            recovered_state=start_state,
            recovery_point=recovery_point,
            events_replayed=len(events_to_replay),
            snapshot_used=snapshot_used,
            recovery_time=time.time() - start_time
        )
    
    def _recover_best_effort(
        self,
        aggregate_id: str,
        reducer: Optional[Callable],
        start_time: float
    ) -> RecoveryResult:
        """尽力恢复"""
        # 优先尝试快照
        snapshot_result = self._recover_from_snapshot(aggregate_id, start_time)
        if snapshot_result.success:
            return snapshot_result
        
        # 然后尝试事件
        events_result = self._recover_from_events(aggregate_id, reducer, start_time)
        if events_result.success:
            return events_result
        
        # 都失败
        return RecoveryResult(
            success=False,
            aggregate_id=aggregate_id,
            recovered_state=None,
            recovery_point=None,
            events_replayed=0,
            snapshot_used=False,
            error_message="No snapshot or events found",
            recovery_time=time.time() - start_time
        )
    
    def save_recovery_point(
        self,
        aggregate_id: str,
        snapshot_id: Optional[str] = None,
        last_event_id: Optional[str] = None,
        version: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RecoveryPoint:
        """
        保存恢复点
        
        Args:
            aggregate_id: 聚合 ID
            snapshot_id: 快照 ID
            last_event_id: 最后事件 ID
            version: 版本号
            metadata: 元数据
            
        Returns:
            RecoveryPoint: 恢复点
        """
        recovery_point = RecoveryPoint(
            aggregate_id=aggregate_id,
            snapshot_id=snapshot_id,
            last_event_id=last_event_id,
            version=version,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self._recovery_points[aggregate_id] = recovery_point
        return recovery_point
    
    def get_recovery_point(self, aggregate_id: str) -> Optional[RecoveryPoint]:
        """获取恢复点"""
        return self._recovery_points.get(aggregate_id)
    
    def register_hook(self, event: str, callback: Callable) -> None:
        """注册钩子"""
        if event in self._recovery_hooks:
            self._recovery_hooks[event].append(callback)
    
    def validate_recovery(self, aggregate_id: str) -> Dict[str, Any]:
        """
        验证恢复能力
        
        Args:
            aggregate_id: 聚合 ID
            
        Returns:
            Dict: 验证结果
        """
        snapshot = self.snapshot_manager.get_latest_snapshot(aggregate_id)
        events = self.event_store.get_event_stream(aggregate_id)
        
        return {
            "aggregate_id": aggregate_id,
            "has_snapshot": snapshot is not None,
            "has_events": len(events) > 0,
            "event_count": len(events),
            "snapshot_version": snapshot.version if snapshot else None,
            "latest_event_id": events[-1].event_id if events else None,
            "can_recover": snapshot is not None or len(events) > 0
        }
    
    def export_recovery_points(self) -> List[Dict[str, Any]]:
        """导出恢复点"""
        return [rp.to_dict() for rp in self._recovery_points.values()]
    
    def import_recovery_points(self, recovery_points: List[Dict[str, Any]]) -> None:
        """导入恢复点"""
        for rp_dict in recovery_points:
            rp = RecoveryPoint.from_dict(rp_dict)
            self._recovery_points[rp.aggregate_id] = rp
