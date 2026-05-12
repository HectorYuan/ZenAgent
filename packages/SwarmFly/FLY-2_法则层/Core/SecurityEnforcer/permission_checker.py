"""
权限检查器 (Permission Checker)

实现基于RBAC的权限管理:
- 角色定义与权限分配
- 权限验证与检查
- 权限继承与委托
- 动态权限调整
"""

from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, Flag, auto
import logging

logger = logging.getLogger(__name__)


class Permission(Flag):
    """权限标志"""
    NONE = 0
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    DELETE = auto()
    ADMIN = auto()
    ALL = READ | WRITE | EXECUTE | DELETE | ADMIN


class PermissionLevel(Enum):
    """权限级别"""
    DENIED = 0
    READ_ONLY = 1
    READ_WRITE = 2
    EXECUTE = 3
    FULL = 4


@dataclass
class Role:
    """角色"""
    name: str
    permissions: Permission
    inherits_from: List[str] = field(default_factory=list)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_permission(self, permission: Permission) -> bool:
        """检查是否拥有权限"""
        return permission in self.permissions or Permission.ALL in self.permissions
    
    def add_permission(self, permission: Permission):
        """添加权限"""
        self.permissions = self.permissions | permission
    
    def remove_permission(self, permission: Permission):
        """移除权限"""
        self.permissions = self.permissions & ~permission


@dataclass
class User:
    """用户/智能体"""
    user_id: str
    name: str
    roles: List[str] = field(default_factory=list)
    direct_permissions: Permission = Permission.NONE
    groups: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_active: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_permission(self, permission: Permission, roles: Dict[str, Role]) -> bool:
        """检查是否拥有权限"""
        if not self.is_active:
            return False
        
        # 检查直接权限
        if permission in self.direct_permissions or Permission.ALL in self.direct_permissions:
            return True
        
        # 检查角色权限
        for role_name in self.roles:
            role = roles.get(role_name)
            if role and role.has_permission(permission):
                return True
            
            # 检查继承的角色
            if role:
                for parent_role_name in role.inherits_from:
                    parent_role = roles.get(parent_role_name)
                    if parent_role and parent_role.has_permission(permission):
                        return True
        
        return False


@dataclass
class PermissionContext:
    """权限检查上下文"""
    user: User
    resource_type: str
    resource_id: Optional[str] = None
    action: str = "read"
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PermissionCheckResult:
    """权限检查结果"""
    allowed: bool
    reason: str = ""
    required_permissions: Set[Permission] = field(default_factory=set)
    granted_permissions: Set[Permission] = field(default_factory=set)
    missing_permissions: Set[Permission] = field(default_factory=set)


@dataclass
class ResourcePolicy:
    """资源策略"""
    resource_type: str
    resource_id_pattern: str  # 支持通配符
    required_permissions: Permission
    conditions: List[Callable[[PermissionContext], bool]] = field(default_factory=list)
    deny_rules: List[str] = field(default_factory=list)


class PermissionChecker:
    """
    权限检查器
    
    实现基于RBAC的权限管理系统:
    - 角色和权限管理
    - 权限验证
    - 资源级别策略
    - 审计追踪
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 角色存储
        self.roles: Dict[str, Role] = {}
        
        # 用户存储
        self.users: Dict[str, User] = {}
        
        # 资源策略
        self.resource_policies: Dict[str, List[ResourcePolicy]] = {}
        
        # 权限检查钩子
        self.pre_check_hooks: List[Callable] = []
        self.post_check_hooks: List[Callable] = []
        
        # 初始化默认角色
        self._init_default_roles()
        
        # 统计
        self.stats = {
            'total_checks': 0,
            'allowed_checks': 0,
            'denied_checks': 0
        }
    
    def _init_default_roles(self):
        """初始化默认角色"""
        # 管理员角色
        self.roles['admin'] = Role(
            name='admin',
            permissions=Permission.ALL,
            description='Full system access'
        )
        
        # 操作员角色
        self.roles['operator'] = Role(
            name='operator',
            permissions=Permission.READ | Permission.WRITE | Permission.EXECUTE,
            description='Can read, write and execute'
        )
        
        # 只读角色
        self.roles['reader'] = Role(
            name='reader',
            permissions=Permission.READ,
            description='Read-only access'
        )
        
        # 审计角色
        self.roles['auditor'] = Role(
            name='auditor',
            permissions=Permission.READ,
            description='Read-only with audit access',
            metadata={'audit_access': True}
        )
    
    # ==================== 角色管理 ====================
    
    def create_role(
        self,
        name: str,
        permissions: Permission = Permission.NONE,
        inherits_from: Optional[List[str]] = None,
        description: str = ""
    ) -> Role:
        """创建角色"""
        role = Role(
            name=name,
            permissions=permissions,
            inherits_from=inherits_from or [],
            description=description
        )
        self.roles[name] = role
        logger.info(f"Role created: {name}")
        return role
    
    def update_role(self, name: str, **kwargs) -> bool:
        """更新角色"""
        if name not in self.roles:
            return False
        
        role = self.roles[name]
        for key, value in kwargs.items():
            if hasattr(role, key):
                setattr(role, key, value)
        
        return True
    
    def delete_role(self, name: str) -> bool:
        """删除角色"""
        if name not in self.roles:
            return False
        
        # 检查是否有用户使用该角色
        for user in self.users.values():
            if name in user.roles:
                logger.warning(f"Cannot delete role {name}: assigned to users")
                return False
        
        del self.roles[name]
        logger.info(f"Role deleted: {name}")
        return True
    
    def get_role(self, name: str) -> Optional[Role]:
        """获取角色"""
        return self.roles.get(name)
    
    def list_roles(self) -> List[Role]:
        """列出所有角色"""
        return list(self.roles.values())
    
    # ==================== 用户管理 ====================
    
    def create_user(
        self,
        user_id: str,
        name: str,
        roles: Optional[List[str]] = None,
        permissions: Permission = Permission.NONE
    ) -> User:
        """创建用户"""
        user = User(
            user_id=user_id,
            name=name,
            roles=roles or [],
            direct_permissions=permissions
        )
        self.users[user_id] = user
        logger.info(f"User created: {user_id}")
        return user
    
    def update_user(self, user_id: str, **kwargs) -> bool:
        """更新用户"""
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        return True
    
    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        if user_id in self.users:
            del self.users[user_id]
            logger.info(f"User deleted: {user_id}")
            return True
        return False
    
    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        return self.users.get(user_id)
    
    def assign_role(self, user_id: str, role_name: str) -> bool:
        """分配角色"""
        if user_id not in self.users or role_name not in self.roles:
            return False
        
        user = self.users[user_id]
        if role_name not in user.roles:
            user.roles.append(role_name)
            logger.info(f"Role {role_name} assigned to user {user_id}")
        
        return True
    
    def revoke_role(self, user_id: str, role_name: str) -> bool:
        """撤销角色"""
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        if role_name in user.roles:
            user.roles.remove(role_name)
            logger.info(f"Role {role_name} revoked from user {user_id}")
            return True
        
        return False
    
    # ==================== 权限检查 ====================
    
    def check_permission(
        self,
        context: PermissionContext,
        required_permission: Permission,
        resource_policy: Optional[ResourcePolicy] = None
    ) -> PermissionCheckResult:
        """
        检查权限
        
        Args:
            context: 权限上下文
            required_permission: 所需权限
            
        Returns:
            PermissionCheckResult: 检查结果
        """
        self.stats['total_checks'] += 1
        
        # 执行前置钩子
        for hook in self.pre_check_hooks:
            try:
                hook(context, required_permission)
            except Exception as e:
                logger.error(f"Pre-check hook error: {e}")
        
        result = PermissionCheckResult(
            allowed=False,
            required_permissions={required_permission}
        )
        
        # 检查资源策略条件
        if resource_policy and resource_policy.conditions:
            for condition in resource_policy.conditions:
                if not condition(context):
                    result.reason = "Context condition not met"
                    return result
        
        # 检查用户权限
        if context.user.has_permission(required_permission, self.roles):
            result.allowed = True
            result.granted_permissions.add(required_permission)
            result.reason = "Permission granted"
            self.stats['allowed_checks'] += 1
        else:
            result.missing_permissions.add(required_permission)
            result.reason = "Permission denied: insufficient rights"
            self.stats['denied_checks'] += 1
        
        # 执行后置钩子
        for hook in self.post_check_hooks:
            try:
                hook(context, required_permission, result)
            except Exception as e:
                logger.error(f"Post-check hook error: {e}")
        
        return result
    
    def check_multiple_permissions(
        self,
        context: PermissionContext,
        required_permissions: Set[Permission]
    ) -> PermissionCheckResult:
        """检查多个权限(所有权限都需要)"""
        all_granted = set()
        missing = set()
        
        for perm in required_permissions:
            result = self.check_permission(context, perm)
            if result.allowed:
                all_granted.add(perm)
            else:
                missing.add(perm)
        
        return PermissionCheckResult(
            allowed=len(missing) == 0,
            required_permissions=required_permissions,
            granted_permissions=all_granted,
            missing_permissions=missing,
            reason="All permissions granted" if not missing else "Some permissions missing"
        )
    
    def require_permission(self, context: PermissionContext, permission: Permission):
        """要求权限，不满足则抛出异常"""
        result = self.check_permission(context, permission)
        if not result.allowed:
            raise PermissionError(
                f"Permission denied: {result.reason}. "
                f"Required: {permission}, User: {context.user.user_id}"
            )
    
    # ==================== 资源策略 ====================
    
    def register_resource_policy(self, policy: ResourcePolicy):
        """注册资源策略"""
        if policy.resource_type not in self.resource_policies:
            self.resource_policies[policy.resource_type] = []
        
        self.resource_policies[policy.resource_type].append(policy)
        logger.info(f"Resource policy registered: {policy.resource_type}")
    
    def get_resource_policy(
        self,
        resource_type: str,
        resource_id: str
    ) -> Optional[ResourcePolicy]:
        """获取匹配的资源策略"""
        policies = self.resource_policies.get(resource_type, [])
        
        import re
        for policy in policies:
            if re.match(policy.resource_id_pattern, resource_id):
                return policy
        
        return None
    
    def check_resource_access(
        self,
        context: PermissionContext,
        resource_type: str,
        resource_id: str,
        action: str
    ) -> PermissionCheckResult:
        """检查资源访问权限"""
        policy = self.get_resource_policy(resource_type, resource_id)
        
        if not policy:
            # 没有策略，默认拒绝
            return PermissionCheckResult(
                allowed=False,
                reason=f"No policy defined for {resource_type}"
            )
        
        return self.check_permission(context, policy.required_permissions)
    
    # ==================== 工具方法 ====================
    
    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """获取用户的所有有效权限"""
        user = self.users.get(user_id)
        if not user:
            return set()
        
        permissions = set()
        permissions.update(user.direct_permissions)
        
        for role_name in user.roles:
            role = self.roles.get(role_name)
            if role:
                permissions.update(role.permissions)
                # 处理继承
                for parent_name in role.inherits_from:
                    parent = self.roles.get(parent_name)
                    if parent:
                        permissions.update(parent.permissions)
        
        return permissions
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'total_roles': len(self.roles),
            'total_users': len(self.users),
            'active_users': sum(1 for u in self.users.values() if u.is_active)
        }
