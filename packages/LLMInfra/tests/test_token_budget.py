"""
Token Budget Manager 单元测试
"""

import pytest
from ..core import Message, MessageRole
from ..config import TokenBudgetConfig
from ..token_budget import (
    TokenEstimator,
    IntentClassifier,
    TokenBudgetManager,
    IntentCategory,
    BudgetResult,
)


def _user(text: str) -> Message:
    return Message(role=MessageRole.USER, content=text)


def _system(text: str) -> Message:
    return Message(role=MessageRole.SYSTEM, content=text)


def _assistant(text: str) -> Message:
    return Message(role=MessageRole.ASSISTANT, content=text)


# ── TokenEstimator ──────────────────────────────────────────


class TestTokenEstimator:
    def test_empty_string(self):
        assert TokenEstimator.estimate("") == 0

    def test_none_like(self):
        assert TokenEstimator.estimate("") == 0

    def test_short_text(self):
        # "hello" = 5 chars, 5//4 = 1
        assert TokenEstimator.estimate("hello") == 1

    def test_longer_text(self):
        # 20 chars -> 5 tokens
        assert TokenEstimator.estimate("a" * 20) == 5

    def test_estimate_messages(self):
        msgs = [_user("hello"), _assistant("hi there")]
        # "hello"=5//4=1, "hi there"=8//4=2 -> 3
        assert TokenEstimator.estimate_messages(msgs) == 3

    def test_estimate_empty_messages(self):
        assert TokenEstimator.estimate_messages([]) == 0


# ── IntentClassifier ────────────────────────────────────────


class TestIntentClassifier:
    def test_simple_greeting(self):
        msgs = [_user("Hi")]
        intent, conf = IntentClassifier.classify(msgs)
        assert intent == IntentCategory.SIMPLE_QA
        assert conf == 1.0

    def test_simple_question(self):
        msgs = [_user("What time is it?")]
        intent, _ = IntentClassifier.classify(msgs)
        # "what" alone doesn't match "what is", so SIMPLE_QA
        assert intent == IntentCategory.SIMPLE_QA

    def test_general_knowledge(self):
        msgs = [_user("What is machine learning?")]
        intent, _ = IntentClassifier.classify(msgs)
        assert intent == IntentCategory.GENERAL_REASONING

    def test_general_by_length(self):
        # 超过 500 字符 -> GENERAL_REASONING
        msgs = [_user("x" * 600)]
        intent, _ = IntentClassifier.classify(msgs)
        assert intent == IntentCategory.GENERAL_REASONING

    def test_complex_reasoning_keyword(self):
        msgs = [_user("Analyze the trade-offs of microservices vs monolith")]
        intent, _ = IntentClassifier.classify(msgs)
        assert intent == IntentCategory.COMPLEX_REASONING

    def test_complex_by_length(self):
        # 超过 2000 字符 -> COMPLEX_REASONING
        msgs = [_user("x" * 2500)]
        intent, _ = IntentClassifier.classify(msgs)
        assert intent == IntentCategory.COMPLEX_REASONING

    def test_creative_writing(self):
        # 需要关键词 + 长度>200
        msgs = [_user("Write a story about " + "x" * 250)]
        intent, _ = IntentClassifier.classify(msgs)
        assert intent == IntentCategory.CREATIVE_WRITING

    def test_creative_chinese(self):
        msgs = [_user("写一篇关于人工智能未来的文章 " + "x" * 250)]
        intent, _ = IntentClassifier.classify(msgs)
        assert intent == IntentCategory.CREATIVE_WRITING

    def test_system_message_excluded(self):
        # 分类只看最后一条 USER 消息
        msgs = [_system("You are a helpful assistant"), _user("Hi")]
        intent, _ = IntentClassifier.classify(msgs)
        assert intent == IntentCategory.SIMPLE_QA

    def test_empty_messages(self):
        intent, _ = IntentClassifier.classify([])
        assert intent == IntentCategory.SIMPLE_QA

    def test_no_user_message(self):
        msgs = [_system("You are helpful")]
        intent, _ = IntentClassifier.classify(msgs)
        assert intent == IntentCategory.SIMPLE_QA


# ── TokenBudgetManager ──────────────────────────────────────


class TestTokenBudgetManager:
    def setup_method(self):
        self.config = TokenBudgetConfig()
        self.manager = TokenBudgetManager(self.config)

    def test_disabled_returns_none(self):
        config = TokenBudgetConfig(enabled=False)
        mgr = TokenBudgetManager(config)
        msgs = [_user("Hello, how are you?")]
        result = mgr.allocate(msgs)
        assert result.max_tokens is None

    def test_explicit_max_tokens_respected(self):
        msgs = [_user("Hi")]
        result = self.manager.allocate(msgs, caller_max_tokens=5000)
        assert result.max_tokens == 5000

    def test_simple_qa_allocation(self):
        msgs = [_user("Hi")]
        result = self.manager.allocate(msgs)
        assert result.max_tokens == self.config.simple_qa_max_tokens
        assert result.intent == IntentCategory.SIMPLE_QA

    def test_general_reasoning_allocation(self):
        msgs = [_user("What is deep learning?")]
        result = self.manager.allocate(msgs)
        assert result.max_tokens == self.config.general_max_tokens
        assert result.intent == IntentCategory.GENERAL_REASONING

    def test_complex_reasoning_allocation(self):
        msgs = [_user("Analyze the trade-offs between SQL and NoSQL databases")]
        result = self.manager.allocate(msgs)
        assert result.max_tokens == self.config.complex_max_tokens
        assert result.intent == IntentCategory.COMPLEX_REASONING

    def test_creative_writing_allocation(self):
        msgs = [_user("Write a story about " + "x" * 250)]
        result = self.manager.allocate(msgs)
        assert result.max_tokens == self.config.creative_max_tokens
        assert result.intent == IntentCategory.CREATIVE_WRITING

    def test_budget_result_fields(self):
        msgs = [_user("Hello world")]
        result = self.manager.allocate(msgs)
        assert isinstance(result, BudgetResult)
        assert result.estimated_input_tokens > 0
        assert result.truncated is False

    def test_no_truncation_when_under_limit(self):
        msgs = [_user("short")]
        result = self.manager.maybe_truncate(msgs)
        assert len(result) == 1
        assert result[0].content == "short"

    def test_truncation_preserves_system(self):
        # 构造大量消息超过 max_context_tokens (8000 tokens ~ 32000 chars)
        system_msg = _system("You are a helpful assistant")
        history = []
        for i in range(100):
            history.append(_user(f"Message {i} " + "x" * 400))
            history.append(_assistant(f"Reply {i} " + "x" * 400))

        messages = [system_msg] + history
        result = self.manager.maybe_truncate(messages)

        # system 消息应保留
        assert result[0].role == MessageRole.SYSTEM
        assert result[0].content == "You are a helpful assistant"
        # 总消息数应减少
        assert len(result) < len(messages)

    def test_truncation_preserves_recent(self):
        system_msg = _system("System prompt")
        history = []
        for i in range(100):
            history.append(_user(f"msg{i} " + "x" * 400))
            history.append(_assistant(f"rep{i} " + "x" * 400))

        messages = [system_msg] + history
        result = self.manager.maybe_truncate(messages)

        # 最后的消息应保留
        last_contents = [m.content for m in result[-4:]]
        assert any("msg99" in c for c in last_contents)

    def test_truncation_inserts_placeholder(self):
        system_msg = _system("System")
        history = []
        for i in range(100):
            history.append(_user(f"msg{i} " + "x" * 400))
            history.append(_assistant(f"rep{i} " + "x" * 400))

        messages = [system_msg] + history
        result = self.manager.maybe_truncate(messages)

        # 应有截断占位消息
        placeholders = [m for m in result if "truncated" in m.content.lower()]
        assert len(placeholders) == 1

    def test_disabled_no_truncation(self):
        config = TokenBudgetConfig(enabled=False)
        mgr = TokenBudgetManager(config)
        msgs = [_user("x" * 100000)]
        result = mgr.maybe_truncate(msgs)
        assert len(result) == 1
