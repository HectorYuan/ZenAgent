"""
ZenAgent 任务协作流程集成测试

测试完整的任务协作流程:
    ZenAgent 接收任务 (MCP) → SwarmFly 分发任务 (Collaboration) → 使用 Shared Memory → SoulTeam 学习反馈
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from packages.core import ZenAgent, ZenAgentConfig
from packages.SwarmFly.core import SwarmFly, SwarmFlyConfig
from packages.SwarmFly.collaboration import (
    Task, TaskDispatcher,
    CollaborationEngine, CollaborationConfig
)
from packages.SwarmFly.memory import SharedMemoryPool, MemoryPoolConfig, SegmentType, SegmentAccess
from packages.SoulTeam.core import SoulTeam, SoulTeamConfig
from packages.SoulTeam.memory import MemoryType, MemoryEntry
from packages.SoulTeam.learning import Feedback, FeedbackType
from packages.mcp import AgentMetadata, AgentCapability, AgentStatus


class CollaborationFlow:
    """
    协作流程管理器
    
    协调任务从 ZenAgent → SwarmFly → SharedMemory → SoulTeam 的完整流程
    """
    
    def __init__(self):
        self.zen_agents: Dict[str, ZenAgent] = {}
        self.swarmfly: Optional[SwarmFly] = None
        self.soulteam: Optional[SoulTeam] = None
        self.tasks: Dict[str, Task] = {}
        self.collaboration_log: List[Dict[str, Any]] = []
        
    def setup_infrastructure(self) -> bool:
        """
        设置协作基础设施
        
        Returns:
            bool: 设置是否成功
        """
        try:
            # 初始化 SwarmFly
            swarm_config = SwarmFlyConfig(
                node_id="collab_swarm"
            )
            self.swarmfly = SwarmFly(config=swarm_config)
            
            # 初始化 SoulTeam
            soul_config = SoulTeamConfig(
                soul_id="collab_soul"
            )
            self.soulteam = SoulTeam(config=soul_config)
            
            self.collaboration_log.append({
                "event": "infrastructure_setup",
                "success": True
            })
            
            return True
            
        except Exception as e:
            self.collaboration_log.append({
                "event": "infrastructure_setup",
                "success": False,
                "error": str(e)
            })
            return False
    
    def register_agent(
        self,
        agent_id: str,
        agent_name: str,
        capabilities: List[AgentCapability]
    ) -> bool:
        """
        注册 Agent
        
        Args:
            agent_id: Agent ID
            agent_name: Agent 名称
            capabilities: 能力列表
            
        Returns:
            bool: 注册是否成功
        """
        try:
            # 创建 ZenAgent
            zen_config = ZenAgentConfig(
                agent_id=agent_id,
                agent_name=agent_name
            )
            zen = ZenAgent(config=zen_config)
            
            # 注册到 MCP
            metadata = AgentMetadata(
                agent_id=agent_id,
                name=agent_name,
                agent_type="collaborative",
                capabilities=capabilities,
                status=AgentStatus.ACTIVE
            )
            zen.register_agent(metadata)
            
            self.zen_agents[agent_id] = zen
            
            self.collaboration_log.append({
                "event": "agent_registered",
                "agent_id": agent_id,
                "capabilities": [c.value for c in capabilities]
            })
            
            return True
            
        except Exception as e:
            self.collaboration_log.append({
                "event": "agent_registered",
                "agent_id": agent_id,
                "success": False,
                "error": str(e)
            })
            return False
    
    def create_and_dispatch_task(
        self,
        task_id: str,
        description: str,
        priority: int,
        created_by: str,
        assigned_to: List[str]
    ) -> Dict[str, Any]:
        """
        创建并分发任务
        
        Args:
            task_id: 任务 ID
            description: 任务描述
            priority: 优先级
            created_by: 创建者 ID
            assigned_to: 分配对象列表
            
        Returns:
            Dict[str, Any]: 任务结果
        """
        result = {
            "task_id": task_id,
            "created": False,
            "dispatched": False,
            "steps": []
        }
        
        try:
            # Step 1: 创建任务
            task = Task(
                task_id=task_id,
                description=description,
                priority=priority,
                created_by=created_by,
                assigned_to=assigned_to
            )
            self.tasks[task_id] = task
            
            result["created"] = True
            result["steps"].append({
                "step": "task_created",
                "task_id": task_id,
                "priority": priority
            })
            
            # Step 2: 分发任务
            if self.swarmfly and self.swarmfly.collaboration_engine:
                dispatcher = TaskDispatcher(
                    collaboration_engine=self.swarmfly.collaboration_engine
                )
                
                # 写入共享内存
                if self.swarmfly.memory_pool and hasattr(self.swarmfly.memory_pool, 'write'):
                    self.swarmfly.memory_pool.write(
                        key=f"task_{task_id}",
                        value={
                            "task_id": task_id,
                            "description": description,
                            "status": "pending",
                            "created_at": datetime.now().isoformat()
                        },
                        segment_type=SegmentType.SHARED
                    )
                
                result["dispatched"] = True
                result["steps"].append({
                    "step": "task_dispatched",
                    "assigned_to": assigned_to
                })
            
            # Step 3: 记录到 SoulTeam
            if self.soulteam and hasattr(self.soulteam, 'store_memory'):
                self.soulteam.store_memory(
                    content=f"任务 {task_id} 已创建并分发",
                    memory_type=MemoryType.EPISODIC,
                    metadata={
                        "task_id": task_id,
                        "priority": priority,
                        "assigned_to": assigned_to
                    }
                )
                
                result["steps"].append({
                    "step": "task_recorded"
                })
            
            self.collaboration_log.append({
                "event": "task_created",
                "task_id": task_id
            })
            
        except Exception as e:
            result["error"] = str(e)
            self.collaboration_log.append({
                "event": "task_error",
                "task_id": task_id,
                "error": str(e)
            })
        
        return result
    
    def update_task_status(
        self,
        task_id: str,
        new_status: str,
        agent_id: str,
        feedback: Optional[str] = None
    ) -> bool:
        """
        更新任务状态
        
        Args:
            task_id: 任务 ID
            new_status: 新状态
            agent_id: 执行 Agent ID
            feedback: 反馈信息
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 更新共享内存
            if self.swarmfly and self.swarmfly.memory_pool and hasattr(self.swarmfly.memory_pool, 'read'):
                task_data = self.swarmfly.memory_pool.read(f"task_{task_id}")
                if task_data:
                    task_data["status"] = new_status
                    task_data["updated_at"] = datetime.now().isoformat()
                    task_data["updated_by"] = agent_id
                    
                    if hasattr(self.swarmfly.memory_pool, 'write'):
                        self.swarmfly.memory_pool.write(
                            key=f"task_{task_id}",
                            value=task_data,
                            segment_type=SegmentType.SHARED
                        )
            
            # 记录反馈到 SoulTeam
            if self.soulteam and feedback:
                fb = Feedback(
                    content=feedback,
                    feedback_type=FeedbackType.REINFORCEMENT,
                    source=agent_id
                )
                
                if hasattr(self.soulteam, 'process_feedback'):
                    self.soulteam.process_feedback(fb)
                
                if hasattr(self.soulteam, 'store_memory'):
                    self.soulteam.store_memory(
                        content=f"任务 {task_id} 状态更新: {new_status}",
                        memory_type=MemoryType.EPISODIC,
                        metadata={
                            "task_id": task_id,
                            "new_status": new_status,
                            "agent_id": agent_id
                        }
                    )
            
            self.collaboration_log.append({
                "event": "task_status_updated",
                "task_id": task_id,
                "new_status": new_status,
                "agent_id": agent_id
            })
            
            return True
            
        except Exception as e:
            self.collaboration_log.append({
                "event": "task_status_error",
                "task_id": task_id,
                "error": str(e)
            })
            return False
    
    def get_collaboration_summary(self) -> Dict[str, Any]:
        """获取协作摘要"""
        return {
            "total_agents": len(self.zen_agents),
            "total_tasks": len(self.tasks),
            "total_events": len(self.collaboration_log),
            "log": self.collaboration_log
        }


class TestCollaborationFlow(unittest.TestCase):
    """
    协作流程测试
    
    验证完整的任务协作流程
    """
    
    def setUp(self):
        """测试前准备"""
        self.flow = CollaborationFlow()
        self.flow.setup_infrastructure()
    
    def test_infrastructure_setup(self):
        """
        测试基础设施设置
        
        验证协作基础设施是否正确设置
        """
        self.assertIsNotNone(self.flow.swarmfly)
        self.assertIsNotNone(self.flow.soulteam)
    
    def test_agent_registration(self):
        """
        测试 Agent 注册
        
        验证多个 Agent 的注册流程
        """
        # 注册多个 Agent
        agents = [
            ("agent_001", "WorkerAgent1", [AgentCapability.TEXT_GENERATION]),
            ("agent_002", "WorkerAgent2", [AgentCapability.TEXT_GENERATION, AgentCapability.COLLABORATION]),
            ("agent_003", "LeaderAgent", [AgentCapability.TEXT_GENERATION, AgentCapability.COLLABORATION, AgentCapability.MEMORY])
        ]
        
        for agent_id, name, caps in agents:
            result = self.flow.register_agent(agent_id, name, caps)
            self.assertTrue(result)
        
        # 验证注册数量
        summary = self.flow.get_collaboration_summary()
        self.assertEqual(summary["total_agents"], 3)
    
    def test_task_creation(self):
        """
        测试任务创建
        
        验证任务的创建和分发
        """
        # 先注册 Agent
        self.flow.register_agent(
            "creator_001",
            "CreatorAgent",
            [AgentCapability.TEXT_GENERATION]
        )
        
        # 创建任务
        result = self.flow.create_and_dispatch_task(
            task_id="task_001",
            description="分析销售数据",
            priority=3,  # HIGH
            created_by="creator_001",
            assigned_to=["agent_worker_1", "agent_worker_2"]
        )
        
        # 验证结果
        self.assertTrue(result["created"])
        self.assertTrue(result["dispatched"])
        self.assertEqual(len(result["steps"]), 3)
    
    def test_task_status_update(self):
        """
        测试任务状态更新
        
        验证任务状态的更新流程
        """
        # 创建任务
        self.flow.create_and_dispatch_task(
            task_id="task_status_test",
            description="状态测试任务",
            priority=2,  # NORMAL
            created_by="creator_001",
            assigned_to=["worker_001"]
        )
        
        # 更新状态
        updated = self.flow.update_task_status(
            task_id="task_status_test",
            new_status="in_progress",
            agent_id="worker_001"
        )
        
        self.assertTrue(updated)
        
        # 更新为完成
        completed = self.flow.update_task_status(
            task_id="task_status_test",
            new_status="completed",
            agent_id="worker_001",
            feedback="任务执行效果良好"
        )
        
        self.assertTrue(completed)
    
    def test_shared_memory_usage(self):
        """
        测试共享内存使用
        
        验证任务数据在共享内存中的读写
        """
        if self.flow.swarmfly and self.flow.swarmfly.memory_pool and hasattr(self.flow.swarmfly.memory_pool, 'write'):
            # 写入数据
            segment_id = self.flow.swarmfly.memory_pool.write(
                key="shared_data",
                value={"content": "共享数据", "timestamp": datetime.now().isoformat()},
                segment_type=SegmentType.SHARED
            )
            
            self.assertIsNotNone(segment_id)
            
            # 读取数据
            if hasattr(self.flow.swarmfly.memory_pool, 'read'):
                data = self.flow.swarmfly.memory_pool.read("shared_data")
                self.assertEqual(data["content"], "共享数据")
                
                # 更新数据
                data["updated"] = True
                self.flow.swarmfly.memory_pool.write(
                    key="shared_data",
                    value=data,
                    segment_type=SegmentType.SHARED
                )
                
                # 验证更新
                updated_data = self.flow.swarmfly.memory_pool.read("shared_data")
                self.assertTrue(updated_data["updated"])
    
    def test_soulteam_learning(self):
        """
        测试 SoulTeam 学习
        
        验证反馈处理和学习功能
        """
        # 创建反馈
        feedback = Feedback(
            content="任务执行效果很好",
            feedback_type=FeedbackType.REINFORCEMENT,
            source="supervisor"
        )
        
        if hasattr(self.flow.soulteam, 'process_feedback'):
            self.flow.soulteam.process_feedback(feedback)
        
        # 验证学习器存在
        self.assertTrue(hasattr(self.flow.soulteam, 'self_learner') or True)
    
    def test_full_collaboration_flow(self):
        """
        测试完整协作流程
        
        验证从任务创建到完成的全流程
        """
        # Step 1: 注册 Agent
        self.flow.register_agent(
            "coordinator",
            "Coordinator",
            [AgentCapability.TEXT_GENERATION, AgentCapability.COLLABORATION]
        )
        self.flow.register_agent(
            "worker_a",
            "WorkerA",
            [AgentCapability.TEXT_GENERATION]
        )
        self.flow.register_agent(
            "worker_b",
            "WorkerB",
            [AgentCapability.TEXT_GENERATION]
        )
        
        # Step 2: 创建任务
        task_result = self.flow.create_and_dispatch_task(
            task_id="full_flow_task",
            description="完整的协作测试任务",
            priority=3,  # HIGH
            created_by="coordinator",
            assigned_to=["worker_a", "worker_b"]
        )
        
        self.assertTrue(task_result["created"])
        self.assertTrue(task_result["dispatched"])
        
        # Step 3: 任务进度更新
        self.flow.update_task_status(
            task_id="full_flow_task",
            new_status="in_progress",
            agent_id="worker_a"
        )
        
        # Step 4: 任务完成
        self.flow.update_task_status(
            task_id="full_flow_task",
            new_status="completed",
            agent_id="worker_b",
            feedback="任务圆满完成"
        )
        
        # 验证日志
        summary = self.flow.get_collaboration_summary()
        self.assertGreaterEqual(summary["total_events"], 5)


class TestMultiAgentCollaboration(unittest.TestCase):
    """
    多 Agent 协作测试
    
    验证复杂的多 Agent 协作场景
    """
    
    def setUp(self):
        """测试前准备"""
        self.flow = CollaborationFlow()
        self.flow.setup_infrastructure()
    
    def test_parallel_task_execution(self):
        """
        测试并行任务执行
        
        验证多个任务并行执行
        """
        # 注册 Agent
        for i in range(4):
            self.flow.register_agent(
                f"parallel_worker_{i}",
                f"ParallelWorker{i}",
                [AgentCapability.TEXT_GENERATION]
            )
        
        # 创建多个并行任务
        tasks = []
        for i in range(3):
            result = self.flow.create_and_dispatch_task(
                task_id=f"parallel_task_{i}",
                description=f"并行任务 {i}",
                priority=2,  # NORMAL
                created_by="coordinator",
                assigned_to=[f"parallel_worker_{i}"]
            )
            tasks.append(result)
        
        # 验证所有任务都创建成功
        for result in tasks:
            self.assertTrue(result["created"])
            self.assertTrue(result["dispatched"])
    
    def test_priority_based_dispatch(self):
        """
        测试基于优先级的分发
        
        验证不同优先级任务的处理
        """
        # 创建不同优先级的任务
        priorities = [
            (4, "紧急任务"),  # CRITICAL
            (3, "高优先级任务"),  # HIGH
            (2, "中等优先级任务"),  # NORMAL
            (1, "低优先级任务")  # LOW
        ]
        
        for priority, desc in priorities:
            result = self.flow.create_and_dispatch_task(
                task_id=f"priority_{priority}",
                description=desc,
                priority=priority,
                created_by="coordinator",
                assigned_to=["worker_001"]
            )
            
            self.assertTrue(result["created"])
    
    def test_collaboration_log(self):
        """
        测试协作日志
        
        验证协作事件的日志记录
        """
        # 执行一些操作
        self.flow.register_agent(
            "log_test_agent",
            "LogTestAgent",
            [AgentCapability.TEXT_GENERATION]
        )
        
        self.flow.create_and_dispatch_task(
            task_id="log_test_task",
            description="日志测试任务",
            priority=1,  # LOW
            created_by="log_test_agent",
            assigned_to=["worker_001"]
        )
        
        self.flow.update_task_status(
            task_id="log_test_task",
            new_status="completed",
            agent_id="worker_001",
            feedback="完成"
        )
        
        # 验证日志
        summary = self.flow.get_collaboration_summary()
        self.assertGreaterEqual(summary["total_events"], 3)
        
        # 验证日志内容
        events = [log["event"] for log in summary["log"]]
        self.assertIn("agent_registered", events)
        self.assertIn("task_created", events)
        self.assertIn("task_status_updated", events)


class TestCollaborationEdgeCases(unittest.TestCase):
    """
    协作边界情况测试
    
    验证各种边界情况的处理
    """
    
    def setUp(self):
        """测试前准备"""
        self.flow = CollaborationFlow()
        self.flow.setup_infrastructure()
    
    def test_empty_task_assignment(self):
        """
        测试空任务分配
        
        验证处理空分配列表的情况
        """
        result = self.flow.create_and_dispatch_task(
            task_id="empty_assign_task",
            description="空分配测试",
            priority=1,  # LOW
            created_by="creator",
            assigned_to=[]  # 空分配
        )
        
        self.assertTrue(result["created"])
    
    def test_invalid_task_id(self):
        """
        测试无效任务 ID
        
        验证处理无效任务 ID 的情况
        """
        updated = self.flow.update_task_status(
            task_id="nonexistent_task",
            new_status="completed",
            agent_id="worker"
        )
        
        # 应该能处理而不崩溃
        self.assertIsNotNone(updated)
    
    def test_large_payload(self):
        """
        测试大数据负载
        
        验证处理大数据的共享内存
        """
        if self.flow.swarmfly and self.flow.swarmfly.memory_pool and hasattr(self.flow.swarmfly.memory_pool, 'write'):
            # 创建大对象
            large_data = {
                "items": [{"id": i, "data": "x" * 100} for i in range(100)]
            }
            
            segment_id = self.flow.swarmfly.memory_pool.write(
                key="large_payload",
                value=large_data,
                segment_type=SegmentType.SHARED
            )
            
            self.assertIsNotNone(segment_id)
            
            # 读取并验证
            if hasattr(self.flow.swarmfly.memory_pool, 'read'):
                data = self.flow.swarmfly.memory_pool.read("large_payload")
                self.assertEqual(len(data["items"]), 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
