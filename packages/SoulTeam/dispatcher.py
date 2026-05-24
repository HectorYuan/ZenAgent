"""
六车道调度器 (M10 Phase G)

设计依据: 智能体调度指南 v2.1

3 规划车道 + 3 执行车道 + 晋升规则 + 并发控制
"""

import asyncio
import time
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field


class LaneType(str, Enum):
    PLAN_STRATEGY = "plan_strategy"     # 规划: 策略
    PLAN_TACTICAL = "plan_tactical"     # 规划: 战术
    PLAN_OPERATIONAL = "plan_operational"  # 规划: 操作
    EXEC_CRITICAL = "exec_critical"     # 执行: 关键
    EXEC_STANDARD = "exec_standard"     # 执行: 标准
    EXEC_BACKGROUND = "exec_background"  # 执行: 后台


class LaneState(str, Enum):
    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    OVERLOADED = "OVERLOADED"
    DRAINING = "DRAINING"


@dataclass
class LaneConfig:
    lane: LaneType
    max_concurrent: int = 3
    priority: int = 3
    promote_threshold: float = 0.8    # 利用率 > 此值触发晋升
    demote_threshold: float = 0.2     # 利用率 < 此值触发降级
    timeout: float = 300.0


DEFAULT_LANE_CONFIGS = {
    LaneType.PLAN_STRATEGY: LaneConfig(LaneType.PLAN_STRATEGY, max_concurrent=2, priority=1),
    LaneType.PLAN_TACTICAL: LaneConfig(LaneType.PLAN_TACTICAL, max_concurrent=3, priority=2),
    LaneType.PLAN_OPERATIONAL: LaneConfig(LaneType.PLAN_OPERATIONAL, max_concurrent=5, priority=3),
    LaneType.EXEC_CRITICAL: LaneConfig(LaneType.EXEC_CRITICAL, max_concurrent=2, priority=1, timeout=600),
    LaneType.EXEC_STANDARD: LaneConfig(LaneType.EXEC_STANDARD, max_concurrent=3, priority=2),
    LaneType.EXEC_BACKGROUND: LaneConfig(LaneType.EXEC_BACKGROUND, max_concurrent=5, priority=4),
}


@dataclass
class DispatchTask:
    task_id: str
    lane: LaneType
    agent_id: str
    payload: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None


class LaneDispatcher:
    """六车道调度器"""

    def __init__(self):
        self._lanes: dict[LaneType, LaneConfig] = dict(DEFAULT_LANE_CONFIGS)
        self._active: dict[LaneType, list[DispatchTask]] = {lt: [] for lt in LaneType}
        self._waiting: dict[LaneType, list[DispatchTask]] = {lt: [] for lt in LaneType}
        self._agent_loads: dict[str, int] = {}
        self._lock = asyncio.Lock()

    @property
    def stats(self) -> dict:
        return {
            lt.value: {
                "active": len(self._active.get(lt, [])),
                "waiting": len(self._waiting.get(lt, [])),
                "config": {
                    "max_concurrent": self._lanes[lt].max_concurrent,
                    "priority": self._lanes[lt].priority,
                }
            }
            for lt in LaneType
        }

    async def submit(self, task_id: str, agent_id: str, lane: LaneType,
                     payload: dict = None) -> DispatchTask:
        """提交任务到指定车道"""
        task = DispatchTask(task_id=task_id, lane=lane, agent_id=agent_id,
                            payload=payload or {})

        async with self._lock:
            cfg = self._lanes[lane]
            if len(self._active[lane]) < cfg.max_concurrent:
                self._active[lane].append(task)
                task.started_at = time.time()
                self._agent_loads[agent_id] = self._agent_loads.get(agent_id, 0) + 1
            else:
                # 尝试晋升到更高优先级车道
                promoted = await self._try_promote(task)
                if not promoted:
                    self._waiting[lane].append(task)

        return task

    async def complete(self, task_id: str, lane: LaneType, agent_id: str):
        """完成任务"""
        async with self._lock:
            self._active[lane] = [t for t in self._active[lane] if t.task_id != task_id]
            self._agent_loads[agent_id] = max(0, self._agent_loads.get(agent_id, 1) - 1)

            # 从等待队列中补入
            if self._waiting[lane]:
                next_task = self._waiting[lane].pop(0)
                self._active[lane].append(next_task)
                next_task.started_at = time.time()

    async def _try_promote(self, task: DispatchTask) -> bool:
        """尝试晋升到更高优先级车道"""
        priorities = sorted(self._lanes.items(), key=lambda x: x[1].priority)
        for lane, cfg in priorities:
            if cfg.priority >= self._lanes[task.lane].priority:
                continue
            if len(self._active[lane]) < cfg.max_concurrent:
                task.lane = lane
                self._active[lane].append(task)
                task.started_at = time.time()
                return True
        return False

    def get_agent_load(self, agent_id: str) -> int:
        return self._agent_loads.get(agent_id, 0)
