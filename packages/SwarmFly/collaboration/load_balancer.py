"""
负载均衡器

管理 Agent 的负载并进行智能任务分配
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import threading


class LoadMetric(Enum):
    """负载指标枚举"""
    CPU = "cpu"
    MEMORY = "memory"
    TASKS = "tasks"
    LATENCY = "latency"
    CUSTOM = "custom"


class BalancingStrategy(Enum):
    """负载均衡策略枚举"""
    LEAST_LOADED = "least_loaded"       # 最低负载
    ROUND_ROBIN = "round_robin"          # 轮询
    WEIGHTED = "weighted"               # 加权
    THROTTLING = "throttling"            # 限流
    ADAPTIVE = "adaptive"               # 自适应


@dataclass
class AgentLoad:
    """
    Agent 负载信息
    
    记录 Agent 的各项负载指标
    """
    agent_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 基础指标
    cpu_usage: float = 0.0      # CPU 使用率 0-100
    memory_usage: float = 0.0  # 内存使用率 0-100
    task_count: int = 0        # 当前任务数
    
    # 性能指标
    avg_response_time: float = 0.0  # 平均响应时间（毫秒）
    error_rate: float = 0.0         # 错误率 0-1
    
    # 自定义指标
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    # 权重（用于加权负载均衡）
    weight: float = 1.0
    
    @property
    def total_load(self) -> float:
        """
        计算综合负载分数
        
        Returns:
            float: 负载分数（越高表示越繁忙）
        """
        cpu_factor = self.cpu_usage / 100 * 0.3
        memory_factor = self.memory_usage / 100 * 0.2
        task_factor = min(self.task_count / 10, 1.0) * 0.3
        latency_factor = min(self.avg_response_time / 1000, 1.0) * 0.2
        
        return (cpu_factor + memory_factor + task_factor + latency_factor) * self.weight
    
    @property
    def normalized_load(self) -> float:
        """
        获取归一化负载分数
        
        Returns:
            float: 0-1 之间的负载分数
        """
        return min(max(self.total_load, 0.0), 1.0)
    
    def get_metric(self, metric: LoadMetric) -> float:
        """
        获取指定指标值
        
        Args:
            metric: 负载指标类型
            
        Returns:
            float: 指标值
        """
        if metric == LoadMetric.CPU:
            return self.cpu_usage
        elif metric == LoadMetric.MEMORY:
            return self.memory_usage
        elif metric == LoadMetric.TASKS:
            return float(self.task_count)
        elif metric == LoadMetric.LATENCY:
            return self.avg_response_time
        elif metric == LoadMetric.CUSTOM:
            return self.total_load
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "task_count": self.task_count,
            "avg_response_time": self.avg_response_time,
            "error_rate": self.error_rate,
            "weight": self.weight,
            "total_load": self.total_load,
            "normalized_load": self.normalized_load,
            "custom_metrics": self.custom_metrics,
        }


@dataclass
class LoadBalancer:
    """
    负载均衡器
    
    监控 Agent 负载并提供智能分配建议
    """
    
    strategy: BalancingStrategy = BalancingStrategy.LEAST_LOADED
    capacity_threshold: float = 0.9  # 容量阈值
    
    def __post_init__(self):
        """初始化后处理"""
        self._agent_loads: Dict[str, AgentLoad] = {}
        self._load_history: Dict[str, List[AgentLoad]] = {}  # agent_id -> 历史记录
        self._lock = threading.RLock()
        self._max_history = 100  # 最大历史记录数
        
        # 回调
        self._on_overloaded: List[Callable[[str, AgentLoad], None]] = []
        self._on_underloaded: List[Callable[[str, AgentLoad], None]] = []
    
    @property
    def agent_count(self) -> int:
        """获取监控的 Agent 数量"""
        return len(self._agent_loads)
    
    @property
    def overloaded_agents(self) -> List[str]:
        """获取过载的 Agent ID 列表"""
        return [
            agent_id for agent_id, load in self._agent_loads.items()
            if load.normalized_load >= self.capacity_threshold
        ]
    
    @property
    def underloaded_agents(self) -> List[str]:
        """获取低负载的 Agent ID 列表"""
        return [
            agent_id for agent_id, load in self._agent_loads.items()
            if load.normalized_load < 0.3
        ]
    
    def register_agent(
        self,
        agent_id: str,
        weight: float = 1.0,
    ) -> AgentLoad:
        """
        注册 Agent
        
        Args:
            agent_id: Agent ID
            weight: Agent 权重
            
        Returns:
            AgentLoad: 初始负载信息
        """
        with self._lock:
            load = AgentLoad(agent_id=agent_id, weight=weight)
            self._agent_loads[agent_id] = load
            self._load_history[agent_id] = [load]
            return load
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        注销 Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            if agent_id in self._agent_loads:
                del self._agent_loads[agent_id]
                self._load_history.pop(agent_id, None)
                return True
            return False
    
    def update_load(
        self,
        agent_id: str,
        cpu_usage: Optional[float] = None,
        memory_usage: Optional[float] = None,
        task_count: Optional[int] = None,
        avg_response_time: Optional[float] = None,
        error_rate: Optional[float] = None,
        custom_metrics: Optional[Dict[str, float]] = None,
    ) -> AgentLoad:
        """
        更新 Agent 负载信息
        
        Args:
            agent_id: Agent ID
            cpu_usage: CPU 使用率
            memory_usage: 内存使用率
            task_count: 任务数量
            avg_response_time: 平均响应时间
            error_rate: 错误率
            custom_metrics: 自定义指标
            
        Returns:
            AgentLoad: 更新后的负载信息
        """
        with self._lock:
            if agent_id not in self._agent_loads:
                self.register_agent(agent_id)
            
            load = self._agent_loads[agent_id]
            prev_load = load.normalized_load
            
            # 更新指标
            if cpu_usage is not None:
                load.cpu_usage = cpu_usage
            if memory_usage is not None:
                load.memory_usage = memory_usage
            if task_count is not None:
                load.task_count = task_count
            if avg_response_time is not None:
                load.avg_response_time = avg_response_time
            if error_rate is not None:
                load.error_rate = error_rate
            if custom_metrics:
                load.custom_metrics.update(custom_metrics)
            
            load.timestamp = datetime.now()
            
            # 记录历史
            if agent_id in self._load_history:
                self._load_history[agent_id].append(load)
                # 限制历史长度
                if len(self._load_history[agent_id]) > self._max_history:
                    self._load_history[agent_id].pop(0)
            
            # 检查过载/低载状态变化
            curr_load = load.normalized_load
            if prev_load < self.capacity_threshold and curr_load >= self.capacity_threshold:
                self._trigger_callbacks(self._on_overloaded, agent_id, load)
            elif prev_load >= 0.3 and curr_load < 0.3:
                self._trigger_callbacks(self._on_underloaded, agent_id, load)
            
            return load
    
    def increment_task(self, agent_id: str) -> None:
        """
        增加 Agent 任务计数
        
        Args:
            agent_id: Agent ID
        """
        if agent_id in self._agent_loads:
            self._agent_loads[agent_id].task_count += 1
    
    def decrement_task(self, agent_id: str) -> None:
        """
        减少 Agent 任务计数
        
        Args:
            agent_id: Agent ID
        """
        if agent_id in self._agent_loads:
            self._agent_loads[agent_id].task_count = max(
                0, self._agent_loads[agent_id].task_count - 1
            )
    
    def get_load(self, agent_id: str) -> Optional[AgentLoad]:
        """
        获取 Agent 负载信息
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Optional[AgentLoad]: 负载信息
        """
        return self._agent_loads.get(agent_id)
    
    def get_least_loaded_agent(
        self,
        exclude_agents: Optional[List[str]] = None,
        min_capacity: float = 1.0,
    ) -> Optional[str]:
        """
        获取负载最低的 Agent
        
        Args:
            exclude_agents: 排除的 Agent 列表
            min_capacity: 最小剩余容量
            
        Returns:
            Optional[str]: Agent ID
        """
        with self._lock:
            candidates = [
                (agent_id, load)
                for agent_id, load in self._agent_loads.items()
                if (exclude_agents is None or agent_id not in exclude_agents)
                and load.normalized_load < min_capacity
            ]
            
            if not candidates:
                return None
            
            # 返回负载最低的
            return min(candidates, key=lambda x: x[1].normalized_load)[0]
    
    def select_agent(
        self,
        exclude_agents: Optional[List[str]] = None,
        preferred_agents: Optional[List[str]] = None,
        required_capacity: float = 1.0,
    ) -> Optional[str]:
        """
        根据策略选择最佳 Agent
        
        Args:
            exclude_agents: 排除的 Agent
            preferred_agents: 优先选择的 Agent
            required_capacity: 最低剩余容量
            
        Returns:
            Optional[str]: 选中的 Agent ID
        """
        with self._lock:
            if self.strategy == BalancingStrategy.LEAST_LOADED:
                return self.get_least_loaded_agent(
                    exclude_agents=exclude_agents,
                    min_capacity=required_capacity,
                )
            
            elif self.strategy == BalancingStrategy.ROUND_ROBIN:
                return self._round_robin_select(
                    exclude_agents=exclude_agents,
                    min_capacity=required_capacity,
                )
            
            elif self.strategy == BalancingStrategy.WEIGHTED:
                return self._weighted_select(
                    exclude_agents=exclude_agents,
                    preferred_agents=preferred_agents,
                    min_capacity=required_capacity,
                )
            
            elif self.strategy == BalancingStrategy.ADAPTIVE:
                return self._adaptive_select(
                    exclude_agents=exclude_agents,
                    preferred_agents=preferred_agents,
                    min_capacity=required_capacity,
                )
            
            return None
    
    def _round_robin_select(
        self,
        exclude_agents: List[str],
        min_capacity: float,
    ) -> Optional[str]:
        """轮询选择"""
        candidates = [
            agent_id for agent_id, load in self._agent_loads.items()
            if (exclude_agents is None or agent_id not in exclude_agents)
            and load.normalized_load < min_capacity
        ]
        
        if not candidates:
            return None
        
        # 简单的轮询实现：选择任务最少的
        return min(candidates, key=lambda a: self._agent_loads[a].task_count)
    
    def _weighted_select(
        self,
        exclude_agents: List[str],
        preferred_agents: List[str],
        min_capacity: float,
    ) -> Optional[str]:
        """加权选择"""
        candidates = [
            (agent_id, load)
            for agent_id, load in self._agent_loads.items()
            if (exclude_agents is None or agent_id not in exclude_agents)
            and load.normalized_load < min_capacity
        ]
        
        if not candidates:
            return None
        
        # 优先考虑 preferred_agents
        for agent_id, _ in candidates:
            if preferred_agents and agent_id in preferred_agents:
                return agent_id
        
        # 否则按加权负载选择
        return min(candidates, key=lambda x: x[1].normalized_load / x[1].weight)[0]
    
    def _adaptive_select(
        self,
        exclude_agents: List[str],
        preferred_agents: List[str],
        min_capacity: float,
    ) -> Optional[str]:
        """自适应选择 - 根据历史表现动态调整"""
        candidates = [
            (agent_id, load, self._get_trend_score(agent_id))
            for agent_id, load in self._agent_loads.items()
            if (exclude_agents is None or agent_id not in exclude_agents)
            and load.normalized_load < min_capacity
        ]
        
        if not candidates:
            return None
        
        # 优先考虑性能趋势好的
        candidates.sort(key=lambda x: x[2])  # 按趋势分数排序
        
        if preferred_agents:
            for agent_id, _, _ in candidates:
                if agent_id in preferred_agents:
                    return agent_id
        
        return candidates[0][0]
    
    def _get_trend_score(self, agent_id: str) -> float:
        """获取 Agent 的性能趋势分数"""
        history = self._load_history.get(agent_id, [])
        if len(history) < 2:
            return 0.0
        
        # 计算负载趋势
        recent = history[-5:] if len(history) >= 5 else history
        if len(recent) < 2:
            return 0.0
        
        # 简单的趋势计算：平均负载变化
        avg_load = sum(h.total_load for h in recent) / len(recent)
        return avg_load
    
    def get_load_distribution(self) -> Dict[str, float]:
        """获取负载分布"""
        return {
            agent_id: load.normalized_load
            for agent_id, load in self._agent_loads.items()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取负载统计信息"""
        if not self._agent_loads:
            return {
                "agent_count": 0,
                "avg_load": 0.0,
                "max_load": 0.0,
                "min_load": 0.0,
                "overloaded_count": 0,
                "underloaded_count": 0,
            }
        
        loads = [l.normalized_load for l in self._agent_loads.values()]
        
        return {
            "agent_count": len(self._agent_loads),
            "avg_load": sum(loads) / len(loads),
            "max_load": max(loads),
            "min_load": min(loads),
            "overloaded_count": len(self.overloaded_agents),
            "underloaded_count": len(self.underloaded_agents),
        }
    
    def register_callback(
        self,
        event: str,
        callback: Callable[..., None],
    ) -> None:
        """注册回调"""
        if event == "overloaded":
            self._on_overloaded.append(callback)
        elif event == "underloaded":
            self._on_underloaded.append(callback)
    
    def _trigger_callbacks(
        self,
        callbacks: List[Callable[..., None]],
        *args: Any,
    ) -> None:
        """触发回调"""
        for callback in callbacks:
            try:
                callback(*args)
            except Exception:
                pass
