"""
事件总线
提供发布/订阅模式的事件通信
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Callable, Any, Optional
import json
import time
import threading


class EventType(Enum):
    """事件类型枚举"""
    AGENT_CREATED = "agent.created"
    AGENT_DESTROYED = "agent.destroyed"
    SESSION_STARTED = "session.started"
    SESSION_ENDED = "session.ended"
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"
    TASK_SUBMITTED = "task.submitted"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    ERROR = "system.error"


@dataclass
class Event:
    """事件对象"""
    event_type: EventType
    source: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    event_id: str = ""


class EventBus:
    """
    事件总线
    支持发布/订阅模式，支持 Redis 分布式
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 use_redis: bool = True):
        """
        初始化事件总线
        """
        self.redis_url = redis_url
        self.use_redis = use_redis
        
        # Redis 连接
        self._redis = None
        if use_redis:
            try:
                import redis
                self._redis = redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self.use_redis = False
        
        # 本地订阅者
        self._local_subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        
    def publish(self, event: Event) -> int:
        """发布事件"""
        count = self._publish_local(event)
        
        if self.use_redis and self._redis:
            try:
                channel = event.event_type.value
                message = json.dumps({
                    'event_type': event.event_type.value,
                    'source': event.source,
                    'data': event.data,
                    'timestamp': event.timestamp,
                })
                self._redis.publish(channel, message)
            except Exception:
                pass
                
        return count
    
    def _publish_local(self, event: Event) -> int:
        """本地发布"""
        count = 0
        with self._lock:
            key = event.event_type.value
            if key in self._local_subscribers:
                for callback in self._local_subscribers[key]:
                    try:
                        callback(event)
                        count += 1
                    except Exception:
                        pass
        return count
    
    def subscribe(self, event_type: str, callback: Callable) -> str:
        """订阅事件"""
        import uuid
        sub_id = str(uuid.uuid4())
        with self._lock:
            if event_type not in self._local_subscribers:
                self._local_subscribers[event_type] = []
            self._local_subscribers[event_type].append(callback)
        return sub_id
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                'local_subscribers': sum(len(v) for v in self._local_subscribers.values()),
                'event_types': list(self._local_subscribers.keys()),
                'use_redis': self.use_redis,
            }
