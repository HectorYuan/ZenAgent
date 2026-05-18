"""
Provider 工厂类
"""

from typing import Dict, Type
import logging

from ..config import Settings
from .base import BaseProvider
from .openai_provider import OpenAIProvider
from .mock_provider import MockProvider
from .modelnexus_provider import ModelNexusProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Provider 工厂"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._providers: Dict[str, BaseProvider] = {}
        self._provider_classes: Dict[str, Type[BaseProvider]] = {
            "openai": OpenAIProvider,
            "anthropic": OpenAIProvider,  # 如果有兼容端点可以复用
            "qianwen": OpenAIProvider,
            "zhipu": OpenAIProvider,
            "ernie": OpenAIProvider,
            "mock": MockProvider,  # 用于测试的 Mock Provider
            "modelnexus": ModelNexusProvider,  # ModelNexus 网关
        }

    def register_provider(
        self,
        provider_name: str,
        provider_class: Type[BaseProvider]
    ):
        """
        注册新的 Provider 类

        Args:
            provider_name: 提供商名称
            provider_class: Provider 类
        """
        self._provider_classes[provider_name] = provider_class
        logger.info(f"Registered provider: {provider_name}")

    def get_provider(self, provider_name: str) -> BaseProvider:
        """
        获取 Provider 实例

        Args:
            provider_name: 提供商名称

        Returns:
            BaseProvider 实例
        """
        if provider_name in self._providers:
            return self._providers[provider_name]

        if provider_name not in self._provider_classes:
            raise ValueError(f"Provider '{provider_name}' not registered")

        if provider_name not in self.settings.providers:
            raise ValueError(f"Provider '{provider_name}' not configured")

        provider_class = self._provider_classes[provider_name]
        provider_instance = provider_class(provider_name, self.settings)
        self._providers[provider_name] = provider_instance

        logger.debug(f"Created provider instance: {provider_name}")
        return provider_instance

    def get_available_providers(self) -> list[str]:
        """
        获取所有可用的提供商名称

        Returns:
            提供商名称列表
        """
        return list(self._provider_classes.keys())

    def clear_cache(self):
        """清除缓存的实例"""
        self._providers.clear()
