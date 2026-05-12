# SUB层子智能体管理
"""
SubAgentManager - 子智能体管理模块

管理所有子智能体的生命周期、状态和交互
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


class SubAgentStatus(Enum):
    """子智能体状态"""
    INITIALIZING = "initializing"
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    TERMINATED = "terminated"


class SubAgentType(Enum):
    """子智能体类型"""
    EXECUTOR = "executor"       # 执行器
    OBSERVER = "observer"       # 观察者
    COORDINATOR = "coordinator" # 协调者
    SPECIALIST = "specialist"   # 专家


class SubAgent:
    """子智能体基类"""
    
    def __init__(self, agent_id: str, agent_type: SubAgentType, config: Dict):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.name = config.get("name", agent_id)
        self.description = config.get("description", "")
        
        # 状态
        self.status = SubAgentStatus.INITIALIZING
        self.parent_id = config.get("parent_id")
        self.team_id = config.get("team_id")
        
        # 能力
        self.capabilities = config.get("capabilities", [])
        self.tools = config.get("tools", [])
        
        # 状态数据
        self.context: Dict[str, Any] = {}
        self.task_history: List[Dict] = []
        self.performance_metrics: Dict[str, Any] = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "avg_execution_time": 0,
            "success_rate": 1.0
        }
        
        # 事件回调
        self.on_status_change: Optional[Callable] = None
        self.on_task_complete: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        self.status = SubAgentStatus.IDLE
        logger.info(f"SubAgent {agent_id} initialized")
    
    def set_status(self, new_status: SubAgentStatus):
        """设置状态"""
        old_status = self.status
        self.status = new_status
        
        if self.on_status_change:
            self.on_status_change(self.agent_id, old_status, new_status)
        
        logger.debug(f"SubAgent {self.agent_id}: {old_status.value} -> {new_status.value}")
    
    def execute_task(self, task: Dict) -> Dict:
        """执行任务"""
        self.set_status(SubAgentStatus.WORKING)
        
        task_id = task.get("task_id", str(uuid.uuid4()))
        start_time = datetime.now()
        
        try:
            # 执行任务逻辑
            result = self._execute(task)
            
            # 记录执行历史
            execution_time = (datetime.now() - start_time).total_seconds()
            self.task_history.append({
                "task_id": task_id,
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "execution_time": execution_time,
                "status": "success",
                "result": result
            })
            
            # 更新性能指标
            self._update_metrics(execution_time, success=True)
            
            self.set_status(SubAgentStatus.IDLE)
            
            if self.on_task_complete:
                self.on_task_complete(self.agent_id, task_id, result)
            
            return {"status": "success", "result": result, "task_id": task_id}
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.task_history.append({
                "task_id": task_id,
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "execution_time": execution_time,
                "status": "failed",
                "error": str(e)
            })
            
            self._update_metrics(execution_time, success=False)
            self.set_status(SubAgentStatus.IDLE)
            
            if self.on_error:
                self.on_error(self.agent_id, task_id, str(e))
            
            return {"status": "error", "error": str(e), "task_id": task_id}
    
    def _execute(self, task: Dict) -> Any:
        """实际执行逻辑 - 子类重写"""
        raise NotImplementedError
    
    def _update_metrics(self, execution_time: float, success: bool):
        """更新性能指标"""
        metrics = self.performance_metrics
        
        if success:
            metrics["tasks_completed"] += 1
        else:
            metrics["tasks_failed"] += 1
        
        total_tasks = metrics["tasks_completed"] + metrics["tasks_failed"]
        metrics["success_rate"] = metrics["tasks_completed"] / total_tasks if total_tasks > 0 else 1.0
        
        # 更新平均执行时间
        if total_tasks == 1:
            metrics["avg_execution_time"] = execution_time
        else:
            metrics["avg_execution_time"] = (
                (metrics["avg_execution_time"] * (total_tasks - 1) + execution_time) / total_tasks
            )
    
    def get_state(self) -> Dict:
        """获取状态"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "name": self.name,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "team_id": self.team_id,
            "capabilities": self.capabilities,
            "context": self.context,
            "performance_metrics": self.performance_metrics,
            "task_history_size": len(self.task_history)
        }
    
    def terminate(self):
        """终止子智能体"""
        self.set_status(SubAgentStatus.TERMINATED)
        logger.info(f"SubAgent {self.agent_id} terminated")


class SubAgentManager:
    """子智能体管理器"""
    
    def __init__(self):
        self.agents: Dict[str, SubAgent] = {}
        self.agent_factory: Dict[SubAgentType, type] = {}
        self.parent_agent_map: Dict[str, List[str]] = {}  # parent_id -> [child_ids]
        
        # 注册默认工厂
        self._register_default_factories()
    
    def _register_default_factories(self):
        """注册默认工厂"""
        self.agent_factory[SubAgentType.EXECUTOR] = ExecutorSubAgent
        self.agent_factory[SubAgentType.OBSERVER] = ObserverSubAgent
        self.agent_factory[SubAgentType.COORDINATOR] = CoordinatorSubAgent
        self.agent_factory[SubAgentType.SPECIALIST] = SpecialistSubAgent
    
    def create_agent(self, agent_type: SubAgentType, config: Dict) -> str:
        """创建子智能体"""
        agent_id = config.get("agent_id", f"sub_{len(self.agents)}")
        
        if agent_id in self.agents:
            logger.warning(f"Agent {agent_id} already exists")
            return agent_id
        
        # 获取工厂
        factory = self.agent_factory.get(agent_type, SubAgent)
        
        # 创建智能体
        agent = factory(agent_id, agent_type, config)
        self.agents[agent_id] = agent
        
        # 更新父子关系
        parent_id = config.get("parent_id")
        if parent_id:
            if parent_id not in self.parent_agent_map:
                self.parent_agent_map[parent_id] = []
            self.parent_agent_map[parent_id].append(agent_id)
        
        logger.info(f"SubAgent {agent_id} created")
        return agent_id
    
    def get_agent(self, agent_id: str) -> Optional[SubAgent]:
        """获取子智能体"""
        return self.agents.get(agent_id)
    
    def list_agents(self, parent_id: Optional[str] = None, 
                    agent_type: Optional[SubAgentType] = None,
                    status: Optional[SubAgentStatus] = None) -> List[SubAgent]:
        """列出子智能体"""
        agents = list(self.agents.values())
        
        if parent_id:
            child_ids = self.parent_agent_map.get(parent_id, [])
            agents = [a for a in agents if a.agent_id in child_ids]
        
        if agent_type:
            agents = [a for a in agents if a.agent_type == agent_type]
        
        if status:
            agents = [a for a in agents if a.status == status]
        
        return agents
    
    def destroy_agent(self, agent_id: str) -> bool:
        """销毁子智能体"""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        
        # 终止智能体
        agent.terminate()
        
        # 更新父子关系
        parent_id = agent.parent_id
        if parent_id and parent_id in self.parent_agent_map:
            if agent_id in self.parent_agent_map[parent_id]:
                self.parent_agent_map[parent_id].remove(agent_id)
        
        # 销毁子智能体
        children = self.parent_agent_map.get(agent_id, [])
        for child_id in children:
            self.destroy_agent(child_id)
        
        del self.agents[agent_id]
        
        logger.info(f"SubAgent {agent_id} destroyed")
        return True
    
    def execute_task(self, agent_id: str, task: Dict) -> Dict:
        """执行任务"""
        agent = self.agents.get(agent_id)
        if not agent:
            return {"status": "error", "message": f"Agent {agent_id} not found"}
        
        return agent.execute_task(task)
    
    def batch_execute(self, agent_ids: List[str], tasks: List[Dict]) -> List[Dict]:
        """批量执行"""
        results = []
        
        for i, agent_id in enumerate(agent_ids):
            if i < len(tasks):
                result = self.execute_task(agent_id, tasks[i])
                results.append(result)
            else:
                results.append({"status": "error", "message": "No task for agent"})
        
        return results
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        status_counts = {}
        type_counts = {}
        
        for agent in self.agents.values():
            # 状态统计
            status = agent.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # 类型统计
            agent_type = agent.agent_type.value
            type_counts[agent_type] = type_counts.get(agent_type, 0) + 1
        
        return {
            "total": len(self.agents),
            "by_status": status_counts,
            "by_type": type_counts
        }


# 内置子智能体类型

class ExecutorSubAgent(SubAgent):
    """执行器子智能体"""
    
    def __init__(self, agent_id: str, agent_type: SubAgentType, config: Dict):
        super().__init__(agent_id, SubAgentType.EXECUTOR, config)
        self.executor_type = config.get("executor_type", "general")
    
    def _execute(self, task: Dict) -> Any:
        """执行任务"""
        # 执行器逻辑
        action = task.get("action", "execute")
        
        if action == "execute":
            return {"executed": True, "agent_id": self.agent_id, "task": task}
        elif action == "process":
            return {"processed": True, "agent_id": self.agent_id, "data": task.get("data")}
        else:
            return {"handled": True, "agent_id": self.agent_id}


class ObserverSubAgent(SubAgent):
    """观察器子智能体"""
    
    def __init__(self, agent_id: str, agent_type: SubAgentType, config: Dict):
        super().__init__(agent_id, SubAgentType.OBSERVER, config)
        self.observation_targets = config.get("targets", [])
    
    def _execute(self, task: Dict) -> Any:
        """执行观察任务"""
        return {
            "observed": True,
            "agent_id": self.agent_id,
            "targets": self.observation_targets,
            "observation": task.get("observation", {})
        }


class CoordinatorSubAgent(SubAgent):
    """协调器子智能体"""
    
    def __init__(self, agent_id: str, agent_type: SubAgentType, config: Dict):
        super().__init__(agent_id, SubAgentType.COORDINATOR, config)
        self.managed_agents = config.get("managed_agents", [])
    
    def _execute(self, task: Dict) -> Any:
        """执行协调任务"""
        action = task.get("action", "coordinate")
        
        return {
            "coordinated": True,
            "agent_id": self.agent_id,
            "managed_agents": self.managed_agents,
            "action": action
        }


class SpecialistSubAgent(SubAgent):
    """专家子智能体"""
    
    def __init__(self, agent_id: str, agent_type: SubAgentType, config: Dict):
        super().__init__(agent_id, SubAgentType.SPECIALIST, config)
        self.specialty = config.get("specialty", "general")
        self.expertise_level = config.get("expertise_level", 1)
    
    def _execute(self, task: Dict) -> Any:
        """执行专家任务"""
        return {
            "specialized_result": True,
            "agent_id": self.agent_id,
            "specialty": self.specialty,
            "expertise_level": self.expertise_level,
            "task": task.get("task")
        }
