# SwarmFly 主控制器
"""
SwarmFly Controller - 智能体集群主控制器

整合所有FLY层，提供统一的智能体集群管理接口
"""

import sys

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import logging
import json

from .fly_layers import (
    Fly0Master, Fly1Mission, Fly2Rules, Fly3Trends, Fly4Skills, Fly5Tools,
    FLYLevel, TaskStatus, AgentRole
)

logger = logging.getLogger(__name__)


class SwarmFlyController:
    """SwarmFly 智能体集群主控制器"""
    
    def __init__(self):
        # 初始化所有FLY层
        self.fly0 = Fly0Master()
        self.fly1 = Fly1Mission()
        self.fly2 = Fly2Rules()
        self.fly3 = Fly3Trends()
        self.fly4 = Fly4Skills()
        self.fly5 = Fly5Tools()
        
        # 智能体注册表
        self.agents: Dict[str, Dict] = {}
        
        # 团队注册表
        self.teams: Dict[str, Dict] = {}
        
        # 层间通信通道
        self.channels: Dict[str, List[Callable]] = {}
        
        # 事件总线
        self.event_bus: Dict[str, List[Callable]] = {}
        
        logger.info("SwarmFly Controller initialized")
    
    # =========================================================================
    # 智能体管理
    # =========================================================================
    
    def register_agent(self, agent_id: str, agent_config: Dict) -> bool:
        """注册智能体"""
        if agent_id in self.agents:
            logger.warning(f"Agent {agent_id} already registered")
            return False
        
        agent_data = {
            "agent_id": agent_id,
            "name": agent_config.get("name", agent_id),
            "role": agent_config.get("role", AgentRole.TEAM_MEMBER.value),
            "type": agent_config.get("type", "general"),
            "team": agent_config.get("team"),
            "skills": agent_config.get("skills", []),
            "engines": agent_config.get("engines", []),
            "status": "idle",
            "registered_at": datetime.now().isoformat(),
            "current_task": None,
            "metrics": {
                "tasks_completed": 0,
                "tasks_failed": 0,
                "collaboration_score": 0
            }
        }
        
        self.agents[agent_id] = agent_data
        
        # 使命对齐
        self.fly1.align_agent(
            agent_id,
            agent_config.get("mission", self.fly1.CORE_MISSION),
            agent_config.get("values", ["用户中心", "效率优先", "持续进化"])
        )
        
        logger.info(f"Agent registered: {agent_id}")
        self._emit_event("agent_registered", {"agent_id": agent_id})
        return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """注销智能体"""
        if agent_id not in self.agents:
            return False
        
        del self.agents[agent_id]
        logger.info(f"Agent unregistered: {agent_id}")
        self._emit_event("agent_unregistered", {"agent_id": agent_id})
        return True
    
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """获取智能体信息"""
        return self.agents.get(agent_id)
    
    def list_agents(self, team: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
        """列出智能体"""
        agents = list(self.agents.values())
        
        if team:
            agents = [a for a in agents if a.get("team") == team]
        
        if status:
            agents = [a for a in agents if a.get("status") == status]
        
        return agents
    
    def update_agent_status(self, agent_id: str, status: str, task_id: Optional[str] = None) -> bool:
        """更新智能体状态"""
        if agent_id not in self.agents:
            return False
        
        self.agents[agent_id]["status"] = status
        self.agents[agent_id]["current_task"] = task_id
        
        return True
    
    # =========================================================================
    # 任务管理
    # =========================================================================
    
    def submit_task(self, task: Dict) -> str:
        """提交任务"""
        task_id = self.fly0.submit_task(task)
        self._emit_event("task_submitted", {"task_id": task_id, "task": task})
        return task_id
    
    def dispatch_task(self, task_id: str, agent_id: str) -> bool:
        """分发任务"""
        if agent_id not in self.agents:
            logger.error(f"Agent {agent_id} not found")
            return False
        
        # 验证任务
        task = self.fly0.get_task_status(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return False
        
        # 验证交互规则
        valid, msg = self.fly2.validate_interaction(
            "system", agent_id,
            {"agent_id": "system", "task_id": task_id, "timestamp": datetime.now().isoformat()}
        )
        
        if not valid:
            logger.error(f"Interaction validation failed: {msg}")
            return False
        
        # 分发任务
        success = self.fly0.dispatch_task(task_id, agent_id)
        
        if success:
            self.update_agent_status(agent_id, "busy", task_id)
            self._emit_event("task_dispatched", {"task_id": task_id, "agent_id": agent_id})
        
        return success
    
    def complete_task(self, task_id: str, result: Any) -> bool:
        """完成任务"""
        task = self.fly0.get_task_status(task_id)
        if not task or not task.get("assignee"):
            return False
        
        agent_id = task["assignee"]
        success = self.fly0.complete_task(task_id, result)
        
        if success:
            self.update_agent_status(agent_id, "idle")
            self.agents[agent_id]["metrics"]["tasks_completed"] += 1
            self._emit_event("task_completed", {"task_id": task_id, "result": result})
        
        return success
    
    def fail_task(self, task_id: str, error: str) -> bool:
        """任务失败"""
        task = self.fly0.get_task_status(task_id)
        if not task or not task.get("assignee"):
            return False
        
        agent_id = task["assignee"]
        success = self.fly0.fail_task(task_id, error)
        
        if success:
            self.update_agent_status(agent_id, "error")
            self.agents[agent_id]["metrics"]["tasks_failed"] += 1
            self._emit_event("task_failed", {"task_id": task_id, "error": error})
        
        return success
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        return self.fly0.get_task_status(task_id)
    
    # =========================================================================
    # 团队管理
    # =========================================================================
    
    def create_team(self, team_id: str, team_config: Dict) -> bool:
        """创建团队"""
        if team_id in self.teams:
            return False
        
        team_data = {
            "team_id": team_id,
            "name": team_config.get("name", team_id),
            "leader": team_config.get("leader"),
            "members": team_config.get("members", []),
            "mission": team_config.get("mission", ""),
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "metrics": {
                "tasks_completed": 0,
                "collaboration_score": 0
            }
        }
        
        self.teams[team_id] = team_data
        
        # 更新团队成员
        for member_id in team_data["members"]:
            if member_id in self.agents:
                self.agents[member_id]["team"] = team_id
        
        logger.info(f"Team created: {team_id}")
        return True
    
    def add_to_team(self, team_id: str, agent_id: str) -> bool:
        """添加成员到团队"""
        if team_id not in self.teams:
            return False
        
        if agent_id not in self.agents:
            return False
        
        if agent_id not in self.teams[team_id]["members"]:
            self.teams[team_id]["members"].append(agent_id)
            self.agents[agent_id]["team"] = team_id
        
        return True
    
    def remove_from_team(self, team_id: str, agent_id: str) -> bool:
        """从团队移除成员"""
        if team_id not in self.teams:
            return False
        
        if agent_id in self.teams[team_id]["members"]:
            self.teams[team_id]["members"].remove(agent_id)
            self.agents[agent_id]["team"] = None
        
        return True
    
    def get_team(self, team_id: str) -> Optional[Dict]:
        """获取团队信息"""
        return self.teams.get(team_id)
    
    def list_teams(self) -> List[Dict]:
        """列出所有团队"""
        return list(self.teams.values())
    
    # =========================================================================
    # 协作管理
    # =========================================================================
    
    def request_collaboration(self, requester_id: str, target_id: str, task: Dict) -> str:
        """请求协作"""
        collab_id = f"collab_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        collab_request = {
            "collab_id": collab_id,
            "requester": requester_id,
            "target": target_id,
            "task": task,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        # 发送消息
        self.fly5.send_message(requester_id, target_id, {
            "type": "collaboration_request",
            "collab_id": collab_id,
            "task": task
        })
        
        logger.info(f"Collaboration requested: {collab_id}")
        return collab_id
    
    def collaborate(self, team_id: str, task: Dict) -> Dict:
        """团队协作执行任务"""
        if team_id not in self.teams:
            return {"status": "error", "message": "Team not found"}
        
        team = self.teams[team_id]
        
        # 分解任务给团队成员
        subtasks = self._decompose_task(task, len(team["members"]))
        
        results = []
        for i, member_id in enumerate(team["members"]):
            if i < len(subtasks):
                task_id = self.submit_task(subtasks[i])
                self.dispatch_task(task_id, member_id)
                results.append({"agent_id": member_id, "task_id": task_id})
        
        team["metrics"]["tasks_completed"] += 1
        
        return {
            "status": "success",
            "team_id": team_id,
            "subtasks": len(subtasks),
            "assignments": results
        }
    
    def aggregate_results(self, task_ids: List[str]) -> Dict:
        """聚合多个任务的结果"""
        results = []
        
        for task_id in task_ids:
            task = self.fly0.get_task_status(task_id)
            if task and task.get("result"):
                results.append({
                    "task_id": task_id,
                    "result": task["result"]
                })
        
        return {
            "status": "success",
            "total": len(task_ids),
            "completed": len(results),
            "results": results
        }
    
    def resolve_conflicts(self, agents: List[str], resource: str) -> Optional[str]:
        """解决冲突"""
        agent_objs = []
        
        for agent_id in agents:
            agent = self.agents.get(agent_id)
            if agent:
                agent_objs.append({
                    "agent_id": agent_id,
                    "priority": self._calculate_agent_priority(agent),
                    "has_core_task": agent.get("current_task") is not None
                })
        
        winner = self.fly2.resolve_conflict(agent_objs, resource)
        
        if winner:
            self._emit_event("conflict_resolved", {
                "resource": resource,
                "winner": winner,
                "losers": [a for a in agents if a != winner]
            })
        
        return winner
    
    # =========================================================================
    # 技能管理
    # =========================================================================
    
    def register_skill(self, skill_metadata: Dict, skill_impl: Any) -> str:
        """注册技能"""
        return self.fly4.register_skill(skill_metadata, skill_impl)
    
    def call_skill(self, skill_id: str, params: Dict) -> Dict:
        """调用技能"""
        return self.fly4.call_skill(skill_id, params)
    
    def find_skills(self, query: str) -> List[Dict]:
        """搜索技能"""
        return self.fly4.find_skills(query)
    
    # =========================================================================
    # 趋势管理
    # =========================================================================
    
    def add_trend(self, trend: Dict) -> str:
        """添加趋势"""
        return self.fly3.add_trend(trend)
    
    def adjust_strategy(self, adjustment: Dict) -> None:
        """调整策略"""
        self.fly3.adjust_strategy(adjustment)
    
    # =========================================================================
    # 事件处理
    # =========================================================================
    
    def subscribe(self, event: str, callback: Callable) -> None:
        """订阅事件"""
        if event not in self.event_bus:
            self.event_bus[event] = []
        self.event_bus[event].append(callback)
    
    def _emit_event(self, event: str, data: Dict) -> None:
        """触发事件"""
        if event in self.event_bus:
            for callback in self.event_bus[event]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")
    
    # =========================================================================
    # 辅助方法
    # =========================================================================
    
    def _decompose_task(self, task: Dict, num_workers: int) -> List[Dict]:
        """分解任务"""
        description = task.get("description", "")
        
        # 简单按字数分解
        chunk_size = max(1, len(description) // num_workers)
        
        subtasks = []
        for i in range(num_workers):
            start = i * chunk_size
            end = start + chunk_size if i < num_workers - 1 else len(description)
            
            subtasks.append({
                "description": description[start:end],
                "requirements": task.get("requirements", []),
                "priority": task.get("priority", 5),
                "parent_task": task.get("task_id")
            })
        
        return subtasks
    
    def _calculate_agent_priority(self, agent: Dict) -> int:
        """计算智能体优先级"""
        priority = 5
        
        # 基于角色
        if agent.get("role") == AgentRole.TEAM_LEADER.value:
            priority += 2
        
        # 基于历史表现
        metrics = agent.get("metrics", {})
        completed = metrics.get("tasks_completed", 0)
        failed = metrics.get("tasks_failed", 0)
        
        if completed > 10:
            priority += 2
        if failed > completed * 0.2:
            priority -= 2
        
        return max(1, min(10, priority))
    
    # =========================================================================
    # 状态获取
    # =========================================================================
    
    def get_status(self) -> Dict:
        """获取系统状态"""
        return {
            "agents": {
                "total": len(self.agents),
                "idle": len([a for a in self.agents.values() if a["status"] == "idle"]),
                "busy": len([a for a in self.agents.values() if a["status"] == "busy"])
            },
            "teams": {
                "total": len(self.teams)
            },
            "tasks": self.fly0.get_stats(),
            "skills": {
                "total": len(self.fly4.state.get("skills", {}))
            },
            "trends": {
                "total": len(self.fly3.state.get("trends", []))
            }
        }
    
    def get_full_state(self) -> Dict:
        """获取完整状态"""
        return {
            "fly0": self.fly0.get_state(),
            "fly1": self.fly1.get_state(),
            "fly2": self.fly2.get_state(),
            "fly3": self.fly3.get_state(),
            "fly4": self.fly4.get_state(),
            "fly5": self.fly5.get_state(),
            "agents": self.agents,
            "teams": self.teams
        }
    
    def export_state(self, filepath: str) -> bool:
        """导出状态到文件"""
        try:
            state = self.get_full_state()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Export state error: {e}")
            return False


# 全局控制器实例
_controller = None

def get_controller() -> SwarmFlyController:
    """获取全局控制器实例"""
    global _controller
    if _controller is None:
        _controller = SwarmFlyController()
    return _controller
