# SwarmFly FLY层核心框架
"""
SwarmFly - 智能体集群协同控制器

FLY层架构:
- FLY-0: 主智能体层（任务理解/分派/验收）
- FLY-1: 使命层（愿景/目标设定）
- FLY-2: 法则层（规则/约束）
- FLY-3: 趋势层（市场/技术趋势）
- FLY-4: 技能层（能力/技能）
- FLY-5: 工具层（工具/资源）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


# ============================================================================
# FLY层枚举定义
# ============================================================================

class FLYLevel(Enum):
    """FLY层级别枚举"""
    fly0master = "fly0"      # 主智能体
    fly1mission = "fly1"     # 使命层
    fly2rules = "fly2"         # 法则层
    fly3trends = "fly3"       # 趋势层
    fly4skills = "fly4"       # 技能层
    fly5tools = "fly5"        # 工具层


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRole(Enum):
    """智能体角色枚举"""
    MASTER = "master"         # 主智能体
    TEAM_LEADER = "team_leader"  # 团队领导
    TEAM_MEMBER = "team_member"  # 团队成员
    SUB_AGENT = "sub_agent"      # 子智能体


# ============================================================================
# FLY层基类
# ============================================================================

class FLYLayer:
    """FLY层基类"""
    
    def __init__(self, level: FLYLevel, name: str):
        self.level = level
        self.name = name
        self.state: Dict[str, Any] = {}
        self.enabled = True
        self.listeners: List[Callable] = []
    
    def get_state(self) -> Dict[str, Any]:
        """获取层状态"""
        return {
            "level": self.level.value,
            "name": self.name,
            "enabled": self.enabled,
            "state": self.state
        }
    
    def update_state(self, key: str, value: Any):
        """更新层状态"""
        self.state[key] = value
        self._notify_listeners()
    
    def add_listener(self, callback: Callable):
        """添加状态变化监听器"""
        self.listeners.append(callback)
    
    def _notify_listeners(self):
        """通知所有监听器"""
        for listener in self.listeners:
            try:
                listener(self.state)
            except Exception as e:
                logger.error(f"Listener error: {e}")


# ============================================================================
# FLY-0 主智能体层
# ============================================================================

class Fly0Master(FLYLayer):
    """FLY-0 主智能体层"""
    
    def __init__(self):
        super().__init__(FLYLevel.fly0master, "MasterAgent")
        self.task_queue: List[Dict] = []
        self.active_tasks: Dict[str, Dict] = {}
        self.completed_tasks: Dict[str, Dict] = {}
        self.task_id_counter = 0
    
    def submit_task(self, task: Dict[str, Any]) -> str:
        """提交任务"""
        self.task_id_counter += 1
        task_id = f"task_{self.task_id_counter}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        task_obj = {
            "task_id": task_id,
            "description": task.get("description", ""),
            "requirements": task.get("requirements", []),
            "priority": task.get("priority", 5),
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "assignee": None,
            "result": None
        }
        
        self.task_queue.append(task_obj)
        self.task_queue.sort(key=lambda x: x["priority"], reverse=True)
        
        logger.info(f"Task submitted: {task_id}")
        return task_id
    
    def dispatch_task(self, task_id: str, agent_id: str) -> bool:
        """分发任务给智能体"""
        task = None
        # 查找任务所在的列表
        for t in self.task_queue:
            if t["task_id"] == task_id:
                task = t
                self.task_queue.remove(t)
                break
        
        if not task:
            # 检查是否已经在active_tasks中
            task = self.active_tasks.get(task_id)
            if not task:
                return False
        
        task["status"] = TaskStatus.RUNNING.value
        task["assignee"] = agent_id
        task["dispatched_at"] = datetime.now().isoformat()
        
        self.active_tasks[task_id] = task
        
        logger.info(f"Task {task_id} dispatched to {agent_id}")
        return True
    
    def complete_task(self, task_id: str, result: Any) -> bool:
        """任务完成"""
        task = self.active_tasks.get(task_id)
        if not task:
            return False
        
        task["status"] = TaskStatus.COMPLETED.value
        task["result"] = result
        task["completed_at"] = datetime.now().isoformat()
        
        self.completed_tasks[task_id] = task
        del self.active_tasks[task_id]
        
        logger.info(f"Task {task_id} completed")
        return True
    
    def fail_task(self, task_id: str, error: str) -> bool:
        """任务失败"""
        task = self.active_tasks.get(task_id)
        if not task:
            return False
        
        task["status"] = TaskStatus.FAILED.value
        task["error"] = error
        task["failed_at"] = datetime.now().isoformat()
        
        # 保留在completed_tasks中作为失败记录
        self.completed_tasks[task_id] = task
        del self.active_tasks[task_id]
        
        logger.error(f"Task {task_id} failed: {error}")
        return True
    
    def get_next_task(self) -> Optional[Dict]:
        """获取下一个待处理任务"""
        if self.task_queue:
            return self.task_queue[0]
        return None
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id]
        for task in self.task_queue:
            if task["task_id"] == task_id:
                return task
        return None
    
    def _find_task(self, task_id: str) -> Optional[Dict]:
        """查找任务"""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id]
        for task in self.task_queue:
            if task["task_id"] == task_id:
                return task
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "pending": len(self.task_queue),
            "running": len(self.active_tasks),
            "completed": len(self.completed_tasks),
            "total": self.task_id_counter
        }


# ============================================================================
# FLY-1 使命层
# ============================================================================

class Fly1Mission(FLYLayer):
    """FLY-1 使命层"""
    
    CORE_MISSION = "成为高效、协作、自我进化的智能体协作网络"
    
    VALUE_SYSTEM = [
        {"name": "用户中心", "weight": 0.4, "description": "始终以用户需求为核心"},
        {"name": "效率优先", "weight": 0.3, "description": "优化资源分配，提升协作效率"},
        {"name": "持续进化", "weight": 0.3, "description": "建立自我改进机制"}
    ]
    
    def __init__(self):
        super().__init__(FLYLevel.fly1mission, "MissionLayer")
        self.state["mission"] = self.CORE_MISSION
        self.state["values"] = self.VALUE_SYSTEM
        self.state["alignment_scores"] = {}
    
    def get_mission(self) -> str:
        """获取核心使命"""
        return self.CORE_MISSION
    
    def get_values(self) -> List[Dict]:
        """获取价值体系"""
        return self.VALUE_SYSTEM
    
    def calculate_alignment(self, agent_mission: str, agent_values: List[str]) -> float:
        """计算使命对齐度"""
        score = 0.0
        
        # 使命匹配度
        if agent_mission == self.CORE_MISSION:
            score += 50
        
        # 价值匹配度 - 支持字符串列表或字典列表
        if agent_values:
            if isinstance(agent_values[0], dict):
                agent_value_names = [v.get("name", "") for v in agent_values if isinstance(v, dict)]
            else:
                agent_value_names = agent_values
                
            expected_values = [v["name"] for v in self.VALUE_SYSTEM]
            matches = set(agent_value_names) & set(expected_values)
            score += (len(matches) / len(expected_values)) * 50
        
        return score
    
    def align_agent(self, agent_id: str, agent_mission: str, agent_values: List[str]) -> Dict:
        """对齐智能体使命"""
        alignment_score = self.calculate_alignment(agent_mission, agent_values)
        
        self.state["alignment_scores"][agent_id] = {
            "score": alignment_score,
            "timestamp": datetime.now().isoformat(),
            "mission": agent_mission,
            "values": agent_values
        }
        
        return {
            "agent_id": agent_id,
            "alignment_score": alignment_score,
            "aligned": alignment_score >= 70
        }
    
    def get_misaligned_agents(self) -> List[str]:
        """获取未对齐的智能体"""
        return [
            agent_id for agent_id, data in self.state["alignment_scores"].items()
            if data["score"] < 70
        ]


# ============================================================================
# FLY-2 法则层
# ============================================================================

class Fly2Rules(FLYLayer):
    """FLY-2 法则层"""
    
    def __init__(self):
        super().__init__(FLYLevel.fly2rules, "LawLayer")
        self._init_rules()
    
    def _init_rules(self):
        """初始化规则"""
        self.state["collaboration_rules"] = {
            "message_format": "json",
            "required_fields": ["agent_id", "task_id", "timestamp"],
            "timeout_seconds": 30,
            "retry_count": 3
        }
        
        self.state["resource_rules"] = {
            "core_task_ratio": 0.7,
            "normal_task_ratio": 0.5,
            "low_priority_ratio": 0.3
        }
        
        self.state["security_rules"] = {
            "encryption_required": True,
            "sensitive_data_masking": True,
            "permission_model": "RBAC"
        }
        
        self.state["evolution_rules"] = {
            "experience_threshold": 100,
            "upgrade_verification": True,
            "architecture_review_cycle_days": 90
        }
    
    def validate_interaction(self, sender: str, receiver: str, message: Dict) -> tuple:
        """验证交互合法性"""
        required_fields = self.state["collaboration_rules"]["required_fields"]
        
        for field in required_fields:
            if field not in message:
                return False, f"Missing required field: {field}"
        
        return True, "Valid interaction"
    
    def resolve_conflict(self, agents: List[Dict], resource: str) -> Optional[str]:
        """解决资源冲突"""
        if not agents:
            return None
        
        # 按优先级排序
        sorted_agents = sorted(agents, key=lambda x: x.get("priority", 5), reverse=True)
        
        # 检查是否有核心任务
        for agent in sorted_agents:
            if agent.get("has_core_task"):
                return agent["agent_id"]
        
        return sorted_agents[0]["agent_id"]
    
    def get_resource_allocation(self, task_priority: str) -> float:
        """获取资源分配比例"""
        rules = self.state["resource_rules"]
        
        if task_priority == "core":
            return rules["core_task_ratio"]
        elif task_priority == "normal":
            return rules["normal_task_ratio"]
        else:
            return rules["low_priority_ratio"]


# ============================================================================
# FLY-3 趋势层
# ============================================================================

class Fly3Trends(FLYLayer):
    """FLY-3 趋势层"""
    
    def __init__(self):
        super().__init__(FLYLevel.fly3trends, "TrendLayer")
        self.state["trends"] = []
        self.state["last_update"] = None
        self.state["strategy_adjustments"] = []
    
    def add_trend(self, trend: Dict) -> str:
        """添加趋势"""
        trend_id = f"trend_{len(self.state['trends']) + 1}"
        trend["trend_id"] = trend_id
        trend["detected_at"] = datetime.now().isoformat()
        
        self.state["trends"].append(trend)
        self.state["last_update"] = datetime.now().isoformat()
        
        return trend_id
    
    def get_technology_trends(self) -> List[Dict]:
        """获取技术趋势"""
        return [t for t in self.state["trends"] if t.get("type") == "technology"]
    
    def get_market_trends(self) -> List[Dict]:
        """获取市场趋势"""
        return [t for t in self.state["trends"] if t.get("type") == "market"]
    
    def get_user_demand_trends(self) -> List[Dict]:
        """获取用户需求趋势"""
        return [t for t in self.state["trends"] if t.get("type") == "user_demand"]
    
    def adjust_strategy(self, adjustment: Dict) -> None:
        """调整策略"""
        adjustment["adjusted_at"] = datetime.now().isoformat()
        self.state["strategy_adjustments"].append(adjustment)
    
    def get_latest_strategy(self) -> Optional[Dict]:
        """获取最新策略"""
        if self.state["strategy_adjustments"]:
            return self.state["strategy_adjustments"][-1]
        return None


# ============================================================================
# FLY-4 技能层
# ============================================================================

class Fly4Skills(FLYLayer):
    """FLY-4 技能层"""
    
    def __init__(self):
        super().__init__(FLYLevel.fly4skills, "SkillLayer")
        self.state["skills"] = {}
        self.state["skill_calls"] = []
    
    def register_skill(self, skill_metadata: Dict, skill_impl: Any) -> str:
        """注册技能"""
        skill_id = f"skill_{len(self.state['skills']) + 1:04d}"
        skill_metadata["skill_id"] = skill_id
        skill_metadata["registered_at"] = datetime.now().isoformat()
        
        self.state["skills"][skill_id] = {
            "metadata": skill_metadata,
            "implementation": skill_impl,
            "call_count": 0,
            "success_count": 0,
            "failure_count": 0
        }
        
        return skill_id
    
    def get_skill(self, skill_id: str) -> Optional[Dict]:
        """获取技能"""
        return self.state["skills"].get(skill_id)
    
    def find_skills(self, query: str) -> List[Dict]:
        """搜索技能"""
        results = []
        query_lower = query.lower()
        
        for skill_id, skill_data in self.state["skills"].items():
            metadata = skill_data["metadata"]
            name = metadata.get("name", "").lower()
            description = metadata.get("description", "").lower()
            tags = [t.lower() for t in metadata.get("tags", [])]
            
            if query_lower in name or query_lower in description or query_lower in tags:
                results.append(metadata)
        
        return results
    
    def call_skill(self, skill_id: str, params: Dict) -> Dict:
        """调用技能"""
        skill = self.state["skills"].get(skill_id)
        if not skill:
            return {"status": "error", "message": f"Skill {skill_id} not found"}
        
        skill["call_count"] += 1
        
        try:
            result = skill["implementation"](**params)
            skill["success_count"] += 1
            
            self.state["skill_calls"].append({
                "skill_id": skill_id,
                "params": params,
                "result": result,
                "success": True,
                "called_at": datetime.now().isoformat()
            })
            
            return {"status": "success", "data": result}
        except Exception as e:
            skill["failure_count"] += 1
            
            self.state["skill_calls"].append({
                "skill_id": skill_id,
                "params": params,
                "error": str(e),
                "success": False,
                "called_at": datetime.now().isoformat()
            })
            
            return {"status": "error", "message": str(e)}
    
    def get_skill_stats(self, skill_id: str) -> Optional[Dict]:
        """获取技能统计"""
        skill = self.state["skills"].get(skill_id)
        if not skill:
            return None
        
        call_count = skill["call_count"]
        success_count = skill["success_count"]
        
        return {
            "skill_id": skill_id,
            "call_count": call_count,
            "success_count": success_count,
            "failure_count": skill["failure_count"],
            "success_rate": success_count / call_count if call_count > 0 else 0
        }


# ============================================================================
# FLY-5 工具层
# ============================================================================

class Fly5Tools(FLYLayer):
    """FLY-5 工具层"""
    
    def __init__(self):
        super().__init__(FLYLevel.fly5tools, "ToolLayer")
        self.state["tools"] = {}
        self.state["message_queue"] = []
        self.state["cache"] = {}
    
    def register_tool(self, tool_id: str, tool_type: str, tool_impl: Any) -> None:
        """注册工具"""
        self.state["tools"][tool_id] = {
            "type": tool_type,
            "implementation": tool_impl,
            "registered_at": datetime.now().isoformat()
        }
    
    def get_tool(self, tool_id: str) -> Optional[Dict]:
        """获取工具"""
        return self.state["tools"].get(tool_id)
    
    def send_message(self, sender: str, receiver: str, message: Dict) -> str:
        """发送消息"""
        msg_id = f"msg_{len(self.state['message_queue']) + 1}"
        
        msg = {
            "msg_id": msg_id,
            "sender": sender,
            "receiver": receiver,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "status": "sent"
        }
        
        self.state["message_queue"].append(msg)
        return msg_id
    
    def get_messages(self, receiver: str) -> List[Dict]:
        """获取消息"""
        return [m for m in self.state["message_queue"] if m["receiver"] == receiver]
    
    def cache_set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """设置缓存"""
        self.state["cache"][key] = {
            "value": value,
            "expires_at": datetime.now().timestamp() + ttl
        }
    
    def cache_get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self.state["cache"]:
            return None
        
        cache_entry = self.state["cache"][key]
        if datetime.now().timestamp() > cache_entry["expires_at"]:
            del self.state["cache"][key]
            return None
        
        return cache_entry["value"]
