"""
优先级任务队列 + 背压控制器

设计依据: E2E_OPTIMIZATION_DESIGN §模块4, M8_P5

三优先级 P0/P1/P2 + 水位监测 + 自动拒绝
"""

import asyncio
import time
import logging
from typing import Any, Optional, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class Priority(int, Enum):
    P0_REALTIME = 1   # 实时，队列小，不限速
    P1_NORMAL = 2     # 普通，标准限速
    P2_BACKGROUND = 3  # 后台，严格限速


@dataclass(order=True)
class PriorityTask:
    """优先级任务"""
    priority: Priority
    created_at: float = field(default_factory=time.monotonic, compare=False)
    task_id: str = field(default="", compare=False)
    payload: Any = field(default=None, compare=False)

    def __post_init__(self):
        if not self.task_id:
            import uuid
            self.task_id = str(uuid.uuid4())


@dataclass
class QueueStats:
    """队列统计"""
    p0_enqueued: int = 0
    p1_enqueued: int = 0
    p2_enqueued: int = 0
    p0_dequeued: int = 0
    p1_dequeued: int = 0
    p2_dequeued: int = 0
    rejected: int = 0
    rejected_by_backpressure: int = 0
    avg_wait_ms: float = 0.0
    peak_queue_depth: int = 0

    @property
    def total_enqueued(self) -> int:
        return self.p0_enqueued + self.p1_enqueued + self.p2_enqueued

    @property
    def reject_rate(self) -> float:
        if self.total_enqueued + self.rejected == 0:
            return 0.0
        return self.rejected / (self.total_enqueued + self.rejected)


class BackpressureController:
    """
    背压控制器

    根据队列水位自动拒绝低优先级任务
    """

    def __init__(
        self,
        warning_threshold: float = 0.5,   # 开始拒绝 P2
        critical_threshold: float = 0.8,   # 拒绝 P2+P1
        panic_threshold: float = 0.95,     # 拒绝全部
    ):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.panic_threshold = panic_threshold
        self._current_depth = 0
        self._max_depth = 0

    def update_depth(self, current_depth: int, max_depth: int):
        """更新当前水位"""
        self._current_depth = current_depth
        self._max_depth = max(max_depth, 1)

    @property
    def water_level(self) -> float:
        """水位百分比 0-1"""
        return self._current_depth / max(self._max_depth, 1)

    def can_accept(self, priority: Priority) -> bool:
        """
        检查是否可以接受指定优先级的任务

        返回 False = 拒绝
        """
        wl = self.water_level

        if wl >= self.panic_threshold:
            return False  # 拒绝全部

        if wl >= self.critical_threshold:
            return priority == Priority.P0_REALTIME  # 只接受 P0

        if wl >= self.warning_threshold:
            return priority != Priority.P2_BACKGROUND  # 拒绝 P2

        return True

    def get_status(self) -> dict:
        return {
            "water_level": round(self.water_level, 3),
            "current_depth": self._current_depth,
            "max_depth": self._max_depth,
            "warning": self.water_level >= self.warning_threshold,
            "critical": self.water_level >= self.critical_threshold,
            "panic": self.water_level >= self.panic_threshold,
        }


class PriorityTaskQueue:
    """
    优先级任务队列

    - P0: 实时, capacity=20, 不限速
    - P1: 普通, capacity=200
    - P2: 后台, capacity=500
    - 背压: 水位上升自动拒绝低优先级
    """

    P0_CAPACITY = 20
    P1_CAPACITY = 200
    P2_CAPACITY = 500
    TOTAL_CAPACITY = P0_CAPACITY + P1_CAPACITY + P2_CAPACITY

    def __init__(self, backpressure: Optional[BackpressureController] = None):
        self._queue: asyncio.PriorityQueue[PriorityTask] = asyncio.PriorityQueue(
            maxsize=self.TOTAL_CAPACITY
        )
        self._backpressure = backpressure or BackpressureController()
        self._stats = QueueStats()
        self._lock = asyncio.Lock()
        self._wait_times: list[float] = []  # 用于计算平均等待时间

    @property
    def stats(self) -> dict:
        return {
            "p0_enqueued": self._stats.p0_enqueued,
            "p1_enqueued": self._stats.p1_enqueued,
            "p2_enqueued": self._stats.p2_enqueued,
            "rejected": self._stats.rejected,
            "rejected_by_backpressure": self._stats.rejected_by_backpressure,
            "queue_size": self._queue.qsize(),
            "peak_queue_depth": self._stats.peak_queue_depth,
            "reject_rate": round(self._stats.reject_rate, 4),
            "avg_wait_ms": round(self._stats.avg_wait_ms, 1),
            "backpressure": self._backpressure.get_status(),
        }

    def _get_capacity(self, priority: Priority) -> int:
        if priority == Priority.P0_REALTIME:
            return self.P0_CAPACITY
        elif priority == Priority.P1_NORMAL:
            return self.P1_CAPACITY
        return self.P2_CAPACITY

    async def enqueue(
        self,
        payload: Any,
        priority: Priority = Priority.P1_NORMAL,
        timeout: Optional[float] = None,
    ) -> Optional[PriorityTask]:
        """
        入队任务

        Returns:
            PriorityTask if enqueued, None if rejected
        """
        async with self._lock:
            # 背压检查
            self._backpressure.update_depth(self._queue.qsize(), self.TOTAL_CAPACITY)
            if not self._backpressure.can_accept(priority):
                self._stats.rejected += 1
                self._stats.rejected_by_backpressure += 1
                logger.debug(f"Backpressure rejected {priority.name} (water_level={self._backpressure.water_level:.2f})")
                return None

        task = PriorityTask(priority=priority, payload=payload)

        try:
            if timeout is not None:
                await asyncio.wait_for(self._queue.put(task), timeout=timeout)
            else:
                self._queue.put_nowait(task)
        except (asyncio.QueueFull, asyncio.TimeoutError):
            self._stats.rejected += 1
            return None

        async with self._lock:
            if priority == Priority.P0_REALTIME:
                self._stats.p0_enqueued += 1
            elif priority == Priority.P1_NORMAL:
                self._stats.p1_enqueued += 1
            else:
                self._stats.p2_enqueued += 1

            # 更新峰值
            self._stats.peak_queue_depth = max(
                self._stats.peak_queue_depth, self._queue.qsize()
            )

        return task

    async def dequeue(self, timeout: Optional[float] = None) -> Optional[PriorityTask]:
        """
        出队任务（按优先级）

        Returns:
            PriorityTask or None
        """
        try:
            if timeout is not None:
                task = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            else:
                task = await self._queue.get()
        except asyncio.TimeoutError:
            return None

        wait_time = (time.monotonic() - task.created_at) * 1000
        self._wait_times.append(wait_time)
        if len(self._wait_times) > 100:
            self._wait_times = self._wait_times[-100:]
        self._stats.avg_wait_ms = sum(self._wait_times) / len(self._wait_times)

        async with self._lock:
            if task.priority == Priority.P0_REALTIME:
                self._stats.p0_dequeued += 1
            elif task.priority == Priority.P1_NORMAL:
                self._stats.p1_dequeued += 1
            else:
                self._stats.p2_dequeued += 1

        return task

    async def process(
        self,
        handler: Callable[[Any], Awaitable[Any]],
        timeout: Optional[float] = None,
    ) -> Optional[Any]:
        """
        便捷方法: 出队 → 处理

        Returns:
            处理结果
        """
        task = await self.dequeue(timeout=timeout)
        if task is None:
            return None
        return await handler(task.payload)

    def reset_stats(self):
        self._stats = QueueStats()
        self._wait_times.clear()
