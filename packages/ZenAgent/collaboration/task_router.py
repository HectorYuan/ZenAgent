"""
任务路由
将任务智能路由到合适的 Agent
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime
import uuid

try:
    from ..mcp.registry import AgentRegistry, AgentCapability, RegisteredAgent
except ImportError:
    # 当作为顶层包导入时的回退
    from mcp.registry import AgentRegistry, AgentCapability, RegisteredAgent


class RouteStrategy(Enum):
    """路由策略枚举"""
    RANDOM = "random"              # 随机选择
    ROUND_ROBIN = "round_robin"    # 轮询
    LEAST_LOADED = "least_loaded" # 最小负载
    BEST_CAPABILITY = "best_capability"  # 最佳能力匹配
    AFFINITY = "affinity"         # 亲和性路由


@dataclass
class TaskRoute:
    """任务路由结果"""
    route_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # 路由决策
    target_agent_id: Optional[str] = None
    target_agent_ids: List[str] = field(default_factory=list)  # 多路由
    
    # 路由策略
    strategy: RouteStrategy = RouteStrategy.BEST_CAPABILITY
    
    # 路由信息
    confidence: float = 0.0  # 置信度 0.0 - 1.0
    reason: str = ""
    
    # 任务信息
    task_type: str = ""
    task_data: Dict[str, Any] = field(default_factory=dict)
    
    # 备选路由
    alternatives: List["TaskRoute"] = field(default_factory=list)
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_valid(self) -> bool:
        """路由是否有效"""
        return self.target_agent_id is not None or len(self.target_agent_ids) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "route_id": self.route_id,
            "target_agent_id": self.target_agent_id,
            "target_agent_ids": self.target_agent_ids,
            "strategy": self.strategy.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "task_type": self.task_type,
            "alternatives": [alt.to_dict() for alt in self.alternatives],
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class RoutingRule:
    """路由规则"""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    
    # 匹配条件
    task_type: Optional[str] = None
    required_capabilities: List[AgentCapability] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # 目标 Agent
    target_agent_id: Optional[str] = None
    target_category: Optional[str] = None
    
    # 路由策略
    strategy: RouteStrategy = RouteStrategy.BEST_CAPABILITY
    
    # 优先级
    priority: int = 0  # 数字越大优先级越高
    
    # 启用状态
    enabled: bool = True
    
    def matches(self, task_type: str, capabilities: List[AgentCapability], tags: List[str]) -> bool:
        """检查是否匹配"""
        # 检查任务类型
        if self.task_type and self.task_type != task_type:
            return False
        
        # 检查能力
        if self.required_capabilities:
            if not all(cap in capabilities for cap in self.required_capabilities):
                return False
        
        # 检查标签
        if self.tags:
            if not any(tag in tags for tag in self.tags):
                return False
        
        return True


@dataclass
class TaskRouter:
    """
    任务路由器
    
    智能地将任务路由到合适的 Agent
    """
    
    # Agent 注册表
    _registry: Optional[AgentRegistry] = None
    
    # 路由规则
    _rules: List[RoutingRule] = field(default_factory=list)
    
    # 路由统计
    _routing_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # 轮询索引
    _round_robin_index: Dict[str, int] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化路由器"""
        # 添加默认路由策略
        self._add_default_rules()
    
    def set_registry(self, registry: AgentRegistry) -> None:
        """设置 Agent 注册表"""
        self._registry = registry
    
    def _add_default_rules(self) -> None:
        """添加默认路由规则"""
        # 默认规则：按最佳能力匹配
        default_rule = RoutingRule(
            name="default",
            description="默认路由规则",
            strategy=RouteStrategy.BEST_CAPABILITY,
            priority=0,
        )
        self._rules.append(default_rule)
    
    def add_rule(self, rule: RoutingRule) -> None:
        """
        添加路由规则
        
        Args:
            rule: 路由规则
        """
        self._rules.append(rule)
        # 按优先级排序
        self._rules.sort(key=lambda x: x.priority, reverse=True)
    
    def remove_rule(self, rule_id: str) -> bool:
        """
        移除路由规则
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            bool: 是否成功移除
        """
        for i, rule in enumerate(self._rules):
            if rule.rule_id == rule_id:
                self._rules.pop(i)
                return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[RoutingRule]:
        """获取路由规则"""
        for rule in self._rules:
            if rule.rule_id == rule_id:
                return rule
        return None
    
    def list_rules(self) -> List[RoutingRule]:
        """列出所有规则"""
        return list(self._rules)
    
    def route(
        self,
        task_type: str,
        required_capabilities: Optional[List[AgentCapability]] = None,
        tags: Optional[List[str]] = None,
        task_data: Optional[Dict[str, Any]] = None,
        strategy: Optional[RouteStrategy] = None,
        allow_multi: bool = False,
    ) -> TaskRoute:
        """
        路由任务
        
        Args:
            task_type: 任务类型
            required_capabilities: 必需的能力
            tags: 标签筛选
            task_data: 任务数据
            strategy: 路由策略（可选）
            allow_multi: 是否允许多路由
            
        Returns:
            TaskRoute: 路由结果
        """
        if self._registry is None:
            return TaskRoute(
                task_type=task_type,
                reason="Agent registry not configured",
            )
        
        # 转换为 AgentCapability 枚举
        capabilities = required_capabilities or []
        capability_enums = []
        for cap in capabilities:
            if isinstance(cap, str):
                try:
                    capability_enums.append(AgentCapability(cap))
                except ValueError:
                    pass
            else:
                capability_enums.append(cap)
        
        # 查找匹配的规则
        matched_rule = None
        for rule in self._rules:
            if not rule.enabled:
                continue
            if rule.matches(task_type, capability_enums, tags or []):
                matched_rule = rule
                break
        
        # 确定路由策略
        route_strategy = strategy or (
            matched_rule.strategy if matched_rule else RouteStrategy.BEST_CAPABILITY
        )
        
        # 执行路由
        if matched_rule and matched_rule.target_agent_id:
            # 规则指定了目标
            route = TaskRoute(
                target_agent_id=matched_rule.target_agent_id,
                strategy=route_strategy,
                confidence=1.0,
                reason=f"Matched rule: {matched_rule.name}",
                task_type=task_type,
                task_data=task_data or {},
            )
        else:
            # 使用策略选择
            route = self._route_by_strategy(
                task_type=task_type,
                capabilities=capability_enums,
                tags=tags or [],
                strategy=route_strategy,
                allow_multi=allow_multi,
                task_data=task_data,
            )
        
        # 记录统计
        self._record_routing(route)
        
        return route
    
    def _route_by_strategy(
        self,
        task_type: str,
        capabilities: List[AgentCapability],
        tags: List[str],
        strategy: RouteStrategy,
        allow_multi: bool,
        task_data: Optional[Dict[str, Any]],
    ) -> TaskRoute:
        """根据策略路由"""
        if self._registry is None:
            return TaskRoute(task_type=task_type, reason="No registry")
        
        # 获取可用 Agent
        available_agents = self._registry.list_available()
        
        if not available_agents:
            return TaskRoute(
                task_type=task_type,
                reason="No available agents",
            )
        
        # 按策略选择
        if strategy == RouteStrategy.RANDOM:
            import random
            agent = random.choice(available_agents)
            return TaskRoute(
                target_agent_id=agent.metadata.agent_id,
                strategy=strategy,
                confidence=1.0 / len(available_agents),
                reason="Random selection",
                task_type=task_type,
                task_data=task_data or {},
            )
        
        elif strategy == RouteStrategy.ROUND_ROBIN:
            # 轮询选择
            category = "default"
            if self._round_robin_index.get(category, 0) >= len(available_agents):
                self._round_robin_index[category] = 0
            agent = available_agents[self._round_robin_index[category]]
            self._round_robin_index[category] += 1
            return TaskRoute(
                target_agent_id=agent.metadata.agent_id,
                strategy=strategy,
                confidence=1.0,
                reason="Round robin selection",
                task_type=task_type,
                task_data=task_data or {},
            )
        
        elif strategy == RouteStrategy.LEAST_LOADED:
            # 最小负载
            available_agents.sort(
                key=lambda a: a.current_tasks / a.metadata.max_concurrent_tasks
            )
            agent = available_agents[0]
            load = agent.current_tasks / agent.metadata.max_concurrent_tasks
            return TaskRoute(
                target_agent_id=agent.metadata.agent_id,
                strategy=strategy,
                confidence=1.0 - load,
                reason="Least loaded selection",
                task_type=task_type,
                task_data=task_data or {},
            )
        
        elif strategy == RouteStrategy.BEST_CAPABILITY:
            # 最佳能力匹配
            if not capabilities:
                # 无特定能力要求，选择最空闲的
                available_agents.sort(
                    key=lambda a: a.current_tasks / a.metadata.max_concurrent_tasks
                )
                agent = available_agents[0]
                return TaskRoute(
                    target_agent_id=agent.metadata.agent_id,
                    strategy=strategy,
                    confidence=0.5,
                    reason="No specific capabilities required",
                    task_type=task_type,
                    task_data=task_data or {},
                )
            
            # 按能力匹配度排序
            scored_agents = []
            for agent in available_agents:
                agent_caps = set(agent.metadata.capabilities)
                required = set(capabilities)
                matched = len(agent_caps & required)
                total = len(required)
                score = matched / total if total > 0 else 0.0
                scored_agents.append((agent, score))
            
            scored_agents.sort(key=lambda x: x[1], reverse=True)
            
            if scored_agents:
                agent, score = scored_agents[0]
                alternatives = []
                
                # 生成备选路由
                if allow_multi and len(scored_agents) > 1:
                    for alt_agent, alt_score in scored_agents[1:3]:
                        alternatives.append(TaskRoute(
                            target_agent_id=alt_agent.metadata.agent_id,
                            strategy=strategy,
                            confidence=alt_score,
                            reason="Alternative capability match",
                            task_type=task_type,
                        ))
                
                return TaskRoute(
                    target_agent_id=agent.metadata.agent_id,
                    strategy=strategy,
                    confidence=score,
                    reason=f"Best capability match ({score:.2f})",
                    task_type=task_type,
                    task_data=task_data or {},
                    alternatives=alternatives,
                )
        
        # 默认返回第一个可用
        return TaskRoute(
            target_agent_id=available_agents[0].metadata.agent_id,
            strategy=strategy,
            confidence=0.3,
            reason="Default fallback",
            task_type=task_type,
            task_data=task_data or {},
        )
    
    def _record_routing(self, route: TaskRoute) -> None:
        """记录路由统计"""
        agent_id = route.target_agent_id
        if agent_id is None:
            return
        
        if agent_id not in self._routing_stats:
            self._routing_stats[agent_id] = {
                "total_routes": 0,
                "successful_routes": 0,
                "failed_routes": 0,
            }
        
        stats = self._routing_stats[agent_id]
        stats["total_routes"] += 1
    
    def record_success(self, agent_id: str) -> None:
        """记录成功路由"""
        if agent_id in self._routing_stats:
            self._routing_stats[agent_id]["successful_routes"] += 1
    
    def record_failure(self, agent_id: str) -> None:
        """记录失败路由"""
        if agent_id in self._routing_stats:
            self._routing_stats[agent_id]["failed_routes"] += 1
    
    def get_stats(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取路由统计
        
        Args:
            agent_id: Agent ID（可选）
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        if agent_id:
            return self._routing_stats.get(agent_id, {})
        
        total_routes = sum(s["total_routes"] for s in self._routing_stats.values())
        successful = sum(s["successful_routes"] for s in self._routing_stats.values())
        failed = sum(s["failed_routes"] for s in self._routing_stats.values())
        
        return {
            "total_routes": total_routes,
            "successful_routes": successful,
            "failed_routes": failed,
            "success_rate": successful / total_routes if total_routes > 0 else 0.0,
            "agent_stats": self._routing_stats,
        }


# 全局路由器实例
_default_router: Optional[TaskRouter] = None


def get_router() -> TaskRouter:
    """获取全局路由器"""
    global _default_router
    if _default_router is None:
        _default_router = TaskRouter()
    return _default_router
