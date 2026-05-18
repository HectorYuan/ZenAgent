"""
LLMInfra - L0 层：LLM 基础设施层

提供大模型网关、统一接口、成本控制等功能
支持本地 Provider 和 ModelNexus 网关两种模式
"""

__version__ = "1.1.0"

from .core import LLMClient, LLMResponse, Message, MessageRole
from .providers import ProviderFactory, BaseProvider, MockProvider
from .config import Settings, ProviderConfig, CacheConfig, RateLimitConfig
from .exceptions import LLMError, ProviderError, RateLimitError

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
    "LLMError",
    "ProviderError",
    "RateLimitError",
    "ModelNexusAdapter",
    "ModelNexusFallbackAdapter",
    "has_modelnexus",
]

def has_modelnexus() -> bool:
    """检查 ModelNexus 是否可用"""
    return _HAS_MODELNEXUS
