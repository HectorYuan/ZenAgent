"""
优先级管理器 (Priority Manager)

管理智能体的优先级计算、动态调整和竞争解决。
支持多种优先级算法和实时优先级更新。
"""

import time
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class PriorityLevel(Enum):
    """优先级级别"""
    CRITICAL = 100  # 核心任务
    URGENT = 80     # 紧急任务
    HIGH = 60       # 高优先级
    NORMAL = 50     # 普通任务
    LOW = 20        # 低优先级
    BACKGROUND = 10 # 后台任务


@dataclass
class PriorityScore:
    """优先级评分"""
    total_score: float
    components: Dict[str, float] = field(default_factory=dict)
    level: PriorityLevel = PriorityLevel.NORMAL
    calculated_at: datetime = field(default_factory=datetime.now)
    
    def __lt__(self, other):
        return self.total_score < other.total_score
    
    def __gt__(self, other):
        return self.total_score > other.total_score


@dataclass
class AgentPriority:
    """智能体优先级"""
    agent_id: str
    base_priority: int = 50
    dynamic_bonus: float = 0.0
    historical_score: float = 50.0
    current_load: float = 0.0
    deadline_bonus: float = 0.0
    level: PriorityLevel = PriorityLevel.NORMAL
    
    @property
    def effective_priority(self) -> float:
        """有效优先级"""
        return self.base_priority + self.dynamic_bonus + self.deadline_bonus


class PriorityCalculator:
    """优先级计算器"""
    
    # 权重配置
    DEFAULT_WEIGHTS = {
        'base': 0.4,
        'historical': 0.25,
        'load': 0.15,
        'deadline': 0.2
    }
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._normalize_weights()
    
    def _normalize_weights(self):
        """归一化权重"""
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {
                k: v / total for k, v in self.weights.items()
            }
    
    def calculate(
        self,
        agent: 'AgentPriority',
        task_deadline: Optional[datetime] = None,
        task_importance: float = 1.0
    ) -> PriorityScore:
        """计算综合优先级"""
        
        components = {}
        
        # 1. 基础优先级得分(归一化到0-100)
        components['base'] = agent.base_priority * self.weights['base']
        
        # 2. 历史表现得分
        components['historical'] = agent.historical_score * self.weights['historical']
        
        # 3. 负载得分(负载越低得分越高)
        load_factor = max(0, 100 - agent.current_load)
        components['load'] = load_factor * self.weights['load']
        
        # 4. 截止时间得分
        deadline_score = 0.0
        if task_deadline:
            time_until_deadline = (task_deadline - datetime.now()).total_seconds()
            
            if time_until_deadline < 0:
                # 已超时，给予最高分
                deadline_score = 100 * self.weights['deadline']
            elif time_until_deadline < 300:  # 5分钟内
                deadline_score = 80 * self.weights['deadline']
            elif time_until_deadline < 1800:  # 30分钟内
                deadline_score = 60 * self.weights['deadline']
            else:
                deadline_score = 40 * self.weights['deadline']
        
        components['deadline'] = deadline_score
        
        # 5. 任务重要性调整
        importance_factor = max(0.5, min(2.0, task_importance))
        
        # 计算总分
        total_score = sum(components.values()) * importance_factor
        
        # 确定优先级级别
        level = self._score_to_level(total_score)
        
        return PriorityScore(
            total_score=min(100, total_score),
            components=components,
            level=level
        )
    
    def _score_to_level(self, score: float) -> PriorityLevel:
        """分数转级别"""
        if score >= 90:
            return PriorityLevel.CRITICAL
        elif score >= 70:
            return PriorityLevel.URGENT
        elif score >= 55:
            return PriorityLevel.HIGH
        elif score >= 40:
            return PriorityLevel.NORMAL
        elif score >= 20:
            return PriorityLevel.LOW
        else:
            return PriorityLevel.BACKGROUND


class PriorityManager:
    """
    优先级管理器
    
    管理智能体和任务的优先级:
    - 优先级计算与评估
    - 动态优先级调整
    - 优先级继承
    - 竞争解决
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 优先级计算器
        self.calculator = PriorityCalculator(
            self.config.get('weights')
        )
        
        # 智能体优先级存储
        self.agent_priorities: Dict[str, AgentPriority] = {}
        
        # 优先级历史记录
        self.priority_history: Dict[str, List[PriorityScore]] = defaultdict(list)
        
        # 优先级变更回调
        self.on_priority_change: List[Callable] = []
        
        # 统计
        self.stats = {
            'total_calculations': 0,
            'dynamic_adjustments': 0,
            'contests_resolved': 0
        }
    
    def register_agent(self, agent_id: str, base_priority: int = 50):
        """注册智能体"""
        if agent_id not in self.agent_priorities:
            self.agent_priorities[agent_id] = AgentPriority(
                agent_id=agent_id,
                base_priority=base_priority
            )
            logger.info(f"Agent registered: {agent_id} with priority {base_priority}")
    
    def unregister_agent(self, agent_id: str):
        """注销智能体"""
        if agent_id in self.agent_priorities:
            del self.agent_priorities[agent_id]
            logger.info(f"Agent unregistered: {agent_id}")
    
    def update_base_priority(self, agent_id: str, base_priority: int):
        """更新基础优先级"""
        if agent_id in self.agent_priorities:
            self.agent_priorities[agent_id].base_priority = base_priority
            self._trigger_priority_change(agent_id)
    
    def update_historical_score(self, agent_id: str, success_rate: float, avg_quality: float):
        """
        更新历史表现评分
        
        基于成功率和质量更新历史评分
        """
        if agent_id not in self.agent_priorities:
            return
        
        agent = self.agent_priorities[agent_id]
        
        # 计算新评分 (成功率和质量的加权平均)
        new_score = (success_rate * 0.6 + avg_quality * 0.4) * 100
        
        # 指数移动平均
        alpha = 0.3  # 新数据权重
        agent.historical_score = alpha * new_score + (1 - alpha) * agent.historical_score
        
        self._trigger_priority_change(agent_id)
    
    def update_load(self, agent_id: str, current_load: float):
        """更新当前负载"""
        if agent_id in self.agent_priorities:
            self.agent_priorities[agent_id].current_load = current_load
    
    def get_priority(
        self,
        agent_id: str,
        task_deadline: Optional[datetime] = None,
        task_importance: float = 1.0
    ) -> PriorityScore:
        """获取智能体优先级评分"""
        if agent_id not in self.agent_priorities:
            # 自动注册
            self.register_agent(agent_id)
        
        agent = self.agent_priorities[agent_id]
        score = self.calculator.calculate(agent, task_deadline, task_importance)
        
        # 记录历史
        self.priority_history[agent_id].append(score)
        if len(self.priority_history[agent_id]) > 100:
            self.priority_history[agent_id] = self.priority_history[agent_id][-100:]
        
        self.stats['total_calculations'] += 1
        
        return score
    
    def resolve_contest(
        self,
        contestants: List[str],
        resource: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        解决竞争
        
        在多个智能体竞争同一资源时，决定获胜者
        
        Args:
            contestants: 竞争者ID列表
            resource: 竞争的资源
            context: 额外上下文
            
        Returns:
            获胜者ID，无获胜者则返回None
        """
        if not contestants:
            return None
        
        if len(contestants) == 1:
            return contestants[0]
        
        context = context or {}
        
        # 计算每个竞争者的优先级
        scores = []
        for agent_id in contestants:
            score = self.get_priority(
                agent_id,
                context.get('deadline'),
                context.get('importance', 1.0)
            )
            scores.append((agent_id, score))
        
        # 按优先级排序
        scores.sort(key=lambda x: x[1].total_score, reverse=True)
        
        winner_id = scores[0][0]
        
        self.stats['contests_resolved'] += 1
        
        logger.info(
            f"Contest resolved: {winner_id} won over {[c for c,_ in scores[1:]]} "
            f"(score: {scores[0][1].total_score:.2f})"
        )
        
        return winner_id
    
    def resolve_contest_with_tiebreaker(
        self,
        contestants: List[str],
        tiebreaker: str = 'historical'
    ) -> Optional[str]:
        """使用决胜规则解决平局"""
        if not contestants:
            return None
        
        if len(contestants) == 1:
            return contestants[0]
        
        # 初步评分
        scores = []
        for agent_id in contestants:
            score = self.get_priority(agent_id)
            scores.append((agent_id, score.total_score))
        
        # 按分数排序
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # 检查平局
        if scores[0][1] != scores[1][1]:
            return scores[0][0]
        
        # 决胜规则
        if tiebreaker == 'historical':
            # 使用历史评分决胜
            tiebreaker_scores = [
                (agent_id, self.agent_priorities.get(agent_id, AgentPriority(agent_id='')).historical_score)
                for agent_id, _ in scores
                if agent_id in self.agent_priorities
            ]
            tiebreaker_scores.sort(key=lambda x: x[1], reverse=True)
            return tiebreaker_scores[0][0]
        
        elif tiebreaker == 'load':
            # 使用负载决胜(负载低者优先)
            load_scores = [
                (agent_id, self.agent_priorities.get(agent_id, AgentPriority(agent_id='')).current_load)
                for agent_id, _ in scores
                if agent_id in self.agent_priorities
            ]
            load_scores.sort(key=lambda x: x[1])  # 升序，低负载优先
            return load_scores[0][0]
        
        elif tiebreaker == 'random':
            import random
            return random.choice([agent for agent, _ in scores])
        
        # 默认返回最高分
        return scores[0][0]
    
    def _trigger_priority_change(self, agent_id: str):
        """触发优先级变更回调"""
        self.stats['dynamic_adjustments'] += 1
        
        for callback in self.on_priority_change:
            try:
                callback(agent_id, self.agent_priorities[agent_id])
            except Exception as e:
                logger.error(f"Priority change callback error: {e}")
    
    def get_agent_priority_level(self, agent_id: str) -> PriorityLevel:
        """获取智能体当前优先级级别"""
        score = self.get_priority(agent_id)
        return score.level
    
    def get_top_agents(self, n: int = 10) -> List[Tuple[str, PriorityScore]]:
        """获取优先级最高的N个智能体"""
        scores = []
        for agent_id in self.agent_priorities:
            score = self.get_priority(agent_id)
            scores.append((agent_id, score))
        
        scores.sort(key=lambda x: x[1].total_score, reverse=True)
        return scores[:n]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'registered_agents': len(self.agent_priorities),
            'priority_levels': {
                level.name: sum(
                    1 for a in self.agent_priorities.values()
                    if a.level == level
                )
                for level in PriorityLevel
            }
        }
