"""
协作链引擎 (M10 Phase C)

设计依据: 智能体集群运行机制 v1.2 + 智能体协作编排机制 v1.0

5 条预定义协作链 + 4 种执行模式 + 链式编排
"""

import asyncio
import time
import logging
from typing import Optional, Any, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, field

from .protocol import ExecutionMode, TaskStatus

logger = logging.getLogger(__name__)


class ChainStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


@dataclass
class ChainStep:
    """协作链步骤"""
    step_id: str
    agent_id: str
    task: str
    depends_on: list[str] = field(default_factory=list)  # 依赖的 step_id
    timeout: float = 60.0
    retries: int = 1

    def to_dict(self) -> dict:
        return {"step_id": self.step_id, "agent_id": self.agent_id,
                "task": self.task, "depends_on": self.depends_on,
                "timeout": self.timeout, "retries": self.retries}


@dataclass
class ChainDefinition:
    """协作链定义"""
    chain_id: str
    name: str
    description: str
    mode: ExecutionMode
    steps: list[ChainStep]
    team_id: str = ""
    max_duration: float = 300.0

    def to_dict(self) -> dict:
        return {"chain_id": self.chain_id, "name": self.name,
                "description": self.description, "mode": self.mode.value,
                "steps": [s.to_dict() for s in self.steps],
                "team_id": self.team_id, "max_duration": self.max_duration}


@dataclass
class ChainResult:
    """协作链执行结果"""
    chain_id: str
    status: ChainStatus
    step_results: dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0
    error: Optional[str] = None


# ---- 5 条预定义协作链 ----
CHAINS: dict[str, ChainDefinition] = {
    "IA-AL": ChainDefinition(
        chain_id="IA-AL", name="投资分析-配置", description="Invest Analysis → Allocation",
        mode=ExecutionMode.SEQUENTIAL, team_id="TEAM-INVEST",
        steps=[
            ChainStep("s1", "SUB-1.2", "市场数据采集与分析"),
            ChainStep("s2", "SUB-1.3", "风险评估建模", depends_on=["s1"]),
            ChainStep("s3", "SUB-1.1", "投资策略制定", depends_on=["s2"]),
            ChainStep("s4", "SUB-1.4", "组合优化配置", depends_on=["s3"]),
        ],
    ),
    "TR-DV": ChainDefinition(
        chain_id="TR-DV", name="技术评审-开发验证", description="Tech Review → Dev Verify",
        mode=ExecutionMode.SEQUENTIAL, team_id="TEAM-RD",
        steps=[
            ChainStep("s1", "SUB-3.1", "架构评审"),
            ChainStep("s2", "SUB-3.2", "后端开发", depends_on=["s1"]),
            ChainStep("s3", "SUB-3.3", "前端开发", depends_on=["s1"]),
            ChainStep("s4", "SUB-3.5", "测试验证", depends_on=["s2", "s3"]),
        ],
    ),
    "OO-SE": ChainDefinition(
        chain_id="OO-SE", name="运维-安全加固", description="Ops Observability → Security Enhance",
        mode=ExecutionMode.PARALLEL, team_id="TEAM-RD",
        steps=[
            ChainStep("s1", "SUB-3.6", "部署监控"),
            ChainStep("s2", "SUB-3.4", "安全数据分析"),
        ],
    ),
    "CR-DE": ChainDefinition(
        chain_id="CR-DE", name="创作-设计表达", description="Creative → Design Expression",
        mode=ExecutionMode.SEQUENTIAL, team_id="TEAM-LEARN",
        steps=[
            ChainStep("s1", "SUB-3.9", "创新概念生成"),
            ChainStep("s2", "SUB-3.7", "知识整理与文档化", depends_on=["s1"]),
            ChainStep("s3", "SUB-3.8", "技能传授", depends_on=["s2"]),
        ],
    ),
    "PR-PT": ChainDefinition(
        chain_id="PR-PT", name="规划-执行追踪", description="Plan → Execute Track",
        mode=ExecutionMode.FAN_OUT_FAN_IN, team_id="TEAM-OPS",
        steps=[
            ChainStep("s1", "SUB-2.3", "资源规划"),
            ChainStep("s2", "SUB-2.1", "任务分发", depends_on=["s1"]),
            ChainStep("s3", "SUB-2.2", "质量审计", depends_on=["s2"]),
        ],
    ),
}


class ChainExecutor:
    """协作链执行器"""

    def __init__(self, agent_call_fn: Optional[Callable[[str, str], Awaitable[Any]]] = None):
        self._call_fn = agent_call_fn
        self._chains = dict(CHAINS)

    def register_chain(self, chain: ChainDefinition):
        self._chains[chain.chain_id] = chain

    def get_chain(self, chain_id: str) -> Optional[ChainDefinition]:
        return self._chains.get(chain_id)

    @property
    def available_chains(self) -> list[str]:
        return list(self._chains.keys())

    async def execute(self, chain_id: str, context: dict = None) -> ChainResult:
        """执行协作链"""
        chain = self._chains.get(chain_id)
        if not chain:
            return ChainResult(chain_id=chain_id, status=ChainStatus.FAILED,
                               error=f"Chain {chain_id} not found")

        start = time.monotonic()
        results: dict[str, Any] = {}
        context = context or {}

        if chain.mode == ExecutionMode.SINGLE:
            results = await self._execute_single(chain.steps[0], context)
        elif chain.mode == ExecutionMode.SEQUENTIAL:
            results = await self._execute_sequential(chain.steps, context)
        elif chain.mode == ExecutionMode.PARALLEL:
            results = await self._execute_parallel(chain.steps, context)
        elif chain.mode == ExecutionMode.FAN_OUT_FAN_IN:
            results = await self._execute_fan_out(chain.steps, context)
        else:
            results = await self._execute_sequential(chain.steps, context)

        failed = sum(1 for v in results.values()
                     if isinstance(v, dict) and v.get("error"))
        status = (ChainStatus.FAILED if failed == len(chain.steps)
                  else ChainStatus.PARTIAL if failed > 0
                  else ChainStatus.COMPLETED)

        return ChainResult(chain_id=chain_id, status=status,
                           step_results=results,
                           duration=time.monotonic() - start)

    async def _execute_single(self, step: ChainStep, ctx: dict) -> dict:
        return {step.step_id: await self._call_step(step, ctx)}

    async def _execute_sequential(self, steps: list[ChainStep], ctx: dict) -> dict:
        results = {}
        completed = set()
        for step in steps:
            # Check dependencies
            if step.depends_on:
                if not all(d in completed for d in step.depends_on):
                    results[step.step_id] = {"error": "Dependency not met", "status": "skipped"}
                    continue
            results[step.step_id] = await self._call_step(step, ctx)
            if "error" not in str(results[step.step_id]):
                completed.add(step.step_id)
        return results

    async def _execute_parallel(self, steps: list[ChainStep], ctx: dict) -> dict:
        tasks = [self._call_step(s, ctx) for s in steps]
        step_results = await asyncio.gather(*tasks, return_exceptions=True)
        return {s.step_id: (r if not isinstance(r, Exception) else {"error": str(r)})
                for s, r in zip(steps, step_results)}

    async def _execute_fan_out(self, steps: list[ChainStep], ctx: dict) -> dict:
        # Fan-out: all steps in parallel
        tasks = [self._call_step(s, ctx) for s in steps]
        step_results = await asyncio.gather(*tasks, return_exceptions=True)
        results = {s.step_id: (r if not isinstance(r, Exception) else {"error": str(r)})
                   for s, r in zip(steps, step_results)}
        return results

    async def _call_step(self, step: ChainStep, context: dict) -> dict:
        """调用单个步骤"""
        if not self._call_fn:
            return {"step_id": step.step_id, "agent_id": step.agent_id,
                    "status": "mock", "output": f"Mock result for {step.task}"}

        for attempt in range(step.retries + 1):
            try:
                result = await asyncio.wait_for(
                    self._call_fn(step.agent_id, step.task),
                    timeout=step.timeout
                )
                return {"step_id": step.step_id, "agent_id": step.agent_id,
                        "status": "completed", "output": result}
            except asyncio.TimeoutError:
                if attempt == step.retries:
                    return {"step_id": step.step_id, "agent_id": step.agent_id,
                            "status": "timeout", "error": f"Timeout after {step.timeout}s"}
            except Exception as e:
                if attempt == step.retries:
                    return {"step_id": step.step_id, "agent_id": step.agent_id,
                            "status": "error", "error": str(e)}
        return {"step_id": step.step_id, "status": "error", "error": "Unknown"}
