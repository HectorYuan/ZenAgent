"""
异步预缓存模块

设计依据: M8_P1_CACHE_ENHANCEMENT_DESIGN.md §3.2

PreCacheWorker: 单 Worker 协程，监听热点变化，异步调用 LLM 预计算高频响应
"""

import asyncio
import logging
from typing import Optional, Callable, Awaitable, Any
from dataclasses import dataclass, field

from .core import ChatRequest, LLMResponse
from .cache import HotLevel, CacheManager

logger = logging.getLogger(__name__)


@dataclass
class PreCacheTask:
    """预缓存任务"""
    cache_key: str
    request: ChatRequest
    priority: int = 0           # 优先级 (越高越先执行)
    created_at: float = 0.0


@dataclass
class PreCacheStats:
    """预缓存统计"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0      # 队列满时丢弃
    queue_max_size: int = 0
    current_queue_size: int = 0

    @property
    def success_rate(self) -> float:
        if self.completed_tasks + self.failed_tasks == 0:
            return 0.0
        return self.completed_tasks / (self.completed_tasks + self.failed_tasks)


class PreCacheWorker:
    """
    异步预缓存 Worker

    单协程后台运行，从队列取任务执行 LLM 预计算
    """

    def __init__(
        self,
        cache_manager: CacheManager,
        llm_caller: Callable[[ChatRequest], Awaitable[LLMResponse]],
        queue_size: int = 20,
        hot_level_trigger: HotLevel = HotLevel.HOT
    ):
        self._cache = cache_manager
        self._llm_caller = llm_caller
        self._queue: asyncio.Queue[PreCacheTask] = asyncio.Queue(maxsize=queue_size)
        self._hot_level_trigger = hot_level_trigger
        self._stats = PreCacheStats(queue_max_size=queue_size)
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False

    @property
    def stats(self) -> PreCacheStats:
        return self._stats

    async def enqueue(self, key: str, request: ChatRequest, priority: int = 0):
        """
        入队预缓存任务

        队列满时丢弃最低优先级任务
        """
        task = PreCacheTask(
            cache_key=key,
            request=request,
            priority=priority,
            created_at=asyncio.get_event_loop().time()
        )

        try:
            self._queue.put_nowait(task)
            self._stats.total_tasks += 1
            self._stats.current_queue_size = self._queue.qsize()
            logger.debug(f"Precache enqueued: {key[:30]}... (queue={self._queue.qsize()})")
        except asyncio.QueueFull:
            # 队列满，尝试替换低优先级任务
            self._stats.skipped_tasks += 1
            logger.debug(f"Precache queue full, skipped: {key[:30]}...")

    async def _worker_loop(self):
        """工作循环：从队列取任务并执行预缓存"""
        while self._running:
            try:
                # 阻塞等待任务，超时 1 秒检查运行状态
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)

                await self._execute_task(task)

                self._queue.task_done()
                self._stats.current_queue_size = self._queue.qsize()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Precache worker error: {e}")
                await asyncio.sleep(0.5)

    async def _execute_task(self, task: PreCacheTask):
        """执行单个预缓存任务"""
        try:
            logger.debug(f"Precache executing: {task.cache_key[:30]}...")

            # 调用 LLM 获取响应
            response = await self._llm_caller(task.request)

            # 写入缓存（标记为预缓存）
            await self._cache.set(
                task.request,
                response.model_dump(),
                precached=True
            )

            self._cache.tracker.record_precache()
            self._stats.completed_tasks += 1
            logger.debug(f"Precache completed: {task.cache_key[:30]}...")

        except Exception as e:
            self._stats.failed_tasks += 1
            logger.warning(f"Precache failed: {task.cache_key[:30]}... error={e}")

    async def start(self):
        """启动预缓存 Worker"""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("PreCacheWorker started")

    async def stop(self):
        """停止预缓存 Worker"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        logger.info("PreCacheWorker stopped")

    def get_stats(self) -> dict:
        """获取预缓存统计"""
        return {
            "total_tasks": self._stats.total_tasks,
            "completed_tasks": self._stats.completed_tasks,
            "failed_tasks": self._stats.failed_tasks,
            "skipped_tasks": self._stats.skipped_tasks,
            "success_rate": round(self._stats.success_rate, 4),
            "current_queue_size": self._stats.current_queue_size,
            "queue_max_size": self._stats.queue_max_size,
        }

    def should_precache(self, key: str) -> bool:
        """检查是否需要预缓存该 key"""
        level = self._cache.tracker.get_level(key)
        return level == self._hot_level_trigger
