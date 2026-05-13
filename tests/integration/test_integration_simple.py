"""
ZenAgent 简化版集成测试

针对当前 ZenAgent 模块的实际状态进行测试
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from packages.SwarmFly.core import SwarmFly, SwarmFlyConfig
from packages.SwarmFly.lifecycle import AgentState, AgentLifecycle, InvalidTransitionError
from packages.SwarmFly.collaboration import Task, TaskDispatcher, TaskPriority, TaskStatus, CollaborationConfig, CollaborationEngine
from packages.SwarmFly.memory import SharedMemoryPool, SegmentType, MemorySegment


class TestSwarmFlyCore(unittest.TestCase):
    """SwarmFly 核心功能测试"""
    
    def test_swarmfly_initialization(self):
        """测试 SwarmFly 初始化"""
        config = SwarmFlyConfig(
            node_id="test_swarm",
            node_name="TestSwarm"
        )
        swarm = SwarmFly(config=config)
        
        self.assertIsNotNone(swarm)
        self.assertEqual(swarm.config.node_id, "test_swarm")
    
    def test_lifecycle_state_transitions(self):
        """测试生命周期状态转换"""
        lifecycle = AgentLifecycle(
            agent_id="test_agent",
            initial_state=AgentState.CREATED
        )
        
        # 验证初始状态
        self.assertEqual(lifecycle.state, AgentState.CREATED)
        
        # 执行转换
        lifecycle.transition_to(AgentState.INITIALIZING)
        self.assertEqual(lifecycle.state, AgentState.INITIALIZING)
        
        lifecycle.transition_to(AgentState.READY)
        self.assertEqual(lifecycle.state, AgentState.READY)
        
        lifecycle.transition_to(AgentState.RUNNING)
        self.assertEqual(lifecycle.state, AgentState.RUNNING)
        
        lifecycle.transition_to(AgentState.STOPPED)
        self.assertEqual(lifecycle.state, AgentState.STOPPED)


class TestCollaborationCore(unittest.TestCase):
    """协作核心功能测试"""
    
    def test_task_creation(self):
        """测试任务创建"""
        task = Task(
            task_id="test_task_001",
            name="测试任务",
            description="测试任务描述",
            priority=TaskPriority.HIGH
        )
        
        self.assertEqual(task.task_id, "test_task_001")
        self.assertEqual(task.name, "测试任务")
        self.assertEqual(task.priority, TaskPriority.HIGH)
    
    def test_task_status_update(self):
        """测试任务状态更新"""
        task = Task(
            task_id="test_task_002",
            name="测试任务",
            priority=TaskPriority.NORMAL
        )
        
        # 验证默认状态
        self.assertEqual(task.status, TaskStatus.PENDING)
        
        # 更新状态
        task.status = TaskStatus.RUNNING
        self.assertEqual(task.status, TaskStatus.RUNNING)
    
    def test_task_dispatcher_creation(self):
        """测试任务分发器创建"""
        dispatcher = TaskDispatcher()
        
        self.assertIsNotNone(dispatcher)
        self.assertIsNotNone(dispatcher._tasks)


class TestSharedMemory(unittest.TestCase):
    """共享内存测试"""
    
    def test_memory_pool_initialization(self):
        """测试内存池初始化"""
        pool = SharedMemoryPool(pool_id="test_pool", node_id="test_node")
        
        self.assertIsNotNone(pool)
        self.assertEqual(pool.pool_id, "test_pool")
    
    def test_segment_creation(self):
        """测试段创建"""
        pool = SharedMemoryPool(pool_id="test_pool", node_id="test_node")
        
        # 创建段
        segment = pool.create_segment(
            name="test_segment",
            segment_type=SegmentType.SHARED
        )
        
        self.assertIsNotNone(segment)
        self.assertEqual(segment.name, "test_segment")
    
    def test_segment_read_write(self):
        """测试段读写"""
        pool = SharedMemoryPool(pool_id="test_pool", node_id="test_node")
        
        # 创建段
        pool.create_segment(
            name="rw_segment",
            segment_type=SegmentType.SHARED
        )
        
        # 写入数据
        pool.write_with_lock(
            segment_name="rw_segment",
            agent_id="test_agent",
            data={"key": "value"}
        )
        
        # 读取数据
        data = pool.read_with_lock(
            segment_name="rw_segment",
            agent_id="test_agent"
        )
        
        self.assertEqual(data["key"], "value")


class TestAgentStateMachine(unittest.TestCase):
    """Agent 状态机测试"""
    
    def test_complete_lifecycle(self):
        """测试完整的生命周期"""
        lifecycle = AgentLifecycle(
            agent_id="lifecycle_test",
            initial_state=AgentState.CREATED
        )
        
        # 完整生命周期路径
        states = [
            AgentState.INITIALIZING,
            AgentState.READY,
            AgentState.RUNNING,
            AgentState.PAUSED,
            AgentState.RUNNING,
            AgentState.STOPPED,
            AgentState.DISPOSED
        ]
        
        for state in states:
            lifecycle.transition_to(state)
            self.assertEqual(lifecycle.state, state)
    
    def test_initializing_to_error(self):
        """测试初始化到错误状态的转换"""
        lifecycle = AgentLifecycle(
            agent_id="error_test",
            initial_state=AgentState.CREATED
        )
        
        # 转换到 INITIALIZING
        lifecycle.transition_to(AgentState.INITIALIZING)
        self.assertEqual(lifecycle.state, AgentState.INITIALIZING)
        
        # 从 INITIALIZING 可以转到 ERROR
        lifecycle.transition_to(AgentState.ERROR)
        self.assertEqual(lifecycle.state, AgentState.ERROR)


class TestTaskPriorities(unittest.TestCase):
    """任务优先级测试"""
    
    def test_priority_levels(self):
        """测试优先级级别"""
        tasks = []
        
        for priority in [TaskPriority.LOW, TaskPriority.NORMAL, TaskPriority.HIGH, TaskPriority.CRITICAL]:
            task = Task(
                task_id=f"priority_task_{priority.value}",
                name=f"优先级 {priority.value} 任务",
                priority=priority
            )
            tasks.append(task)
        
        # 验证优先级
        self.assertEqual(tasks[0].priority, TaskPriority.LOW)
        self.assertEqual(tasks[1].priority, TaskPriority.NORMAL)
        self.assertEqual(tasks[2].priority, TaskPriority.HIGH)
        self.assertEqual(tasks[3].priority, TaskPriority.CRITICAL)


class TestMemorySegments(unittest.TestCase):
    """内存段测试"""
    
    def test_segment_types(self):
        """测试内存段类型"""
        # 验证所有段类型存在
        self.assertIsNotNone(SegmentType.SHARED)
        self.assertIsNotNone(SegmentType.PRIVATE)
        self.assertIsNotNone(SegmentType.PROTECTED)
        self.assertIsNotNone(SegmentType.CACHED)
    
    def test_segment_operations(self):
        """测试段操作"""
        pool = SharedMemoryPool(pool_id="ops_pool", node_id="test_node")
        
        # 创建多个段
        for i in range(5):
            segment = pool.create_segment(
                name=f"segment_{i}",
                segment_type=SegmentType.SHARED
            )
            self.assertIsNotNone(segment)
        
        # 获取段
        segment = pool.get_segment("segment_2")
        self.assertIsNotNone(segment)
        
        # 删除段
        deleted = pool.delete_segment("segment_2")
        self.assertTrue(deleted)
        
        # 验证删除
        segment = pool.get_segment("segment_2")
        self.assertIsNone(segment)


class TestSwarmFlyComponents(unittest.TestCase):
    """SwarmFly 组件测试"""
    
    def test_collaboration_engine_init(self):
        """测试协作引擎初始化"""
        config = CollaborationConfig()
        engine = CollaborationEngine(config=config)
        
        self.assertIsNotNone(engine)
        self.assertEqual(engine.config, config)
    
    def test_task_dispatcher_init(self):
        """测试任务分发器初始化"""
        dispatcher = TaskDispatcher()
        
        self.assertIsNotNone(dispatcher)
        self.assertEqual(len(dispatcher._tasks), 0)


class TestIntegrationScenarios(unittest.TestCase):
    """集成场景测试"""
    
    def test_agent_creation_workflow(self):
        """测试 Agent 创建工作流"""
        # 1. 创建 SwarmFly 实例
        swarm = SwarmFly(config=SwarmFlyConfig(
            node_id="workflow_swarm",
            node_name="WorkflowSwarm"
        ))
        self.assertIsNotNone(swarm)
        
        # 2. 创建生命周期
        lifecycle = AgentLifecycle(
            agent_id="workflow_agent",
            initial_state=AgentState.CREATED
        )
        lifecycle.transition_to(AgentState.INITIALIZING)
        lifecycle.transition_to(AgentState.READY)
        lifecycle.transition_to(AgentState.RUNNING)
        
        self.assertEqual(lifecycle.state, AgentState.RUNNING)
        
        # 3. 创建任务
        task = Task(
            task_id="workflow_task",
            name="工作流测试任务",
            description="测试描述",
            priority=TaskPriority.HIGH
        )
        self.assertIsNotNone(task)
        
        # 4. 任务状态更新
        task.status = TaskStatus.RUNNING
        task.status = TaskStatus.COMPLETED
        
        # 5. 生命周期结束
        lifecycle.transition_to(AgentState.STOPPED)
        lifecycle.transition_to(AgentState.DISPOSED)
        
        self.assertEqual(lifecycle.state, AgentState.DISPOSED)
    
    def test_collaboration_workflow(self):
        """测试协作工作流"""
        # 1. 创建协作引擎
        engine = CollaborationEngine(config=CollaborationConfig())
        
        # 2. 创建任务分发器
        dispatcher = TaskDispatcher()
        
        # 3. 创建多个任务
        tasks = []
        for i in range(3):
            task = Task(
                task_id=f"collab_task_{i}",
                name=f"协作任务 {i}",
                priority=TaskPriority(3 - i)
            )
            tasks.append(task)
        
        # 验证任务创建
        self.assertEqual(len(tasks), 3)
        
        # 4. 更新任务状态
        for task in tasks:
            task.status = TaskStatus.RUNNING
            task.status = TaskStatus.COMPLETED
    
    def test_memory_sharing_workflow(self):
        """测试内存共享工作流"""
        # 1. 创建内存池
        pool = SharedMemoryPool(pool_id="sharing_pool", node_id="test_node")
        
        # 2. 写入共享数据
        pool.create_segment(
            name="shared_state",
            segment_type=SegmentType.SHARED
        )
        
        pool.write_with_lock(
            segment_name="shared_state",
            agent_id="agent_1",
            data={
                "task_results": [],
                "agent_states": {}
            }
        )
        
        # 3. 读取并更新
        current = pool.read_with_lock(
            segment_name="shared_state",
            agent_id="agent_2"
        )
        
        current["task_results"].append({"task_id": "new_task"})
        current["agent_states"]["agent_1"] = "running"
        
        pool.write_with_lock(
            segment_name="shared_state",
            agent_id="agent_2",
            data=current
        )
        
        # 4. 验证更新
        updated = pool.read_with_lock(
            segment_name="shared_state",
            agent_id="agent_1"
        )
        self.assertEqual(len(updated["task_results"]), 1)
        self.assertIn("agent_1", updated["agent_states"])


class TestErrorHandling(unittest.TestCase):
    """错误处理测试"""
    
    def test_invalid_state_transition(self):
        """测试无效状态转换"""
        lifecycle = AgentLifecycle(
            agent_id="error_test",
            initial_state=AgentState.CREATED
        )
        
        # 尝试非法转换 - 应该抛出异常
        with self.assertRaises(InvalidTransitionError):
            lifecycle.transition_to(AgentState.DISPOSED)
    
    def test_missing_segment(self):
        """测试缺失的段"""
        pool = SharedMemoryPool(pool_id="error_pool", node_id="test_node")
        
        # 读取不存在的段
        segment = pool.get_segment("nonexistent")
        self.assertIsNone(segment)
    
    def test_task_with_various_priorities(self):
        """测试不同优先级的任务"""
        # 创建各种优先级的任务
        for i, priority in enumerate(TaskPriority):
            task = Task(
                task_id=f"priority_test_{i}",
                name=f"测试 {priority.name}",
                priority=priority
            )
            self.assertEqual(task.priority, priority)


class TestMultiAgentScenario(unittest.TestCase):
    """多 Agent 场景测试"""
    
    def test_multiple_agents_lifecycle(self):
        """测试多 Agent 生命周期"""
        agents = []
        
        for i in range(5):
            lifecycle = AgentLifecycle(
                agent_id=f"agent_{i}",
                initial_state=AgentState.CREATED
            )
            
            # 每个 Agent 都经历完整生命周期
            lifecycle.transition_to(AgentState.INITIALIZING)
            lifecycle.transition_to(AgentState.READY)
            lifecycle.transition_to(AgentState.RUNNING)
            
            agents.append(lifecycle)
        
        # 验证所有 Agent 都在运行状态
        for agent in agents:
            self.assertEqual(agent.state, AgentState.RUNNING)
    
    def test_shared_memory_among_agents(self):
        """测试 Agent 间共享内存"""
        pool = SharedMemoryPool(pool_id="multi_agent_pool", node_id="test_node")
        
        # 创建共享段
        pool.create_segment(
            name="agent1_data",
            segment_type=SegmentType.SHARED
        )
        
        # Agent 1 写入
        pool.write_with_lock(
            segment_name="agent1_data",
            agent_id="agent_1",
            data={"from": "agent_1", "data": "test"}
        )
        
        # Agent 2 读取
        data = pool.read_with_lock(
            segment_name="agent1_data",
            agent_id="agent_2"
        )
        self.assertEqual(data["from"], "agent_1")
        
        # Agent 2 更新
        pool.write_with_lock(
            segment_name="agent1_data",
            agent_id="agent_2",
            data={"from": "agent_2", "data": "updated"}
        )
        
        # 验证更新
        updated = pool.read_with_lock(
            segment_name="agent1_data",
            agent_id="agent_1"
        )
        self.assertEqual(updated["from"], "agent_2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
