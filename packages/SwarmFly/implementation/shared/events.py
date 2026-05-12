"""
FLY深度实现 - 事件总线
"""

from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import logging


logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型"""
    # 系统事件
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    
    # 智能体事件
    AGENT_REGISTERED = "agent.registered"
    AGENT_UNREGISTERED = "agent.unregistered"
    AGENT_STATE_CHANGED = "agent.state_changed"
    
    # 任务事件
    TASK_SUBMITTED = "task.submitted"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    
    # 规则事件
    RULE_ADDED = "rule.added"
    RULE_UPDATED = "rule.updated"
    RULE_DELETED = "rule.deleted"
    RULE_TRIGGERED = "rule.triggered"
    RULE_CONFLICT = "rule.conflict"
    
    # 资源事件
    RESOURCE_ALLOCATED = "resource.allocated"
    RESOURCE_RELEASED = "resource.released"
    RESOURCE_EXHAUSTED = "resource.exhausted"
    
    # 趋势事件
    TREND_DETECTED = "trend.detected"
    ANOMALY_DETECTED = "anomaly.detected"
    PREDICTION_UPDATED = "prediction.updated"
    
    # 工具事件
    TOOL_REGISTERED = "tool.registered"
    TOOL_UNREGISTERED = "tool.unregistered"
    TOOL_INVOKED = "tool.invoked"
    TOOL_FAILED = "tool.failed"


@dataclass
class Event:
    """事件"""
    event_type: EventType
    source: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    
    def __str__(self) -> str:
        return f"Event({self.event_type.value}, source={self.source})"


class EventBus:
    """事件总线"""
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._async_subscribers: Dict[EventType, List[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history_size = 1000
        self._lock = asyncio.Lock()
    
    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]):
        """订阅事件（同步）"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed handler to {event_type.value}")
    
    def subscribe_async(self, event_type: EventType, handler: Callable[[Event], Any]):
        """订阅事件（异步）"""
        if event_type not in self._async_subscribers:
            self._async_subscribers[event_type] = []
        self._async_subscribers[event_type].append(handler)
        logger.debug(f"Subscribed async handler to {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """取消订阅"""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]
        if event_type in self._async_subscribers:
            self._async_subscribers[event_type] = [
                h for h in self._async_subscribers[event_type] if h != handler
            ]
    
    async def publish(self, event: Event):
        """发布事件"""
        async with self._lock:
            # 添加到历史记录
            self._event_history.append(event)
            if len(self._event_history) > self._max_history_size:
                self._event_history = self._event_history[-self._max_history_size:]
        
        logger.info(f"Publishing event: {event}")
        
        # 处理同步订阅者
        if event.event_type in self._subscribers:
            for handler in self._subscribers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
        
        # 处理异步订阅者
        if event.event_type in self._async_subscribers:
            for handler in self._async_subscribers[event.event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Error in async event handler: {e}")
    
    def publish_sync(self, event: Event):
        """同步发布事件"""
        # 添加到历史记录
        self._event_history.append(event)
        if len(self._event_history) > self._max_history_size:
            self._event_history = self._event_history[-self._max_history_size:]
        
        logger.info(f"Publishing sync event: {event}")
        
        if event.event_type in self._subscribers:
            for handler in self._subscribers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error in sync event handler: {e}")
    
    def get_history(self, event_type: Optional[EventType] = None, 
                   limit: int = 100) -> List[Event]:
        """获取事件历史"""
        if event_type:
            return [e for e in self._event_history if e.event_type == event_type][-limit:]
        return self._event_history[-limit:]
    
    def clear_history(self):
        """清除历史记录"""
        self._event_history.clear()


# 全局事件总线实例
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """获取全局事件总线"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus
