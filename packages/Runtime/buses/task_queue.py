"""
任务队列
基于 Redis Streams 的持久化任务队列
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
import json
import time
import uuid
import threading


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class Task:
    """任务对象"""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None


class TaskQueue:
    """
    任务队列
    支持 Redis Streams 和本地内存模式
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 use_redis: bool = True, queue_name: str = "zenagent:tasks"):
        """
        初始化任务队列
        """
        self.redis_url = redis_url
        self.use_redis = use_redis
        self.queue_name = queue_name
        
        # Redis 连接
        self._redis = None
        if use_redis:
            try:
                import redis
                self._redis = redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self.use_redis = False
        
        # 本地内存队列
        self._local_queue: List[Task] = []
        self._lock = threading.RLock()
        
    def enqueue(self, task: Task) -> str:
        """
        入队任务
        
        Args:
            task: 任务对象
            
        Returns:
            任务 ID
        """
        task.task_id = task.task_id or str(uuid.uuid4())
        
        if self.use_redis and self._redis:
            return self._enqueue_redis(task)
        else:
            return self._enqueue_local(task)
    
    def _enqueue_redis(self, task: Task) -> str:
        """Redis 入队"""
        try:
            message = {
                'task_id': task.task_id,
                'task_type': task.task_type,
                'payload': json.dumps(task.payload),
                'priority': task.priority.value,
                'created_at': str(task.created_at),
                'status': task.status,
            }
            self._redis.xadd(self.queue_name, message)
            return task.task_id
        except Exception:
            return self._enqueue_local(task)
    
    def _enqueue_local(self, task: Task) -> str:
        """本地入队"""
        with self._lock:
            self._local_queue.append(task)
            # 按优先级排序
            self._local_queue.sort(key=lambda t: t.priority.value, reverse=True)
        return task.task_id
    
    def dequeue(self, timeout: int = 0) -> Optional[Task]:
        """
        出队任务
        
        Args:
            timeout: 超时时间（秒），0 表示非阻塞
            
        Returns:
            任务对象或 None
        """
        if self.use_redis and self._redis:
            return self._dequeue_redis(timeout)
        else:
            return self._dequeue_local()
    
    def _dequeue_redis(self, timeout: int) -> Optional[Task]:
        """Redis 出队"""
        try:
            result = self._redis.xread({self.queue_name: '0'}, count=1, block=timeout * 1000)
            if result:
                stream_id, data = result[0][1][0]
                task = Task(
                    task_id=data['task_id'],
                    task_type=data['task_type'],
                    payload=json.loads(data['payload']),
                    priority=TaskPriority(int(data['priority'])),
                    created_at=float(data['created_at']),
                    status=data['status'],
                )
                self._redis.xdel(self.queue_name, stream_id)
                return task
        except Exception:
            pass
        return self._dequeue_local()
    
    def _dequeue_local(self) -> Optional[Task]:
        """本地出队"""
        with self._lock:
            if self._local_queue:
                return self._local_queue.pop(0)
        return None
    
    def ack(self, task_id: str, result: Any = None, error: str = None) -> bool:
        """
        确认任务完成
        
        Args:
            task_id: 任务 ID
            result: 执行结果
            error: 错误信息
            
        Returns:
            是否成功
        """
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                'queue_length': len(self._local_queue),
                'use_redis': self.use_redis,
                'queue_name': self.queue_name,
            }
