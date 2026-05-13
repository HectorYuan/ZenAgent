"""
任务分发器

负责任务的创建、分配和跟踪
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime
import uuid
import threading


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"       # 待处理
    QUEUED = "queued"         # 已入队
    ASSIGNED = "assigned"     # 已分配
    RUNNING = "running"       # 执行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消


class DispatchStrategy(Enum):
    """分发策略枚举"""
    RANDOM = "random"              # 随机分发
    ROUND_ROBIN = "round_robin"    # 轮询分发
    LEAST_LOADED = "least_loaded"  # 最低负载
    PRIORITY = "priority"          # 优先级
    AFFINITY = "affinity"           # 亲和性


@dataclass
class Task:
    """
    任务数据类
    
    表示一个可分发的工作单元
    """
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    
    # 任务内容
    payload: Dict[str, Any] = field(default_factory=dict)
    
    # 分配信息
    assigned_agent: Optional[str] = None
    preferred_agents: List[str] = field(default_factory=list)
    excluded_agents: List[str] = field(default_factory=list)
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 结果
    result: Optional[Any] = None
    error: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    
    # 依赖
    dependencies: List[str] = field(default_factory=list)
    dependent_tasks: List[str] = field(default_factory=list)
    
    # 重试
    max_retries: int = 3
    retry_count: int = 0
    
    @property
    def is_completed(self) -> bool:
        """任务是否已完成"""
        return self.status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
    
    @property
    def can_retry(self) -> bool:
        """是否可以重试"""
        return (
            self.status == TaskStatus.FAILED
            and self.retry_count < self.max_retries
        )
    
    def get_duration(self) -> Optional[float]:
        """获取任务执行时长（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "assigned_agent": self.assigned_agent,
            "created_at": self.created_at.isoformat(),
            "duration": self.get_duration(),
            "retry_count": self.retry_count,
            "tags": list(self.tags),
        }


@dataclass
class TaskDispatcher:
    """
    任务分发器
    
    管理任务队列并负责将任务分配给 Agent
    """
    
    strategy: DispatchStrategy = DispatchStrategy.ROUND_ROBIN
    
    def __post_init__(self):
        """初始化后处理"""
        self._tasks: Dict[str, Task] = {}
        self._queues: Dict[TaskPriority, List[str]] = {
            priority: [] for priority in TaskPriority
        }
        self._agent_assignments: Dict[str, List[str]] = {}  # agent_id -> task_ids
        self._round_robin_index: Dict[TaskPriority, int] = {
            priority: 0 for priority in TaskPriority
        }
        self._lock = threading.RLock()
        
        # 可用的 Agent
        self._available_agents: List[str] = []
        
        # 回调
        self._on_task_assigned: List[Callable[[Task, str], None]] = []
        self._on_task_completed: List[Callable[[Task], None]] = []
        self._on_task_failed: List[Callable[[Task], None]] = []
    
    @property
    def pending_count(self) -> int:
        """待处理任务数量"""
        return sum(len(queue) for queue in self._queues.values())
    
    @property
    def assigned_count(self) -> int:
        """已分配任务数量"""
        return len(self._tasks) - self.pending_count - sum(
            1 for t in self._tasks.values() if t.is_completed
        )
    
    def register_agent(self, agent_id: str) -> None:
        """
        注册可用的 Agent
        
        Args:
            agent_id: Agent ID
        """
        with self._lock:
            if agent_id not in self._available_agents:
                self._available_agents.append(agent_id)
                self._agent_assignments[agent_id] = []
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        注销 Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            if agent_id in self._available_agents:
                self._available_agents.remove(agent_id)
                # 重新分配该 Agent 的任务
                tasks_to_requeue = self._agent_assignments.pop(agent_id, [])
                for task_id in tasks_to_requeue:
                    if task_id in self._tasks:
                        self._requeue_task(task_id)
                return True
            return False
    
    def get_available_agents(self) -> List[str]:
        """获取可用 Agent 列表"""
        return self._available_agents.copy()
    
    def submit_task(
        self,
        name: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        description: str = "",
        preferred_agents: Optional[List[str]] = None,
        excluded_agents: Optional[List[str]] = None,
        tags: Optional[Set[str]] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Task:
        """
        提交新任务
        
        Args:
            name: 任务名称
            payload: 任务数据
            priority: 优先级
            description: 描述
            preferred_agents: 优先分配的 Agent
            excluded_agents: 排除的 Agent
            tags: 任务标签
            dependencies: 依赖的任务 ID
            
        Returns:
            Task: 创建的任务对象
        """
        with self._lock:
            task = Task(
                name=name,
                description=description,
                payload=payload,
                priority=priority,
                preferred_agents=preferred_agents or [],
                excluded_agents=excluded_agents or [],
                tags=tags or set(),
                dependencies=dependencies or [],
            )
            
            self._tasks[task.task_id] = task
            self._queues[priority].append(task.task_id)
            task.status = TaskStatus.QUEUED
            
            return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        获取任务对象
        
        Args:
            task_id: 任务 ID
            
        Returns:
            Optional[Task]: 任务对象
        """
        return self._tasks.get(task_id)
    
    def get_next_task(
        self,
        agent_id: Optional[str] = None,
        filter_tags: Optional[Set[str]] = None,
    ) -> Optional[Task]:
        """
        获取下一个待分配的任务
        
        Args:
            agent_id: 请求任务的 Agent ID
            filter_tags: 标签过滤器
            
        Returns:
            Optional[Task]: 下一个任务
        """
        with self._lock:
            # 按优先级从高到低检查
            for priority in sorted(TaskPriority, key=lambda p: p.value, reverse=True):
                queue = self._queues[priority]
                tasks_to_remove = []
                
                for i, task_id in enumerate(queue):
                    task = self._tasks.get(task_id)
                    if not task:
                        tasks_to_remove.append(i)
                        continue
                    
                    # 检查依赖
                    if not self._check_dependencies(task):
                        continue
                    
                    # 检查标签过滤
                    if filter_tags and not task.tags.intersection(filter_tags):
                        continue
                    
                    # 检查 Agent 亲和性
                    if agent_id:
                        if agent_id in task.excluded_agents:
                            continue
                        # 优先分配给偏好的 Agent
                        if task.preferred_agents and agent_id not in task.preferred_agents:
                            continue
                    
                    # 移除任务
                    tasks_to_remove.append(i)
                    self._assign_task(task, agent_id)
                    return task
                
                # 清理无效任务引用
                for i in reversed(tasks_to_remove):
                    if i < len(queue):
                        queue.pop(i)
            
            return None
    
    def dispatch_task(
        self,
        task_id: str,
        agent_id: str,
    ) -> bool:
        """
        手动分配任务给 Agent
        
        Args:
            task_id: 任务 ID
            agent_id: Agent ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.is_completed:
                return False
            
            if agent_id not in self._available_agents:
                return False
            
            # 从队列移除
            for queue in self._queues.values():
                if task_id in queue:
                    queue.remove(task_id)
                    break
            
            self._assign_task(task, agent_id)
            return True
    
    def _assign_task(self, task: Task, agent_id: Optional[str]) -> None:
        """分配任务给 Agent"""
        task.assigned_agent = agent_id
        task.assigned_at = datetime.now()
        task.status = TaskStatus.ASSIGNED
        
        if agent_id:
            if agent_id not in self._agent_assignments:
                self._agent_assignments[agent_id] = []
            self._agent_assignments[agent_id].append(task.task_id)
        
        # 触发回调
        for callback in self._on_task_assigned:
            try:
                callback(task, agent_id)
            except Exception:
                pass
    
    def _requeue_task(self, task_id: str) -> None:
        """重新入队任务"""
        task = self._tasks.get(task_id)
        if task and not task.is_completed:
            task.status = TaskStatus.QUEUED
            task.assigned_agent = None
            task.assigned_at = None
            self._queues[task.priority].append(task_id)
    
    def _check_dependencies(self, task: Task) -> bool:
        """检查任务依赖是否满足"""
        for dep_id in task.dependencies:
            dep_task = self._tasks.get(dep_id)
            if dep_task and dep_task.status != TaskStatus.COMPLETED:
                return False
        return True
    
    def complete_task(
        self,
        task_id: str,
        result: Any = None,
    ) -> bool:
        """
        标记任务完成
        
        Args:
            task_id: 任务 ID
            result: 任务结果
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            
            # 从 Agent 分配列表移除
            if task.assigned_agent and task.assigned_agent in self._agent_assignments:
                if task_id in self._agent_assignments[task.assigned_agent]:
                    self._agent_assignments[task.assigned_agent].remove(task_id)
            
            # 触发回调
            for callback in self._on_task_completed:
                try:
                    callback(task)
                except Exception:
                    pass
            
            return True
    
    def fail_task(
        self,
        task_id: str,
        error: str,
    ) -> bool:
        """
        标记任务失败
        
        Args:
            task_id: 任务 ID
            error: 错误信息
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            task.error = error
            task.retry_count += 1
            
            if task.can_retry:
                # 重试
                self._requeue_task(task)
            else:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                
                # 触发回调
                for callback in self._on_task_failed:
                    try:
                        callback(task)
                    except Exception:
                        pass
            
            return True
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.is_completed:
                return False
            
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            
            # 从队列移除
            for queue in self._queues.values():
                if task_id in queue:
                    queue.remove(task_id)
                    break
            
            return True
    
    def get_tasks_by_agent(self, agent_id: str) -> List[Task]:
        """获取 Agent 的所有任务"""
        task_ids = self._agent_assignments.get(agent_id, [])
        return [self._tasks[t] for t in task_ids if t in self._tasks]
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """获取指定状态的任务"""
        return [t for t in self._tasks.values() if t.status == status]
    
    def get_tasks_by_tag(self, tag: str) -> List[Task]:
        """获取指定标签的任务"""
        return [t for t in self._tasks.values() if tag in t.tags]
    
    def register_callback(
        self,
        event: str,
        callback: Callable[..., None],
    ) -> None:
        """
        注册事件回调
        
        Args:
            event: 事件类型
            callback: 回调函数
        """
        if event == "task_assigned":
            self._on_task_assigned.append(callback)
        elif event == "task_completed":
            self._on_task_completed.append(callback)
        elif event == "task_failed":
            self._on_task_failed.append(callback)
    
    def get_queue_summary(self) -> Dict[str, Any]:
        """获取队列摘要"""
        return {
            "total_tasks": len(self._tasks),
            "pending_by_priority": {
                p.value: len(self._queues[p])
                for p in TaskPriority
            },
            "assigned_count": self.assigned_count,
            "completed_count": len(self.get_tasks_by_status(TaskStatus.COMPLETED)),
            "failed_count": len(self.get_tasks_by_status(TaskStatus.FAILED)),
            "available_agents": len(self._available_agents),
        }
