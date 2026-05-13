"""
角色定义

定义 Agent 的角色类型和角色能力
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable
import threading


class AgentRole(Enum):
    """Agent 角色枚举"""
    LEADER = "leader"           # 领导者
    COORDINATOR = "coordinator" # 协调者
    WORKER = "worker"           # 工作者
    SPECIALIST = "specialist"   # 专家
    OBSERVER = "observer"       # 观察者
    COMMUNICATOR = "communicator"  # 通信者
    MONITOR = "monitor"         # 监控者
    EXECUTOR = "executor"       # 执行者


@dataclass
class RoleCapability:
    """
    角色能力
    
    定义角色可以执行的操作
    """
    name: str
    description: str
    required: bool = True
    priority: int = 0  # 能力优先级
    weight: float = 1.0  # 能力权重


@dataclass
class RoleDefinition:
    """
    角色定义
    
    定义角色的完整描述
    """
    role: AgentRole
    name: str
    description: str
    
    # 能力
    capabilities: List[RoleCapability] = field(default_factory=list)
    
    # 约束
    max_count: int = 0  # 0 表示无限制
    min_count: int = 0
    
    # 权限
    permissions: Set[str] = field(default_factory=set)
    
    # 优先级
    priority: int = 0  # 角色优先级
    
    # 可选配置
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_capability(self, capability_name: str) -> bool:
        """检查是否具有指定能力"""
        return any(c.name == capability_name for c in self.capabilities)
    
    def get_capability(self, capability_name: str) -> Optional[RoleCapability]:
        """获取指定能力"""
        for cap in self.capabilities:
            if cap.name == capability_name:
                return cap
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "role": self.role.value,
            "name": self.name,
            "description": self.description,
            "capabilities": [
                {
                    "name": c.name,
                    "description": c.description,
                    "required": c.required,
                    "priority": c.priority,
                }
                for c in self.capabilities
            ],
            "max_count": self.max_count,
            "min_count": self.min_count,
            "permissions": list(self.permissions),
            "priority": self.priority,
        }


class RoleRegistry:
    """
    角色注册表
    
    管理预定义的角色
    """
    
    def __init__(self):
        """初始化注册表"""
        self._roles: Dict[AgentRole, RoleDefinition] = {}
        self._lock = threading.RLock()
        self._register_default_roles()
    
    def _register_default_roles(self) -> None:
        """注册默认角色"""
        # Leader
        self.register(RoleDefinition(
            role=AgentRole.LEADER,
            name="Team Leader",
            description="团队领导者，负责整体决策和方向把控",
            capabilities=[
                RoleCapability("decision_making", "决策能力", priority=10),
                RoleCapability("coordination", "协调能力", priority=8),
                RoleCapability("delegation", "任务分配能力", priority=7),
            ],
            max_count=1,
            min_count=1,
            permissions={"admin", "delegate", "monitor"},
            priority=10,
        ))
        
        # Coordinator
        self.register(RoleDefinition(
            role=AgentRole.COORDINATOR,
            name="Coordinator",
            description="任务协调者，负责任务调度和进度跟踪",
            capabilities=[
                RoleCapability("task_scheduling", "任务调度", priority=8),
                RoleCapability("progress_tracking", "进度跟踪", priority=7),
                RoleCapability("resource_allocation", "资源分配", priority=6),
            ],
            max_count=3,
            min_count=0,
            permissions={"schedule", "track", "notify"},
            priority=7,
        ))
        
        # Worker
        self.register(RoleDefinition(
            role=AgentRole.WORKER,
            name="Worker",
            description="普通工作者，负责执行具体任务",
            capabilities=[
                RoleCapability("task_execution", "任务执行", priority=8),
                RoleCapability("reporting", "进度报告", priority=5),
            ],
            max_count=0,  # 无限制
            min_count=0,
            permissions={"execute", "report"},
            priority=5,
        ))
        
        # Specialist
        self.register(RoleDefinition(
            role=AgentRole.SPECIALIST,
            name="Specialist",
            description="领域专家，提供专业知识和技能",
            capabilities=[
                RoleCapability("expert_knowledge", "专业知识", priority=10),
                RoleCapability("consultation", "咨询能力", priority=7),
            ],
            max_count=0,
            min_count=0,
            permissions={"consult", "advise"},
            priority=8,
        ))
        
        # Observer
        self.register(RoleDefinition(
            role=AgentRole.OBSERVER,
            name="Observer",
            description="观察者，监控团队状态但不干预",
            capabilities=[
                RoleCapability("monitoring", "监控能力", priority=7),
                RoleCapability("reporting", "报告能力", priority=5),
            ],
            max_count=5,
            min_count=0,
            permissions={"observe", "report"},
            priority=3,
        ))
        
        # Communicator
        self.register(RoleDefinition(
            role=AgentRole.COMMUNICATOR,
            name="Communicator",
            description="通信者，负责团队内外沟通",
            capabilities=[
                RoleCapability("communication", "沟通能力", priority=9),
                RoleCapability("negotiation", "谈判能力", priority=7),
            ],
            max_count=3,
            min_count=0,
            permissions={"communicate", "negotiate"},
            priority=6,
        ))
        
        # Monitor
        self.register(RoleDefinition(
            role=AgentRole.MONITOR,
            name="Monitor",
            description="监控者，实时监控系统状态",
            capabilities=[
                RoleCapability("system_monitoring", "系统监控", priority=9),
                RoleCapability("alerting", "告警能力", priority=8),
            ],
            max_count=2,
            min_count=0,
            permissions={"monitor", "alert"},
            priority=6,
        ))
        
        # Executor
        self.register(RoleDefinition(
            role=AgentRole.EXECUTOR,
            name="Executor",
            description="执行者，负责快速执行任务",
            capabilities=[
                RoleCapability("fast_execution", "快速执行", priority=9),
                RoleCapability("error_handling", "错误处理", priority=6),
            ],
            max_count=0,
            min_count=0,
            permissions={"execute"},
            priority=5,
        ))
    
    def register(self, definition: RoleDefinition) -> None:
        """
        注册角色定义
        
        Args:
            definition: 角色定义
        """
        with self._lock:
            self._roles[definition.role] = definition
    
    def get_role(self, role: AgentRole) -> Optional[RoleDefinition]:
        """获取角色定义"""
        return self._roles.get(role)
    
    def get_all_roles(self) -> List[RoleDefinition]:
        """获取所有角色定义"""
        return list(self._roles.values())
    
    def get_roles_by_priority(self) -> List[RoleDefinition]:
        """按优先级获取角色"""
        return sorted(self._roles.values(), key=lambda r: r.priority, reverse=True)
    
    def check_role_constraints(
        self,
        role: AgentRole,
        current_count: int,
    ) -> bool:
        """
        检查角色约束
        
        Args:
            role: 角色类型
            current_count: 当前数量
            
        Returns:
            bool: 是否可以添加
        """
        definition = self.get_role(role)
        if not definition:
            return False
        
        if definition.max_count > 0 and current_count >= definition.max_count:
            return False
        
        return True
    
    def get_recommended_roles(self, count: int) -> List[AgentRole]:
        """
        获取推荐的必选角色
        
        Args:
            count: 团队规模
            
        Returns:
            List[AgentRole]: 推荐的必选角色
        """
        recommended = []
        
        for role_def in self.get_roles_by_priority():
            if role_def.min_count > 0:
                recommended.append(role_def.role)
        
        return recommended


# 全局角色注册表
_global_registry = RoleRegistry()


def get_role_registry() -> RoleRegistry:
    """获取全局角色注册表"""
    return _global_registry
