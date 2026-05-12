# TEAM层团队协作
"""
TeamCollaboration - 团队协作模块

管理团队内部的协作模式、任务分配和结果聚合
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum
import logging
import uuid

logger = logging.getLogger(__name__)


class CollaborationMode(Enum):
    """协作模式"""
    SEQUENTIAL = "sequential"       # 顺序协作
    PARALLEL = "parallel"           # 并行协作
    HIERARCHICAL = "hierarchical"   # 层级协作
    PEER_TO_PEER = "peer_to_peer"   # 点对点协作
    MASTER_SLAVE = "master_slave"   # 主从协作


class TeamRole(Enum):
    """团队角色"""
    LEADER = "leader"               # 领导
    COORDINATOR = "coordinator"     # 协调者
    MEMBER = "member"               # 成员
    SPECIALIST = "specialist"       # 专家


class Team:
    """团队"""
    
    def __init__(self, team_id: str, name: str, config: Dict):
        self.team_id = team_id
        self.name = name
        
        # 成员管理
        self.members: Dict[str, Dict] = {}
        self.leader_id: Optional[str] = config.get("leader_id")
        
        # 协作配置
        self.collaboration_mode = CollaborationMode(config.get("mode", "parallel"))
        self.max_concurrent_tasks = config.get("max_concurrent_tasks", 5)
        
        # 任务管理
        self.tasks: Dict[str, Dict] = {}
        self.task_queue: List[str] = []
        
        # 协作状态
        self.status = "active"
        self.created_at = datetime.now().isoformat()
        
        # 事件回调
        self.on_task_assigned: Optional[Callable] = None
        self.on_task_completed: Optional[Callable] = None
        self.on_collaboration_event: Optional[Callable] = None
        
        # 性能指标
        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "collaboration_score": 0.0,
            "avg_task_time": 0.0
        }
        
        logger.info(f"Team {team_id} created")
    
    def add_member(self, member_id: str, role: TeamRole, config: Dict = None) -> bool:
        """添加成员"""
        if member_id in self.members:
            return False
        
        member_data = {
            "member_id": member_id,
            "role": role.value,
            "name": config.get("name", member_id) if config else member_id,
            "skills": config.get("skills", []) if config else [],
            "status": "idle",
            "current_task": None,
            "tasks_completed": 0,
            "tasks_failed": 0
        }
        
        self.members[member_id] = member_data
        
        if role == TeamRole.LEADER:
            self.leader_id = member_id
        
        logger.info(f"Member {member_id} added to team {self.team_id}")
        self._emit_event("member_added", {"member_id": member_id, "role": role.value})
        return True
    
    def remove_member(self, member_id: str) -> bool:
        """移除成员"""
        if member_id not in self.members:
            return False
        
        del self.members[member_id]
        
        if self.leader_id == member_id:
            self.leader_id = None
        
        logger.info(f"Member {member_id} removed from team {self.team_id}")
        self._emit_event("member_removed", {"member_id": member_id})
        return True
    
    def get_member(self, member_id: str) -> Optional[Dict]:
        """获取成员"""
        return self.members.get(member_id)
    
    def list_members(self, role: Optional[TeamRole] = None) -> List[Dict]:
        """列出成员"""
        members = list(self.members.values())
        
        if role:
            members = [m for m in members if m["role"] == role.value]
        
        return members
    
    def assign_task(self, task: Dict, member_id: Optional[str] = None) -> str:
        """分配任务"""
        task_id = task.get("task_id", f"task_{uuid.uuid4()}")
        
        task_obj = {
            "task_id": task_id,
            "description": task.get("description", ""),
            "requirements": task.get("requirements", []),
            "status": "pending",
            "assigned_to": member_id,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None
        }
        
        self.tasks[task_id] = task_obj
        
        if member_id:
            self._assign_to_member(task_id, member_id)
        else:
            self.task_queue.append(task_id)
        
        logger.info(f"Task {task_id} assigned in team {self.team_id}")
        return task_id
    
    def _assign_to_member(self, task_id: str, member_id: str):
        """分配任务给成员"""
        if member_id not in self.members:
            logger.warning(f"Member {member_id} not in team {self.team_id}")
            return
        
        self.tasks[task_id]["assigned_to"] = member_id
        self.tasks[task_id]["status"] = "assigned"
        self.tasks[task_id]["started_at"] = datetime.now().isoformat()
        
        self.members[member_id]["status"] = "busy"
        self.members[member_id]["current_task"] = task_id
        
        self._emit_event("task_assigned", {
            "task_id": task_id,
            "member_id": member_id
        })
    
    def complete_task(self, task_id: str, result: Any) -> bool:
        """完成任务"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task["status"] = "completed"
        task["completed_at"] = datetime.now().isoformat()
        task["result"] = result
        
        # 更新成员状态
        member_id = task.get("assigned_to")
        if member_id and member_id in self.members:
            self.members[member_id]["status"] = "idle"
            self.members[member_id]["current_task"] = None
            self.members[member_id]["tasks_completed"] += 1
        
        # 更新团队指标
        self._update_metrics(success=True)
        
        self._emit_event("task_completed", {
            "task_id": task_id,
            "member_id": member_id,
            "result": result
        })
        
        return True
    
    def fail_task(self, task_id: str, error: str) -> bool:
        """任务失败"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task["status"] = "failed"
        task["completed_at"] = datetime.now().isoformat()
        task["error"] = error
        
        # 更新成员状态
        member_id = task.get("assigned_to")
        if member_id and member_id in self.members:
            self.members[member_id]["status"] = "idle"
            self.members[member_id]["current_task"] = None
            self.members[member_id]["tasks_failed"] += 1
        
        # 更新团队指标
        self._update_metrics(success=False)
        
        self._emit_event("task_failed", {
            "task_id": task_id,
            "member_id": member_id,
            "error": error
        })
        
        return True
    
    def collaborate(self, task: Dict) -> Dict:
        """团队协作执行任务"""
        mode = self.collaboration_mode
        
        if mode == CollaborationMode.PARALLEL:
            return self._parallel_collaborate(task)
        elif mode == CollaborationMode.SEQUENTIAL:
            return self._sequential_collaborate(task)
        elif mode == CollaborationMode.HIERARCHICAL:
            return self._hierarchical_collaborate(task)
        elif mode == CollaborationMode.PEER_TO_PEER:
            return self._p2p_collaborate(task)
        elif mode == CollaborationMode.MASTER_SLAVE:
            return self._master_slave_collaborate(task)
        else:
            return {"status": "error", "message": f"Unknown mode: {mode}"}
    
    def _parallel_collaborate(self, task: Dict) -> Dict:
        """并行协作"""
        # 分解任务
        subtasks = self._decompose_task(task)
        
        assignments = []
        for i, (member_id, subtask) in enumerate(zip(self.members.keys(), subtasks)):
            task_id = self.assign_task(subtask, member_id)
            assignments.append({"member_id": member_id, "task_id": task_id})
        
        return {
            "status": "success",
            "mode": "parallel",
            "total_subtasks": len(subtasks),
            "assignments": assignments
        }
    
    def _sequential_collaborate(self, task: Dict) -> Dict:
        """顺序协作"""
        subtasks = self._decompose_task(task)
        
        # 第一个任务分配给第一个可用成员
        first_member = self._get_next_available_member()
        if not first_member:
            return {"status": "error", "message": "No available member"}
        
        task_id = self.assign_task(subtasks[0], first_member)
        
        return {
            "status": "success",
            "mode": "sequential",
            "first_task_id": task_id,
            "first_member": first_member,
            "total_subtasks": len(subtasks)
        }
    
    def _hierarchical_collaborate(self, task: Dict) -> Dict:
        """层级协作"""
        if not self.leader_id:
            return {"status": "error", "message": "No leader in team"}
        
        # 领导分解任务
        subtasks = self._decompose_task(task)
        
        # 分配给下级
        members = list(self.members.keys())
        members.remove(self.leader_id)
        
        assignments = []
        for i, subtask in enumerate(subtasks):
            if i < len(members):
                member_id = members[i]
            else:
                member_id = self.leader_id
            
            task_id = self.assign_task(subtask, member_id)
            assignments.append({"member_id": member_id, "task_id": task_id})
        
        return {
            "status": "success",
            "mode": "hierarchical",
            "leader": self.leader_id,
            "assignments": assignments
        }
    
    def _p2p_collaborate(self, task: Dict) -> Dict:
        """点对点协作"""
        subtasks = self._decompose_task(task)
        
        # 每个成员处理一个子任务
        assignments = []
        for member_id, subtask in zip(self.members.keys(), subtasks):
            task_id = self.assign_task(subtask, member_id)
            assignments.append({"member_id": member_id, "task_id": task_id})
        
        return {
            "status": "success",
            "mode": "peer_to_peer",
            "assignments": assignments
        }
    
    def _master_slave_collaborate(self, task: Dict) -> Dict:
        """主从协作"""
        if not self.leader_id:
            return {"status": "error", "message": "No master in team"}
        
        subtasks = self._decompose_task(task)
        
        # 主节点处理主任务
        main_task_id = self.assign_task(task, self.leader_id)
        
        # 从节点处理子任务
        members = [m for m in self.members.keys() if m != self.leader_id]
        
        slave_assignments = []
        for i, subtask in enumerate(subtasks):
            if i < len(members):
                task_id = self.assign_task(subtask, members[i])
                slave_assignments.append({"member_id": members[i], "task_id": task_id})
        
        return {
            "status": "success",
            "mode": "master_slave",
            "master": self.leader_id,
            "main_task_id": main_task_id,
            "slave_assignments": slave_assignments
        }
    
    def _decompose_task(self, task: Dict) -> List[Dict]:
        """分解任务"""
        description = task.get("description", "")
        num_subtasks = len(self.members)
        
        # 简单按字数分解
        chunk_size = max(1, len(description) // num_subtasks) if description else 1
        
        subtasks = []
        for i in range(num_subtasks):
            start = i * chunk_size
            end = start + chunk_size if i < num_subtasks - 1 else len(description)
            
            subtask = {
                "description": description[start:end] if description else f"Subtask {i+1}",
                "requirements": task.get("requirements", []),
                "priority": task.get("priority", 5),
                "parent_task": task.get("task_id")
            }
            subtasks.append(subtask)
        
        return subtasks
    
    def _get_next_available_member(self) -> Optional[str]:
        """获取下一个可用成员"""
        for member_id, member in self.members.items():
            if member["status"] == "idle":
                return member_id
        return None
    
    def _update_metrics(self, success: bool):
        """更新性能指标"""
        if success:
            self.metrics["tasks_completed"] += 1
        else:
            self.metrics["tasks_failed"] += 1
        
        total = self.metrics["tasks_completed"] + self.metrics["tasks_failed"]
        if total > 0:
            self.metrics["collaboration_score"] = (
                self.metrics["tasks_completed"] / total
            )
    
    def _emit_event(self, event_type: str, data: Dict):
        """触发事件"""
        if self.on_collaboration_event:
            self.on_collaboration_event(self.team_id, event_type, data)
    
    def aggregate_results(self, task_ids: List[str]) -> Dict:
        """聚合任务结果"""
        results = []
        
        for task_id in task_ids:
            task = self.tasks.get(task_id)
            if task and task.get("result"):
                results.append({
                    "task_id": task_id,
                    "result": task["result"]
                })
        
        return {
            "status": "success",
            "total_tasks": len(task_ids),
            "completed_tasks": len(results),
            "results": results
        }
    
    def get_status(self) -> Dict:
        """获取团队状态"""
        return {
            "team_id": self.team_id,
            "name": self.name,
            "status": self.status,
            "leader": self.leader_id,
            "member_count": len(self.members),
            "task_count": len(self.tasks),
            "pending_tasks": len(self.task_queue),
            "metrics": self.metrics
        }


class TeamCollaborationManager:
    """团队协作管理器"""
    
    def __init__(self):
        self.teams: Dict[str, Team] = {}
        self.team_templates: Dict[str, Dict] = {}
        
        # 注册默认模板
        self._register_default_templates()
    
    def _register_default_templates(self):
        """注册默认模板"""
        self.team_templates["research"] = {
            "mode": "hierarchical",
            "roles": ["leader", "specialist", "member"],
            "max_concurrent_tasks": 5
        }
        
        self.team_templates["development"] = {
            "mode": "parallel",
            "roles": ["coordinator", "member"],
            "max_concurrent_tasks": 10
        }
        
        self.team_templates["analysis"] = {
            "mode": "peer_to_peer",
            "roles": ["leader", "specialist"],
            "max_concurrent_tasks": 8
        }
    
    def create_team(self, team_id: str, name: str, config: Dict = None) -> Team:
        """创建团队"""
        if team_id in self.teams:
            logger.warning(f"Team {team_id} already exists")
            return self.teams[team_id]
        
        team_config = config or {}
        team = Team(team_id, name, team_config)
        self.teams[team_id] = team
        
        logger.info(f"Team {team_id} created")
        return team
    
    def create_team_from_template(self, team_id: str, name: str, template_name: str) -> Optional[Team]:
        """从模板创建团队"""
        template = self.team_templates.get(template_name)
        if not template:
            logger.warning(f"Template {template_name} not found")
            return None
        
        return self.create_team(team_id, name, template)
    
    def get_team(self, team_id: str) -> Optional[Team]:
        """获取团队"""
        return self.teams.get(team_id)
    
    def destroy_team(self, team_id: str) -> bool:
        """销毁团队"""
        if team_id not in self.teams:
            return False
        
        del self.teams[team_id]
        logger.info(f"Team {team_id} destroyed")
        return True
    
    def list_teams(self) -> List[Dict]:
        """列出所有团队"""
        return [team.get_status() for team in self.teams.values()]
    
    def register_template(self, name: str, template: Dict):
        """注册团队模板"""
        self.team_templates[name] = template
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total_teams = len(self.teams)
        total_members = sum(len(team.members) for team in self.teams.values())
        total_tasks = sum(len(team.tasks) for team in self.teams.values())
        
        return {
            "total_teams": total_teams,
            "total_members": total_members,
            "total_tasks": total_tasks,
            "templates_available": len(self.team_templates)
        }
