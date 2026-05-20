"""
LLMInfra - L0 层：LLM 基础设施层

提供大模型网关、统一接口、成本控制等功能
支持本地 Provider 和 ModelNexus 网关两种模式
"""

__version__ = "1.1.0"

from .core import LLMClient, LLMResponse, Message, MessageRole
from .providers import ProviderFactory, BaseProvider, MockProvider
from .config import Settings, ProviderConfig, CacheConfig, RateLimitConfig, TokenBudgetConfig, ResponseConfig
from .exceptions import LLMError, ProviderError, RateLimitError
from .token_budget import TokenBudgetManager, IntentCategory, BudgetResult
from .response_validator import ResponseValidator, ValidationResult
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState, CircuitBreakerOpenError
from .provider_chain import ProviderChain, ProviderChainConfig, ChainStrategy, ChainResult, create_default_chain
from .cache import CacheManager, HotspotTracker, HotLevel, EvictionManager, RingBuffer
from .precache import PreCacheWorker, PreCacheTask
from .intent_router import IntentRouter, L1RuleClassifier, PathDispatcher, Intent, RoutePath, ClassifyResult, RouteResult

try:
    from .modelnexus_adapter import ModelNexusAdapter, ModelNexusFallbackAdapter
    _HAS_MODELNEXUS = True
except ImportError:
    _HAS_MODELNEXUS = False
    ModelNexusAdapter = None
    ModelNexusFallbackAdapter = None

__all__ = [
    "LLMClient",
    "LLMResponse",
    "Message",
    "MessageRole",
    "ProviderFactory",
    "BaseProvider",
    "MockProvider",
    "Settings",
    "ProviderConfig",
    "CacheConfig",
    "RateLimitConfig",
    "TokenBudgetConfig",
    "TokenBudgetManager",
    "IntentCategory",
    "BudgetResult",
    "ResponseConfig",
    "ResponseValidator",
    "ValidationResult",
    "LLMError",
    "ProviderError",
    "RateLimitError",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "CircuitBreakerOpenError",
    "ProviderChain",
    "ProviderChainConfig",
    "ChainStrategy",
    "ChainResult",
    "create_default_chain",
    "HotspotTracker",
    "HotLevel",
    "EvictionManager",
    "RingBuffer",
    "PreCacheWorker",
    "PreCacheTask",
    "IntentRouter",
    "L1RuleClassifier",
    "PathDispatcher",
    "Intent",
    "RoutePath",
    "ClassifyResult",
    "RouteResult",
    "ModelNexusAdapter",
    "ModelNexusFallbackAdapter",
    "has_modelnexus",
]

def has_modelnexus() -> bool:
    """检查 ModelNexus 是否可用"""
    return _HAS_MODELNEXUS
