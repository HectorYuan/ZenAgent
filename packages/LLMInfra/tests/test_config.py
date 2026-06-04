"""
config 模块单元测试

覆盖: Settings, ProviderConfig, CacheConfig, RateLimitConfig, TokenBudgetConfig, ResponseConfig
"""

import pytest
from unittest.mock import patch

from packages.LLMInfra.config import (
    Settings,
    ProviderConfig,
    CacheConfig,
    RateLimitConfig,
    TokenBudgetConfig,
    ResponseConfig,
)


# ── ProviderConfig ────────────────────────────────────────────


class TestProviderConfig:
    """ProviderConfig 构造与序列化"""

    def test_construct_with_defaults(self):
        """使用默认值构造 ProviderConfig"""
        cfg = ProviderConfig(api_key="sk-test")
        assert cfg.api_key == "sk-test"
        assert cfg.base_url is None
        assert cfg.default_model == "gpt-3.5-turbo"
        assert cfg.models is None
        assert cfg.enabled is True
        assert cfg.max_retries == 3
        assert cfg.timeout == 60

    def test_construct_with_custom_values(self):
        """使用自定义值构造 ProviderConfig"""
        cfg = ProviderConfig(
            api_key="sk-custom",
            base_url="https://api.example.com/v1",
            default_model="gpt-4",
            models=["gpt-4", "gpt-4-turbo"],
            enabled=False,
            max_retries=5,
            timeout=30,
            cost_per_1k_input_tokens=0.01,
            cost_per_1k_output_tokens=0.03,
        )
        assert cfg.api_key == "sk-custom"
        assert cfg.base_url == "https://api.example.com/v1"
        assert cfg.default_model == "gpt-4"
        assert cfg.models == ["gpt-4", "gpt-4-turbo"]
        assert cfg.enabled is False
        assert cfg.max_retries == 5
        assert cfg.timeout == 30
        assert cfg.cost_per_1k_input_tokens == 0.01
        assert cfg.cost_per_1k_output_tokens == 0.03

    def test_dataclass_asdict(self):
        """ProviderConfig 可通过 dataclasses.asdict 序列化"""
        from dataclasses import asdict

        cfg = ProviderConfig(api_key="sk-test", base_url="https://api.test.com")
        d = asdict(cfg)
        assert isinstance(d, dict)
        assert d["api_key"] == "sk-test"
        assert d["base_url"] == "https://api.test.com"
        assert d["default_model"] == "gpt-3.5-turbo"


# ── CacheConfig / RateLimitConfig / TokenBudgetConfig / ResponseConfig ──


class TestSubConfigs:
    """各子配置的默认值验证"""

    def test_cache_config_defaults(self):
        """CacheConfig 默认值"""
        cfg = CacheConfig()
        assert cfg.enabled is True
        assert cfg.type == "redis"
        assert cfg.redis_url == "redis://localhost:6379/0"
        assert cfg.ttl == 3600
        assert cfg.similarity_threshold == 0.9

    def test_rate_limit_config_defaults(self):
        """RateLimitConfig 默认值"""
        cfg = RateLimitConfig()
        assert cfg.enabled is True
        assert cfg.requests_per_minute == 60
        assert cfg.tokens_per_minute == 90000

    def test_token_budget_config_defaults(self):
        """TokenBudgetConfig 默认值"""
        cfg = TokenBudgetConfig()
        assert cfg.enabled is True
        assert cfg.simple_qa_max_tokens == 400
        assert cfg.general_max_tokens == 1150
        assert cfg.complex_max_tokens == 2250
        assert cfg.creative_max_tokens == 3000
        assert cfg.max_context_tokens == 8000
        assert cfg.min_recent_messages == 4

    def test_response_config_defaults(self):
        """ResponseConfig 默认值"""
        cfg = ResponseConfig()
        assert cfg.enabled is True
        assert cfg.auto_retry_on_truncation is True
        assert cfg.max_retry_attempts == 1
        assert cfg.truncation_threshold == 0.95


# ── Settings ──────────────────────────────────────────────────


class TestSettings:
    """Settings 构造与方法"""

    def test_construct_with_defaults(self):
        """Settings 默认构造 — 不加载外部配置"""
        with patch.object(Settings, "_load_providers_from_core_config"):
            s = Settings()
        assert s.default_provider == "openai"
        assert s.log_level == "INFO"
        assert isinstance(s.cache, CacheConfig)
        assert isinstance(s.rate_limit, RateLimitConfig)
        assert isinstance(s.token_budget, TokenBudgetConfig)
        assert isinstance(s.response, ResponseConfig)

    def test_fallback_adds_openai_provider(self):
        """加载配置异常时自动添加 openai fallback provider"""
        with patch(
            "packages.LLMInfra.modelnexus_core_config.get_core_config",
            side_effect=Exception("no config"),
        ):
            s = Settings()
        assert "openai" in s.providers
        assert s.providers["openai"].api_key == ""

    def test_get_provider_config_raises_for_unknown(self):
        """get_provider_config 对未知 provider 抛出 ValueError"""
        with patch.object(Settings, "_load_providers_from_core_config"):
            s = Settings()
        with pytest.raises(ValueError, match="not configured"):
            s.get_provider_config("nonexistent")

    def test_get_provider_config_returns_existing(self):
        """get_provider_config 返回已配置的 provider"""
        with patch.object(Settings, "_load_providers_from_core_config"):
            s = Settings()
        s.providers["test"] = ProviderConfig(api_key="sk-test")
        cfg = s.get_provider_config("test")
        assert cfg.api_key == "sk-test"

    def test_get_provider_model(self):
        """get_provider_model 返回 provider 的默认模型"""
        with patch.object(Settings, "_load_providers_from_core_config"):
            s = Settings()
        s.providers["deepseek"] = ProviderConfig(
            api_key="sk-ds", default_model="deepseek-chat"
        )
        assert s.get_provider_model("deepseek") == "deepseek-chat"

    def test_calculate_cost(self):
        """calculate_cost 正确计算调用成本"""
        with patch.object(Settings, "_load_providers_from_core_config"):
            s = Settings()
        s.providers["openai"] = ProviderConfig(
            api_key="sk-test",
            cost_per_1k_input_tokens=0.0015,
            cost_per_1k_output_tokens=0.002,
        )
        # 1000 input tokens * 0.0015 + 2000 output tokens * 0.002 = 0.0015 + 0.004 = 0.0055
        cost = s.calculate_cost("openai", input_tokens=1000, output_tokens=2000)
        assert abs(cost - 0.0055) < 1e-9
