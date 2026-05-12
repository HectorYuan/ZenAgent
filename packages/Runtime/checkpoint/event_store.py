"""
事件存储 - Event Store

提供事件溯源的存储和查询能力
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import json
import uuid


class EventType(Enum):
    """事件类型"""
    TASK_START = "task_start"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETE = "task_complete"
    TASK_FAIL = "task_fail"
    STATE_CHANGE = "state_change"
    ACTION_EXECUTE = "action_execute"
    ACTION_RESULT = "action_result"
    CHECKPOINT_SAVE = "checkpoint_save"
    CHECKPOINT_RESTORE = "checkpoint_restore"
    CUSTOM = "custom"


@dataclass
class Event:
    """事件"""
    event_id: str
    event_type: EventType
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    aggregate_id: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "metadata": self.metadata,
            "aggregate_id": self.aggregate_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """从字典创建"""
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["event_type"] = EventType(data["event_type"])
        return cls(**data)


class EventStore:
    """
    事件存储
    
    提供事件的追加、查询和重放能力。
    支持事件溯源模式，用于重建聚合状态。
    """
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        max_events: int = 10000
    ):
        """
        初始化事件存储
        
        Args:
            storage_path: 存储路径
            max_events: 最大事件数量
        """
        self.storage_path = storage_path
        self.max_events = max_events
        self._events: List[Event] = []
        self._snapshots: Dict[str, Any] = {}
        self._subscribers: List[Callable[[Event], None]] = []
        self._event_handlers: Dict[EventType, List[Callable]] = {
            et: [] for et in EventType
        }
    
    def append(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        aggregate_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Event:
        """
        追加事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            aggregate_id: 聚合 ID
            correlation_id: 关联 ID
            metadata: 附加元数据
            
        Returns:
            Event: 创建的事件
        """
        # 获取因果链中的上一个事件 ID
        causation_id = None
        if self._events:
            causation_id = self._events[-1].event_id
        
        event = Event(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(),
            data=data,
            metadata=metadata or {},
            aggregate_id=aggregate_id,
            correlation_id=correlation_id,
            causation_id=causation_id
        )
        
        self._events.append(event)
        
        # 触发订阅者
        for subscriber in self._subscribers:
            subscriber(event)
        
        # 触发事件处理器
        for handler in self._event_handlers.get(event_type, []):
            handler(event)
        
        # 持久化
        if self.storage_path:
            self._persist_event(event)
        
        # 清理旧事件
        self._cleanup_old_events()
        
        return event
    
    def get_events(
        self,
        aggregate_id: Optional[str] = None,
        event_types: Optional[List[EventType]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Event]:
        """
        查询事件
        
        Args:
            aggregate_id: 聚合 ID 过滤
            event_types: 事件类型过滤
            since: 起始时间
            until: 结束时间
            limit: 限制数量
            
        Returns:
            List[Event]: 事件列表
        """
        filtered = self._events
        
        if aggregate_id:
            filtered = [e for e in filtered if e.aggregate_id == aggregate_id]
        
        if event_types:
            filtered = [e for e in filtered if e.event_type in event_types]
        
        if since:
            filtered = [e for e in filtered if e.timestamp >= since]
        
        if until:
            filtered = [e for e in filtered if e.timestamp <= until]
        
        if limit:
            filtered = filtered[-limit:]
        
        return filtered
    
    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """根据 ID 获取事件"""
        for event in self._events:
            if event.event_id == event_id:
                return event
        return None
    
    def get_event_stream(
        self,
        aggregate_id: str,
        from_event_id: Optional[str] = None
    ) -> List[Event]:
        """
        获取事件流
        
        Args:
            aggregate_id: 聚合 ID
            from_event_id: 从指定事件开始
            
        Returns:
            List[Event]: 事件流
        """
        events = self.get_events(aggregate_id=aggregate_id)
        
        if from_event_id:
            start_index = next(
                (i for i, e in enumerate(events) if e.event_id == from_event_id),
                None
            )
            if start_index is not None:
                events = events[start_index + 1:]
        
        return events
    
    def replay(
        self,
        aggregate_id: str,
        event_handler: Callable[[Event], Any]
    ) -> List[Any]:
        """
        重放事件
        
        Args:
            aggregate_id: 聚合 ID
            event_handler: 事件处理函数
            
        Returns:
            List[Any]: 处理结果列表
        """
        events = self.get_event_stream(aggregate_id)
        results = []
        
        for event in events:
            result = event_handler(event)
            results.append(result)
        
        return results
    
    def subscribe(self, callback: Callable[[Event], None]) -> None:
        """订阅事件"""
        self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[Event], None]) -> None:
        """取消订阅"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    def register_handler(
        self,
        event_type: EventType,
        handler: Callable[[Event], None]
    ) -> None:
        """注册事件处理器"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def save_snapshot(
        self,
        aggregate_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        保存快照
        
        Args:
            aggregate_id: 聚合 ID
            state: 状态数据
            metadata: 快照元数据
        """
        snapshot_data = {
            "aggregate_id": aggregate_id,
            "state": state,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
            "event_count": len(self.get_events(aggregate_id=aggregate_id))
        }
        self._snapshots[aggregate_id] = snapshot_data
        
        if self.storage_path:
            self._persist_snapshot(aggregate_id, snapshot_data)
    
    def get_snapshot(self, aggregate_id: str) -> Optional[Dict[str, Any]]:
        """
        获取最新快照
        
        Args:
            aggregate_id: 聚合 ID
            
        Returns:
            Optional[Dict]: 快照数据
        """
        return self._snapshots.get(aggregate_id)
    
    def get_event_count(self, aggregate_id: Optional[str] = None) -> int:
        """获取事件数量"""
        if aggregate_id:
            return len(self.get_events(aggregate_id=aggregate_id))
        return len(self._events)
    
    def clear(self, aggregate_id: Optional[str] = None) -> None:
        """
        清除事件
        
        Args:
            aggregate_id: 聚合 ID，为空则清除所有
        """
        if aggregate_id:
            self._events = [
                e for e in self._events
                if e.aggregate_id != aggregate_id
            ]
            if aggregate_id in self._snapshots:
                del self._snapshots[aggregate_id]
        else:
            self._events.clear()
            self._snapshots.clear()
    
    def export_events(self) -> List[Dict[str, Any]]:
        """导出所有事件"""
        return [e.to_dict() for e in self._events]
    
    def import_events(self, events: List[Dict[str, Any]]) -> None:
        """
        导入事件
        
        Args:
            events: 事件列表
        """
        for event_dict in events:
            event = Event.from_dict(event_dict)
            self._events.append(event)
    
    def _cleanup_old_events(self) -> None:
        """清理旧事件"""
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events:]
    
    def _persist_event(self, event: Event) -> None:
        """持久化事件"""
        if not self.storage_path:
            return
        
        import os
        os.makedirs(self.storage_path, exist_ok=True)
        
        event_file = os.path.join(
            self.storage_path,
            f"{event.aggregate_id or 'global'}_{event.event_id}.json"
        )
        
        with open(event_file, 'w', encoding='utf-8') as f:
            json.dump(event.to_dict(), f, ensure_ascii=False, indent=2)
    
    def _persist_snapshot(self, aggregate_id: str, snapshot: Dict[str, Any]) -> None:
        """持久化快照"""
        if not self.storage_path:
            return
        
        import os
        os.makedirs(self.storage_path, exist_ok=True)
        
        snapshot_file = os.path.join(
            self.storage_path,
            f"snapshot_{aggregate_id}.json"
        )
        
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
