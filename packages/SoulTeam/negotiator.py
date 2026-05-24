"""
集群协商器 (M10 Phase N)

7 协商状态 + 回调 — 复用 ZenAgent/collaboration/negotiator.py 模式
"""
import asyncio
import time
from enum import Enum
from typing import Optional, Callable
from dataclasses import dataclass, field


class NegotiationState(str, Enum):
    PENDING = "pending"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    CANCELED = "canceled"
    COMPLETED = "completed"


@dataclass
class NegotiationResult:
    negotiation_id: str
    state: NegotiationState
    result: dict = field(default_factory=dict)
    duration: float = 0.0


class ClusterNegotiator:
    """集群协商器"""

    def __init__(self, timeout: float = 60.0):
        self._timeout = timeout
        self._active: dict[str, dict] = {}
        self._callbacks: dict[str, Callable] = {}

    async def negotiate(self, negotiation_id: str, proposal: dict,
                        participants: list[str]) -> NegotiationResult:
        """协商流程"""
        start = time.time()
        self._active[negotiation_id] = {
            "proposal": proposal, "participants": participants,
            "state": NegotiationState.NEGOTIATING, "responses": {},
            "started": start,
        }
        try:
            await asyncio.wait_for(
                self._collect_responses(negotiation_id, participants),
                timeout=self._timeout
            )
            state = NegotiationState.ACCEPTED
        except asyncio.TimeoutError:
            state = NegotiationState.TIMEOUT

        self._active[negotiation_id]["state"] = state
        return NegotiationResult(negotiation_id, state,
                                 duration=time.time() - start)

    async def _collect_responses(self, nid: str, participants: list[str]):
        """收集各方响应（简化: 直接接受）"""
        for p in participants:
            self._active[nid]["responses"][p] = "accepted"

    def get_active(self) -> list[str]:
        return list(self._active.keys())
