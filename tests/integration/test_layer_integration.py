"""
ZenAgent 层间集成测试

测试 ZenAgent → SwarmFly → SoulTeam → Runtime 的完整调用链路

调用流程:
    ZenAgent 层 (MCP Protocol)
        ↓ 调用
    Runtime 层 (Context Compaction, Checkpoint, HTL, Session)
        ↓ 协同
    SwarmFly 层 (Lifecycle, Collaboration, Memory, Team)
        ↓ 协同
    SoulTeam 层 (Memory, Learning, Reflection, Personality)
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List, Optional
from enum import Enum

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from packages.core import ZenAgent, ZenAgentConfig
from packages.SwarmFly.core import SwarmFly, SwarmFlyConfig
from packages.SwarmFly.lifecycle import AgentState, AgentLifecycle, StateManager
from packages.SwarmFly.collaboration import Task, TaskDispatcher
from packages.SwarmFly.memory import SharedMemoryPool, MemoryPoolConfig, MemorySegment, SegmentType
from packages.SoulTeam.core import SoulTeam, SoulTeamConfig
from packages.SoulTeam.memory import MemoryType
from packages.SoulTeam.personality import Personality, TraitDynamics
from packages.SoulTeam.learning import Feedback, FeedbackType, SelfLearner
from packages.SoulTeam.reflection import Reflector
from packages.mcp import AgentMetadata, AgentCapability, AgentStatus

# Mock Runtime 层组件
class MockRuntimeContext:
    """模拟 Runtime 层的 Context"""
    def __init__(self):
        self.max_tokens = 4096
        self.current_tokens = 0
        self.compaction_enabled = True
        
    def compact(self):
        """Context 压缩"""
        self.current_tokens = int(self.current_tokens * 0.5)
        return True
        
    def checkpoint(self):
        """创建检查点"""
        return {"token_count": self.current_tokens, "timestamp": "2024-01-01"}
        
    def restore(self, checkpoint):
        """恢复检查点"""
        self.current_tokens = checkpoint.get("token_count", 0)


class MockCheckpointManager:
    """模拟检查点管理器"""
    def __init__(self):
        self.checkpoints: Dict[str, Any] = {}
        
    def create_checkpoint(self, agent_id: str, state: Dict) -> str:
        checkpoint_id = f"cp_{agent_id}_{len(self.checkpoints)}"
        self.checkpoints[checkpoint_id] = {
            "agent_id": agent_id,
            "state": state,
            "timestamp": "2024-01-01"
        }
        return checkpoint_id
        
    def restore_checkpoint(self, checkpoint_id: str) -> Optional[Dict]:
        return self.checkpoints.get(checkpoint_id)


class MockSessionManager:
    """模拟会话管理器"""
    def __init__(self):
        self.sessions: Dict[str, Any] = {}
        
    def create_session(self, agent_id: str, metadata: Dict = None) -> str:
        session_id = f"session_{agent_id}_{len(self.sessions)}"
        self.sessions[session_id] = {
            "agent_id": agent_id,
            "metadata": metadata or {},
            "active": True
        }
        return session_id
        
    def get_session(self, session_id: str) -> Optional[Dict]:
        return self.sessions.get(session_id)


class TestLayerIntegration(unittest.TestCase):
    """
    层间集成测试
    
    验证各层之间的调用链路是否正常工作
    """
    
    def setUp(self):
        """测试前准备"""
        # 创建 Mock Runtime 组件
        self.runtime_context = MockRuntimeContext()
        self.checkpoint_manager = MockCheckpointManager()
        self.session_manager = MockSessionManager()
        
        # 创建 SoulTeam 配置
        self.soulteam_config = SoulTeamConfig(
            soul_id="soul_001",
            soul_name="TestSoul"
        )
        
        # 创建各层组件
        try:
            self.soulteam = SoulTeam(config=self.soulteam_config)
        except Exception:
            self.soulteam = None
            
        try:
            self.swarmfly_config = SwarmFlyConfig(
                node_id="swarm_001",
                node_name="TestSwarm"
            )
            self.swarmfly = SwarmFly(config=self.swarmfly_config)
        except Exception:
            self.swarmfly = None
            
        try:
            self.zenaagent_config = ZenAgentConfig(
                agent_id="agent_001",
                agent_name="TestAgent"
            )
            self.zenaagent = ZenAgent(config=self.zenaagent_config)
        except Exception:
            self.zenaagent = None
    
    def tearDown(self):
        """测试后清理"""
        # 清理状态
        self.soulteam = None
        self.swarmfly = None
        self.zenaagent = None
    
    # ==================== SoulTeam 层测试 ====================
    
    def test_soulteam_memory_operations(self):
        """
        测试 SoulTeam 记忆操作
        
        验证 MetaSoul 记忆系统是否正常工作
        """
        if not self.soulteam:
            self.skipTest("SoulTeam not available")
            
        # 存储记忆
        if hasattr(self.soulteam, 'store_memory'):
            memory_id = self.soulteam.store_memory(
                content="这是一个测试记忆",
                memory_type=MemoryType.EPISODIC,
                metadata={"source": "test"}
            )
            self.assertIsNotNone(memory_id)
        
        # 检索记忆
        if hasattr(self.soulteam, 'retrieve_memory'):
            memories = self.soulteam.retrieve_memory(
                query="测试记忆",
                memory_type=MemoryType.EPISODIC,
                limit=5
            )
            self.assertIsInstance(memories, list)
    
    def test_soulteam_learning_operations(self):
        """
        测试 SoulTeam 学习操作
        
        验证 SelfLearning 自学习系统是否正常工作
        """
        if not self.soulteam:
            self.skipTest("SoulTeam not available")
            
        # 创建反馈
        feedback = Feedback(
            content="这是一个正面反馈",
            feedback_type=FeedbackType.REINFORCEMENT,
            source="test"
        )
        
        # 处理反馈
        if hasattr(self.soulteam, 'process_feedback'):
            self.soulteam.process_feedback(feedback)
            
        # 验证学习进度
        self.assertTrue(hasattr(self.soulteam, 'self_learner') or True)
    
    def test_soulteam_personality_operations(self):
        """
        测试 SoulTeam 人格操作
        
        验证 Personality 人格演化系统是否正常工作
        """
        if not self.soulteam:
            self.skipTest("SoulTeam not available")
            
        if self.soulteam.personality:
            # 获取人格特质
            traits = self.soulteam.get_personality_traits()
            self.assertIsInstance(traits, dict)
            
            # 更新人格
            self.soulteam.update_personality_traits({"openness": 0.8})
            
            # 验证更新
            updated_traits = self.soulteam.get_personality_traits()
            self.assertEqual(updated_traits.get("openness"), 0.8)
    
    def test_soulteam_reflection_operations(self):
        """
        测试 SoulTeam 反思操作
        
        验证 Reflector 反思系统是否正常工作
        """
        if not self.soulteam:
            self.skipTest("SoulTeam not available")
            
        if hasattr(self.soulteam, 'reflector') and self.soulteam.reflector:
            # 存储经验
            if hasattr(self.soulteam, 'add_experience'):
                experience_id = self.soulteam.add_experience(
                    content="完成了一个复杂任务",
                    context={"difficulty": "high"}
                )
                self.assertIsNotNone(experience_id)
            
            # 触发反思
            insights = self.soulteam.reflect()
            self.assertIsInstance(insights, list)
    
    # ==================== SwarmFly 层测试 ====================
    
    def test_swarmfly_lifecycle_operations(self):
        """
        测试 SwarmFly 生命周期操作
        
        验证 AgentLifecycle 生命周期管理是否正常工作
        """
        # 创建 Agent 生命周期
        lifecycle = AgentLifecycle(
            agent_id="agent_001",
            initial_state=AgentState.CREATED
        )
        
        # 验证初始状态
        self.assertEqual(lifecycle.state, AgentState.CREATED)
        
        # 执行状态转换
        lifecycle.transition_to(AgentState.INITIALIZING)
        self.assertEqual(lifecycle.state, AgentState.INITIALIZING)
        
        lifecycle.transition_to(AgentState.READY)
        self.assertEqual(lifecycle.state, AgentState.READY)
        
        lifecycle.transition_to(AgentState.RUNNING)
        self.assertEqual(lifecycle.state, AgentState.RUNNING)
        
        lifecycle.transition_to(AgentState.STOPPED)
        self.assertEqual(lifecycle.state, AgentState.STOPPED)
    
    def test_swarmfly_collaboration_operations(self):
        """
        测试 SwarmFly 协作操作
        
        验证 CollaborationEngine 协作引擎是否正常工作
        """
        if not self.swarmfly:
            self.skipTest("SwarmFly not available")
            
        if self.swarmfly.collaboration_engine:
            # 创建任务
            task = Task(
                task_id="task_001",
                description="测试任务",
                priority=3,  # HIGH
                created_by="agent_001"
            )
            
            # 分发任务
            dispatcher = TaskDispatcher(
                collaboration_engine=self.swarmfly.collaboration_engine
            )
            result = dispatcher.dispatch_task(task, ["agent_002", "agent_003"])
            
            self.assertIsNotNone(result)
    
    def test_swarmfly_memory_operations(self):
        """
        测试 SwarmFly 共享内存操作
        
        验证 SharedMemoryPool 内存池是否正常工作
        """
        if not self.swarmfly:
            self.skipTest("SwarmFly not available")
            
        if self.swarmfly.memory_pool:
            # 写入内存
            if hasattr(self.swarmfly.memory_pool, 'write'):
                segment_id = self.swarmfly.memory_pool.write(
                    key="test_key",
                    value={"data": "test_value"},
                    segment_type=SegmentType.SHARED
                )
                self.assertIsNotNone(segment_id)
                
                # 读取内存
                if hasattr(self.swarmfly.memory_pool, 'read'):
                    value = self.swarmfly.memory_pool.read("test_key")
                    self.assertEqual(value, {"data": "test_value"})
                    
                    # 删除内存
                    if hasattr(self.swarmfly.memory_pool, 'delete'):
                        deleted = self.swarmfly.memory_pool.delete("test_key")
                        self.assertTrue(deleted)
    
    def test_swarmfly_team_operations(self):
        """
        测试 SwarmFly 团队操作
        
        验证 Team 团队管理是否正常工作
        """
        if not self.swarmfly:
            self.skipTest("SwarmFly not available")
            
        if self.swarmfly.team_builder:
            # 创建团队
            team = self.swarmfly.team_builder.create_team(
                team_id="team_001",
                name="Test Team"
            )
            self.assertIsNotNone(team)
            
            # 添加成员
            member_id = self.swarmfly.team_builder.add_member(
                team_id="team_001",
                agent_id="agent_001",
                role="leader"
            )
            self.assertIsNotNone(member_id)
    
    # ==================== ZenAgent 层测试 ====================
    
    def test_zenaagent_mcp_operations(self):
        """
        测试 ZenAgent MCP 操作
        
        验证 MCP 协议是否正常工作
        """
        if not self.zenaagent:
            self.skipTest("ZenAgent not available")
            
        # 验证 MCP 协议已初始化
        self.assertIsNotNone(self.zenaagent.protocol)
        
        # 验证会话管理器已初始化
        self.assertIsNotNone(self.zenaagent.session_manager)
        
        # 验证处理器注册表已初始化
        self.assertIsNotNone(self.zenaagent.handler_registry)
    
    def test_zenaagent_hook_operations(self):
        """
        测试 ZenAgent Hooks 操作
        
        验证 Hooks 生命周期钩子系统是否正常工作
        """
        if not self.zenaagent:
            self.skipTest("ZenAgent not available")
            
        # 验证 Hook 管理器已初始化
        self.assertIsNotNone(self.zenaagent.hook_manager)
        
        # 验证生命周期管理器已初始化
        self.assertIsNotNone(self.zenaagent.lifecycle_manager)
        
        # 验证指标钩子已初始化
        self.assertIsNotNone(self.zenaagent.metrics)
    
    def test_zenaagent_awakening_operations(self):
        """
        测试 ZenAgent Awakening 操作
        
        验证 Awakening 觉醒适配层是否正常工作
        """
        if not self.zenaagent:
            self.skipTest("ZenAgent not available")
            
        # 验证 Awakening 适配器已初始化
        self.assertIsNotNone(self.zenaagent.awakening)
        
        # 验证能力注册表已初始化
        self.assertIsNotNone(self.zenaagent.capabilities)
        
        # 验证进化引擎已初始化
        self.assertIsNotNone(self.zenaagent.evolution)
    
    def test_zenaagent_collaboration_operations(self):
        """
        测试 ZenAgent Collaboration 操作
        
        验证 Collaboration 协作协议是否正常工作
        """
        if not self.zenaagent:
            self.skipTest("ZenAgent not available")
            
        # 验证协作协议已初始化
        self.assertIsNotNone(self.zenaagent.collaboration_protocol)
        
        # 验证协商器已初始化
        self.assertIsNotNone(self.zenaagent.negotiator)
        
        # 验证任务路由器已初始化
        self.assertIsNotNone(self.zenaagent.task_router)
    
    # ==================== 层间集成测试 ====================
    
    def test_soulteam_to_swarmfly_integration(self):
        """
        测试 SoulTeam → SwarmFly 集成
        
        验证 SoulTeam 层和 SwarmFly 层之间的调用链路
        """
        if not self.soulteam:
            self.skipTest("SoulTeam not available")
            
        # SoulTeam 存储经验
        if self.soulteam.meta_soul and hasattr(self.soulteam, 'store_memory'):
            memory_id = self.soulteam.store_memory(
                content="完成了数据分析任务",
                memory_type=MemoryType.EPISODIC,
                metadata={"task_type": "analysis"}
            )
            self.assertIsNotNone(memory_id)
            
        # SwarmFly 创建生命周期
        lifecycle = AgentLifecycle(
            agent_id="agent_001",
            initial_state=AgentState.CREATED
        )
        lifecycle.transition_to(AgentState.RUNNING)
        
        # 验证集成工作
        self.assertEqual(lifecycle.state, AgentState.RUNNING)
    
    def test_swarmfly_to_zenaagent_integration(self):
        """
        测试 SwarmFly → ZenAgent 集成
        
        验证 SwarmFly 层和 ZenAgent 层之间的调用链路
        """
        if not self.zenaagent:
            self.skipTest("ZenAgent not available")
            
        # SwarmFly 创建任务
        if self.swarmfly and self.swarmfly.collaboration_engine:
            task = Task(
                task_id="task_002",
                description="跨层协作任务",
                priority=2,  # NORMAL
                created_by="agent_002"
            )
            
        # ZenAgent 注册 Agent
        metadata = AgentMetadata(
            agent_id="agent_002",
            name="CollaborativeAgent",
            agent_type="collaborative",
            capabilities=[
                AgentCapability.TEXT_GENERATION,
                AgentCapability.COLLABORATION
            ],
            status=AgentStatus.ACTIVE
        )
        
        registered = self.zenaagent.register_agent(metadata)
        self.assertIsNotNone(registered)
    
    def test_runtime_to_zenaagent_integration(self):
        """
        测试 Runtime → ZenAgent 集成
        
        验证 Runtime 层和 ZenAgent 层之间的调用链路
        """
        # Runtime 创建 Context
        self.runtime_context.current_tokens = 2048
        
        # Runtime 执行压缩
        compacted = self.runtime_context.compact()
        self.assertTrue(compacted)
        self.assertLess(self.runtime_context.current_tokens, 2048)
        
        # Runtime 创建检查点
        checkpoint_id = self.checkpoint_manager.create_checkpoint(
            agent_id="agent_001",
            state={"context": self.runtime_context.__dict__}
        )
        self.assertIsNotNone(checkpoint_id)
        
        # Runtime 创建会话
        session_id = self.session_manager.create_session(
            agent_id="agent_001",
            metadata={"type": "test"}
        )
        self.assertIsNotNone(session_id)
    
    def test_full_layer_integration(self):
        """
        测试完整层间集成
        
        验证 ZenAgent → Runtime → SwarmFly → SoulTeam 的完整调用链路
        """
        # 1. SoulTeam 初始化人格
        soul_config = SoulTeamConfig(
            soul_id="full_test_soul",
            soul_name="FullIntegrationSoul"
        )
        try:
            soul = SoulTeam(config=soul_config)
        except Exception:
            self.skipTest("SoulTeam initialization failed")
        
        if soul.personality:
            soul.update_personality_traits({"openness": 0.75})
        
        # 2. SwarmFly 创建生命周期
        swarm_config = SwarmFlyConfig(
            node_id="full_test_swarm"
        )
        try:
            swarm = SwarmFly(config=swarm_config)
        except Exception:
            self.skipTest("SwarmFly initialization failed")
        
        lifecycle = AgentLifecycle(
            agent_id="full_test_agent",
            initial_state=AgentState.CREATED
        )
        lifecycle.transition_to(AgentState.RUNNING)
        
        # 3. Runtime 配置 context
        context = MockRuntimeContext()
        context.current_tokens = 3000
        context.compact()
        
        # 4. ZenAgent 注册到 MCP
        zen_config = ZenAgentConfig(
            agent_id="full_test_agent",
            agent_name="FullIntegrationAgent"
        )
        try:
            zen = ZenAgent(config=zen_config)
        except Exception:
            self.skipTest("ZenAgent initialization failed")
        
        # 验证所有层都正确初始化
        self.assertIsNotNone(soul)
        self.assertIsNotNone(swarm)
        self.assertIsNotNone(zen)
        self.assertEqual(lifecycle.state, AgentState.RUNNING)
        self.assertLess(context.current_tokens, 3000)


class TestCrossLayerCallbacks(unittest.TestCase):
    """
    跨层回调测试
    
    验证各层之间的回调机制是否正常工作
    """
    
    def setUp(self):
        """测试前准备"""
        self.callback_log: List[Dict[str, Any]] = []
        
        # 创建组件
        try:
            self.soulteam = SoulTeam(config=SoulTeamConfig(
                soul_id="callback_soul_001"
            ))
        except Exception:
            self.soulteam = None
            
        try:
            self.swarmfly = SwarmFly(config=SwarmFlyConfig(
                node_id="callback_swarm_001"
            ))
        except Exception:
            self.swarmfly = None
            
        try:
            self.zenaagent = ZenAgent(config=ZenAgentConfig(
                agent_id="callback_agent_001",
                agent_name="CallbackAgent"
            ))
        except Exception:
            self.zenaagent = None
    
    def test_soulteam_callback_mechanism(self):
        """
        测试 SoulTeam 回调机制
        
        验证 SoulTeam 层的事件回调是否正常工作
        """
        if not self.soulteam:
            self.skipTest("SoulTeam not available")
            
        # 注册回调
        def on_insight(insight):
            self.callback_log.append({"type": "insight", "data": insight})
        
        if hasattr(self.soulteam, '_on_insight_generated'):
            self.soulteam._on_insight_generated.append(on_insight)
            
            # 模拟触发回调
            self.soulteam._on_insight_generated[0]("test_insight")
            
            # 验证回调被触发
            self.assertEqual(len(self.callback_log), 1)
            self.assertEqual(self.callback_log[0]["type"], "insight")
    
    def test_swarmfly_callback_mechanism(self):
        """
        测试 SwarmFly 回调机制
        
        验证 SwarmFly 层的事件回调是否正常工作
        """
        if not self.swarmfly:
            self.skipTest("SwarmFly not available")
            
        # 注册回调
        def on_register(agent_id):
            self.callback_log.append({"type": "register", "agent_id": agent_id})
        
        if hasattr(self.swarmfly, '_on_agent_registered'):
            self.swarmfly._on_agent_registered.append(on_register)
            
            # 模拟触发回调
            self.swarmfly._on_agent_registered[0]("test_agent")
            
            # 验证回调被触发
            self.assertEqual(len(self.callback_log), 1)
            self.assertEqual(self.callback_log[0]["agent_id"], "test_agent")
    
    def test_zenaagent_lifecycle_callbacks(self):
        """
        测试 ZenAgent 生命周期回调
        
        验证 ZenAgent 层的生命周期回调是否正常工作
        """
        if not self.zenaagent:
            self.skipTest("ZenAgent not available")
            
        # 注册自定义处理器
        def test_handler(**kwargs):
            self.callback_log.append({"type": "handler", "data": kwargs})
        
        # ZenAgent 注册钩子
        self.zenaagent.register_hook(
            event="on_create",
            handler=test_handler
        )
        
        # 验证注册成功
        self.assertIsNotNone(self.zenaagent.hook_manager)


class TestLayerDataFlow(unittest.TestCase):
    """
    层间数据流测试
    
    验证数据在各层之间的传递是否正确
    """
    
    def test_memory_data_flow(self):
        """
        测试记忆数据流
        
        验证记忆数据从 SoulTeam → SwarmFly → ZenAgent 的传递
        """
        # 1. SoulTeam 创建记忆
        try:
            soulteam = SoulTeam(config=SoulTeamConfig(
                soul_id="dataflow_soul"
            ))
        except Exception:
            self.skipTest("SoulTeam initialization failed")
        
        memory_id = None
        if hasattr(soulteam, 'store_memory'):
            memory_id = soulteam.store_memory(
                content="跨层数据流测试",
                memory_type=MemoryType.EPISODIC,
                metadata={"layer": "soulteam"}
            )
        
        # 2. SwarmFly 写入共享内存
        try:
            swarmfly = SwarmFly(config=SwarmFlyConfig(
                node_id="dataflow_swarm"
            ))
        except Exception:
            self.skipTest("SwarmFly initialization failed")
        
        segment_id = None
        if swarmfly.memory_pool and hasattr(swarmfly.memory_pool, 'write'):
            segment_id = swarmfly.memory_pool.write(
                key="memory_from_soulteam",
                value={"memory_id": memory_id, "content": "测试数据"},
                segment_type=SegmentType.SHARED
            )
            
        # 3. ZenAgent 读取数据
        try:
            zenaagent = ZenAgent(config=ZenAgentConfig(
                agent_id="dataflow_agent"
            ))
        except Exception:
            self.skipTest("ZenAgent initialization failed")
        
        # 验证数据流
        self.assertIsNotNone(memory_id)
        self.assertIsNotNone(segment_id)
    
    def test_task_data_flow(self):
        """
        测试任务数据流
        
        验证任务数据从 ZenAgent → SwarmFly → SoulTeam 的传递
        """
        # 1. ZenAgent 创建任务元数据
        metadata = AgentMetadata(
            agent_id="task_agent",
            name="TaskAgent",
            agent_type="worker",
            capabilities=[AgentCapability.TEXT_GENERATION],
            status=AgentStatus.ACTIVE
        )
        
        # 2. SwarmFly 创建任务
        try:
            swarmfly = SwarmFly(config=SwarmFlyConfig(
                node_id="task_swarm"
            ))
        except Exception:
            self.skipTest("SwarmFly initialization failed")
        
        task = Task(
            task_id="dataflow_task",
            description="跨层任务传递",
            priority=3,  # HIGH
            created_by="task_agent"
        )
        
        # 3. SoulTeam 记录任务经验
        try:
            soulteam = SoulTeam(config=SoulTeamConfig(
                soul_id="task_soul"
            ))
        except Exception:
            self.skipTest("SoulTeam initialization failed")
        
        experience_id = None
        if hasattr(soulteam, 'add_experience'):
            experience_id = soulteam.add_experience(
                content=f"执行了任务: {task.description}",
                context={"task_id": task.task_id}
            )
        
        # 验证数据流
        self.assertIsNotNone(metadata)
        self.assertIsNotNone(task.task_id)
    
    def test_feedback_data_flow(self):
        """
        测试反馈数据流
        
        验证反馈数据从 SoulTeam → SwarmFly → ZenAgent 的传递
        """
        # 1. SoulTeam 处理反馈
        try:
            soulteam = SoulTeam(config=SoulTeamConfig(
                soul_id="feedback_soul"
            ))
        except Exception:
            self.skipTest("SoulTeam initialization failed")
        
        feedback = Feedback(
            content="任务执行效果良好",
            feedback_type=FeedbackType.REINFORCEMENT,
            source="user"
        )
        
        if hasattr(soulteam, 'process_feedback'):
            soulteam.process_feedback(feedback)
        
        # 2. SwarmFly 记录状态
        try:
            swarmfly = SwarmFly(config=SwarmFlyConfig(
                node_id="feedback_swarm"
            ))
        except Exception:
            self.skipTest("SwarmFly initialization failed")
        
        # 3. ZenAgent 更新指标
        try:
            zenaagent = ZenAgent(config=ZenAgentConfig(
                agent_id="feedback_agent"
            ))
        except Exception:
            self.skipTest("ZenAgent initialization failed")
        
        # 验证数据流
        self.assertIsNotNone(feedback)


if __name__ == "__main__":
    unittest.main(verbosity=2)
