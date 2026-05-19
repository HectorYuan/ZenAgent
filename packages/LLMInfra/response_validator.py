"""
响应完整性校验模块

检测 LLM 响应是否被截断、为空或被内容过滤。
"""

import logging
from dataclasses import dataclass
from typing import Optional

from .core import LLMResponse, ChatRequest
from .config import ResponseConfig

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """校验结果"""
    is_valid: bool
    issue: Optional[str] = None  # "truncated", "empty", "content_filter"
    finish_reason: Optional[str] = None
    detail: Optional[str] = None


class ResponseValidator:
    """响应完整性校验器"""

    def __init__(self, config: ResponseConfig):
        self.config = config

    def validate(self, response: LLMResponse, request: ChatRequest) -> ValidationResult:
        if not self.config.enabled:
            return ValidationResult(is_valid=True, finish_reason=response.finish_reason)

        # 1. 空内容
        if not response.content or not response.content.strip():
            return ValidationResult(
                is_valid=False,
                issue="empty",
                finish_reason=response.finish_reason,
                detail="响应内容为空",
            )

        # 2. 内容过滤
        if response.finish_reason == "content_filter":
            return ValidationResult(
                is_valid=False,
                issue="content_filter",
                finish_reason=response.finish_reason,
                detail="响应被内容过滤器拦截",
            )

        # 3. 明确截断
        if response.finish_reason == "length":
            return ValidationResult(
                is_valid=False,
                issue="truncated",
                finish_reason=response.finish_reason,
                detail="响应因达到 max_tokens 被截断",
            )

        # 4. 疑似截断：completion_tokens 接近 max_tokens
        if request.max_tokens and request.max_tokens > 0:
            completion_tokens = response.usage.get("completion_tokens", 0)
            ratio = completion_tokens / request.max_tokens
            if ratio >= self.config.truncation_threshold:
                return ValidationResult(
                    is_valid=False,
                    issue="truncated",
                    finish_reason=response.finish_reason,
                    detail=f"疑似截断: completion_tokens({completion_tokens}) / max_tokens({request.max_tokens}) = {ratio:.2%}",
                )

        return ValidationResult(is_valid=True, finish_reason=response.finish_reason)
