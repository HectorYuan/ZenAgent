"""
协作协议模块
提供 Agent 间协作的协议定义和协商机制
"""

from .protocols import (
    CollaborationProtocol,
    ProtocolType,
    MessagePriority,
    CollaborationMessage,
    CollaborationRequest,
    CollaborationResponse,
)
from .negotiator import (
    CollaborationNegotiator,
    NegotiationResult,
    NegotiationStatus,
    get_negotiator,
)
from .task_router import (
    TaskRouter,
    RouteStrategy,
    TaskRoute,
    get_router,
)

__all__ = [
    # Protocols
    "CollaborationProtocol",
    "ProtocolType",
    "MessagePriority",
    "CollaborationMessage",
    "CollaborationRequest",
    "CollaborationResponse",
    # Negotiator
    "CollaborationNegotiator",
    "NegotiationResult",
    "NegotiationStatus",
    "get_negotiator",
    # Task Router
    "TaskRouter",
    "RouteStrategy",
    "TaskRoute",
    "get_router",
]
