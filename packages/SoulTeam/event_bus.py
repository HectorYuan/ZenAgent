"""
集群事件总线 (M10 Phase M)

40+ 事件主题 + 发布/订阅
"""
import asyncio
from typing import Callable, Awaitable
from collections import defaultdict


class ClusterEventBus:
    """集群级事件总线"""

    TOPICS = [
        "agent.spawned", "agent.completed", "agent.failed", "agent.aborted",
        "task.assigned", "task.started", "task.completed", "task.failed",
        "chain.started", "chain.completed", "chain.failed",
        "team.formed", "team.disbanded",
        "bagua.routed", "bagua.relayed", "bagua.energy_changed",
        "heartbeat.received", "heartbeat.missed",
        "context.packed", "context.unpacked", "context.archived",
        "lane.promoted", "lane.demoted", "lane.overloaded",
        "proposal.submitted", "proposal.approved", "proposal.rejected",
        "review.completed", "review.escalated",
        "alert.critical", "alert.high", "alert.medium",
        "cluster.scale_up", "cluster.scale_down",
        "error.internal", "error.timeout", "error.circuit_open",
    ]

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._event_count: dict[str, int] = defaultdict(int)

    def subscribe(self, topic: str, callback: Callable[[dict], Awaitable[None]]):
        if topic in self.TOPICS:
            self._subscribers[topic].append(callback)

    async def publish(self, topic: str, data: dict):
        self._event_count[topic] += 1
        for cb in self._subscribers.get(topic, []):
            try:
                await cb(data)
            except Exception:
                pass  # 单个订阅者失败不影响其他

    def get_stats(self) -> dict:
        return dict(self._event_count)
