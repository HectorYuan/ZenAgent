from __future__ import annotations
"""
SwarmFly 核心入口

SwarmFly 层统一入口，整合生命周期、协作引擎、内存池和团队模块
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Callable
from datetime import datetime
import threading
import uuid

# 生命周期模块
from .lifecycle import (
    AgentLifecycle,
    AgentState,
    StateManager,
    LifecycleTransition,
    TransitionRule,
    get_default_rules,
)

# 协作引擎模块
from .collaboration import (
    CollaborationEngine,
    CollaborationConfig,
    TaskDispatcher,
    Task,
    TaskPriority,
    TaskStatus,
    LoadBalancer,
    ConsensusMechanism,
    ConflictResolver,
    ConflictType,
)

# 内存池模块
from .memory import (
    SharedMemoryPool,
    MemoryPoolConfig,
    MemorySegment,
    SegmentType,
    SegmentAccess,
    LockManager,
    SyncProtocol,
    CacheCoherence,
)

# 团队模块
from .team import (
    TeamBuilder,
    Team,
    TeamConfig,
    AgentRole,
    RoleRegistry,
    FormationManager,
    MembershipManager,
    TeamProtocol,
    FormationType,
)

# FLY 六层架构
from .core.fly_layers import (
    Fly0Master,
    Fly1Mission,
    Fly2Rules,
    Fly3Trends,
    Fly4Skills,
    Fly5Tools,
    FLYLevel,
)

# 高级管理模块
from .management import (
    ConfigManager,
    LifecycleManager,
    UnifiedLogger,
    MetricsExporter,
)

# Agent 交接桥接
from .handoff_bridge import HandoffBridge, HandoffPriority

# 执行循环客户端
from .zenloop_client import ZenLoopClient, ExecutionStatus


@dataclass
class SwarmFlyConfig:
    """
    SwarmFly 全局配置
    
    配置 SwarmFly 层的各项参数
    """
    # 节点配置
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_name: str = "SwarmFly Node"
    
    # 生命周期配置
    enable_lifecycle_management: bool = True
    default_transition_rules: List[TransitionRule] = field(default_factory=list)
    
    # 协作配置
    enable_collaboration: bool = True
    collaboration_config: CollaborationConfig = field(default_factory=CollaborationConfig)
    
    # 内存池配置
    enable_shared_memory: bool = True
    memory_pool_config: MemoryPoolConfig = field(default_factory=MemoryPoolConfig)
    
    # 团队配置
    enable_teams: bool = True
    default_team_config: TeamConfig = field(default_factory=TeamConfig)
    
    # 其他
    enable_monitoring: bool = True
    stats_interval: int = 60

    # 高级管理模块
    enable_config_manager: bool = True
    enable_lifecycle_manager: bool = True
    enable_unified_logger: bool = True
    enable_metrics_exporter: bool = True
    enable_handoff_bridge: bool = True
    enable_zenloop: bool = True

    # FLY 六层配置
    enable_fly0_master: bool = True
    enable_fly1_mission: bool = True
    enable_fly2_rules: bool = True
    enable_fly3_trends: bool = True
    enable_fly4_skills: bool = True
    enable_fly5_tools: bool = True


class SwarmFly:
    """
    SwarmFly 核心
    
    整合生命周期、协作、内存和团队功能的统一入口
    """
    
    def __init__(self, config: Optional[SwarmFlyConfig] = None):
        """
        初始化 SwarmFly
        
        Args:
            config: 配置对象
        """
        self.config = config or SwarmFlyConfig()
        self._initialized_at = datetime.now()
        
        # 初始化横切模块
        self._init_lifecycle()
        self._init_collaboration()
        self._init_memory()
        self._init_teams()

        # 初始化 FLY 六层
        self._init_fly_layers()

        # 初始化高级管理模块
        self._init_advanced_management()

        # 注册的 Agent
        self._registered_agents: Set[str] = set()

        # 锁
        self._lock = threading.RLock()

        # 回调
        self._on_agent_registered: List[Callable[[str], None]] = []
        self._on_agent_unregistered: List[Callable[[str], None]] = []
        self._on_error: List[Callable[[str, Exception], None]] = []
    
    def _init_lifecycle(self) -> None:
        """初始化生命周期管理"""
        if self.config.enable_lifecycle_management:
            rules = self.config.default_transition_rules or get_default_rules()
            self.state_manager = StateManager(global_rules=rules)
        else:
            self.state_manager = None
    
    def _init_collaboration(self) -> None:
        """初始化协作引擎"""
        if self.config.enable_collaboration:
            self.collaboration_engine = CollaborationEngine(
                config=self.config.collaboration_config
            )
        else:
            self.collaboration_engine = None
    
    def _init_memory(self) -> None:
        """初始化共享内存池"""
        if self.config.enable_shared_memory:
            self.memory_pool = SharedMemoryPool(
                pool_id=f"pool_{self.config.node_id}",
                node_id=self.config.node_id,
                config=self.config.memory_pool_config,
            )
        else:
            self.memory_pool = None
    
    def _init_teams(self) -> None:
        """初始化团队管理"""
        if self.config.enable_teams:
            self.team_builder = TeamBuilder()
        else:
            self.team_builder = None

    def _init_fly_layers(self) -> None:
        """初始化 FLY 六层架构"""
        # FLY-0: Master - 任务提交、分派、状态追踪
        self.fly0_master = Fly0Master() if self.config.enable_fly0_master else None

        # FLY-1: Mission - 使命对齐、价值体系
        self.fly1_mission = Fly1Mission() if self.config.enable_fly1_mission else None

        # FLY-2: Rules - 规则引擎、冲突解决、RBAC
        self.fly2_rules = Fly2Rules() if self.config.enable_fly2_rules else None

        # FLY-3: Trends - 趋势检测、预测引擎
        self.fly3_trends = Fly3Trends() if self.config.enable_fly3_trends else None

        # FLY-4: Skills - 技能注册、搜索、调用
        self.fly4_skills = Fly4Skills() if self.config.enable_fly4_skills else None

        # FLY-5: Tools - 工具注册、消息队列、资源池
        self.fly5_tools = Fly5Tools() if self.config.enable_fly5_tools else None

    # ==================== Agent 管理 ====================
    
    def _init_advanced_management(self) -> None:
        """初始化高级管理模块"""
        # 统一日志
        if self.config.enable_unified_logger:
            self.logger = UnifiedLogger()
        else:
            self.logger = None

        # 配置管理
        if self.config.enable_config_manager:
            self.config_manager = ConfigManager()
        else:
            self.config_manager = None

        # 生命周期管理
        if self.config.enable_lifecycle_manager:
            self.lifecycle_manager = LifecycleManager()
        else:
            self.lifecycle_manager = None

        # 指标导出
        if self.config.enable_metrics_exporter:
            self.metrics_exporter = MetricsExporter()
        else:
            self.metrics_exporter = None

        # Agent 交接桥接
        if self.config.enable_handoff_bridge:
            self.handoff_bridge = HandoffBridge()
        else:
            self.handoff_bridge = None

        # 执行循环
        if self.config.enable_zenloop:
            self.zenloop = ZenLoopClient()
        else:
            self.zenloop = None

    def register_agent(
        self,
        agent_id: str,
        role: str = "worker",
    ) -> bool:
        """
        注册 Agent
        
        Args:
            agent_id: Agent ID
            role: Agent 角色
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            if agent_id in self._registered_agents:
                return False
            
            self._registered_agents.add(agent_id)
            
            # 注册到各组件
            if self.state_manager:
                self.state_manager.register_agent(agent_id)
            
            if self.collaboration_engine:
                self.collaboration_engine.register_agent(agent_id)
            
            if self.memory_pool:
                self.memory_pool.register_agent(agent_id)
            
            # 触发回调
            for callback in self._on_agent_registered:
                try:
                    callback(agent_id)
                except Exception as e:
                    self._handle_error("register_agent", e)
            
            return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        注销 Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            if agent_id not in self._registered_agents:
                return False
            
            self._registered_agents.discard(agent_id)
            
            # 从各组件注销
            if self.state_manager:
                self.state_manager.unregister_agent(agent_id)
            
            if self.collaboration_engine:
                self.collaboration_engine.unregister_agent(agent_id)
            
            if self.memory_pool:
                self.memory_pool.unregister_agent(agent_id)
            
            # 触发回调
            for callback in self._on_agent_unregistered:
                try:
                    callback(agent_id)
                except Exception as e:
                    self._handle_error("unregister_agent", e)
            
            return True
    
    def get_registered_agents(self) -> List[str]:
        """获取已注册的 Agent"""
        return list(self._registered_agents)
    
    # ==================== 生命周期 ====================
    
    def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """获取 Agent 状态"""
        if self.state_manager:
            return self.state_manager.get_state(agent_id)
        return None
    
    def transition_agent_state(
        self,
        agent_id: str,
        target_state: AgentState,
        reason: str = "",
    ) -> bool:
        """
        转换 Agent 状态
        
        Args:
            agent_id: Agent ID
            target_state: 目标状态
            reason: 转换原因
            
        Returns:
            bool: 是否成功
        """
        if self.state_manager:
            result = self.state_manager.transition(agent_id, target_state, reason)
            return result.success
        return False
    
    def create_agent_lifecycle(
        self,
        agent_id: str,
        initial_state: AgentState = AgentState.CREATED,
    ) -> Optional[AgentLifecycle]:
        """
        创建 Agent 生命周期对象
        
        Args:
            agent_id: Agent ID
            initial_state: 初始状态
            
        Returns:
            Optional[AgentLifecycle]: 生命周期对象
        """
        if self.state_manager:
            return self.state_manager.register_agent(agent_id, initial_state)
        return None
    
    # ==================== 协作 ====================
    
    def submit_task(
        self,
        name: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        tags: Optional[Set[str]] = None,
    ) -> Optional[Task]:
        """
        提交任务
        
        Args:
            name: 任务名称
            payload: 任务数据
            priority: 优先级
            tags: 任务标签
            
        Returns:
            Optional[Task]: 创建的任务
        """
        if self.collaboration_engine:
            return self.collaboration_engine.submit_task(
                name=name,
                payload=payload,
                priority=priority,
                tags=tags,
            )
        return None
    
    def dispatch_task(self, agent_id: str) -> Optional[Task]:
        """
        为 Agent 分发任务
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Optional[Task]: 分发的任务
        """
        if self.collaboration_engine:
            return self.collaboration_engine.dispatch_next_task(agent_id)
        return None
    
    def complete_task(
        self,
        task_id: str,
        agent_id: str,
        result: Any = None,
    ) -> bool:
        """标记任务完成"""
        if self.collaboration_engine:
            return self.collaboration_engine.complete_task(task_id, agent_id, result)
        return False
    
    def update_agent_load(
        self,
        agent_id: str,
        **kwargs: Any,
    ) -> None:
        """更新 Agent 负载"""
        if self.collaboration_engine:
            self.collaboration_engine.update_agent_load(agent_id, **kwargs)
    
    # ==================== 内存 ====================
    
    def create_shared_segment(
        self,
        name: str,
        owner_id: Optional[str] = None,
        initial_data: Any = None,
    ) -> Optional[MemorySegment]:
        """
        创建共享内存段
        
        Args:
            name: 段名称
            owner_id: 所有者 ID
            initial_data: 初始数据
            
        Returns:
            Optional[MemorySegment]: 创建的内存段
        """
        if self.memory_pool:
            return self.memory_pool.create_segment(
                name=name,
                owner_id=owner_id,
                initial_data=initial_data,
            )
        return None
    
    def read_shared_data(
        self,
        segment_name: str,
        agent_id: str,
    ) -> Optional[Any]:
        """读取共享数据"""
        if self.memory_pool:
            return self.memory_pool.read_with_lock(segment_name, agent_id)
        return None
    
    def write_shared_data(
        self,
        segment_name: str,
        agent_id: str,
        data: Any,
    ) -> bool:
        """写入共享数据"""
        if self.memory_pool:
            return self.memory_pool.write_with_lock(segment_name, agent_id, data)
        return False
    
    # ==================== 团队 ====================
    
    def create_team(
        self,
        name: str,
        formation_type: FormationType = FormationType.HIERARCHICAL,
        initial_members: Optional[List[str]] = None,
    ) -> Optional[Team]:
        """
        创建团队
        
        Args:
            name: 团队名称
            formation_type: 编队类型
            initial_members: 初始成员
            
        Returns:
            Optional[Team]: 创建的团队
        """
        if self.team_builder:
            config = TeamConfig(name=name, formation_type=formation_type)
            result = self.team_builder.create_team(config, initial_members)
            return result.team if result.success else None
        return None
    
    def add_to_team(
        self,
        team_id: str,
        agent_id: str,
        role: str = "worker",
    ) -> bool:
        """添加到团队"""
        if self.team_builder:
            member = self.team_builder.add_member(team_id, agent_id, role)
            return member is not None
        return False
    
    # ==================== 回调 ====================
    
    def register_callback(
        self,
        event: str,
        callback: Callable[..., None],
    ) -> None:
        """注册回调"""
        if event == "agent_registered":
            self._on_agent_registered.append(callback)
        elif event == "agent_unregistered":
            self._on_agent_unregistered.append(callback)
        elif event == "error":
            self._on_error.append(callback)
    
    def _handle_error(self, context: str, error: Exception) -> None:
        """处理错误"""
        for callback in self._on_error:
            try:
                callback(context, error)
            except Exception:
                pass
    
    # ==================== 状态和统计 ====================
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "node_id": self.config.node_id,
            "node_name": self.config.node_name,
            "initialized_at": self._initialized_at.isoformat(),
            "registered_agents": len(self._registered_agents),
            "lifecycle_enabled": self.config.enable_lifecycle_management,
            "collaboration_enabled": self.config.enable_collaboration,
            "memory_enabled": self.config.enable_shared_memory,
            "teams_enabled": self.config.enable_teams,
        }
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """获取详细状态"""
        status = self.get_status()
        
        if self.state_manager:
            status["lifecycle"] = self.state_manager.get_all_agents_summary()
        
        if self.collaboration_engine:
            status["collaboration"] = self.collaboration_engine.get_status()
        
        if self.memory_pool:
            status["memory"] = self.memory_pool.get_detailed_stats()
        
        if self.team_builder:
            status["teams"] = self.team_builder.get_statistics()
        
        return status
    
    def __repr__(self) -> str:
        return f"SwarmFly(node_id={self.config.node_id}, agents={len(self._registered_agents)})"


# 模块便捷访问
def create_swarmfly(config: Optional[SwarmFlyConfig] = None) -> SwarmFly:
    """
    创建 SwarmFly 实例
    
    Args:
        config: 配置对象
        
    Returns:
        SwarmFly: SwarmFly 实例
    """
    return SwarmFly(config)


# 导出所有公共接口
__all__ = [
    # 核心
    "SwarmFly",
    "SwarmFlyConfig",
    "create_swarmfly",
    # 生命周期
    "AgentLifecycle",
    "AgentState",
    "StateManager",
    "LifecycleTransition",
    # 协作
    "CollaborationEngine",
    "CollaborationConfig",
    "Task",
    "TaskPriority",
    "TaskStatus",
    "LoadBalancer",
    "ConflictResolver",
    "ConflictType",
    # 内存
    "SharedMemoryPool",
    "MemoryPoolConfig",
    "MemorySegment",
    "SegmentType",
    "SegmentAccess",
    "LockManager",
    "CacheCoherence",
    # 团队
    "TeamBuilder",
    "Team",
    "TeamConfig",
    "AgentRole",
    "FormationManager",
    "MembershipManager",
    "TeamProtocol",
    "FormationType",
]
