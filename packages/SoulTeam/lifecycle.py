"""
子 Agent 生命周期管理 (M10 Phase H)

设计依据: 子智能体运行机制 v1.0

6 状态 + 7 工具 (spawn/send/history/list/status/abort/recover)
"""

import asyncio
import time
from enum import Enum
from typing import Optional, Any
from dataclasses import dataclass, field


class SubAgentState(str, Enum):
    UNCREATED = "uncreated"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    RECOVERED = "recovered"
    ABORTED = "aborted"


@dataclass
class SubAgentRecord:
    agent_id: str
    state: SubAgentState = SubAgentState.UNCREATED
    session_id: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    task_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    metadata: dict = field(default_factory=dict)


class SubAgentManager:
    """子 Agent 生命周期管理器"""

    def __init__(self):
        self._agents: dict[str, SubAgentRecord] = {}
        self._lock = asyncio.Lock()

    # ---- 7 工具 ----

    async def spawn(self, agent_id: str, session_id: str = "",
                    metadata: dict = None) -> SubAgentRecord:
        """创建子 Agent"""
        async with self._lock:
            record = SubAgentRecord(
                agent_id=agent_id, session_id=session_id,
                state=SubAgentState.RUNNING, metadata=metadata or {},
            )
            self._agents[agent_id] = record
            return record

    async def send(self, agent_id: str, task: str) -> bool:
        """发送任务给子 Agent"""
        rec = self._agents.get(agent_id)
        if not rec or rec.state not in (SubAgentState.RUNNING, SubAgentState.RECOVERED):
            return False
        rec.task_count += 1
        rec.updated_at = time.time()
        return True

    def history(self, agent_id: str) -> Optional[dict]:
        """查看历史"""
        rec = self._agents.get(agent_id)
        if not rec:
            return None
        return {
            "agent_id": rec.agent_id, "state": rec.state.value,
            "tasks": rec.task_count, "success": rec.success_count,
            "fail": rec.fail_count, "session": rec.session_id,
        }

    def list_all(self) -> list[dict]:
        """列出所有子 Agent"""
        return [self.history(aid) for aid in self._agents]

    async def status(self, agent_id: str) -> SubAgentState:
        """查询状态"""
        rec = self._agents.get(agent_id)
        return rec.state if rec else SubAgentState.UNCREATED

    async def abort(self, agent_id: str) -> bool:
        """中止子 Agent"""
        async with self._lock:
            rec = self._agents.get(agent_id)
            if not rec:
                return False
            rec.state = SubAgentState.ABORTED
            rec.updated_at = time.time()
            return True

    async def recover(self, agent_id: str) -> bool:
        """恢复子 Agent (从 BLOCKED/ABORTED)"""
        async with self._lock:
            rec = self._agents.get(agent_id)
            if not rec or rec.state not in (SubAgentState.BLOCKED, SubAgentState.ABORTED):
                return False
            rec.state = SubAgentState.RECOVERED
            rec.updated_at = time.time()
            return True

    async def complete(self, agent_id: str, success: bool = True):
        """完成 Agent 任务"""
        async with self._lock:
            rec = self._agents.get(agent_id)
            if rec:
                rec.state = SubAgentState.COMPLETED if success else SubAgentState.BLOCKED
                rec.success_count += 1 if success else 0
                rec.fail_count += 0 if success else 1
                rec.updated_at = time.time()
