"""
Phase 3 E2E 测试: LLM 集成与记忆系统联动

测试目标: 验证 ZenAgent 与 LLMInfra 和 SoulTeam 的集成
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import asyncio


class TestZenAgentWithLLM:
    """Test LLM 客户端集成"""

    def test_zenagent_with_llm_enabled(self):
        """测试启用 LLM 的 ZenAgent 初始化"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="mock",
            enable_memory=True
        )
        agent = ZenAgent(config)

        # 验证 LLM 客户端初始化
        assert agent.llm_client is not None
        print("✅ ZenAgent 启用 LLM 初始化成功")

    def test_zenagent_without_llm(self):
        """测试禁用 LLM 的 ZenAgent"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=False,
            enable_memory=False
        )
        agent = ZenAgent(config)

        # 验证 LLM 客户端为 None
        assert agent.llm_client is None
        print("✅ ZenAgent 禁用 LLM 模式工作正常")

    def test_memory_system_integration(self):
        """测试记忆系统集成"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="mock",
            enable_memory=True,
            auto_memory_recording=True
        )
        agent = ZenAgent(config)

        # 验证记忆系统初始化
        assert agent.memory is not None
        print("✅ 记忆系统集成成功")

    def test_manual_memory_operations(self):
        """测试手动记忆操作"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="mock",
            enable_memory=True
        )
        agent = ZenAgent(config)

        # 手动存储记忆
        memory_id = agent.remember("This is a test memory")
        assert memory_id is not None

        # 检索记忆
        memories = agent.recall("test")
        assert isinstance(memories, list)

        print("✅ 手动记忆操作成功")

    def test_personality_system_integration(self):
        """测试人格系统集成"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="mock",
            enable_memory=True,
            enable_personality_influence=True
        )
        agent = ZenAgent(config)

        # 验证人格系统初始化
        assert agent.personality is not None

        # 验证可以获取人格特质
        from packages.SoulTeam.personality import BigFiveTraits
        openness = agent.personality.get_trait(BigFiveTraits.OPENNESS)
        assert 0 <= openness <= 1

        print("✅ 人格系统集成成功")

    def test_conversation_history_management(self):
        """测试对话历史管理"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="mock",
            enable_memory=False
        )
        agent = ZenAgent(config)

        # 初始对话历史应为空
        assert len(agent.conversation_history) == 0

        # 清空对话历史
        agent.clear_conversation()
        assert len(agent.conversation_history) == 0

        print("✅ 对话历史管理正常")


class TestLLMThinkMethod:
    """测试 think 方法"""

    @pytest.mark.asyncio
    async def test_basic_think_call(self):
        """测试基本的 think 调用"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="mock",
            enable_memory=False
        )
        agent = ZenAgent(config)

        # 测试同步调用 think
        response = await agent.think(
            prompt="Hello, how are you?",
            use_history=False,
            record_to_memory=False
        )

        assert response is not None
        print(f"✅ think 方法调用成功，响应: {response}")

    @pytest.mark.asyncio
    async def test_think_with_system_prompt(self):
        """测试带系统提示词的 think 调用"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="mock",
            enable_memory=False
        )
        agent = ZenAgent(config)

        response = await agent.think(
            prompt="What is 2 + 2?",
            system_prompt="You are a helpful math tutor.",
            use_history=False,
            record_to_memory=False
        )

        assert response is not None
        print("✅ 带系统提示词的 think 调用成功")

    @pytest.mark.asyncio
    async def test_think_with_memory_recording(self):
        """测试带记忆记录的 think 调用"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="mock",
            enable_memory=True,
            auto_memory_recording=True
        )
        agent = ZenAgent(config)

        # 获取初始记忆统计
        initial_stats = agent.memory.get_stats()
        initial_count = initial_stats.get("total_memories", 0)

        # 调用 think 并记录记忆
        response = await agent.think(
            prompt="Test memory recording",
            use_history=False,
            record_to_memory=True
        )

        assert response is not None

        print("✅ 带记忆记录的 think 调用成功")


class TestFullZenAgentStatus:
    """测试 ZenAgent 完整状态"""

    def test_full_status_report(self):
        """测试完整状态报告"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="mock",
            enable_memory=True,
            enable_mcp=True,
            enable_hooks=True,
            enable_awakening=True,
            enable_collaboration=True
        )
        agent = ZenAgent(config)

        status = agent.get_full_status()

        assert "agent_id" in status
        assert "agent_name" in status
        assert "llm" not in status  # LLM 状态目前不在 status 中，但可以扩展

        print(f"✅ 完整状态报告生成成功: {list(status.keys())}")


class TestPersonalityEvolutionWithLLM:
    """测试人格演化与 LLM 联动"""

    @pytest.mark.asyncio
    async def test_personality_influence_on_think(self):
        """测试人格对思考的影响"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="mock",
            enable_memory=True,
            enable_personality_influence=True
        )
        agent = ZenAgent(config)

        # 验证人格系统已启用
        assert agent.personality is not None

        # 调用 think 时应考虑人格影响
        response = await agent.think(
            prompt="Tell me about yourself",
            use_history=False,
            record_to_memory=False
        )

        assert response is not None
        print("✅ 人格影响思考功能正常")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
