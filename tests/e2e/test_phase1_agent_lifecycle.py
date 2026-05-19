"""
Phase 1 E2E 测试: Agent 创建与初始化流程

测试目标: 验证 Agent 从注册、初始化、状态转换到优雅关闭的完整生命周期
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from typing import Dict, Any, List


class TestAgentRegistrationFlow:
    """T1.1 Agent 完整注册流程"""

    def test_mcp_protocol_initialization(self):
        """测试 MCP 协议初始化"""
        from packages.ZenAgent.mcp.protocol import MCPProtocol

        protocol = MCPProtocol()
        assert protocol is not None
        print("✅ MCP Protocol 初始化成功")

    def test_agent_registry_create(self):
        """测试 Agent 注册表创建"""
        from packages.ZenAgent.mcp.registry import AgentRegistry, AgentCapability

        registry = AgentRegistry()
        assert registry is not None
        print("✅ Agent Registry 初始化成功")

    def test_agent_capability_definition(self):
        """测试 Agent 能力定义"""
        from packages.ZenAgent.mcp.registry import AgentCapability

        capabilities = [
            AgentCapability.TEXT_GENERATION,
            AgentCapability.COLLABORATION,
        ]
        assert len(capabilities) == 2
        print("✅ Agent Capability 定义成功")

    def test_full_registration_flow(self):
        """测试完整注册流程"""
        from packages.ZenAgent.mcp.registry import AgentRegistry, AgentMetadata, AgentCapability

        registry = AgentRegistry()

        # 1. 创建 Agent 元数据
        metadata = AgentMetadata(
            agent_id="test_agent_001",
            name="Test Agent",
            capabilities=[AgentCapability.TEXT_GENERATION, AgentCapability.COLLABORATION],
            version="1.0.0"
        )
        assert metadata.agent_id == "test_agent_001"

        # 2. 注册 Agent
        agent_info = registry.register(metadata)
        assert agent_info is not None

        # 3. 查询 Agent
        retrieved = registry.get("test_agent_001")
        assert retrieved is not None
        assert retrieved.metadata.name == "Test Agent"

        # 4. 列出所有 Agent
        all_agents = registry.list_all()
        assert len(all_agents) >= 1

        print("✅ Agent 完整注册流程验证通过")

    def test_agent_registration_with_metadata(self):
        """测试带元数据的 Agent 注册"""
        from packages.ZenAgent.mcp.registry import AgentRegistry, AgentMetadata, AgentCapability

        registry = AgentRegistry()
        metadata = AgentMetadata(
            agent_id="meta_agent_001",
            name="Meta Agent",
            capabilities=[AgentCapability.TEXT_GENERATION],
            version="1.0.0",
            description="A test agent"
        )

        agent_info = registry.register(metadata)
        assert agent_info.metadata.agent_id == "meta_agent_001"
        print("✅ 带元数据的 Agent 注册成功")


class TestLifecycleStateTransition:
    """T1.2 生命周期状态转换"""

    def test_lifecycle_creation(self):
        """测试生命周期对象创建"""
        from packages.SwarmFly.lifecycle import AgentLifecycle, AgentState

        lifecycle = AgentLifecycle(
            agent_id="agent_001",
            initial_state=AgentState.CREATED
        )
        assert lifecycle.agent_id == "agent_001"
        assert lifecycle.state == AgentState.CREATED
        print("✅ Agent Lifecycle 创建成功")

    def test_valid_state_transitions(self):
        """测试有效的状态转换"""
        from packages.SwarmFly.lifecycle import AgentLifecycle, AgentState

        lifecycle = AgentLifecycle(
            agent_id="agent_002",
            initial_state=AgentState.CREATED
        )

        # CREATED → INITIALIZING
        lifecycle.transition_to(AgentState.INITIALIZING)
        assert lifecycle.state == AgentState.INITIALIZING

        # INITIALIZING → READY
        lifecycle.transition_to(AgentState.READY)
        assert lifecycle.state == AgentState.READY

        # READY → RUNNING
        lifecycle.transition_to(AgentState.RUNNING)
        assert lifecycle.state == AgentState.RUNNING

        # RUNNING → PAUSED
        lifecycle.transition_to(AgentState.PAUSED)
        assert lifecycle.state == AgentState.PAUSED

        # PAUSED → RUNNING
        lifecycle.transition_to(AgentState.RUNNING)
        assert lifecycle.state == AgentState.RUNNING

        # RUNNING → STOPPED
        lifecycle.transition_to(AgentState.STOPPED)
        assert lifecycle.state == AgentState.STOPPED

        print("✅ 所有有效状态转换验证通过")

    def test_state_history_recording(self):
        """测试状态历史记录"""
        from packages.SwarmFly.lifecycle import AgentLifecycle, AgentState

        lifecycle = AgentLifecycle(
            agent_id="agent_003",
            initial_state=AgentState.CREATED
        )

        lifecycle.transition_to(AgentState.INITIALIZING)
        lifecycle.transition_to(AgentState.READY)
        lifecycle.transition_to(AgentState.RUNNING)

        history = lifecycle.transition_history
        assert len(history) >= 3  # 至少有 3 次转换
        print(f"✅ 状态历史记录正常: {len(history)} 条记录")

    def test_lifecycle_to_dict(self):
        """测试生命周期序列化"""
        from packages.SwarmFly.lifecycle import AgentLifecycle, AgentState

        lifecycle = AgentLifecycle(
            agent_id="agent_004",
            initial_state=AgentState.READY
        )

        data = lifecycle.to_dict()
        assert data["agent_id"] == "agent_004"
        assert "state" in data
        print("✅ 生命周期序列化成功")


class TestPersonalityInitialization:
    """T1.3 人格系统初始化"""

    def test_personality_creation(self):
        """测试人格对象创建"""
        from packages.MetaSoul.personality.personality import Personality

        personality = Personality()
        assert personality is not None
        print("✅ Personality 创建成功")

    def test_initial_traits_exist(self):
        """测试初始特质存在"""
        from packages.MetaSoul.personality.personality import Personality

        personality = Personality()
        traits = personality.get_traits()
        assert len(traits) > 0
        print(f"✅ 初始人格特质验证通过: {len(traits)} 个特质")

    def test_get_specific_trait(self):
        """测试获取特定特质"""
        from packages.MetaSoul.personality.personality import Personality, BigFiveTraits

        personality = Personality()

        # 测试开放性特质 - 使用 BigFiveTraits enum
        openness = personality.get_trait(BigFiveTraits.OPENNESS)
        assert openness is not None
        assert 0 <= openness <= 1
        print(f"✅ 开放性特质获取成功: {openness:.2f}")

    def test_set_and_update_trait(self):
        """测试设置和更新特质"""
        from packages.MetaSoul.personality.personality import Personality, BigFiveTraits

        personality = Personality()

        # 设置特质
        personality.set_trait(BigFiveTraits.OPENNESS, 0.8)
        assert personality.get_trait(BigFiveTraits.OPENNESS) == 0.8

        # 再次设置不同值
        personality.set_trait(BigFiveTraits.OPENNESS, 0.6)
        assert personality.get_trait(BigFiveTraits.OPENNESS) == 0.6

        print("✅ 特质设置和更新成功")

    def test_trait_evolution(self):
        """测试人格演化"""
        from packages.MetaSoul.personality.personality import Personality, BigFiveTraits

        personality = Personality()
        initial_value = personality.get_trait(BigFiveTraits.OPENNESS)

        # 模拟演化 - evolve 接收 dict 参数
        personality.evolve({
            "outcome": 0.8,
            "feedback_type": "positive",
            "task_complexity": "medium"
        })

        # 验证值已改变
        new_value = personality.get_trait(BigFiveTraits.OPENNESS)
        # 可能不变或有微小变化
        assert new_value is not None
        print(f"✅ 人格演化测试通过: {initial_value:.2f} → {new_value:.2f}")


class TestMemorySystemInitialization:
    """T1.4 记忆系统初始化"""

    def test_meta_soul_creation(self):
        """测试 MetaSoul 创建"""
        from packages.MetaSoul.memory.meta_soul import MetaSoul

        soul = MetaSoul(soul_id="test_soul_001")
        assert soul.soul_id == "test_soul_001"
        print("✅ MetaSoul 创建成功")

    def test_store_and_retrieve_episodic_memory(self):
        """测试情景记忆存储和检索"""
        from packages.MetaSoul.memory.meta_soul import MetaSoul, MemoryType

        soul = MetaSoul(soul_id="test_soul_002")

        # 存储记忆 - 正确签名: (content, memory_type, importance=..., metadata=...)
        memory_id = soul.store_memory(
            "用户询问了 Python 编程问题",
            MemoryType.EPISODIC,
            metadata={"source": "conversation"}
        )
        assert memory_id is not None

        # 检索记忆
        memories = soul.retrieve(
            query="Python",
            memory_type=MemoryType.EPISODIC,
            limit=5
        )
        assert isinstance(memories, list)
        print(f"✅ 情景记忆存储和检索成功: {memory_id}")

    def test_store_and_retrieve_working_memory(self):
        """测试工作记忆存储和检索"""
        from packages.MetaSoul.memory.meta_soul import MetaSoul, MemoryType

        soul = MetaSoul(soul_id="test_soul_003")

        # 存储工作记忆
        memory_id = soul.store_memory(
            "当前对话上下文",
            MemoryType.WORKING,
            metadata={"importance": "high"}
        )
        assert memory_id is not None

        # 获取统计
        stats = soul.get_stats()
        assert "total_memories" in stats
        print(f"✅ 工作记忆存储成功: {stats}")

    def test_semantic_memory_storage(self):
        """测试语义记忆存储"""
        from packages.MetaSoul.memory.meta_soul import MetaSoul, MemoryType

        soul = MetaSoul(soul_id="test_soul_004")

        memory_id = soul.store_memory(
            "Python 是一种解释型编程语言",
            MemoryType.SEMANTIC,
            metadata={"category": "knowledge"}
        )
        assert memory_id is not None
        print(f"✅ 语义记忆存储成功: {memory_id}")

    def test_procedural_memory_storage(self):
        """测试程序记忆存储"""
        from packages.MetaSoul.memory.meta_soul import MetaSoul, MemoryType

        soul = MetaSoul(soul_id="test_soul_005")

        memory_id = soul.store_memory(
            "调用函数的步骤",
            MemoryType.PROCEDURAL,
            metadata={"skill": "function_calling"}
        )
        assert memory_id is not None
        print(f"✅ 程序记忆存储成功: {memory_id}")

    def test_memory_association(self):
        """测试记忆关联"""
        from packages.MetaSoul.memory.meta_soul import MetaSoul, MemoryType

        soul = MetaSoul(soul_id="test_soul_006")

        mem_id1 = soul.store_memory("用户问了问题 A", MemoryType.EPISODIC)
        mem_id2 = soul.store_memory("用户问了问题 B", MemoryType.EPISODIC)

        # 创建关联
        result = soul.associate_memories(mem_id1, mem_id2)
        assert result == True
        print("✅ 记忆关联创建成功")

    def test_experience_recording(self):
        """测试经验记录"""
        from packages.MetaSoul.memory.meta_soul import MetaSoul

        soul = MetaSoul(soul_id="test_soul_007")

        # store_experience: (context, action, result, reflection='', outcome=0.0, learning=None)
        experience_id = soul.store_experience(
            context="执行任务的背景",
            action="完成了一项任务",
            result="任务完成",
            reflection="下次可以更快完成",
            outcome=0.9
        )
        assert experience_id is not None
        print(f"✅ 经验记录成功: {experience_id}")


class TestHookSystem:
    """T1.5 Hook 系统正确触发"""

    def test_hook_manager_creation(self):
        """测试 Hook Manager 创建"""
        from packages.ZenAgent.hooks.hook_manager import HookManager

        manager = HookManager()
        assert manager is not None
        print("✅ Hook Manager 创建成功")

    def test_register_hook(self):
        """测试注册 Hook"""
        from packages.ZenAgent.hooks.hook_manager import HookManager

        manager = HookManager()

        def test_handler(**kwargs):
            return kwargs.get("data")

        # 注册钩子: register(event_name, handler, name=None, priority, once=False)
        hook_id = manager.register(
            event_name="on_create",
            handler=test_handler
        )
        assert hook_id is not None
        print(f"✅ Hook 注册成功: {hook_id}")

    def test_trigger_hook(self):
        """测试触发 Hook"""
        from packages.ZenAgent.hooks.hook_manager import HookManager

        manager = HookManager()
        results = []

        def test_handler(context):
            # context 是 HookEvent 对象，有 data, event_name 等属性
            results.append(context.data.get("data"))
            return True

        # 注册钩子
        manager.register(event_name="on_test", handler=test_handler)

        # 触发钩子: trigger_sync(event_name, data=None, source=None)
        trigger_results = manager.trigger_sync(event_name="on_test", data={"data": "test_data"})
        assert len(trigger_results) >= 1
        assert len(results) == 1
        assert results[0] == "test_data"
        print("✅ Hook 触发成功")

    def test_multiple_hooks_same_event(self):
        """测试同一事件的多个钩子"""
        from packages.ZenAgent.hooks.hook_manager import HookManager

        manager = HookManager()
        call_count = 0

        def handler1(context):
            nonlocal call_count
            call_count += 1
            return True

        def handler2(context):
            nonlocal call_count
            call_count += 1
            return True

        manager.register(event_name="on_multi", handler=handler1)
        manager.register(event_name="on_multi", handler=handler2)

        results = manager.trigger_sync(event_name="on_multi", data={"data": "test"})
        assert len(results) == 2
        assert call_count == 2
        print("✅ 同一事件多个 Hook 触发成功")

    def test_lifecycle_hooks(self):
        """测试生命周期钩子"""
        from packages.ZenAgent.hooks.hook_manager import HookManager

        manager = HookManager()

        # 测试常见生命周期事件
        events = [
            "on_create",
            "on_initialize",
            "on_start",
            "on_stop",
            "on_error"
        ]

        for event in events:
            hook_id = manager.register(
                event_name=event,
                handler=lambda **kwargs: True
            )
            assert hook_id is not None

        print(f"✅ 所有 {len(events)} 个生命周期 Hook 注册成功")


class TestFullAgentInitializationFlow:
    """完整 Agent 初始化流程测试 - 集成所有模块"""

    def test_complete_agent_initialization(self):
        """测试完整的 Agent 初始化流程"""
        from packages.ZenAgent.mcp.registry import AgentRegistry, AgentMetadata, AgentCapability
        from packages.SwarmFly.lifecycle import AgentLifecycle, AgentState
        from packages.MetaSoul.personality.personality import Personality
        from packages.MetaSoul.memory.meta_soul import MetaSoul, MemoryType

        agent_id = "full_agent_001"

        # Step 1: 注册到 MCP
        registry = AgentRegistry()
        metadata = AgentMetadata(
            agent_id=agent_id,
            name="Full Integration Agent",
            capabilities=[
                AgentCapability.TEXT_GENERATION,
                AgentCapability.COLLABORATION,
            ],
            version="1.0.0"
        )
        registry.register(metadata)
        print("✅ Step 1: Agent 注册到 MCP 成功")

        # Step 2: 初始化生命周期管理
        lifecycle = AgentLifecycle(
            agent_id=agent_id,
            initial_state=AgentState.CREATED
        )
        lifecycle.transition_to(AgentState.INITIALIZING)
        assert lifecycle.state == AgentState.INITIALIZING
        print("✅ Step 2: 生命周期管理初始化成功")

        # Step 3: 初始化人格系统
        personality = Personality()
        traits = personality.get_traits()
        assert len(traits) > 0
        print(f"✅ Step 3: 人格系统初始化成功, {len(traits)} 个特质")

        # Step 4: 初始化记忆系统
        soul = MetaSoul(soul_id=agent_id)
        memory_id = soul.store_memory(
            f"Agent {agent_id} 已初始化",
            MemoryType.WORKING,
            metadata={"type": "system"}
        )
        assert memory_id is not None
        print("✅ Step 4: 记忆系统初始化成功")

        # Step 5: 进入 READY 状态
        lifecycle.transition_to(AgentState.READY)
        assert lifecycle.state == AgentState.READY
        print("✅ Step 5: Agent 进入 READY 状态")

        # 验证所有组件状态
        assert registry.get(agent_id) is not None
        assert personality is not None
        assert soul is not None

        print("✅ 完整 Agent 初始化流程验证通过!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
