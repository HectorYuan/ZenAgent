"""
LLMInfra 基础测试
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from .core import LLMClient, Message, MessageRole, ChatRequest, LLMResponse
from .config import Settings, ProviderConfig
from .exceptions import ProviderError, RateLimitError


def test_message_creation():
    """测试消息创建"""
    msg = Message(role=MessageRole.USER, content="Hello")
    assert msg.role == MessageRole.USER
    assert msg.content == "Hello"
    assert msg.name is None


def test_settings_creation():
    """测试配置创建"""
    settings = Settings()
    assert settings.default_provider == "openai"
    assert "openai" in settings.providers


def test_chat_request():
    """测试聊天请求"""
    messages = [Message(role=MessageRole.USER, content="Hello")]
    request = ChatRequest(model="gpt-3.5-turbo", messages=messages)
    assert request.model == "gpt-3.5-turbo"
    assert len(request.messages) == 1


def test_llm_response():
    """测试响应模型"""
    messages = [Message(role=MessageRole.USER, content="Hello")]
    response = LLMResponse(
        provider="openai",
        model="gpt-3.5-turbo",
        content="Hi!",
        messages=messages,
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        cost=0.000015
    )
    assert response.provider == "openai"
    assert response.cost > 0


@pytest.mark.asyncio
async def test_client_creation():
    """测试客户端创建"""
    settings = Settings()
    client = LLMClient(settings)
    assert client.settings is not None
    assert client.provider_factory is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
