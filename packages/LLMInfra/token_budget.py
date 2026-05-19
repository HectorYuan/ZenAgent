"""
Token 预算管理模块

按问题意图动态分配 max_tokens，管理上下文窗口大小。
"""

import logging
from enum import Enum
from typing import List, Optional, Tuple
from dataclasses import dataclass

from .core import Message, MessageRole
from .config import TokenBudgetConfig

logger = logging.getLogger(__name__)


class IntentCategory(str, Enum):
    """意图分类"""
    SIMPLE_QA = "simple_qa"
    GENERAL_REASONING = "general"
    COMPLEX_REASONING = "complex"
    CREATIVE_WRITING = "creative"


@dataclass
class BudgetResult:
    """预算分配结果"""
    max_tokens: Optional[int]
    intent: IntentCategory
    estimated_input_tokens: int
    truncated: bool


class TokenEstimator:
    """Token 数量粗估器（len//4 启发式）"""

    @staticmethod
    def estimate(text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    @staticmethod
    def estimate_messages(messages: List[Message]) -> int:
        return sum(TokenEstimator.estimate(msg.content) for msg in messages)


class IntentClassifier:
    """基于规则的意图分类器"""

    CREATIVE_KEYWORDS = {
        "write", "story", "poem", "essay", "create", "draft", "compose",
        "generate article", "write a", "write an",
        "写", "创作", "写一篇", "编一个", "写一个故事", "写首诗", "写篇文章",
    }

    COMPLEX_KEYWORDS = {
        "analyze", "compare", "evaluate", "explain why", "reason", "prove",
        "debug", "optimize", "think step by step", "chain of thought",
        "trade-off", "tradeoff", "pros and cons", "design a system",
        "分析", "比较", "推理", "证明", "优化", "为什么", "权衡", "设计一个系统",
    }

    GENERAL_KEYWORDS = {
        "how", "what is", "what are", "describe", "summarize", "translate",
        "define", "explain", "list", "tell me about",
        "怎么", "是什么", "描述", "翻译", "总结", "解释", "列举", "告诉我",
    }

    @staticmethod
    def classify(messages: List[Message]) -> Tuple[IntentCategory, float]:
        if not messages:
            return IntentCategory.SIMPLE_QA, 1.0

        # 只看最后一条用户消息
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                last_user_msg = msg.content.lower()
                break

        if not last_user_msg:
            return IntentCategory.SIMPLE_QA, 1.0

        total_chars = sum(len(msg.content) for msg in messages)

        # 1. 创意写作：关键词 + 长文本
        if total_chars > 200:
            for kw in IntentClassifier.CREATIVE_KEYWORDS:
                if kw in last_user_msg:
                    return IntentCategory.CREATIVE_WRITING, 1.0

        # 2. 复杂推理：关键词 或 超长输入
        if total_chars > 2000:
            return IntentCategory.COMPLEX_REASONING, 1.0
        for kw in IntentClassifier.COMPLEX_KEYWORDS:
            if kw in last_user_msg:
                return IntentCategory.COMPLEX_REASONING, 1.0

        # 3. 一般推理：关键词 或 中等输入
        if total_chars > 500:
            return IntentCategory.GENERAL_REASONING, 1.0
        for kw in IntentClassifier.GENERAL_KEYWORDS:
            if kw in last_user_msg:
                return IntentCategory.GENERAL_REASONING, 1.0

        # 4. 简单问答
        return IntentCategory.SIMPLE_QA, 1.0


class TokenBudgetManager:
    """Token 预算管理器"""

    def __init__(self, config: TokenBudgetConfig):
        self.config = config
        self._classifier = IntentClassifier()
        self._estimator = TokenEstimator()

    def allocate(
        self, messages: List[Message], caller_max_tokens: Optional[int] = None
    ) -> BudgetResult:
        estimated_input = self._estimator.estimate_messages(messages)

        # 调用方显式指定则尊重
        if caller_max_tokens is not None:
            return BudgetResult(
                max_tokens=caller_max_tokens,
                intent=IntentCategory.SIMPLE_QA,
                estimated_input_tokens=estimated_input,
                truncated=False,
            )

        # 未启用则不限制
        if not self.config.enabled:
            return BudgetResult(
                max_tokens=None,
                intent=IntentCategory.SIMPLE_QA,
                estimated_input_tokens=estimated_input,
                truncated=False,
            )

        intent, _ = self._classifier.classify(messages)
        budget_map = {
            IntentCategory.SIMPLE_QA: self.config.simple_qa_max_tokens,
            IntentCategory.GENERAL_REASONING: self.config.general_max_tokens,
            IntentCategory.COMPLEX_REASONING: self.config.complex_max_tokens,
            IntentCategory.CREATIVE_WRITING: self.config.creative_max_tokens,
        }
        max_tokens = budget_map[intent]

        logger.debug(
            "Token budget: intent=%s, max_tokens=%d, estimated_input=%d",
            intent.value, max_tokens, estimated_input,
        )

        return BudgetResult(
            max_tokens=max_tokens,
            intent=intent,
            estimated_input_tokens=estimated_input,
            truncated=False,
        )

    def maybe_truncate(self, messages: List[Message]) -> List[Message]:
        if not self.config.enabled:
            return messages

        estimated = self._estimator.estimate_messages(messages)
        if estimated <= self.config.max_context_tokens:
            return messages

        # 分离 system 消息和非 system 消息
        system_msgs = [m for m in messages if m.role == MessageRole.SYSTEM]
        non_system_msgs = [m for m in messages if m.role != MessageRole.SYSTEM]

        # 保留最近的消息
        keep_count = max(self.config.min_recent_messages, len(non_system_msgs) // 2)
        kept = non_system_msgs[-keep_count:]
        removed_count = len(non_system_msgs) - len(kept)

        if removed_count <= 0:
            return messages

        # 插入截断占位消息
        from .core import MessageRole as MR
        placeholder = Message(
            role=MR.USER,
            content=f"[Previous conversation truncated: {removed_count} messages removed to fit context window]",
        )

        result = system_msgs + [placeholder] + kept
        logger.debug(
            "Context truncated: removed %d messages, kept %d (estimated %d -> ~%d tokens)",
            removed_count, len(kept), estimated,
            self._estimator.estimate_messages(result),
        )
        return result
