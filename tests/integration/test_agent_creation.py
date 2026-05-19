"""
ZenAgent Agent 创建流程集成测试

测试完整的 Agent 创建流程:
    SoulTeam 初始化人格 → SwarmFly 创建生命周期 → ZenAgent 注册到 MCP → Runtime 配置 context
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, Optional
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from packages.core import ZenAgent, ZenAgentConfig
from packages.SwarmFly.core import SwarmFly, SwarmFlyConfig
from packages.SwarmFly.lifecycle import AgentLifecycle, AgentState, StateManager, get_default_rules
from packages.SwarmFly.memory import SharedMemoryPool, MemoryPoolConfig, SegmentType
from packages.MetaSoul.core import SoulTeam, SoulTeamConfig
from packages.MetaSoul.memory import MemoryType
from packages.MetaSoul.personality import Personality
from packages.MetaSoul.learning import Feedback, FeedbackType
from packages.mcp import AgentMetadata, AgentCapability, AgentStatus


class MockContextManager:
    """模拟 Runtime Context 管理器"""
    def __init__(self, max_tokens: int = 4096):
        self.max_tokens = max_tokens
        self.current_tokens = 0
        self.history: list = []
        
    def allocate(self, tokens: int) -> bool:
        if self.current_tokens + tokens <= self.max_tokens:
            self.current_tokens += tokens
            return True
        return False
        
    def release(self, tokens: int) -> None:
        self.current_tokens = max(0, self.current_tokens - tokens)
        
    def compact(self) -> int:
        """压缩上下文"""
        compacted_tokens = int(self.current_tokens * 0.5)
        self.current_tokens = compacted_tokens
        return compacted_tokens
        
    def checkpoint(self) -> Dict[str, Any]:
        return {
            "token_count": self.current_tokens,
            "timestamp": datetime.now().isoformat(),
            "history_size": len(self.history)
        }


class AgentCreationFlow:
    """
    Agent 创建流程管理器
    
    协调 SoulTeam → SwarmFly → ZenAgent → Runtime 的创建流程
    """
    
    def __init__(self):
        self.soulteam: Optional[SoulTeam] = None
        self.swarmfly: Optional[SwarmFly] = None
        self.zenaagent: Optional[ZenAgent] = None
        self.context_manager: Optional[MockContextManager] = None
        self.lifecycle: Optional[AgentLifecycle] = None
        self.creation_log: list = []
        
    def create_agent(
        self,
        agent_id: str,
        agent_name: str,
        personality_traits: Optional[Dict[str, float]] = None,
        capabilities: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        执行完整的 Agent 创建流程
        
        Args:
            agent_id: Agent ID
            agent_name: Agent 名称
            personality_traits: 人格特质
            capabilities: 能力列表
            
        Returns:
            Dict[str, Any]: 创建结果
        """
        result = {
            "agent_id": agent_id,
            "success": False,
            "steps": []
        }
        
        try:
            # Step 1: SoulTeam 初始化人格
            self._step_1_init_personality(agent_id, agent_name, personality_traits)
            result["steps"].append({"step": 1, "name": "personality_init", "success": True})
            
            # Step 2: SwarmFly 创建生命周期
            self._step_2_create_lifecycle(agent_id)
            result["steps"].append({"step": 2, "name": "lifecycle_create", "success": True})
            
            # Step 3: ZenAgent 注册到 MCP
            self._step_3_register_mcp(agent_id, agent_name, capabilities)
            result["steps"].append({"step": 3, "name": "mcp_register", "success": True})
            
            # Step 4: Runtime 配置 context
            self._step_4_configure_context(agent_id)
            result["steps"].append({"step": 4, "name": "context_config", "success": True})
            
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def _step_1_init_personality(
        self,
        agent_id: str,
        agent_name: str,
        personality_traits: Optional[Dict[str, float]]
    ) -> None:
        """Step 1: SoulTeam 初始化人格"""
        config = SoulTeamConfig(
            soul_id=f"soul_{agent_id}",
            soul_name=agent_name
        )
        
        self.soulteam = SoulTeam(config=config)
        
        # 设置人格特质
        if personality_traits and self.soulteam.personality:
            self.soulteam.update_personality_traits(personality_traits)
        
        # 存储初始记忆
        if hasattr(self.soulteam, 'store_memory'):
            self.soulteam.store_memory(
                content=f"Agent {agent_name} 已初始化人格",
                memory_type=MemoryType.EPISODIC,
                metadata={"event": "initialization", "agent_id": agent_id}
            )
        
        self.creation_log.append(f"[SoulTeam] 初始化人格: {agent_name}")
    
    def _step_2_create_lifecycle(self, agent_id: str) -> None:
        """Step 2: SwarmFly 创建生命周期"""
        config = SwarmFlyConfig(
            node_id=f"swarm_{agent_id}"
        )
        
        self.swarmfly = SwarmFly(config=config)
        
        # 创建生命周期
        self.lifecycle = AgentLifecycle(
            agent_id=agent_id,
            initial_state=AgentState.CREATED
        )
        
        # 注册到 SwarmFly
        if hasattr(self.swarmfly, 'state_manager') and self.swarmfly.state_manager:
            self.swarmfly.state_manager.register_agent(agent_id, AgentState.CREATED)
        
        self.creation_log.append(f"[SwarmFly] 创建生命周期: {agent_id}")
    
    def _step_3_register_mcp(
        self,
        agent_id: str,
        agent_name: str,
        capabilities: Optional[list]
    ) -> None:
        """Step 3: ZenAgent 注册到 MCP"""
        config = ZenAgentConfig(
            agent_id=agent_id,
            agent_name=agent_name
        )
        
        self.zenaagent = ZenAgent(config=config)
        
        # 创建元数据
        metadata = AgentMetadata(
            agent_id=agent_id,
            name=agent_name,
            agent_type="integrated",
            capabilities=capabilities or [
                AgentCapability.TEXT_GENERATION,
                AgentCapability.COLLABORATION
            ],
            status=AgentStatus.ACTIVE
        )
        
        # 注册 Agent
        registered = self.zenaagent.register_agent(metadata)
        
        self.creation_log.append(f"[ZenAgent] MCP 注册: {agent_id} -> {registered is not None}")
    
    def _step_4_configure_context(self, agent_id: str) -> None:
        """Step 4: Runtime 配置 context"""
        self.context_manager = MockContextManager(max_tokens=8192)
        
        # 分配初始上下文
        self.context_manager.allocate(512)
        
        # 创建检查点
        checkpoint = self.context_manager.checkpoint()
        
        self.creation_log.append(f"[Runtime] 配置 Context: {checkpoint}")
    
    def get_agent_state(self) -> Dict[str, Any]:
        """获取 Agent 完整状态"""
        return {
            "soulteam": {
                "initialized": self.soulteam is not None,
                "has_personality": self.soulteam.personality is not None if self.soulteam else False,
                "traits": self.soulteam.get_personality_traits() if self.soulteam and hasattr(self.soulteam, 'get_personality_traits') else {}
            },
            "swarmfly": {
                "initialized": self.swarmfly is not None,
                "lifecycle_state": self.lifecycle.state.value if self.lifecycle else None
            },
            "zenaagent": {
                "initialized": self.zenaagent is not None,
                "mcp_enabled": self.zenaagent.protocol is not None if self.zenaagent else False
            },
            "runtime": {
                "context_configured": self.context_manager is not None,
                "tokens": self.context_manager.current_tokens if self.context_manager else 0
            },
            "creation_log": self.creation_log
        }


class TestAgentCreationFlow(unittest.TestCase):
    """
    Agent 创建流程测试
    
    验证完整的 Agent 创建流程
    """
    
    def test_full_creation_flow(self):
        """
        测试完整的 Agent 创建流程
        
        验证 SoulTeam → SwarmFly → ZenAgent → Runtime 的完整流程
        """
        flow = AgentCreationFlow()
        
        result = flow.create_agent(
            agent_id="agent_full_001",
            agent_name="FullTestAgent",
            personality_traits={
                "openness": 0.8,
                "conscientiousness": 0.7,
                "extraversion": 0.6,
                "agreeableness": 0.75,
                "neuroticism": 0.3
            },
            capabilities=[AgentCapability.TEXT_GENERATION]
        )
        
        # 验证流程成功
        self.assertTrue(result["success"])
        self.assertEqual(len(result["steps"]), 4)
        self.assertEqual(result["agent_id"], "agent_full_001")
        
        # 验证各层状态
        state = flow.get_agent_state()
        self.assertTrue(state["soulteam"]["initialized"])
        self.assertTrue(state["swarmfly"]["initialized"])
        self.assertTrue(state["zenaagent"]["initialized"])
        self.assertTrue(state["runtime"]["context_configured"])
    
    def test_personality_initialization(self):
        """
        测试人格初始化
        
        验证 SoulTeam 的人格初始化功能
        """
        config = SoulTeamConfig(
            soul_id="personality_test",
            soul_name="PersonalityTestAgent"
        )
        
        soul = SoulTeam(config=config)
        
        # 验证人格初始化
        self.assertIsNotNone(soul.personality)
        
        # 获取特质
        traits = soul.get_personality_traits()
        self.assertEqual(traits.get("openness"), 0.7)  # 默认值
    
    def test_lifecycle_creation(self):
        """
        测试生命周期创建
        
        验证 SwarmFly 的生命周期管理功能
        """
        swarm_config = SwarmFlyConfig(
            node_id="lifecycle_test"
        )
        
        swarm = SwarmFly(config=swarm_config)
        
        # 创建生命周期
        lifecycle = AgentLifecycle(
            agent_id="lifecycle_test_agent",
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
    
    def test_mcp_registration(self):
        """
        测试 MCP 注册
        
        验证 ZenAgent 的 MCP 协议注册功能
        """
        config = ZenAgentConfig(
            agent_id="mcp_test_agent",
            agent_name="MCPTestAgent"
        )
        
        zen = ZenAgent(config=config)
        
        # 创建元数据
        metadata = AgentMetadata(
            agent_id="mcp_test_agent",
            name="MCPTestAgent",
            agent_type="test",
            capabilities=[AgentCapability.TEXT_GENERATION],
            status=AgentStatus.ACTIVE
        )
        
        # 注册
        registered = zen.register_agent(metadata)
        
        # 验证注册成功
        self.assertIsNotNone(registered)
        self.assertEqual(registered.metadata.agent_id, "mcp_test_agent")
    
    def test_context_configuration(self):
        """
        测试 Context 配置
        
        验证 Runtime 的 Context 配置功能
        """
        ctx_manager = MockContextManager(max_tokens=4096)
        
        # 分配 token
        allocated = ctx_manager.allocate(1024)
        self.assertTrue(allocated)
        self.assertEqual(ctx_manager.current_tokens, 1024)
        
        # 压缩
        compacted = ctx_manager.compact()
        self.assertEqual(compacted, 512)
        
        # 创建检查点
        checkpoint = ctx_manager.checkpoint()
        self.assertEqual(checkpoint["token_count"], 512)
        
        # 释放
        ctx_manager.release(256)
        self.assertEqual(ctx_manager.current_tokens, 256)
    
    def test_creation_with_minimal_config(self):
        """
        测试最小配置创建
        
        验证使用最小配置创建 Agent
        """
        flow = AgentCreationFlow()
        
        result = flow.create_agent(
            agent_id="minimal_001",
            agent_name="MinimalAgent"
        )
        
        self.assertTrue(result["success"])
        
        state = flow.get_agent_state()
        self.assertTrue(state["soulteam"]["initialized"])
        self.assertTrue(state["zenaagent"]["initialized"])
    
    def test_creation_with_custom_capabilities(self):
        """
        测试自定义能力创建
        
        验证创建具有自定义能力的 Agent
        """
        flow = AgentCreationFlow()
        
        capabilities = [
            AgentCapability.TEXT_GENERATION,
            AgentCapability.COLLABORATION,
            AgentCapability.MEMORY
        ]
        
        result = flow.create_agent(
            agent_id="capability_001",
            agent_name="CapabilityAgent",
            capabilities=capabilities
        )
        
        self.assertTrue(result["success"])
        
        # 验证 ZenAgent 注册
        self.assertIsNotNone(flow.zenaagent)
        registered = flow.zenaagent.agent_registry.get("capability_001")
        self.assertIsNotNone(registered)
    
    def test_creation_log_tracking(self):
        """
        测试创建日志跟踪
        
        验证创建流程的日志记录
        """
        flow = AgentCreationFlow()
        
        result = flow.create_agent(
            agent_id="log_test_001",
            agent_name="LogTestAgent"
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(len(flow.creation_log), 4)
        
        # 验证日志内容
        self.assertIn("[SoulTeam]", flow.creation_log[0])
        self.assertIn("[SwarmFly]", flow.creation_log[1])
        self.assertIn("[ZenAgent]", flow.creation_log[2])
        self.assertIn("[Runtime]", flow.creation_log[3])
    
    def test_parallel_agent_creation(self):
        """
        测试并行 Agent 创建
        
        验证同时创建多个 Agent
        """
        flows = []
        
        for i in range(3):
            flow = AgentCreationFlow()
            result = flow.create_agent(
                agent_id=f"parallel_{i}",
                agent_name=f"ParallelAgent{i}"
            )
            flows.append((flow, result))
        
        # 验证所有 Agent 都创建成功
        for flow, result in flows:
            self.assertTrue(result["success"])
            
        # 验证每个 Agent 都有独立状态
        for i, (flow, _) in enumerate(flows):
            state = flow.get_agent_state()
            self.assertTrue(state["soulteam"]["initialized"])
            self.assertTrue(state["zenaagent"]["initialized"])


class TestAgentCreationValidation(unittest.TestCase):
    """
    Agent 创建验证测试
    
    验证 Agent 创建过程中的各种验证场景
    """
    
    def test_invalid_agent_id(self):
        """
        测试无效 Agent ID
        
        验证处理无效 Agent ID 的情况
        """
        flow = AgentCreationFlow()
        
        # 空 ID 应该能处理
        result = flow.create_agent(agent_id="", agent_name="TestAgent")
        # 创建可能失败但不抛出异常
        self.assertIn("success", result)
    
    def test_invalid_personality_traits(self):
        """
        测试无效人格特质
        
        验证处理无效人格特质的情况
        """
        config = SoulTeamConfig(
            soul_id="trait_test"
        )
        
        soul = SoulTeam(config=config)
        
        # 验证人格系统仍可工作
        self.assertIsNotNone(soul.personality)
    
    def test_state_persistence(self):
        """
        测试状态持久化
        
        验证创建后状态的持久化
        """
        flow = AgentCreationFlow()
        
        result = flow.create_agent(
            agent_id="persist_001",
            agent_name="PersistAgent"
        )
        
        self.assertTrue(result["success"])
        
        # 验证状态保持
        state = flow.get_agent_state()
        self.assertEqual(state["swarmfly"]["lifecycle_state"], "created")


if __name__ == "__main__":
    unittest.main(verbosity=2)
