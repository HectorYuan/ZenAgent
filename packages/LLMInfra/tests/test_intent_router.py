"""
意图路由测试
"""
import pytest
import asyncio

from packages.LLMInfra.core import Message, MessageRole, ChatRequest, LLMResponse
from packages.LLMInfra.intent_router import (
    IntentRouter,
    L1RuleClassifier,
    PathDispatcher,
    Intent,
    RoutePath,
    ClassifyResult,
    RouteResult,
)


@pytest.fixture(autouse=True)
def reset_zenagent_singleton():
    """重置 ZenAgent 单例，防止测试间状态泄漏"""
    import packages.ZenAgent.core as zc
    zc._default_agent = None
    yield
    zc._default_agent = None


# ============================================================
# L1RuleClassifier 测试
# ============================================================

class TestL1RuleClassifier:
    """L1 规则分类器测试"""

    def test_empty_messages(self):
        """测试空消息"""
        cls = L1RuleClassifier()
        result = cls.classify([])
        assert result.intent == Intent.SIMPLE_QA
        assert result.confidence >= 0.9

    def test_simple_qa(self):
        """测试简单问答"""
        cls = L1RuleClassifier()
        msgs = [Message(role=MessageRole.USER, content="What is Python?")]
        result = cls.classify(msgs)
        assert result.intent in (Intent.SIMPLE_QA, Intent.GENERAL_REASONING)

    def test_simple_qa_chinese(self):
        """测试中文简单问答"""
        cls = L1RuleClassifier()
        msgs = [Message(role=MessageRole.USER, content="什么是 Python?")]
        result = cls.classify(msgs)
        assert result.intent in (Intent.SIMPLE_QA, Intent.GENERAL_REASONING)

    def test_knowledge_retrieval(self):
        """测试知识检索"""
        cls = L1RuleClassifier()
        msgs = [Message(role=MessageRole.USER, content="tell me about wiki python")]
        result = cls.classify(msgs)
        assert result.intent == Intent.KNOWLEDGE_RETRIEVAL

    def test_tool_calling_code_block(self):
        """测试工具调用 - 代码块"""
        cls = L1RuleClassifier()
        msgs = [Message(role=MessageRole.USER, content="```python\ndef foo():\n    pass\n```\nwhat's wrong?")]
        result = cls.classify(msgs)
        assert result.intent == Intent.TOOL_CALLING

    def test_tool_calling_error(self):
        """测试工具调用 - 错误信息"""
        cls = L1RuleClassifier()
        msgs = [Message(role=MessageRole.USER, content="I got this error: ImportError: no module named requests, traceback: ...")]
        result = cls.classify(msgs)
        assert result.intent == Intent.TOOL_CALLING

    def test_complex_reasoning(self):
        """测试复杂推理"""
        cls = L1RuleClassifier()
        msgs = [Message(role=MessageRole.USER, content="Analyze the trade-offs between microservices and monolith architecture")]
        result = cls.classify(msgs)
        assert result.intent == Intent.COMPLEX_REASONING

    def test_complex_chinese(self):
        """测试中文复杂推理"""
        cls = L1RuleClassifier()
        msgs = [Message(role=MessageRole.USER, content="请分析微服务和单体架构之间的权衡")]
        result = cls.classify(msgs)
        assert result.intent == Intent.COMPLEX_REASONING

    def test_creative_writing(self):
        """测试创意写作"""
        cls = L1RuleClassifier()
        msgs = [Message(role=MessageRole.USER, content="write a story about a robot learning to paint")]*10
        result = cls.classify(msgs)
        assert result.intent == Intent.CREATIVE_WRITING

    def test_creative_chinese(self):
        """测试中文创意写作"""
        cls = L1RuleClassifier()
        msgs = [Message(role=MessageRole.USER, content="写一篇关于人工智能未来的文章")]*10
        result = cls.classify(msgs)
        assert result.intent == Intent.CREATIVE_WRITING

    def test_very_long_input(self):
        """测试超长输入 → 复杂推理"""
        cls = L1RuleClassifier()
        long_text = "x" * 4000
        msgs = [Message(role=MessageRole.USER, content=long_text)]
        result = cls.classify(msgs)
        assert result.intent == Intent.COMPLEX_REASONING

    def test_confidence_less_than_one_for_unmatched(self):
        """测试未匹配时的置信度 < 1.0"""
        cls = L1RuleClassifier()
        msgs = [Message(role=MessageRole.USER, content="hello")]
        result = cls.classify(msgs)
        assert result.confidence <= 0.95

    def test_tool_pattern_with_code_and_api(self):
        """测试多代码/API 模式命中分数更高"""
        cls = L1RuleClassifier()
        msgs = [Message(role=MessageRole.USER, content="function error in my code ``` def broken(): pass ``` what api should I call?")]
        result = cls.classify(msgs)
        assert result.intent == Intent.TOOL_CALLING
        assert result.confidence >= 0.9  # 多个模式命中


# ============================================================
# PathDispatcher 测试
# ============================================================

class TestPathDispatcher:
    """路径分发器测试"""

    def test_intent_to_path_mapping(self):
        """测试意图→路径映射"""
        dispatcher = PathDispatcher()
        assert dispatcher.get_path(Intent.SIMPLE_QA) == RoutePath.FAST
        assert dispatcher.get_path(Intent.CREATIVE_WRITING) == RoutePath.DEEP
        assert dispatcher.get_path(Intent.KNOWLEDGE_RETRIEVAL) == RoutePath.RAG

    def test_degradation_fast_to_deep(self):
        """测试 FastPath 退化到 DeepPath"""
        dispatcher = PathDispatcher()
        assert dispatcher.get_degradation_path(RoutePath.FAST) == RoutePath.DEEP

    def test_degradation_deep_to_fallback(self):
        """测试 DeepPath 退化到 FallbackPath"""
        dispatcher = PathDispatcher()
        assert dispatcher.get_degradation_path(RoutePath.DEEP) == RoutePath.FALLBACK

    def test_degradation_fallback_is_terminal(self):
        """测试 FallbackPath 是终点"""
        dispatcher = PathDispatcher()
        assert dispatcher.get_degradation_path(RoutePath.FALLBACK) == RoutePath.FALLBACK

    def test_degradation_chain(self):
        """测试完整退化链"""
        dispatcher = PathDispatcher()
        # FAST → DEEP → FALLBACK
        path = RoutePath.FAST
        path = dispatcher.get_degradation_path(path)
        assert path == RoutePath.DEEP
        path = dispatcher.get_degradation_path(path)
        assert path == RoutePath.FALLBACK
        path = dispatcher.get_degradation_path(path)
        assert path == RoutePath.FALLBACK  # terminal


# ============================================================
# IntentRouter 测试
# ============================================================

class TestIntentRouter:
    """意图路由器测试"""

    def test_classify_simple(self):
        """测试简单分类"""
        router = IntentRouter()
        msgs = [Message(role=MessageRole.USER, content="hello")]
        result = router.classify(msgs)
        assert result.intent is not None
        assert result.confidence > 0
        assert result.level == 1

    def test_classify_high_confidence(self):
        """测试高置信度直接分流"""
        router = IntentRouter()
        msgs = [Message(role=MessageRole.USER, content="analyze the tradeoffs between 3 different database systems")]
        result = router.classify(msgs)
        assert result.intent == Intent.COMPLEX_REASONING

    def test_stats_updated(self):
        """测试统计更新"""
        router = IntentRouter()
        for _ in range(5):
            router.classify([Message(role=MessageRole.USER, content="hello")])

        stats = router.stats
        assert stats["total_requests"] == 5

    @pytest.mark.asyncio
    async def test_execute_fast_path(self):
        """测试执行 FastPath"""
        router = IntentRouter()
        request = ChatRequest(
            model="test",
            messages=[Message(role=MessageRole.USER, content="hello")]
        )

        async def mock_fast(req):
            return LLMResponse(
                provider="mock", model="test", content="fast response",
                messages=list(req.messages),
                usage={"prompt_tokens": 1, "completion_tokens": 1}
            )

        result = await router.execute_path(
            path=RoutePath.FAST,
            request=request,
            fast_executor=mock_fast
        )

        assert result.success
        assert result.response.content == "fast response"
        assert result.path == RoutePath.FAST

    @pytest.mark.asyncio
    async def test_execute_with_degradation(self):
        """测试路径退化"""
        router = IntentRouter()
        request = ChatRequest(
            model="test",
            messages=[Message(role=MessageRole.USER, content="complex")]
        )

        # FastPath 失败，应退化到 DeepPath
        async def failing_fast(req):
            raise RuntimeError("FastPath failed")

        async def working_deep(req):
            return LLMResponse(
                provider="mock", model="test", content="deep response",
                messages=list(req.messages),
                usage={"prompt_tokens": 2, "completion_tokens": 2}
            )

        result = await router.execute_path(
            path=RoutePath.FAST,
            request=request,
            fast_executor=failing_fast,
            deep_executor=working_deep
        )

        assert result.success
        assert result.response.content == "deep response"
        assert result.degradation_path == RoutePath.FAST  # 从 Fast 退化

    @pytest.mark.asyncio
    async def test_execute_all_fail_to_fallback(self):
        """测试所有路径失败最终到 Fallback"""
        router = IntentRouter()
        request = ChatRequest(
            model="test",
            messages=[Message(role=MessageRole.USER, content="anything")]
        )

        async def always_fail(req):
            raise RuntimeError("Failed")

        async def working_fallback(req):
            return LLMResponse(
                provider="fallback", model="fallback", content="fallback response",
                messages=list(req.messages),
                usage={"prompt_tokens": 0, "completion_tokens": 0}
            )

        result = await router.execute_path(
            path=RoutePath.FAST,
            request=request,
            fast_executor=always_fail,
            deep_executor=always_fail,
            fallback_executor=working_fallback
        )

        assert result.success
        assert result.response.content == "fallback response"

    @pytest.mark.asyncio
    async def test_stats_records_degradation(self):
        """测试统计数据记录退化"""
        router = IntentRouter()
        request = ChatRequest(
            model="test",
            messages=[Message(role=MessageRole.USER, content="test")]
        )

        async def working(req):
            return LLMResponse(
                provider="mock", model="test", content="ok",
                messages=list(req.messages),
                usage={"prompt_tokens": 1, "completion_tokens": 1}
            )

        await router.execute_path(
            path=RoutePath.FAST,
            request=request,
            fast_executor=working
        )

        stats = router.stats
        assert stats["fast_path"] >= 1


# ============================================================
# 端到端集成测试
# ============================================================

class TestEndToEndRouting:
    """端到端路由集成测试"""

    @pytest.mark.asyncio
    async def test_zenagent_think_with_router(self):
        """测试 ZenAgent think() 使用意图路由"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="mock",
            enable_memory=False,
            enable_personality_influence=False,
        )
        agent = ZenAgent(config)

        assert agent.intent_router is not None

        # 简单问题走 FastPath
        response = await agent.think("What is Python?")
        assert response is not None
        assert response.provider == "mock"

    @pytest.mark.asyncio
    async def test_zenagent_think_without_router(self):
        """测试 ZenAgent think() 不使用路由（回退到原路径）"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="mock",
            enable_memory=False,
            enable_personality_influence=False,
        )
        agent = ZenAgent(config)

        response = await agent.think("hello", use_router=False)
        assert response is not None

    @pytest.mark.asyncio
    async def test_zenagent_router_stats_in_status(self):
        """测试路由器统计出现在完整状态中"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="mock",
            enable_memory=False,
        )
        agent = ZenAgent(config)
        await agent.think("test question")

        status = agent.get_full_status()
        assert "intent_router" in status
        assert status["intent_router"]["total_requests"] >= 1

    @pytest.mark.asyncio
    async def test_chat_fast_path(self):
        """测试 LLMClient.chat_fast()"""
        from packages.LLMInfra.core import LLMClient
        from packages.LLMInfra.config import Settings, ProviderConfig

        settings = Settings(
            providers={"mock": ProviderConfig(api_key="", base_url="", default_model="mock-model")},
            default_provider="mock",
        )
        client = LLMClient(settings=settings)
        request = ChatRequest(
            model="mock-model",
            messages=[Message(role=MessageRole.USER, content="hello")]
        )
        response = await client.chat_fast(request)
        assert response is not None
        assert response.provider == "mock"

    @pytest.mark.asyncio
    async def test_chat_deep_path(self):
        """测试 LLMClient.chat_deep()"""
        from packages.LLMInfra.core import LLMClient
        from packages.LLMInfra.config import Settings, ProviderConfig

        settings = Settings(
            providers={"mock": ProviderConfig(api_key="", base_url="", default_model="mock-model")},
            default_provider="mock",
        )
        client = LLMClient(settings=settings)
        request = ChatRequest(
            model="mock-model",
            messages=[Message(role=MessageRole.USER, content="complex analysis needed")]
        )
        response = await client.chat_deep(request)
        assert response is not None

    @pytest.mark.asyncio
    async def test_chat_fallback_path(self):
        """测试 LLMClient.chat_fallback()"""
        from packages.LLMInfra.core import LLMClient

        client = LLMClient()
        request = ChatRequest(
            model="mock-model",
            messages=[Message(role=MessageRole.USER, content="anything")]
        )
        response = await client.chat_fallback(request)
        assert response is not None
        assert response.provider == "fallback"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
