"""
响应完整性校验器单元测试
"""

import pytest
from ..core import Message, MessageRole, ChatRequest, LLMResponse
from ..config import ResponseConfig
from ..response_validator import ResponseValidator, ValidationResult


def _make_response(content="Hello", finish_reason="stop", completion_tokens=10):
    return LLMResponse(
        provider="test",
        model="test-model",
        content=content,
        messages=[],
        usage={"prompt_tokens": 10, "completion_tokens": completion_tokens, "total_tokens": 20},
        finish_reason=finish_reason,
    )


def _make_request(max_tokens=None):
    return ChatRequest(
        model="test-model",
        messages=[Message(role=MessageRole.USER, content="test")],
        max_tokens=max_tokens,
    )


class TestResponseValidator:
    def setup_method(self):
        self.config = ResponseConfig()
        self.validator = ResponseValidator(self.config)

    def test_normal_response_valid(self):
        response = _make_response()
        result = self.validator.validate(response, _make_request())
        assert result.is_valid is True
        assert result.issue is None

    def test_empty_content_invalid(self):
        response = _make_response(content="")
        result = self.validator.validate(response, _make_request())
        assert result.is_valid is False
        assert result.issue == "empty"

    def test_whitespace_only_empty(self):
        response = _make_response(content="   ")
        result = self.validator.validate(response, _make_request())
        assert result.is_valid is False
        assert result.issue == "empty"

    def test_content_filter_invalid(self):
        response = _make_response(finish_reason="content_filter")
        result = self.validator.validate(response, _make_request())
        assert result.is_valid is False
        assert result.issue == "content_filter"

    def test_truncated_by_finish_reason(self):
        response = _make_response(finish_reason="length")
        result = self.validator.validate(response, _make_request())
        assert result.is_valid is False
        assert result.issue == "truncated"

    def test_truncated_by_token_ratio(self):
        # completion_tokens(95) / max_tokens(100) = 0.95 >= threshold(0.95)
        response = _make_response(completion_tokens=95)
        request = _make_request(max_tokens=100)
        result = self.validator.validate(response, request)
        assert result.is_valid is False
        assert result.issue == "truncated"

    def test_not_truncated_below_threshold(self):
        # completion_tokens(94) / max_tokens(100) = 0.94 < threshold(0.95)
        response = _make_response(completion_tokens=94)
        request = _make_request(max_tokens=100)
        result = self.validator.validate(response, request)
        assert result.is_valid is True

    def test_no_max_tokens_skips_ratio_check(self):
        # 没有 max_tokens 时不做比值检查
        response = _make_response(completion_tokens=9999)
        request = _make_request(max_tokens=None)
        result = self.validator.validate(response, request)
        assert result.is_valid is True

    def test_disabled_always_valid(self):
        config = ResponseConfig(enabled=False)
        validator = ResponseValidator(config)
        response = _make_response(content="", finish_reason="length")
        result = validator.validate(response, _make_request())
        assert result.is_valid is True

    def test_result_has_finish_reason(self):
        response = _make_response(finish_reason="stop")
        result = self.validator.validate(response, _make_request())
        assert result.finish_reason == "stop"

    def test_result_has_detail_on_failure(self):
        response = _make_response(finish_reason="length")
        result = self.validator.validate(response, _make_request())
        assert result.detail is not None
        assert "截断" in result.detail


class TestCustomThreshold:
    def test_custom_threshold(self):
        config = ResponseConfig(truncation_threshold=0.90)
        validator = ResponseValidator(config)
        # 90/100 = 0.90 >= 0.90
        response = _make_response(completion_tokens=90)
        request = _make_request(max_tokens=100)
        result = validator.validate(response, request)
        assert result.is_valid is False
        assert result.issue == "truncated"
