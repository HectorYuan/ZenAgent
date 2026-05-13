"""
冲突解决器

处理多 Agent 协作中的资源冲突和决策冲突
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Set, Type
from datetime import datetime
from abc import ABC, abstractmethod
import threading


class ConflictType(Enum):
    """冲突类型枚举"""
    RESOURCE = "resource"           # 资源冲突
    DECISION = "decision"           # 决策冲突
    PRIORITY = "priority"           # 优先级冲突
    TIMING = "timing"              # 时序冲突
    SEMANTIC = "semantic"          # 语义冲突
    DATA = "data"                   # 数据冲突


class ResolutionStrategy(Enum):
    """解决策略枚举"""
    FIRST_COME_FIRST_SERVED = "fcfs"       # 先到先得
    HIGHEST_PRIORITY = "priority"         # 最高优先级
    WEIGHTED_VOTING = "weighted_voting"   # 加权投票
    RANDOM = "random"                     # 随机
    NEGOTIATION = "negotiation"           # 协商
    ROLLBACK = "rollback"                # 回滚
    MERGE = "merge"                       # 合并
    MANUAL = "manual"                     # 人工介入


@dataclass
class Conflict:
    """
    冲突数据类
    
    表示一个需要解决的冲突
    """
    conflict_id: str
    conflict_type: ConflictType
    
    # 冲突描述
    description: str = ""
    
    # 涉及的 Agent
    involved_agents: List[str] = field(default_factory=list)
    
    # 冲突资源/目标
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    
    # 各方立场
    positions: Dict[str, Any] = field(default_factory=dict)
    
    # 优先级
    priority: int = 0
    
    # 时间信息
    detected_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_resolved(self) -> bool:
        """冲突是否已解决"""
        return self.resolved_at is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "conflict_id": self.conflict_id,
            "conflict_type": self.conflict_type.value,
            "description": self.description,
            "involved_agents": self.involved_agents,
            "resource_id": self.resource_id,
            "priority": self.priority,
            "is_resolved": self.is_resolved,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class ResolutionResult:
    """
    冲突解决结果
    
    记录冲突解决的结果
    """
    success: bool
    conflict_id: str
    strategy: ResolutionStrategy
    
    # 解决方案
    resolution: Any = None
    winner_id: Optional[str] = None
    
    # 影响分析
    affected_agents: List[str] = field(default_factory=list)
    rollback_required: bool = False
    
    # 时间信息
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self) -> None:
        """结束解决过程"""
        self.end_time = datetime.now()
    
    @property
    def duration(self) -> Optional[float]:
        """解决耗时（秒）"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "conflict_id": self.conflict_id,
            "strategy": self.strategy.value,
            "resolution": str(self.resolution) if self.resolution else None,
            "winner_id": self.winner_id,
            "affected_agents": self.affected_agents,
            "rollback_required": self.rollback_required,
            "duration": self.duration,
        }


class ConflictResolver:
    """
    冲突解决器
    
    提供多种冲突解决策略
    """
    
    def __init__(self, default_strategy: ResolutionStrategy = ResolutionStrategy.HIGHEST_PRIORITY):
        """
        初始化冲突解决器
        
        Args:
            default_strategy: 默认解决策略
        """
        self.default_strategy = default_strategy
        self._conflicts: Dict[str, Conflict] = {}
        self._resolved_history: List[ResolutionResult] = []
        self._lock = threading.RLock()
        
        # 策略处理器
        self._strategies: Dict[ResolutionStrategy, Callable] = {
            ResolutionStrategy.FIRST_COME_FIRST_SERVED: self._resolve_fcfs,
            ResolutionStrategy.HIGHEST_PRIORITY: self._resolve_priority,
            ResolutionStrategy.WEIGHTED_VOTING: self._resolve_weighted_voting,
            ResolutionStrategy.RANDOM: self._resolve_random,
            ResolutionStrategy.NEGOTIATION: self._resolve_negotiation,
            ResolutionStrategy.ROLLBACK: self._resolve_rollback,
            ResolutionStrategy.MERGE: self._resolve_merge,
        }
        
        # 回调
        self._on_conflict_detected: List[Callable[[Conflict], None]] = []
        self._on_conflict_resolved: List[Callable[[Conflict, ResolutionResult], None]] = []
        
        # Agent 权重
        self._agent_weights: Dict[str, float] = {}
    
    def set_agent_weight(self, agent_id: str, weight: float) -> None:
        """
        设置 Agent 权重
        
        Args:
            agent_id: Agent ID
            weight: 权重值
        """
        self._agent_weights[agent_id] = weight
    
    def get_agent_weight(self, agent_id: str) -> float:
        """获取 Agent 权重"""
        return self._agent_weights.get(agent_id, 1.0)
    
    def register_conflict(
        self,
        conflict_type: ConflictType,
        involved_agents: List[str],
        description: str = "",
        positions: Optional[Dict[str, Any]] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        priority: int = 0,
    ) -> Conflict:
        """
        注册新冲突
        
        Args:
            conflict_type: 冲突类型
            involved_agents: 涉及的 Agent
            description: 冲突描述
            positions: 各方立场
            resource_id: 资源 ID
            resource_type: 资源类型
            priority: 优先级
            
        Returns:
            Conflict: 创建的冲突对象
        """
        import uuid
        
        conflict = Conflict(
            conflict_id=str(uuid.uuid4()),
            conflict_type=conflict_type,
            description=description,
            involved_agents=involved_agents,
            positions=positions or {},
            resource_id=resource_id,
            resource_type=resource_type,
            priority=priority,
        )
        
        with self._lock:
            self._conflicts[conflict.conflict_id] = conflict
        
        # 触发回调
        for callback in self._on_conflict_detected:
            try:
                callback(conflict)
            except Exception:
                pass
        
        return conflict
    
    def resolve(
        self,
        conflict_id: str,
        strategy: Optional[ResolutionStrategy] = None,
        **kwargs: Any,
    ) -> ResolutionResult:
        """
        解决冲突
        
        Args:
            conflict_id: 冲突 ID
            strategy: 解决策略
            **kwargs: 附加参数
            
        Returns:
            ResolutionResult: 解决结果
        """
        strategy = strategy or self.default_strategy
        
        with self._lock:
            conflict = self._conflicts.get(conflict_id)
            if not conflict:
                return ResolutionResult(
                    success=False,
                    conflict_id=conflict_id,
                    strategy=strategy,
                    metadata={"error": "Conflict not found"},
                )
            
            if conflict.is_resolved:
                return ResolutionResult(
                    success=False,
                    conflict_id=conflict_id,
                    strategy=strategy,
                    metadata={"error": "Conflict already resolved"},
                )
            
            # 执行解决策略
            handler = self._strategies.get(strategy)
            if not handler:
                return ResolutionResult(
                    success=False,
                    conflict_id=conflict_id,
                    strategy=strategy,
                    metadata={"error": f"Unknown strategy: {strategy}"},
                )
            
            result = handler(conflict, **kwargs)
            
            # 标记冲突已解决
            if result.success:
                conflict.resolved_at = datetime.now()
                self._resolved_history.append(result)
            
            result.finish()
            
            # 触发回调
            for callback in self._on_conflict_resolved:
                try:
                    callback(conflict, result)
                except Exception:
                    pass
            
            return result
    
    def _resolve_fcfs(
        self,
        conflict: Conflict,
        **kwargs: Any,
    ) -> ResolutionResult:
        """先到先得策略"""
        # 简单返回第一个 Agent 的立场
        result = ResolutionResult(
            success=True,
            conflict_id=conflict.conflict_id,
            strategy=ResolutionStrategy.FIRST_COME_FIRST_SERVED,
            resolution=list(conflict.positions.values())[0] if conflict.positions else None,
            winner_id=conflict.involved_agents[0] if conflict.involved_agents else None,
            affected_agents=conflict.involved_agents,
        )
        return result
    
    def _resolve_priority(
        self,
        conflict: Conflict,
        **kwargs: Any,
    ) -> ResolutionResult:
        """最高优先级策略"""
        # 选择优先级最高的 Agent
        if not conflict.involved_agents:
            return ResolutionResult(
                success=False,
                conflict_id=conflict.conflict_id,
                strategy=ResolutionStrategy.HIGHEST_PRIORITY,
                metadata={"error": "No agents involved"},
            )
        
        # 使用 Agent 权重作为优先级
        winner = max(
            conflict.involved_agents,
            key=lambda a: self.get_agent_weight(a),
        )
        
        result = ResolutionResult(
            success=True,
            conflict_id=conflict.conflict_id,
            strategy=ResolutionStrategy.HIGHEST_PRIORITY,
            resolution=conflict.positions.get(winner),
            winner_id=winner,
            affected_agents=conflict.involved_agents,
        )
        
        return result
    
    def _resolve_weighted_voting(
        self,
        conflict: Conflict,
        **kwargs: Any,
    ) -> ResolutionResult:
        """加权投票策略"""
        if not conflict.positions:
            return ResolutionResult(
                success=False,
                conflict_id=conflict.conflict_id,
                strategy=ResolutionStrategy.WEIGHTED_VOTING,
                metadata={"error": "No positions to vote on"},
            )
        
        # 统计每个立场的加权票数
        position_weights: Dict[Any, float] = {}
        for agent_id, position in conflict.positions.items():
            weight = self.get_agent_weight(agent_id)
            position_weights[position] = position_weights.get(position, 0.0) + weight
        
        # 选择加权票数最高的立场
        winner_position = max(position_weights.items(), key=lambda x: x[1])[0]
        
        # 找出支持该立场的 Agent
        winners = [
            agent for agent, pos in conflict.positions.items()
            if pos == winner_position
        ]
        
        result = ResolutionResult(
            success=True,
            conflict_id=conflict.conflict_id,
            strategy=ResolutionStrategy.WEIGHTED_VOTING,
            resolution=winner_position,
            winner_id=winners[0] if winners else None,
            affected_agents=conflict.involved_agents,
            metadata={"position_weights": position_weights},
        )
        
        return result
    
    def _resolve_random(
        self,
        conflict: Conflict,
        **kwargs: Any,
    ) -> ResolutionResult:
        """随机策略"""
        import random
        
        if not conflict.involved_agents:
            return ResolutionResult(
                success=False,
                conflict_id=conflict.conflict_id,
                strategy=ResolutionStrategy.RANDOM,
                metadata={"error": "No agents involved"},
            )
        
        winner = random.choice(conflict.involved_agents)
        
        result = ResolutionResult(
            success=True,
            conflict_id=conflict.conflict_id,
            strategy=ResolutionStrategy.RANDOM,
            resolution=conflict.positions.get(winner),
            winner_id=winner,
            affected_agents=conflict.involved_agents,
        )
        
        return result
    
    def _resolve_negotiation(
        self,
        conflict: Conflict,
        **kwargs: Any,
    ) -> ResolutionResult:
        """协商策略 - 尝试找到折中方案"""
        # 简单的协商：返回所有立场的平均值或合并
        if not conflict.positions:
            return ResolutionResult(
                success=False,
                conflict_id=conflict.conflict_id,
                strategy=ResolutionStrategy.NEGOTIATION,
                metadata={"error": "No positions to negotiate"},
            )
        
        # 尝试合并数字类型的立场
        numeric_positions = [
            v for v in conflict.positions.values()
            if isinstance(v, (int, float))
        ]
        
        if numeric_positions:
            # 返回平均值
            resolution = sum(numeric_positions) / len(numeric_positions)
        else:
            # 返回第一个立场
            resolution = list(conflict.positions.values())[0]
        
        result = ResolutionResult(
            success=True,
            conflict_id=conflict.conflict_id,
            strategy=ResolutionStrategy.NEGOTIATION,
            resolution=resolution,
            affected_agents=conflict.involved_agents,
            metadata={"negotiated": True},
        )
        
        return result
    
    def _resolve_rollback(
        self,
        conflict: Conflict,
        **kwargs: Any,
    ) -> ResolutionResult:
        """回滚策略"""
        result = ResolutionResult(
            success=True,
            conflict_id=conflict.conflict_id,
            strategy=ResolutionStrategy.ROLLBACK,
            resolution=None,
            affected_agents=conflict.involved_agents,
            rollback_required=True,
            metadata={"action": "rollback"},
        )
        
        return result
    
    def _resolve_merge(
        self,
        conflict: Conflict,
        **kwargs: Any,
    ) -> ResolutionResult:
        """合并策略"""
        # 尝试合并所有立场
        merged: Dict[str, Any] = {}
        
        for agent_id, position in conflict.positions.items():
            if isinstance(position, dict):
                merged.update(position)
            elif isinstance(position, list):
                if "merged_list" not in merged:
                    merged["merged_list"] = []
                merged["merged_list"].extend(position)
            else:
                merged[agent_id] = position
        
        result = ResolutionResult(
            success=True,
            conflict_id=conflict.conflict_id,
            strategy=ResolutionStrategy.MERGE,
            resolution=merged,
            affected_agents=conflict.involved_agents,
            metadata={"merged": True},
        )
        
        return result
    
    def get_conflict(self, conflict_id: str) -> Optional[Conflict]:
        """获取冲突对象"""
        return self._conflicts.get(conflict_id)
    
    def get_pending_conflicts(self) -> List[Conflict]:
        """获取待解决的冲突"""
        return [c for c in self._conflicts.values() if not c.is_resolved]
    
    def get_conflicts_by_agent(self, agent_id: str) -> List[Conflict]:
        """获取涉及指定 Agent 的冲突"""
        return [c for c in self._conflicts.values() if agent_id in c.involved_agents]
    
    def get_conflicts_by_type(self, conflict_type: ConflictType) -> List[Conflict]:
        """获取指定类型的冲突"""
        return [c for c in self._conflicts.values() if c.conflict_type == conflict_type]
    
    def register_callback(
        self,
        event: str,
        callback: Callable[..., None],
    ) -> None:
        """注册回调"""
        if event == "conflict_detected":
            self._on_conflict_detected.append(callback)
        elif event == "conflict_resolved":
            self._on_conflict_resolved.append(callback)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_conflicts": len(self._conflicts),
            "pending_conflicts": len(self.get_pending_conflicts()),
            "resolved_conflicts": len(self._resolved_history),
            "by_type": {
                ctype.value: len(self.get_conflicts_by_type(ctype))
                for ctype in ConflictType
            },
        }
