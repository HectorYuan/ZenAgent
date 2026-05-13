"""
团队构建器

提供团队创建、配置和管理的统一接口
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable
from datetime import datetime
import threading
import uuid

from .roles import (
    AgentRole,
    RoleDefinition,
    RoleRegistry,
    get_role_registry,
)
from .formation import (
    Formation,
    FormationType,
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


class TeamStatus(Enum):
    """团队状态枚举"""
    FORMING = "forming"     # 组建中
    ACTIVE = "active"       # 活跃
    PAUSED = "paused"       # 暂停
    DISSOLVED = "dissolved" # 已解散


@dataclass
class TeamConfig:
    """
    团队配置
    
    配置团队的各项参数
    """
    name: str = "Default Team"
    description: str = ""
    
    # 角色配置
    required_roles: List[AgentRole] = field(default_factory=list)
    role_distribution: Dict[AgentRole, int] = field(default_factory=dict)
    
    # 编队配置
    formation_type: FormationType = FormationType.HIERARCHICAL
    
    # 策略配置
    auto_dispatch_tasks: bool = True
    allow_role_switch: bool = False
    
    # 约束配置
    max_members: int = 20
    min_members: int = 1
    
    # 其他
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BuildResult:
    """构建结果"""
    success: bool
    team: Optional['Team'] = None
    message: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class Team:
    """
    团队
    
    表示一个完整的团队
    """
    team_id: str
    name: str
    
    # 状态
    status: TeamStatus = TeamStatus.FORMING
    
    # 配置
    config: TeamConfig = field(default_factory=TeamConfig)
    
    # 创建时间
    created_at: datetime = field(default_factory=datetime.now)
    last_active_at: datetime = field(default_factory=datetime.now)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_active(self) -> bool:
        """团队是否活跃"""
        return self.status == TeamStatus.ACTIVE
    
    @property
    def member_count(self) -> int:
        """成员数量"""
        return self.membership.member_count
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "team_id": self.team_id,
            "name": self.name,
            "status": self.status.value,
            "member_count": self.member_count,
            "created_at": self.created_at.isoformat(),
            "last_active_at": self.last_active_at.isoformat(),
        }


class TeamBuilder:
    """
    团队构建器
    
    提供创建和管理团队的工具
    """
    
    def __init__(
        self,
        role_registry: Optional[RoleRegistry] = None,
        formation_manager: Optional[FormationManager] = None,
    ):
        """
        初始化团队构建器
        
        Args:
            role_registry: 角色注册表
            formation_manager: 编队管理器
        """
        self.role_registry = role_registry or get_role_registry()
        self.formation_manager = formation_manager or FormationManager()
        
        # 团队存储
        self._teams: Dict[str, Team] = {}
        
        # 锁
        self._lock = threading.RLock()
        
        # 回调
        self._on_team_created: List[Callable[[Team], None]] = []
        self._on_team_dissolved: List[Callable[[Team], None]] = []
        self._on_member_joined: List[Callable[[Team, Member], None]] = []
        self._on_member_left: List[Callable[[Team, Member], None]] = []
    
    def create_team(
        self,
        config: TeamConfig,
        initial_members: Optional[List[str]] = None,
    ) -> BuildResult:
        """
        创建团队
        
        Args:
            config: 团队配置
            initial_members: 初始成员 ID 列表
            
        Returns:
            BuildResult: 构建结果
        """
        warnings = []
        errors = []
        
        with self._lock:
            # 创建团队
            team_id = str(uuid.uuid4())
            team = Team(
                team_id=team_id,
                name=config.name,
                config=config,
            )
            
            # 创建组件
            membership = MembershipManager(team_id=team_id)
            protocol = TeamProtocol(team_id=team_id, node_id=team_id)
            
            # 设置编队
            formation = self.formation_manager.get_formation(config.formation_type.value)
            if not formation:
                # 创建默认编队
                formation = Formation(
                    formation_id=f"default_{team_id}",
                    name="Default",
                    formation_type=config.formation_type,
                )
            
            # 关联组件
            team.membership = membership
            team.protocol = protocol
            team.formation = formation
            
            # 添加初始成员
            if initial_members:
                for member_id in initial_members:
                    membership.add_member(agent_id=member_id)
            
            # 验证配置
            validation_result = self._validate_config(team, config)
            errors.extend(validation_result.get("errors", []))
            warnings.extend(validation_result.get("warnings", []))
            
            if errors:
                return BuildResult(
                    success=False,
                    message="Validation failed",
                    errors=errors,
                    warnings=warnings,
                )
            
            # 设置状态
            team.status = TeamStatus.ACTIVE
            
            # 存储团队
            self._teams[team_id] = team
            
            # 触发回调
            for callback in self._on_team_created:
                try:
                    callback(team)
                except Exception:
                    pass
            
            return BuildResult(
                success=True,
                team=team,
                message="Team created successfully",
                warnings=warnings,
            )
    
    def _validate_config(self, team: Team, config: TeamConfig) -> Dict[str, List[str]]:
        """验证配置"""
        errors = []
        warnings = []
        
        # 检查必选角色
        for role in config.required_roles:
            role_def = self.role_registry.get_role(role)
            if not role_def:
                errors.append(f"Role {role.value} not found in registry")
            elif role_def.min_count > 0:
                # 检查是否有足够的角色定义
                pass
        
        # 检查成员限制
        if config.max_members < config.min_members:
            errors.append("max_members must be >= min_members")
        
        return {"errors": errors, "warnings": warnings}
    
    def get_team(self, team_id: str) -> Optional[Team]:
        """获取团队"""
        return self._teams.get(team_id)
    
    def get_all_teams(self) -> List[Team]:
        """获取所有团队"""
        return list(self._teams.values())
    
    def dissolve_team(self, team_id: str) -> bool:
        """
        解散团队
        
        Args:
            team_id: 团队 ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            team = self._teams.get(team_id)
            if not team:
                return False
            
            team.status = TeamStatus.DISSOLVED
            
            # 触发回调
            for callback in self._on_team_dissolved:
                try:
                    callback(team)
                except Exception:
                    pass
            
            # 移除团队
            self._teams.pop(team_id)
            
            return True
    
    def add_member(
        self,
        team_id: str,
        agent_id: str,
        role: str = "worker",
        capabilities: Optional[Dict[str, float]] = None,
    ) -> Optional[Member]:
        """
        添加成员
        
        Args:
            team_id: 团队 ID
            agent_id: Agent ID
            role: 角色
            capabilities: 能力评分
            
        Returns:
            Optional[Member]: 创建的成员对象
        """
        team = self._teams.get(team_id)
        if not team:
            return None
        
        member = team.membership.add_member(
            agent_id=agent_id,
            role=role,
            capabilities=capabilities,
        )
        
        # 更新编队
        available_pos = team.formation.available_positions
        if available_pos:
            team.formation.assign(available_pos[0], agent_id)
        
        # 更新活动时间
        team.last_active_at = datetime.now()
        
        # 触发回调
        for callback in self._on_member_joined:
            try:
                callback(team, member)
            except Exception:
                pass
        
        return member
    
    def remove_member(self, team_id: str, agent_id: str) -> bool:
        """
        移除成员
        
        Args:
            team_id: 团队 ID
            agent_id: Agent ID
            
        Returns:
            bool: 是否成功
        """
        team = self._teams.get(team_id)
        if not team:
            return False
        
        # 获取成员信息（移除前）
        member = team.membership.get_member(agent_id)
        
        # 取消编队分配
        position = team.formation.get_position(agent_id)
        if position:
            team.formation.unassign(position.position_id)
        
        # 移除成员
        success = team.membership.remove_member(agent_id)
        
        if success:
            team.last_active_at = datetime.now()
            
            # 触发回调
            for callback in self._on_member_left:
                try:
                    callback(team, member)
                except Exception:
                    pass
        
        return success
    
    def change_member_role(
        self,
        team_id: str,
        agent_id: str,
        new_role: str,
    ) -> bool:
        """
        更改成员角色
        
        Args:
            team_id: 团队 ID
            agent_id: Agent ID
            new_role: 新角色
            
        Returns:
            bool: 是否成功
        """
        team = self._teams.get(team_id)
        if not team:
            return False
        
        if not team.config.allow_role_switch:
            return False
        
        member = team.membership.get_member(agent_id)
        if not member:
            return False
        
        # 检查新角色约束
        role_def = self.role_registry.get_role(AgentRole(new_role))
        if role_def:
            current_count = sum(
                1 for m in team.membership.get_members_by_role(new_role)
            )
            if not self.role_registry.check_role_constraints(
                AgentRole(new_role), current_count
            ):
                return False
        
        member.role = new_role
        team.last_active_at = datetime.now()
        
        return True
    
    def get_team_status(self, team_id: str) -> Optional[Dict[str, Any]]:
        """获取团队状态"""
        team = self._teams.get(team_id)
        if not team:
            return None
        
        return {
            "team_id": team.team_id,
            "name": team.name,
            "status": team.status.value,
            "member_count": team.member_count,
            "active_member_count": team.membership.active_member_count,
            "role_distribution": team.membership.get_role_distribution(),
            "performance": team.membership.get_performance_summary(),
            "created_at": team.created_at.isoformat(),
            "last_active_at": team.last_active_at.isoformat(),
        }
    
    def register_callback(
        self,
        event: str,
        callback: Callable[..., None],
    ) -> None:
        """注册回调"""
        if event == "team_created":
            self._on_team_created.append(callback)
        elif event == "team_dissolved":
            self._on_team_dissolved.append(callback)
        elif event == "member_joined":
            self._on_member_joined.append(callback)
        elif event == "member_left":
            self._on_member_left.append(callback)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_teams": len(self._teams),
            "active_teams": sum(1 for t in self._teams.values() if t.is_active),
            "total_members": sum(t.member_count for t in self._teams.values()),
        }
