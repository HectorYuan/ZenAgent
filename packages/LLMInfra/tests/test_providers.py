"""Provider 基础测试 (M7)"""
import pytest
from packages.LLMInfra.providers.base import BaseProvider
from packages.LLMInfra.providers.factory import ProviderFactory
from packages.LLMInfra.providers.mock_provider import MockProvider
from packages.LLMInfra.config import Settings, ProviderConfig


class TestProviderFactory:
    def test_available_providers(self):
        settings = Settings(providers={
            "mock": ProviderConfig(api_key="", base_url="", default_model="mock"),
        })
        factory = ProviderFactory(settings)
        providers = factory.get_available_providers()
        assert "mock" in providers
        assert "openai" in providers  # auto-loaded from env

    def test_get_mock_provider(self):
        settings = Settings(providers={
            "mock": ProviderConfig(api_key="", base_url="", default_model="mock"),
        })
        factory = ProviderFactory(settings)
        provider = factory.get_provider("mock")
        assert isinstance(provider, MockProvider)

    def test_invalid_provider(self):
        settings = Settings()
        factory = ProviderFactory(settings)
        with pytest.raises(ValueError):
            factory.get_provider("nonexistent")


class TestMockProvider:
    @pytest.mark.asyncio
    async def test_chat(self):
        from packages.LLMInfra.core import ChatRequest, Message, MessageRole
        settings = Settings(providers={
            "mock": ProviderConfig(api_key="", base_url="", default_model="mock"),
        }, default_provider="mock")
        factory = ProviderFactory(settings)
        provider = factory.get_provider("mock")
        request = ChatRequest(
            model="mock", messages=[Message(role=MessageRole.USER, content="hi")]
        )
        response = await provider.chat(request)
        assert response.content
        assert response.provider == "mock"

    @pytest.mark.asyncio
    async def test_chat_stream(self):
        from packages.LLMInfra.core import ChatRequest, Message, MessageRole
        settings = Settings(providers={
            "mock": ProviderConfig(api_key="", base_url="", default_model="mock"),
        }, default_provider="mock")
        factory = ProviderFactory(settings)
        provider = factory.get_provider("mock")
        request = ChatRequest(
            model="mock", messages=[Message(role=MessageRole.USER, content="test")]
        )
        chunks = []
        async for chunk in provider.chat_stream(request):
            chunks.append(chunk)
        assert len(chunks) > 0
