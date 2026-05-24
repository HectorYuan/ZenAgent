"""
SoulTeam — L5 层：智能体团队编排体系 (M10)

16 Agent + 4 团队 + 5 协作链 + 八卦路由 + 六车道调度
"""

__version__ = "1.0.0"

from .protocol import (
    ClusterMessage, Baton,
    MessageType, TaskStatus, Priority, ExecutionMode, CollaborationProtocol,
)
from .registry import (
    AgentRegistry, AgentProfile, AgentCategory, BaguaPosition,
    AGENT_REGISTRY, TEAMS,
)

__all__ = [
    "ClusterMessage", "Baton",
    "MessageType", "TaskStatus", "Priority", "ExecutionMode", "CollaborationProtocol",
    "AgentRegistry", "AgentProfile", "AgentCategory", "BaguaPosition",
    "AGENT_REGISTRY", "TEAMS",
]
