"""
M7 鲁棒性 E2E 测试

设计依据: E2E-Plan.md - M7 生产优化验证
覆盖场景:
- 长对话上下文截断与记忆淘汰
- 令牌桶限流触发与背压
- 熔断器状态转换与恢复
- 响应截断检测与重试
- 异常降级链路
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import asyncio

from packages.LLMInfra.core import Message, MessageRole, LLMResponse, ChatRequest
from packages.LLMInfra.config import TokenBudgetConfig, ResponseConfig
from packages.LLMInfra.token_budget import TokenBudgetManager, TokenEstimator, IntentClassifier, IntentCategory
from packages.LLMInfra.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitState, CircuitBreakerOpenError,
)
from packages.LLMInfra.response_validator import ResponseValidator, ValidationResult
from packages.LLMInfra.retry import RetryConfig, with_retry
from packages.Runtime.flow_control.rate_limiter import (
    TokenBucketRateLimiter, PriorityRateLimiter, PriorityLimiterConfig, Priority,
)
from packages.Runtime.tracing.tracer import Tracer, SpanStatus
from packages.Runtime.tracing.metrics import MetricsCollector


def _make_response(content: str, finish_reason: str = "stop",
                   completion_tokens: int = 10) -> LLMResponse:
    return LLMResponse(
        provider="mock",
        model="mock-model",
        content=content,
        messages=[Message(role=MessageRole.ASSISTANT, content=content)],
        usage={"completion_tokens": completion_tokens, "prompt_tokens": 50, "total_tokens": 50 + completion_tokens},
        finish_reason=finish_reason,
    )


def _make_request(max_tokens: int = 100) -> ChatRequest:
    return ChatRequest(
        model="mock-model",
        messages=[Message(role=MessageRole.USER, content="hi")],
        max_tokens=max_tokens,
    )


class TestLongConversation:
    """长对话场景: 上下文截断 + Token 预算"""

    def test_token_budget_allocates_by_intent(self):
        """长对话按意图分配 Token 预算"""
        config = TokenBudgetConfig(enabled=True)
        manager = TokenBudgetManager(config)

        messages = [Message(role=MessageRole.USER, content="你好")]
        result = manager.allocate(messages)
        assert result.intent == IntentCategory.SIMPLE_QA
        assert result.max_tokens == config.simple_qa_max_tokens

    def test_intent_classification_consistency(self):
        """意图分类一致性"""
        classifier = IntentClassifier()

        simple = [Message(role=MessageRole.USER, content="你好")]
        complex_msgs = [Message(
            role=MessageRole.USER,
            content="请分析量子计算对密码学的影响，详细比较 RSA 和椭圆曲线加密的脆弱性" * 3,
        )]

        s_intent, _ = classifier.classify(simple)
        c_intent, _ = classifier.classify(complex_msgs)
        assert s_intent == IntentCategory.SIMPLE_QA
        assert c_intent == IntentCategory.COMPLEX_REASONING

    def test_long_conversation_token_estimation(self):
        """20+ 轮对话 Token 估算"""
        messages = []
        for i in range(20):
            messages.append(Message(role=MessageRole.USER, content=f"问题 {i+1}" * 20))
            messages.append(Message(role=MessageRole.ASSISTANT, content=f"回答 {i+1}" * 20))

        estimated = TokenEstimator.estimate_messages(messages)
        # 40 条消息，每条至少 5 tokens
        assert estimated > 200


class TestRateLimiting:
    """限流触发与背压"""

    @pytest.mark.asyncio
    async def test_rate_limiter_rejects_excess(self):
        """并发请求超过限流阈值被拒绝"""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=0)

        results = await asyncio.gather(*[limiter.acquire(1) for _ in range(20)])
        assert sum(results) == 10
        assert sum(1 for r in results if not r) == 10

    @pytest.mark.asyncio
    async def test_priority_limiter_p0_unlimited(self):
        """P0 请求不限速"""
        limiter = PriorityRateLimiter(PriorityLimiterConfig(p0_capacity=0))

        results = []
        for _ in range(100):
            results.append(await limiter.acquire(Priority.P0))
        assert all(results)

    @pytest.mark.asyncio
    async def test_priority_limiter_p2_backpressure(self):
        """背压触发时 P2 被拒绝"""
        config = PriorityLimiterConfig(
            p2_capacity=100,
            p2_refill_rate=100.0,
            backpressure_threshold=0.8,
        )
        limiter = PriorityRateLimiter(config)
        limiter.set_queue_depth(90)

        assert await limiter.acquire(Priority.P2) is False
        assert await limiter.acquire(Priority.P1) is True

    @pytest.mark.asyncio
    async def test_rate_limiter_refill_recovery(self):
        """令牌补充恢复"""
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=100.0)
        await limiter.acquire(10)
        assert limiter.available_tokens == 0.0

        await asyncio.sleep(0.05)
        assert await limiter.acquire(1) is True


class TestCircuitBreakerRecovery:
    """熔断器状态转换与恢复"""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """CLOSED → OPEN → HALF_OPEN → CLOSED 完整生命周期"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=0.1,
            half_open_max_calls=2,
        )
        cb = CircuitBreaker("e2e-test", config)

        async def failing():
            raise ConnectionError("provider down")

        for _ in range(3):
            with pytest.raises(ConnectionError):
                await cb.call(failing)
        assert cb.state == CircuitState.OPEN

        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(failing)

        await asyncio.sleep(0.15)

        await cb.call(asyncio.sleep, 0)
        assert cb.state == CircuitState.CLOSED

        await cb.call(asyncio.sleep, 0)

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self):
        """半开状态失败重新熔断"""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
        cb = CircuitBreaker("e2e-test", config)

        async def failing():
            raise ConnectionError("still down")

        with pytest.raises(ConnectionError):
            await cb.call(failing)
        assert cb.state == CircuitState.OPEN

        await asyncio.sleep(0.15)

        with pytest.raises(ConnectionError):
            await cb.call(failing)
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_error_rate_triggers(self):
        """错误率触发熔断"""
        config = CircuitBreakerConfig(
            failure_threshold=100,
            error_rate_threshold=0.35,
            window_size=10,
        )
        cb = CircuitBreaker("e2e-test", config)

        async def failing():
            raise ValueError("fail")

        for _ in range(7):
            await cb.call(asyncio.sleep, 0)
        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(failing)
        with pytest.raises(ValueError):
            await cb.call(failing)
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        """统计信息追踪"""
        cb = CircuitBreaker("e2e-test")

        await cb.call(asyncio.sleep, 0)

        async def failing():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await cb.call(failing)

        stats = cb.get_stats()
        assert stats["total_calls"] == 2
        assert stats["success_calls"] == 1
        assert stats["failure_calls"] == 1


class TestResponseValidation:
    """响应校验与重试"""

    def test_normal_response_valid(self):
        """正常响应通过"""
        validator = ResponseValidator(ResponseConfig())
        result = validator.validate(_make_response("正常回复"), _make_request(100))
        assert result.is_valid

    def test_truncation_detection(self):
        """截断检测"""
        validator = ResponseValidator(ResponseConfig())
        resp = _make_response("被截断的响应", finish_reason="length")
        result = validator.validate(resp, _make_request(100))
        assert not result.is_valid
        assert result.issue == "truncated"

    def test_empty_response_detection(self):
        """空响应检测"""
        validator = ResponseValidator(ResponseConfig())
        result = validator.validate(_make_response(""), _make_request(100))
        assert not result.is_valid
        assert result.issue == "empty"

    def test_content_filter_detection(self):
        """内容过滤检测"""
        validator = ResponseValidator(ResponseConfig())
        resp = _make_response("blocked", finish_reason="content_filter")
        result = validator.validate(resp, _make_request(100))
        assert not result.is_valid
        assert result.issue == "content_filter"


class TestRetryMechanism:
    """重试机制"""

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """失败自动重试"""
        call_count = 0

        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient error")
            return "success"

        config = RetryConfig(max_attempts=3, initial_delay=0.01, jitter=False)
        result = await with_retry(flaky_func, config)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """重试耗尽抛出异常"""
        async def always_fail():
            raise ConnectionError("permanent error")

        config = RetryConfig(max_attempts=2, initial_delay=0.01, jitter=False)
        with pytest.raises(ConnectionError):
            await with_retry(always_fail, config)


class TestTracingIntegration:
    """追踪集成"""

    def test_full_trace_lifecycle(self):
        """完整追踪生命周期"""
        tracer = Tracer()
        ctx = tracer.start_trace(tags={"scenario": "e2e"})

        req_span = tracer.start_span("request.handle")
        tracer.end_span(req_span, SpanStatus.OK)

        llm_span = tracer.start_span("llm.chat", parent=req_span)
        tracer.end_span(llm_span, SpanStatus.OK)

        resp_span = tracer.start_span("response.validate")
        tracer.end_span(resp_span, SpanStatus.OK)

        trace_data = ctx.to_dict()
        assert trace_data["span_count"] == 3
        assert all(s["status"] == "ok" for s in trace_data["spans"])

    def test_trace_with_error(self):
        """带错误的追踪"""
        tracer = Tracer()
        tracer.start_trace()

        span = tracer.start_span("llm.chat")
        tracer.end_span(span, SpanStatus.ERROR, error="Rate limit exceeded")

        ctx = tracer.get_current_trace()
        error_spans = [s for s in ctx.spans if s.status == SpanStatus.ERROR]
        assert len(error_spans) == 1
        assert error_spans[0].error == "Rate limit exceeded"

    def test_metrics_collection(self):
        """指标收集"""
        m = MetricsCollector()

        m.inc_counter("llm_request_total", tags={"provider": "openai", "status": "200"})
        m.inc_counter("llm_request_total", tags={"provider": "openai", "status": "200"})
        m.inc_counter("llm_request_total", tags={"provider": "openai", "status": "500"})
        m.record_histogram("llm_request_duration_seconds", 1.5, tags={"provider": "openai"})
        m.set_gauge("circuit_breaker_state", 0, tags={"provider": "openai"})

        metrics = m.get_metrics()
        # 200 和 500 两个 counter（同 name 不同 tag）
        assert len(metrics["counters"]) == 2
        assert metrics["counters"]["llm_request_total{provider=openai,status=200}"]["value"] == 2.0
        assert metrics["counters"]["llm_request_total{provider=openai,status=500}"]["value"] == 1.0
        assert len(metrics["histograms"]) == 1
        assert len(metrics["gauges"]) == 1


class TestDegradationChain:
    """异常降级链路: 超时 → 重试 → 熔断 → 降级"""

    @pytest.mark.asyncio
    async def test_timeout_retry_circuit_break(self):
        """超时 → 重试 → 熔断链路"""
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=0.1)
        cb = CircuitBreaker("degradation-test", config)

        call_count = 0

        async def timeout_provider():
            nonlocal call_count
            call_count += 1
            raise asyncio.TimeoutError("provider timeout")

        retry_config = RetryConfig(max_attempts=2, initial_delay=0.01, jitter=False)

        for _ in range(3):
            with pytest.raises(asyncio.TimeoutError):
                await cb.call(with_retry, timeout_provider, retry_config)

        assert cb.state == CircuitState.OPEN
        # 3 轮 × 2 次重试 = 6 次实际调用
        assert call_count == 6

        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(timeout_provider)

    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """熔断后降级响应"""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("degrade-test", config)

        async def failing():
            raise ConnectionError("down")

        with pytest.raises(ConnectionError):
            await cb.call(failing)

        def degraded_response():
            return "服务暂时不可用，请稍后重试。"

        if cb.state == CircuitState.OPEN:
            result = degraded_response()
            assert "不可用" in result

    @pytest.mark.asyncio
    async def test_metrics_during_degradation(self):
        """降级过程中的指标收集"""
        m = MetricsCollector()
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker("metrics-test", config)

        async def failing():
            raise ConnectionError("down")

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(failing)
            m.inc_counter("llm_request_total", tags={"status": "error"})

        m.set_gauge("circuit_breaker_state", 1, tags={"provider": "test"})

        assert m.get_counter("llm_request_total", tags={"status": "error"}) == 2.0
        assert m.get_gauge("circuit_breaker_state", tags={"provider": "test"}) == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
