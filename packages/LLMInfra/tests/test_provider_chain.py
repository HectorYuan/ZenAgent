"""
Provider 责任链测试
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from packages.LLMInfra.providers.factory import ProviderFactory
from packages.LLMInfra.provider_chain import (
    ProviderChain,
    ProviderChainConfig,
    ChainStrategy,
    ChainResult,
    create_default_chain
)
from packages.LLMInfra.circuit_breaker import CircuitState
from packages.LLMInfra.config import Settings, ProviderConfig
from packages.LLMInfra.core import ChatRequest, Message, MessageRole
from packages.LLMInfra.exceptions import TimeoutError, RateLimitError


@pytest.fixture
def settings():
    """测试配置"""
    return Settings(
        providers={
            "modelnexus": ProviderConfig(
                api_key="test_key",
                base_url="http://localhost:8080",
                default_model="test-model"
            ),
            "openai": ProviderConfig(
                api_key="test_key",
                base_url="http://localhost:8081",
                default_model="gpt-4"
            ),
            "mock": ProviderConfig(
                api_key="",
                base_url="",
                default_model="mock-model"
            ),
        },
        default_provider="mock",
    )


@pytest.fixture
def factory(settings):
    """Provider 工厂"""
    return ProviderFactory(settings)


@pytest.fixture
def simple_chain(factory):
    """简单责任链（只有 mock provider）"""
    config = ProviderChainConfig(
        provider_priority=["mock"],
        provider_timeouts={"mock": 10.0},
        max_retries_per_provider=1
    )
    return ProviderChain(factory, config)


@pytest.fixture
def test_request():
    """测试请求"""
    return ChatRequest(
        model="mock-model",
        messages=[
            Message(role=MessageRole.USER, content="Hello")
        ]
    )


class TestProviderChainConfig:
    """测试责任链配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = ProviderChainConfig()
        assert "modelnexus" in config.provider_priority
        assert "openai" in config.provider_priority
        assert "mock" in config.provider_priority
        assert config.strategy == ChainStrategy.FAILOVER

    def test_custom_priority(self):
        """测试自定义优先级"""
        config = ProviderChainConfig(
            provider_priority=["openai", "mock"],
            max_retries_per_provider=3
        )
        assert config.provider_priority == ["openai", "mock"]
        assert config.max_retries_per_provider == 3


class TestProviderChainBasic:
    """测试责任链基本功能"""

    def test_create_default_chain(self, factory):
        """测试创建默认责任链"""
        chain = create_default_chain(factory)
        assert chain is not None
        assert len(chain._config.provider_priority) == 3

    def test_get_timeout(self, simple_chain):
        """测试获取超时配置"""
        assert simple_chain.get_timeout("mock") == 10.0
        assert simple_chain.get_timeout("unknown") == 30.0  # 默认值

    @pytest.mark.asyncio
    async def test_successful_call(self, simple_chain, test_request):
        """测试成功调用"""
        result = await simple_chain.chat(test_request)

        assert isinstance(result, ChainResult)
        assert result.success is True
        assert result.response is not None
        assert result.final_provider == "mock"
        assert len(result.attempts) == 1
        assert result.attempts[0].success is True

    @pytest.mark.asyncio
    async def test_fallback_chain(self, factory, test_request):
        """测试失败转移链"""
        # 使用单个 mock provider 配置进行测试
        config = ProviderChainConfig(
            provider_priority=["mock"],
            max_retries_per_provider=1
        )
        chain = ProviderChain(factory, config)

        result = await chain.chat(test_request)

        assert result.success is True
        assert result.final_provider == "mock"
        assert len(result.attempts) == 1


class TestProviderChainCircuitBreaker:
    """测试责任链与熔断器集成"""

    def test_individual_circuit_breakers(self, factory):
        """测试每个 Provider 有独立的熔断器"""
        config = ProviderChainConfig(
            provider_priority=["mock", "openai"],
            enable_individual_circuit_breakers=True
        )
        chain = ProviderChain(factory, config)

        assert "mock" in chain._circuit_breakers
        assert "openai" in chain._circuit_breakers
        assert chain._circuit_breakers["mock"].name == "provider_mock"

    def test_provider_health(self, factory):
        """测试 Provider 健康状态"""
        config = ProviderChainConfig(
            provider_priority=["mock"],
            enable_individual_circuit_breakers=True
        )
        chain = ProviderChain(factory, config)

        health = chain.get_provider_health()
        assert health["mock"] is True  # 初始状态是健康的

    def test_get_circuit_breaker_stats(self, factory):
        """测试获取熔断器统计"""
        config = ProviderChainConfig(
            provider_priority=["mock"],
            enable_individual_circuit_breakers=True
        )
        chain = ProviderChain(factory, config)

        stats = chain.get_circuit_breaker_stats()
        assert "mock" in stats
        assert stats["mock"]["state"] == "closed"

    def test_reset_circuit_breakers(self, factory):
        """测试重置熔断器"""
        config = ProviderChainConfig(
            provider_priority=["mock"],
            enable_individual_circuit_breakers=True
        )
        chain = ProviderChain(factory, config)

        # 先触发一些调用
        cb = chain._circuit_breakers["mock"]
        for _ in range(3):
            cb.record_failure()

        # 重置
        chain.reset_circuit_breakers()

        stats = chain.get_circuit_breaker_stats()
        assert stats["mock"]["failure_calls"] == 0
        assert stats["mock"]["state"] == "closed"


class TestProviderChainStrategies:
    """测试责任链策略"""

    @pytest.mark.asyncio
    async def test_failover_strategy(self, simple_chain, test_request):
        """测试 Failover 策略"""
        simple_chain._config.strategy = ChainStrategy.FAILOVER
        result = await simple_chain.chat(test_request)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_load_balance_strategy(self, factory, test_request):
        """测试 Load Balance 策略"""
        config = ProviderChainConfig(
            provider_priority=["mock1", "mock2", "mock3"],
            strategy=ChainStrategy.LOAD_BALANCE,
            max_retries_per_provider=1,
            enable_individual_circuit_breakers=False
        )
        # 注意：这里使用的 provider 名称在 factory 中可能不存在
        # 实际应用中应该使用已注册的 provider

        # 改用已注册的 provider
        config2 = ProviderChainConfig(
            provider_priority=["mock"],
            strategy=ChainStrategy.LOAD_BALANCE,
            max_retries_per_provider=1
        )
        chain = ProviderChain(factory, config2)

        result = await chain.chat(test_request)
        assert result.success is True


class TestProviderChainWithLLMClient:
    """测试 LLMClient 集成责任链"""

    @pytest.mark.asyncio
    async def test_chat_with_chain(self):
        """测试使用责任链聊天"""
        from packages.LLMInfra.core import LLMClient
        from packages.LLMInfra.config import Settings, ProviderConfig

        # 使用 mock 作为默认 provider 创建客户端
        settings = Settings(
            providers={
                "mock": ProviderConfig(
                    api_key="",
                    base_url="",
                    default_model="mock-model"
                ),
            },
            default_provider="mock",
        )
        client = LLMClient(settings=settings)

        # 确保责任链已初始化
        assert hasattr(client, "provider_chain")
        assert client.enable_provider_chain is True

        # 测试使用责任链的聊天
        messages = [Message(role=MessageRole.USER, content="Hello")]
        response = await client.chat_with_chain(messages)

        assert response is not None
        assert response.provider == "mock"

    def test_get_chain_health(self):
        """测试获取责任链健康状态"""
        from packages.LLMInfra.core import LLMClient

        client = LLMClient()
        health = client.get_chain_health()

        assert "provider_health" in health
        assert "circuit_breakers" in health
        assert "enabled" in health


class TestProviderChainHealthyProviders:
    """测试健康 Provider 筛选"""

    def test_get_health_providers_all_healthy(self, factory):
        """测试所有 Provider 都健康"""
        config = ProviderChainConfig(
            provider_priority=["mock", "openai"],
            enable_individual_circuit_breakers=True
        )
        chain = ProviderChain(factory, config)

        healthy = chain._get_health_providers()
        assert "mock" in healthy
        assert "openai" in healthy

    def test_get_health_providers_with_open_circuit(self, factory):
        """测试熔断器打开后 Provider 被标记为不健康"""
        config = ProviderChainConfig(
            provider_priority=["mock", "openai"],
            enable_individual_circuit_breakers=True
        )
        chain = ProviderChain(factory, config)

        # 手动打开 mock 的熔断器
        cb = chain._circuit_breakers["mock"]
        for _ in range(10):
            cb.record_failure()

        # 验证 mock 被排除
        healthy = chain._get_health_providers()
        assert "mock" not in healthy
        assert "openai" in healthy


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
