"""
SwarmFly 生命周期管理模块

提供 Agent 生命周期状态机、状态管理器、转换规则等功能
"""

from .agent_lifecycle import (
    AgentLifecycle,
    AgentState,
    LifecycleTransition,
)
from .state_manager import (
    StateManager,
    StateTransitionResult,
    TransitionCallback,
)
from .transitions import (
    TransitionRule,
    TransitionRules,
    TransitionValidator,
    TransitionType,
    get_default_rules,
)
from .exceptions import (
    LifecycleError,
    InvalidTransitionError,
    StateError,
    TransitionError,
)

__all__ = [
    # Agent Lifecycle
    "AgentLifecycle",
    "AgentState",
    "LifecycleTransition",
    # State Manager
    "StateManager",
    "StateTransitionResult",
    "TransitionCallback",
    # Transitions
    "TransitionRule",
    "TransitionRules",
    "TransitionValidator",
    "TransitionType",
    "get_default_rules",
    # Exceptions
    "LifecycleError",
    "InvalidTransitionError",
    "StateError",
    "TransitionError",
]
