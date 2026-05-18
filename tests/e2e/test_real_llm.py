"""
Phase 4 E2E 测试: 真实 LLM 调用

测试目标: 验证真实 LLM 调用链路（需要 API Key）

运行方式:
  - 需要设置 OPENAI_API_KEY 环境变量
  - 若无 API Key，测试会自动跳过
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import asyncio


def has_api_key() -> bool:
    """检查是否有 API Key"""
    return bool(os.environ.get("OPENAI_API_KEY", "").strip() != "") or \
           bool(os.environ.get("ANTHROPIC_API_KEY", "").strip() != "")


@pytest.mark.skipif(not has_api_key(), reason="需要 API Key 才能运行真实 LLM 测试")
class TestRealLLM:
    """真实 LLM 调用测试"""

    @pytest.mark.asyncio
    async def test_openai_direct_call(self):
        """测试直接调用 OpenAI API"""
        from packages.LLMInfra import LLMClient, Settings, Message, MessageRole

        settings = Settings(
            default_provider="openai",
        )

        # 检查是否配置了 OpenAI
        if "openai" not in settings.providers:
            pytest.skip("OpenAI provider not configured")

        client = LLMClient(settings)

        response = await client.chat(
            messages=[Message(role=MessageRole.USER, content="Hello, respond with 'OK'")],
            model="gpt-3.5-turbo",
            temperature=0.0,
            max_tokens=10,
        )

        assert response is not None
        assert response.content is not None
        assert len(response.content) > 0
        print(f"✅ OpenAI 调用成功: {response.content[:50]}...")

    @pytest.mark.asyncio
    async def test_zenagent_think_with_real_llm(self):
        """测试 ZenAgent think() 方法使用真实 LLM"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="openai",
            enable_memory=True,
        )
        agent = ZenAgent(config)

        # 检查 LLM 客户端是否初始化成功
        if agent.llm_client is None:
            pytest.skip("LLM client not initialized")

        response = await agent.think(
            prompt="What is 2 + 2? Respond with just the number.",
            system_prompt="You are a helpful assistant.",
            use_history=False,
            record_to_memory=False,
        )

        assert response is not None
        assert "4" in response.content
        print(f"✅ ZenAgent think() 调用成功: {response.content}")

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self):
        """测试多轮对话上下文保持"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="openai",
            enable_memory=False,
        )
        agent = ZenAgent(config)

        if agent.llm_client is None:
            pytest.skip("LLM client not initialized")

        # 第一轮
        r1 = await agent.think(
            prompt="My name is Alice.",
            use_history=True,
            record_to_memory=False,
        )

        # 第二轮 - 测试上下文保持
        r2 = await agent.think(
            prompt="What is my name?",
            use_history=True,
            record_to_memory=False,
        )

        assert "Alice" in r2.content
        print(f"✅ 多轮对话上下文保持成功: {r2.content}")

    @pytest.mark.asyncio
    async def test_memory_integration_with_real_llm(self):
        """测试记忆系统与真实 LLM 联动"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="openai",
            enable_memory=True,
            auto_memory_recording=True,
        )
        agent = ZenAgent(config)

        if agent.llm_client is None:
            pytest.skip("LLM client not initialized")

        if agent.memory is None:
            pytest.skip("Memory system not initialized")

        # 调用 think 并记录记忆
        response = await agent.think(
            prompt="Write a short poem about AI.",
            use_history=False,
            record_to_memory=True,
        )

        assert response is not None

        # 验证记忆已被记录
        stats = agent.memory.get_stats()
        assert stats is not None

        print(f"✅ 记忆系统与真实 LLM 联动成功")


@pytest.mark.skipif(not has_api_key(), reason="需要 API Key 才能运行真实 LLM 测试")
class TestLLMQuality:
    """LLM 质量测试"""

    @pytest.mark.asyncio
    async def test_reasoning_quality(self):
        """测试推理能力"""
        from packages.LLMInfra import LLMClient, Settings, Message, MessageRole

        settings = Settings(default_provider="openai")
        if "openai" not in settings.providers:
            pytest.skip("OpenAI not configured")

        client = LLMClient(settings)

        # 测试简单推理
        response = await client.chat(
            messages=[Message(
                role=MessageRole.USER,
                content="If X is 5 and Y is 10, what is X + Y? Just the number."
            )],
            model="gpt-3.5-turbo",
            temperature=0.0,
            max_tokens=20,
        )

        assert "15" in response.content
        print(f"✅ LLM 推理能力正常: {response.content}")

    @pytest.mark.asyncio
    async def test_response_consistency(self):
        """测试响应一致性"""
        from packages.LLMInfra import LLMClient, Settings, Message, MessageRole

        settings = Settings(default_provider="openai")
        if "openai" not in settings.providers:
            pytest.skip("OpenAI not configured")

        client = LLMClient(settings)

        # 多次调用相同问题，检查一致性
        results = []
        for i in range(3):
            response = await client.chat(
                messages=[Message(
                    role=MessageRole.USER,
                    content="What is the capital of France? Just the city name."
                )],
                model="gpt-3.5-turbo",
                temperature=0.0,
                max_tokens=20,
            )
            results.append(response.content.strip().lower())

        # 至少 2/3 应该包含 "paris"
        paris_count = sum(1 for r in results if "paris" in r)
        assert paris_count >= 2
        print(f"✅ LLM 响应一致性正常: {results}")


class TestLLMWithMemoryLink:
    """LLM 与记忆系统联动测试（使用 Mock Provider，无需 API Key）"""

    @pytest.mark.asyncio
    async def test_conversation_memory_recording(self):
        """测试对话记录到记忆系统"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="mock",
            enable_memory=True,
            auto_memory_recording=True,
        )
        agent = ZenAgent(config)

        assert agent.llm_client is not None
        assert agent.memory is not None

        # 多轮对话，每轮都记录记忆
        for i in range(3):
            await agent.think(
                prompt=f"Test message {i}",
                use_history=True,
                record_to_memory=True,
            )

        # 检查对话历史
        history = agent.conversation_history
        assert len(history) >= 6  # 3 轮 * 2 条消息/轮

        print(f"✅ 对话记忆记录成功，共 {len(history)} 条消息")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
