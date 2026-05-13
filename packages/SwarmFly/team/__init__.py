"""
SwarmFly 团队构建框架

提供团队构建、角色定义、编队管理和成员管理功能
"""

from .builder import (
    TeamBuilder,
    Team,
    TeamConfig,
    TeamStatus,
    BuildResult,
)
from .roles import (
    AgentRole,
    RoleDefinition,
    RoleCapability,
    RoleRegistry,
    get_role_registry,
)
from .formation import (
    Formation,
    FormationType,
    Position,
    FormationManager,
)
from .membership import (
    MembershipManager,
    Member,
    MembershipStatus,
    MembershipRequest,
)
from .team_protocol import (
    TeamProtocol,
    ProtocolMessage,
    MessageType,
)

__all__ = [
    # Builder
    "TeamBuilder",
    "Team",
    "TeamConfig",
    "TeamStatus",
    "BuildResult",
    # Roles
    "AgentRole",
    "RoleDefinition",
    "RoleCapability",
    "RoleRegistry",
    "get_role_registry",
    # Formation
    "Formation",
    "FormationType",
    "Position",
    "FormationManager",
    # Membership
    "MembershipManager",
    "Member",
    "MembershipStatus",
    "MembershipRequest",
    # Team Protocol
    "TeamProtocol",
    "ProtocolMessage",
    "MessageType",
]
