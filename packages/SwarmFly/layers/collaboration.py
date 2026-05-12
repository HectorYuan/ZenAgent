# 智能体协作框架
"""
AgentCollaboration - 智能体协作框架

提供任务分发、结果聚合和冲突解决机制
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime
from enum import Enum
import logging
import heapq

logger = logging.getLogger(__name__)


class ConflictResolutionStrategy(Enum):
    """冲突解决策略"""
    PRIORITY_BASED = "priority_based"         # 基于优先级
    CAPABILITY_BASED = "capability_based"     # 基于能力
    LOAD_BALANCED = "load_balanced"          # 负载均衡
    ROUND_ROBIN = "round_robin"               # 轮询
    FIRST_COME_FIRST_SERVE = "fcfs"           # 先到先服务


class TaskDistributionStrategy(Enum):
    """任务分发策略"""
    RANDOM = "random"
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    CAPABILITY_MATCH = "capability_match"
    AFFINITY_BASED = "affinity_based"


class TaskDistributor:
    """任务分发器"""
    
    def __init__(self, strategy: TaskDistributionStrategy = TaskDistributionStrategy.LEAST_LOADED):
        self.strategy = strategy
        self.round_robin_index: Dict[str, int] = {}  # team_id -> index
        self.load_scores: Dict[str, float] = {}      # agent_id -> load score
    
    def distribute(self, task: Dict, agents: List[Dict]) -> Optional[str]:
        """分发任务到最佳智能体"""
        if not agents:
            return None
        
        if self.strategy == TaskDistributionStrategy.RANDOM:
            return self._distribute_random(agents)
        elif self.strategy == TaskDistributionStrategy.ROUND_ROBIN:
            return self._distribute_round_robin(task, agents)
        elif self.strategy == TaskDistributionStrategy.LEAST_LOADED:
            return self._distribute_least_loaded(agents)
        elif self.strategy == TaskDistributionStrategy.CAPABILITY_MATCH:
            return self._distribute_capability_match(task, agents)
        elif self.strategy == TaskDistributionStrategy.AFFINITY_BASED:
            return self._distribute_affinity_based(task, agents)
        else:
            return self._distribute_least_loaded(agents)
    
    def _distribute_random(self, agents: List[Dict]) -> str:
        """随机分发"""
        import random
        return random.choice(agents)["agent_id"]
    
    def _distribute_round_robin(self, task: Dict, agents: List[Dict]) -> str:
        """轮询分发"""
        team_id = task.get("team_id", "default")
        
        if team_id not in self.round_robin_index:
            self.round_robin_index[team_id] = 0
        
        index = self.round_robin_index[team_id]
        selected = agents[index % len(agents)]
        
        self.round_robin_index[team_id] = index + 1
        
        return selected["agent_id"]
    
    def _distribute_least_loaded(self, agents: List[Dict]) -> str:
        """最少负载分发"""
        # 计算负载分数
        for agent in agents:
            agent_id = agent["agent_id"]
            current_load = self.load_scores.get(agent_id, 0)
            
            # 基于状态和当前任务计算负载
            if agent.get("status") == "busy":
                current_load += 10
            if agent.get("current_task"):
                current_load += 5
            
            self.load_scores[agent_id] = current_load
        
        # 选择负载最低的
        min_load_agent = min(agents, key=lambda a: self.load_scores.get(a["agent_id"], 0))
        
        return min_load_agent["agent_id"]
    
    def _distribute_capability_match(self, task: Dict, agents: List[Dict]) -> str:
        """能力匹配分发"""
        required_skills = set(task.get("required_skills", []))
        
        if not required_skills:
            return self._distribute_least_loaded(agents)
        
        # 计算每个智能体的匹配度
        scored_agents = []
        for agent in agents:
            agent_skills = set(agent.get("skills", []))
            match_count = len(required_skills & agent_skills)
            
            if match_count > 0:
                match_score = match_count / len(required_skills)
                scored_agents.append((agent, match_score))
        
        if not scored_agents:
            return self._distribute_least_loaded(agents)
        
        # 按匹配度排序
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        
        # 从最高匹配度中选择负载最低的
        best_agents = [a for a, score in scored_agents if score == scored_agents[0][1]]
        
        return self._distribute_least_loaded(best_agents)
    
    def _distribute_affinity_based(self, task: Dict, agents: List[Dict]) -> str:
        """亲和性分发"""
        # 优先选择之前处理过类似任务的智能体
        task_type = task.get("type", "")
        
        affinity_agents = [
            a for a in agents 
            if task_type in a.get("affinity_tasks", [])
        ]
        
        if affinity_agents:
            return self._distribute_least_loaded(affinity_agents)
        
        return self._distribute_least_loaded(agents)
    
    def update_load(self, agent_id: str, delta: float):
        """更新负载分数"""
        self.load_scores[agent_id] = self.load_scores.get(agent_id, 0) + delta


class ResultAggregator:
    """结果聚合器"""
    
    def __init__(self):
        self.aggregation_strategies: Dict[str, Callable] = {
            "merge": self._merge_results,
            "concatenate": self._concatenate_results,
            "summarize": self._summarize_results,
            "average": self._average_results,
            "vote": self._vote_results,
            "weighted": self._weighted_results
        }
    
    def aggregate(self, results: List[Dict], strategy: str = "merge", **kwargs) -> Dict:
        """聚合结果"""
        strategy_func = self.aggregation_strategies.get(strategy, self._merge_results)
        return strategy_func(results, **kwargs)
    
    def _merge_results(self, results: List[Dict], **kwargs) -> Dict:
        """合并结果"""
        merged = {}
        
        for result in results:
            if isinstance(result, dict):
                merged.update(result)
        
        return {
            "status": "success",
            "strategy": "merge",
            "aggregated": merged,
            "count": len(results)
        }
    
    def _concatenate_results(self, results: List[Dict], **kwargs) -> Dict:
        """连接结果"""
        concatenated = []
        
        for result in results:
            if isinstance(result, dict):
                concatenated.append(result)
            elif isinstance(result, list):
                concatenated.extend(result)
            else:
                concatenated.append(result)
        
        return {
            "status": "success",
            "strategy": "concatenate",
            "aggregated": concatenated,
            "count": len(results)
        }
    
    def _summarize_results(self, results: List[Dict], **kwargs) -> Dict:
        """摘要结果"""
        summary = {
            "total_count": len(results),
            "success_count": sum(1 for r in results if r.get("status") == "success"),
            "failed_count": sum(1 for r in results if r.get("status") == "error"),
            "key_findings": [],
            "recommendations": []
        }
        
        # 提取关键发现和建议
        for result in results:
            if isinstance(result, dict):
                if "finding" in result:
                    summary["key_findings"].append(result["finding"])
                if "recommendation" in result:
                    summary["recommendations"].append(result["recommendation"])
        
        return {
            "status": "success",
            "strategy": "summarize",
            "aggregated": summary,
            "count": len(results)
        }
    
    def _average_results(self, results: List[Dict], **kwargs) -> Dict:
        """平均结果"""
        numeric_values = []
        
        for result in results:
            if isinstance(result, dict) and "value" in result:
                try:
                    numeric_values.append(float(result["value"]))
                except (ValueError, TypeError):
                    pass
        
        if not numeric_values:
            return {
                "status": "success",
                "strategy": "average",
                "aggregated": {"message": "No numeric values to average"},
                "count": len(results)
            }
        
        avg = sum(numeric_values) / len(numeric_values)
        
        return {
            "status": "success",
            "strategy": "average",
            "aggregated": {
                "average": avg,
                "min": min(numeric_values),
                "max": max(numeric_values),
                "count": len(numeric_values)
            },
            "count": len(results)
        }
    
    def _vote_results(self, results: List[Dict], **kwargs) -> Dict:
        """投票结果"""
        votes: Dict[str, int] = {}
        
        for result in results:
            if isinstance(result, dict) and "vote" in result:
                vote = str(result["vote"])
                votes[vote] = votes.get(vote, 0) + 1
        
        if not votes:
            return {
                "status": "success",
                "strategy": "vote",
                "aggregated": {"message": "No votes recorded"},
                "count": len(results)
            }
        
        winner = max(votes.items(), key=lambda x: x[1])
        
        return {
            "status": "success",
            "strategy": "vote",
            "aggregated": {
                "winner": winner[0],
                "votes": winner[1],
                "total_votes": len(results),
                "all_votes": votes
            },
            "count": len(results)
        }
    
    def _weighted_results(self, results: List[Dict], **kwargs) -> Dict:
        """加权结果"""
        weights = kwargs.get("weights", {})
        weighted_sum = 0.0
        total_weight = 0.0
        
        for i, result in enumerate(results):
            weight = weights.get(i, 1.0)
            
            if isinstance(result, dict) and "value" in result:
                try:
                    value = float(result["value"])
                    weighted_sum += value * weight
                    total_weight += weight
                except (ValueError, TypeError):
                    pass
        
        if total_weight == 0:
            return {
                "status": "success",
                "strategy": "weighted",
                "aggregated": {"message": "No weighted values"},
                "count": len(results)
            }
        
        weighted_avg = weighted_sum / total_weight
        
        return {
            "status": "success",
            "strategy": "weighted",
            "aggregated": {
                "weighted_average": weighted_avg,
                "total_weight": total_weight
            },
            "count": len(results)
        }


class ConflictResolver:
    """冲突解决器"""
    
    def __init__(self, strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.PRIORITY_BASED):
        self.strategy = strategy
        self.conflict_history: List[Dict] = []
    
    def resolve(self, agents: List[Dict], resource: str, context: Dict = None) -> Tuple[Optional[str], Dict]:
        """解决冲突，返回获胜者"""
        context = context or {}
        
        if self.strategy == ConflictResolutionStrategy.PRIORITY_BASED:
            winner = self._resolve_by_priority(agents)
        elif self.strategy == ConflictResolutionStrategy.CAPABILITY_BASED:
            winner = self._resolve_by_capability(agents, context)
        elif self.strategy == ConflictResolutionStrategy.LOAD_BALANCED:
            winner = self._resolve_by_load(agents)
        elif self.strategy == ConflictResolutionStrategy.ROUND_ROBIN:
            winner = self._resolve_by_round_robin(agents, resource)
        elif self.strategy == ConflictResolutionStrategy.FIRST_COME_FIRST_SERVE:
            winner = self._resolve_by_fcfs(agents)
        else:
            winner = self._resolve_by_priority(agents)
        
        # 记录冲突历史
        self.conflict_history.append({
            "timestamp": datetime.now().isoformat(),
            "resource": resource,
            "candidates": [a["agent_id"] for a in agents],
            "winner": winner,
            "strategy": self.strategy.value
        })
        
        return winner, {
            "resource": resource,
            "winner": winner,
            "losers": [a["agent_id"] for a in agents if a["agent_id"] != winner] if winner else []
        }
    
    def _resolve_by_priority(self, agents: List[Dict]) -> Optional[str]:
        """基于优先级解决"""
        if not agents:
            return None
        
        # 检查是否有核心任务
        for agent in agents:
            if agent.get("has_core_task", False):
                return agent["agent_id"]
        
        # 按优先级排序
        sorted_agents = sorted(
            agents,
            key=lambda a: (
                a.get("priority", 5),
                a.get("metrics", {}).get("tasks_completed", 0)
            ),
            reverse=True
        )
        
        return sorted_agents[0]["agent_id"]
    
    def _resolve_by_capability(self, agents: List[Dict], context: Dict) -> Optional[str]:
        """基于能力解决"""
        if not agents:
            return None
        
        required_capabilities = context.get("required_capabilities", [])
        
        if not required_capabilities:
            return self._resolve_by_priority(agents)
        
        # 计算能力匹配度
        scored_agents = []
        for agent in agents:
            agent_capabilities = set(agent.get("capabilities", []))
            required = set(required_capabilities)
            
            if not required:
                match_score = 0
            else:
                match_score = len(agent_capabilities & required) / len(required)
            
            scored_agents.append((agent, match_score))
        
        # 选择匹配度最高的
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        best_score = scored_agents[0][1]
        
        # 如果有多个最高分，选择优先级最高的
        best_agents = [a for a, score in scored_agents if score == best_score]
        
        return self._resolve_by_priority(best_agents)
    
    def _resolve_by_load(self, agents: List[Dict]) -> Optional[str]:
        """基于负载解决"""
        if not agents:
            return None
        
        # 计算负载分数
        scored_agents = []
        for agent in agents:
            load_score = 0
            
            # 当前任务数
            if agent.get("current_task"):
                load_score += 5
            
            # 历史失败率
            metrics = agent.get("metrics", {})
            completed = metrics.get("tasks_completed", 0)
            failed = metrics.get("tasks_failed", 0)
            
            if completed > 0:
                failure_rate = failed / completed
                load_score += failure_rate * 10
            
            scored_agents.append((agent, load_score))
        
        # 选择负载最低的
        scored_agents.sort(key=lambda x: x[1])
        return scored_agents[0][agent_id]
    
    def _resolve_by_round_robin(self, agents: List[Dict], resource: str) -> Optional[str]:
        """基于轮询解决"""
        if not agents:
            return None
        
        # 简单的轮询选择
        key = f"rr_{resource}"
        if not hasattr(self, '_rr_index'):
            self._rr_index = {}
        
        current_index = self._rr_index.get(key, 0)
        winner = agents[current_index % len(agents)]["agent_id"]
        
        self._rr_index[key] = current_index + 1
        
        return winner
    
    def _resolve_by_fcfs(self, agents: List[Dict]) -> Optional[str]:
        """先到先服务"""
        if not agents:
            return None
        
        # 选择最早到达的
        sorted_agents = sorted(
            agents,
            key=lambda a: a.get("arrival_time", datetime.now().timestamp())
        )
        
        return sorted_agents[0]["agent_id"]
    
    def get_conflict_stats(self) -> Dict:
        """获取冲突统计"""
        if not self.conflict_history:
            return {"total_conflicts": 0}
        
        winner_counts: Dict[str, int] = {}
        for record in self.conflict_history:
            winner = record["winner"]
            if winner:
                winner_counts[winner] = winner_counts.get(winner, 0) + 1
        
        return {
            "total_conflicts": len(self.conflict_history),
            "winner_counts": winner_counts
        }


class AgentCollaborationFramework:
    """智能体协作框架"""
    
    def __init__(self):
        self.distributor = TaskDistributor()
        self.aggregator = ResultAggregator()
        self.conflict_resolver = ConflictResolver()
        
        # 协作统计
        self.stats = {
            "tasks_distributed": 0,
            "results_aggregated": 0,
            "conflicts_resolved": 0
        }
    
    def distribute_task(self, task: Dict, agents: List[Dict]) -> Optional[str]:
        """分发任务"""
        winner = self.distributor.distribute(task, agents)
        
        if winner:
            self.stats["tasks_distributed"] += 1
            self.distributor.update_load(winner, 5)
        
        return winner
    
    def aggregate_results(self, results: List[Dict], strategy: str = "merge", **kwargs) -> Dict:
        """聚合结果"""
        aggregated = self.aggregator.aggregate(results, strategy, **kwargs)
        
        if aggregated.get("status") == "success":
            self.stats["results_aggregated"] += 1
        
        return aggregated
    
    def resolve_conflict(self, agents: List[Dict], resource: str, context: Dict = None) -> Tuple[Optional[str], Dict]:
        """解决冲突"""
        winner, details = self.conflict_resolver.resolve(agents, resource, context)
        
        self.stats["conflicts_resolved"] += 1
        
        return winner, details
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            **self.stats,
            "conflict_stats": self.conflict_resolver.get_conflict_stats()
        }
