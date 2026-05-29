"""
配置管理模块
"""

from typing import Dict, Optional, Any
from dataclasses import dataclass, field
import os
from functools import lru_cache


@dataclass
class ProviderConfig:
    """提供商配置"""
    api_key: str
    base_url: Optional[str] = None
    default_model: str = "gpt-3.5-turbo"
    models: Optional[list[str]] = None
    enabled: bool = True
    max_retries: int = 3
    timeout: int = 60
    cost_per_1k_input_tokens: float = 0.0015
    cost_per_1k_output_tokens: float = 0.002


@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    type: str = "redis"  # redis, memory
    redis_url: Optional[str] = "redis://localhost:6379/0"
    ttl: int = 3600  # 1 hour
    similarity_threshold: float = 0.9


@dataclass
class RateLimitConfig:
    """限流配置"""
    enabled: bool = True
    requests_per_minute: int = 60
    tokens_per_minute: int = 90000


@dataclass
class TokenBudgetConfig:
    """Token 预算配置"""
    enabled: bool = True
    simple_qa_max_tokens: int = 400       # 闲聊/简单问答 (300-500)
    general_max_tokens: int = 1150        # 一般推理 (800-1500)
    complex_max_tokens: int = 2250        # 复杂推理 (1500-3000)
    creative_max_tokens: int = 3000       # 创意写作 (2000-4000)
    max_context_tokens: int = 8000        # 超过此值触发上下文截断
    min_recent_messages: int = 4          # 截断时至少保留的近期消息数


@dataclass
class ResponseConfig:
    """响应完整性校验配置"""
    enabled: bool = True
    auto_retry_on_truncation: bool = True
    max_retry_attempts: int = 1
    truncation_threshold: float = 0.95  # completion_tokens/max_tokens 比值


@dataclass
class Settings:
    """全局配置"""
    default_provider: str = "openai"

    providers: Dict[str, ProviderConfig] = field(default_factory=dict)

    cache: CacheConfig = field(default_factory=CacheConfig)

    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)

    token_budget: TokenBudgetConfig = field(default_factory=TokenBudgetConfig)

    response: ResponseConfig = field(default_factory=ResponseConfig)

    log_level: str = "INFO"

    def __post_init__(self):
        self._load_providers_from_core_config()

    def _load_providers_from_core_config(self):
        """从 ModelNexusCore 集中化配置加载提供商配置"""
        try:
            from packages.LLMInfra.modelnexus_core_config import (
                get_core_config, resolve_provider_key, get_provider_base_url,
                resolve_provider_model
            )
            cfg = get_core_config()
            for name, entry in cfg.providers.items():
                if not entry.enabled:
                    continue
                key = resolve_provider_key(name) or entry.api_key
                if key or name in ("mock", "modelnexus"):
                    base_url = get_provider_base_url(name) or entry.base_url
                    model = resolve_provider_model(name)
                    self.providers[name] = ProviderConfig(
                        api_key=key,
                        base_url=base_url,
                        default_model=model,
                        max_retries=entry.max_retries,
                        timeout=entry.timeout,
                        cost_per_1k_input_tokens=entry.cost_per_1k_input_tokens,
                        cost_per_1k_output_tokens=entry.cost_per_1k_output_tokens,
                    )
        except Exception:
            # Fallback: 如果集中化配置不可用，使用默认空配置
            if "openai" not in self.providers:
                self.providers["openai"] = ProviderConfig(
                    api_key="",
                    base_url="https://api.openai.com/v1",
                    default_model="gpt-3.5-turbo",
                )

    def get_provider_config(self, provider: str) -> ProviderConfig:
        """获取提供商配置"""
        if provider not in self.providers:
            raise ValueError(f"Provider '{provider}' not configured")
        return self.providers[provider]

    def get_provider_model(self, provider: str) -> str:
        """获取提供商默认模型"""
        config = self.get_provider_config(provider)
        return config.default_model

    def calculate_cost(
        self,
        provider: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """计算调用成本"""
        config = self.get_provider_config(provider)
        input_cost = (input_tokens / 1000) * config.cost_per_1k_input_tokens
        output_cost = (output_tokens / 1000) * config.cost_per_1k_output_tokens
        return input_cost + output_cost


@lru_cache()
def get_settings() -> Settings:
    """获取全局配置单例"""
    return Settings()
