"""
协作引擎核心

整合任务分发、负载均衡、共识和冲突解决的统一协作引擎
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime
import threading
import uuid

from .task_dispatcher import (
    TaskDispatcher,
    Task,
    TaskPriority,
    TaskStatus,
    DispatchStrategy,
)
from .load_balancer import (
    LoadBalancer,
    LoadMetric,
    BalancingStrategy,
    AgentLoad,
)
from .consensus import (
    ConsensusMechanism,
    ConsensusResult,
    ConsensusProtocol,
    QuorumConsensus,
    WeightedConsensus,
    UnanimousConsensus,
)
from .conflict_resolver import (
    ConflictResolver,
    Conflict,
    ConflictType,
    ResolutionStrategy,
    ResolutionResult,
)


@dataclass
class CollaborationConfig:
    """
    协作引擎配置
    
    协作引擎的各项配置参数
    """
    # 任务分发配置
    dispatch_strategy: DispatchStrategy = DispatchStrategy.ROUND_ROBIN
    max_queue_size: int = 1000
    
    # 负载均衡配置
    balancing_strategy: BalancingStrategy = BalancingStrategy.LEAST_LOADED
    capacity_threshold: float = 0.9
    
    # 共识配置
    consensus_protocol: ConsensusProtocol = ConsensusProtocol.QUORUM
    
    # 冲突解决配置
    default_resolution_strategy: ResolutionStrategy = ResolutionStrategy.HIGHEST_PRIORITY
    
    # 其他配置
    enable_monitoring: bool = True
    stats_interval: int = 60  # 统计更新间隔（秒）


@dataclass
class TaskResult:
    """
    任务执行结果
    
    封装任务执行的完整结果
    """
    task_id: str
    success: bool
    
    # 执行信息
    agent_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 结果数据
    result: Any = None
    error: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        """执行时长（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "agent_id": self.agent_id,
            "duration": self.duration,
            "result": str(self.result) if self.result else None,
            "error": self.error,
            "metadata": self.metadata,
        }


class CollaborationEngine:
    """
    协作引擎
    
    统一管理多 Agent 的任务协作、负载均衡、共识决策和冲突解决
    """
    
    def __init__(self, config: Optional[CollaborationConfig] = None):
        """
        初始化协作引擎
        
        Args:
            config: 协作配置
        """
        self.config = config or CollaborationConfig()
        
        # 核心组件
        self.dispatcher = TaskDispatcher(strategy=self.config.dispatch_strategy)
        self.load_balancer = LoadBalancer(strategy=self.config.balancing_strategy)
        
        # 初始化共识机制
        self._init_consensus()
        
        # 冲突解决器
        self.conflict_resolver = ConflictResolver(
            default_strategy=self.config.default_resolution_strategy
        )
        
        # 注册 Agent
        self._registered_agents: Set[str] = set()
        
        # 锁
        self._lock = threading.RLock()
        
        # 回调
        self._on_task_result: List[Callable[[TaskResult], None]] = []
        self._on_agent_registered: List[Callable[[str], None]] = []
        self._on_agent_unregistered: List[Callable[[str], None]] = []
        self._on_conflict: List[Callable[[Conflict], None]] = []
        self._on_consensus: List[Callable[[str, ConsensusResult], None]] = []
        
        # 注册内部回调
        self._setup_internal_callbacks()
    
    def _init_consensus(self) -> None:
        """初始化共识机制"""
        if self.config.consensus_protocol == ConsensusProtocol.QUORUM:
            self.consensus = QuorumConsensus()
        elif self.config.consensus_protocol == ConsensusProtocol.WEIGHTED:
            self.consensus = WeightedConsensus()
        elif self.config.consensus_protocol == ConsensusProtocol.UNANIMOUS:
            self.consensus = UnanimousConsensus()
        else:
            self.consensus = QuorumConsensus()  # 默认
    
    def _setup_internal_callbacks(self) -> None:
        """设置内部回调"""
        # 任务完成回调
        self.dispatcher.register_callback("task_completed", self._on_task_completed)
        self.dispatcher.register_callback("task_failed", self._on_task_failed)
        
        # 冲突检测回调
        self.conflict_resolver.register_callback(
            "conflict_detected",
            self._on_conflict_detected
        )
    
    # ==================== Agent 管理 ====================
    
    def register_agent(
        self,
        agent_id: str,
        weight: float = 1.0,
        capabilities: Optional[Set[str]] = None,
    ) -> None:
        """
        注册 Agent
        
        Args:
            agent_id: Agent ID
            weight: Agent 权重
            capabilities: Agent 能力集合
        """
        with self._lock:
            if agent_id in self._registered_agents:
                return
            
            self._registered_agents.add(agent_id)
            
            # 注册到各组件
            self.dispatcher.register_agent(agent_id)
            self.load_balancer.register_agent(agent_id, weight=weight)
            
            # 设置共识权重
            if isinstance(self.consensus, (WeightedConsensus,)):
                self.consensus.set_weight(agent_id, weight)
            
            # 设置冲突解决权重
            self.conflict_resolver.set_agent_weight(agent_id, weight)
            
            # 触发回调
            for callback in self._on_agent_registered:
                try:
                    callback(agent_id)
                except Exception:
                    pass
    
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
            
            self._registered_agents.remove(agent_id)
            
            # 从各组件注销
            self.dispatcher.unregister_agent(agent_id)
            self.load_balancer.unregister_agent(agent_id)
            
            # 触发回调
            for callback in self._on_agent_unregistered:
                try:
                    callback(agent_id)
                except Exception:
                    pass
            
            return True
    
    def get_registered_agents(self) -> List[str]:
        """获取已注册的 Agent 列表"""
        return list(self._registered_agents)
    
    # ==================== 任务管理 ====================
    
    def submit_task(
        self,
        name: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        preferred_agents: Optional[List[str]] = None,
        excluded_agents: Optional[List[str]] = None,
        tags: Optional[Set[str]] = None,
    ) -> Task:
        """
        提交任务
        
        Args:
            name: 任务名称
            payload: 任务数据
            priority: 优先级
            preferred_agents: 优先分配的 Agent
            excluded_agents: 排除的 Agent
            tags: 任务标签
            
        Returns:
            Task: 创建的任务
        """
        task = self.dispatcher.submit_task(
            name=name,
            payload=payload,
            priority=priority,
            preferred_agents=preferred_agents,
            excluded_agents=excluded_agents,
            tags=tags,
        )
        
        return task
    
    def dispatch_next_task(
        self,
        agent_id: str,
        filter_tags: Optional[Set[str]] = None,
    ) -> Optional[Task]:
        """
        为 Agent 分发下一个任务
        
        Args:
            agent_id: Agent ID
            filter_tags: 标签过滤器
            
        Returns:
            Optional[Task]: 分发的任务
        """
        # 检查 Agent 是否注册
        if agent_id not in self._registered_agents:
            self.register_agent(agent_id)
        
        # 获取下一个任务
        task = self.dispatcher.get_next_task(
            agent_id=agent_id,
            filter_tags=filter_tags,
        )
        
        if task:
            # 更新负载
            self.load_balancer.increment_task(agent_id)
        
        return task
    
    def complete_task(
        self,
        task_id: str,
        agent_id: str,
        result: Any = None,
    ) -> bool:
        """
        标记任务完成
        
        Args:
            task_id: 任务 ID
            agent_id: 执行的 Agent ID
            result: 任务结果
            
        Returns:
            bool: 是否成功
        """
        success = self.dispatcher.complete_task(task_id, result)
        
        if success:
            # 更新负载
            self.load_balancer.decrement_task(agent_id)
        
        return success
    
    def fail_task(
        self,
        task_id: str,
        error: str,
    ) -> bool:
        """
        标记任务失败
        
        Args:
            task_id: 任务 ID
            error: 错误信息
            
        Returns:
            bool: 是否成功
        """
        return self.dispatcher.fail_task(task_id, error)
    
    # ==================== 负载管理 ====================
    
    def update_agent_load(
        self,
        agent_id: str,
        **kwargs: Any,
    ) -> AgentLoad:
        """
        更新 Agent 负载
        
        Args:
            agent_id: Agent ID
            **kwargs: 负载指标
        """
        return self.load_balancer.update_load(agent_id, **kwargs)
    
    def get_agent_load(self, agent_id: str) -> Optional[AgentLoad]:
        """获取 Agent 负载"""
        return self.load_balancer.get_load(agent_id)
    
    # ==================== 共识决策 ====================
    
    def propose_decision(
        self,
        value: Any,
        participants: Optional[List[str]] = None,
        protocol: Optional[ConsensusProtocol] = None,
    ) -> str:
        """
        提出决策提案
        
        Args:
            value: 决策值
            participants: 参与者列表
            protocol: 共识协议
            
        Returns:
            str: 轮次 ID
        """
        round_id = str(uuid.uuid4())
        participants = participants or list(self._registered_agents)
        
        # 使用指定的协议
        if protocol and protocol != self.config.consensus_protocol:
            if protocol == ConsensusProtocol.QUORUM:
                consensus = QuorumConsensus()
            elif protocol == ConsensusProtocol.WEIGHTED:
                consensus = WeightedConsensus()
            elif protocol == ConsensusProtocol.UNANIMOUS:
                consensus = UnanimousConsensus()
            else:
                consensus = self.consensus
        else:
            consensus = self.consensus
        
        consensus.propose(round_id, value, participants)
        
        return round_id
    
    def vote(
        self,
        round_id: str,
        voter_id: str,
        value: Any,
        reason: str = "",
    ) -> bool:
        """
        投票
        
        Args:
            round_id: 轮次 ID
            voter_id: 投票者 ID
            value: 投票值
            reason: 投票理由
            
        Returns:
            bool: 是否成功
        """
        return self.consensus.vote(round_id, voter_id, value, reason=reason)
    
    def check_consensus(
        self,
        round_id: str,
    ) -> Optional[Any]:
        """
        检查共识是否达成
        
        Args:
            round_id: 轮次 ID
            
        Returns:
            Optional[Any]: 决策值
        """
        return self.consensus.check_decision(round_id)
    
    # ==================== 冲突管理 ====================
    
    def detect_conflict(
        self,
        involved_agents: List[str],
        conflict_type: ConflictType,
        positions: Dict[str, Any],
        description: str = "",
        resource_id: Optional[str] = None,
    ) -> Conflict:
        """
        检测冲突
        
        Args:
            involved_agents: 涉及的 Agent
            conflict_type: 冲突类型
            positions: 各方立场
            description: 描述
            resource_id: 资源 ID
            
        Returns:
            Conflict: 冲突对象
        """
        return self.conflict_resolver.register_conflict(
            conflict_type=conflict_type,
            involved_agents=involved_agents,
            positions=positions,
            description=description,
            resource_id=resource_id,
        )
    
    def resolve_conflict(
        self,
        conflict_id: str,
        strategy: Optional[ResolutionStrategy] = None,
    ) -> ResolutionResult:
        """
        解决冲突
        
        Args:
            conflict_id: 冲突 ID
            strategy: 解决策略
            
        Returns:
            ResolutionResult: 解决结果
        """
        return self.conflict_resolver.resolve(conflict_id, strategy)
    
    # ==================== 回调管理 ====================
    
    def register_callback(
        self,
        event: str,
        callback: Callable[..., None],
    ) -> None:
        """注册事件回调"""
        if event == "task_result":
            self._on_task_result.append(callback)
        elif event == "agent_registered":
            self._on_agent_registered.append(callback)
        elif event == "agent_unregistered":
            self._on_agent_unregistered.append(callback)
        elif event == "conflict":
            self._on_conflict.append(callback)
        elif event == "consensus":
            self._on_consensus.append(callback)
    
    def _on_task_completed(self, task: Task) -> None:
        """任务完成内部回调"""
        result = TaskResult(
            task_id=task.task_id,
            success=True,
            agent_id=task.assigned_agent,
            started_at=task.started_at,
            completed_at=task.completed_at,
            result=task.result,
        )
        
        for callback in self._on_task_result:
            try:
                callback(result)
            except Exception:
                pass
    
    def _on_task_failed(self, task: Task) -> None:
        """任务失败内部回调"""
        result = TaskResult(
            task_id=task.task_id,
            success=False,
            agent_id=task.assigned_agent,
            error=task.error,
        )
        
        for callback in self._on_task_result:
            try:
                callback(result)
            except Exception:
                pass
    
    def _on_conflict_detected(self, conflict: Conflict) -> None:
        """冲突检测内部回调"""
        for callback in self._on_conflict:
            try:
                callback(conflict)
            except Exception:
                pass
    
    # ==================== 状态查询 ====================
    
    def get_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        return {
            "registered_agents": len(self._registered_agents),
            "task_queue": self.dispatcher.get_queue_summary(),
            "load_balancing": self.load_balancer.get_statistics(),
            "conflicts": self.conflict_resolver.get_statistics(),
        }
    
    def get_pending_tasks(self) -> List[Task]:
        """获取待处理任务"""
        return self.dispatcher.get_tasks_by_status(TaskStatus.QUEUED)
    
    def get_pending_conflicts(self) -> List[Conflict]:
        """获取待解决冲突"""
        return self.conflict_resolver.get_pending_conflicts()
