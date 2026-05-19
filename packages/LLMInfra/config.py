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
        self._load_providers_from_env()

    def _load_providers_from_env(self):
        """从环境变量加载提供商配置"""
        # 默认 OpenAI 配置
        if "openai" not in self.providers:
            self.providers["openai"] = ProviderConfig(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                default_model=os.getenv("OPENAI_DEFAULT_MODEL", "gpt-3.5-turbo"),
                cost_per_1k_input_tokens=0.0015,
                cost_per_1k_output_tokens=0.002
            )

        # 其他提供商配置
        providers_env = ["ANTHROPIC", "QIANWEN", "ZHIPU", "ERNIE", "MIMO"]
        for prov in providers_env:
            api_key = os.getenv(f"{prov}_API_KEY")
            if api_key:
                prov_name = prov.lower()

                # MIMO 特殊处理：优先使用 MIMO_BASE_URL_OPENAI，其次 MIMO_BASE_URL
                if prov_name == "mimo":
                    base_url = os.getenv("MIMO_BASE_URL_OPENAI") or os.getenv("MIMO_BASE_URL")
                else:
                    base_url = os.getenv(f"{prov}_BASE_URL")

                self.providers[prov_name] = ProviderConfig(
                    api_key=api_key,
                    base_url=base_url,
                    default_model=os.getenv(f"{prov}_DEFAULT_MODEL", self._get_default_model(prov_name))
                )

    def _get_default_model(self, provider: str) -> str:
        """获取提供商默认模型"""
        defaults = {
            "openai": "gpt-3.5-turbo",
            "anthropic": "claude-2",
            "qianwen": "qwen-turbo",
            "zhipu": "glm-4",
            "ernie": "ernie-4.0",
            "mimo": "mimo-v2.5-pro"
        }
        return defaults.get(provider, "gpt-3.5-turbo")

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
