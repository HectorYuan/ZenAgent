"""
上下文传递协议 (M10 Phase F)

设计依据: 智能体 context 传递规范 v1.0

5 标准 JSON 文件 + 双向上下文流
"""

import json
import os
import time
from typing import Optional, Any
from dataclasses import dataclass, field, asdict


CONTEXT_DIR = ".shared_state/agent_context"


@dataclass
class EnlightenmentContext:
    """觉悟上下文 — 主→子"""
    session_id: str
    mission: str
    constraints: list[str] = field(default_factory=list)
    expected_output: str = ""
    deadline: float = 0.0
    priority: int = 3

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class TaskContext:
    """任务上下文 — 主→子"""
    task_id: str
    description: str
    input_data: dict = field(default_factory=dict)
    tools_available: list[str] = field(default_factory=list)
    output_format: str = "text"
    max_tokens: int = 4096
    timeout: float = 120.0

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class AgentInstruction:
    """Agent 指令 — 主→子"""
    agent_id: str
    role: str
    specific_steps: list[str] = field(default_factory=list)
    fallback_strategy: str = "degrade"
    escalation_contact: str = "master"
    context_refs: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class TaskResult:
    """任务结果 — 子→主"""
    task_id: str
    status: int = 0  # 0=完成 1=失败 2=部分完成 3=上下文不完整 4=超时
    output: Any = None
    insights: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class EnlightenmentInsight:
    """觉悟洞察 — 子→主"""
    insight_id: str
    session_id: str
    key_findings: list[str] = field(default_factory=list)
    lessons_learned: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class ContextManager:
    """上下文管理器 — 5 文件协议"""

    def __init__(self, base_dir: str = CONTEXT_DIR):
        self._base = base_dir

    def session_dir(self, session_id: str) -> str:
        return os.path.join(self._base, session_id)

    def _ensure_dir(self, path: str):
        os.makedirs(path, exist_ok=True)

    # ---- Create (主→子) ----

    def pack_mission(self, session_id: str, enlightenment: EnlightenmentContext,
                     task: TaskContext, instruction: AgentInstruction) -> str:
        """打包任务: 创建 3 个文件，返回 session_dir"""
        d = self.session_dir(session_id)
        self._ensure_dir(d)

        with open(os.path.join(d, "enlightenment_context.json"), "w") as f:
            f.write(enlightenment.to_json())
        with open(os.path.join(d, "task_context.json"), "w") as f:
            f.write(task.to_json())
        with open(os.path.join(d, "agent_instruction.json"), "w") as f:
            f.write(instruction.to_json())

        return d

    # ---- Read (子→主) ----

    def unpack_result(self, session_id: str) -> Optional[TaskResult]:
        """读取子 Agent 返回的结果"""
        d = self.session_dir(session_id)
        path = os.path.join(d, "task_result.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return TaskResult(**json.load(f))

    # ---- Write (子→主) ----

    def pack_result(self, session_id: str, result: TaskResult):
        """子 Agent 写入结果"""
        d = self.session_dir(session_id)
        self._ensure_dir(d)
        with open(os.path.join(d, "task_result.json"), "w") as f:
            f.write(result.to_json())

    def pack_insight(self, session_id: str, insight: EnlightenmentInsight):
        """子 Agent 写入觉悟洞察"""
        d = self.session_dir(session_id)
        self._ensure_dir(d)
        with open(os.path.join(d, "enlightenment_insight.json"), "w") as f:
            f.write(insight.to_json())

    # ---- Archive ----

    def archive(self, session_id: str):
        """归档会话目录"""
        import shutil
        d = self.session_dir(session_id)
        archive_dir = os.path.join(self._base, "_archive", session_id)
        if os.path.exists(d):
            self._ensure_dir(os.path.dirname(archive_dir))
            shutil.move(d, archive_dir)
