"""
ModelNexusCore 集中化配置 — 所有 LLM 配置的唯一数据源

设计原则:
  - Provider 元数据: providers.yaml 定义（base_url, model, key 映射）
  - API Key: SecureKeyManager 统一管理（Vault → AWS → EnvVar 降级）
  - 不在任何其他地方直接读取 os.environ（除 SecureKeyManager 的 fallback）
"""

import os
import re
import logging
from functools import lru_cache
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

import yaml

logger = logging.getLogger(__name__)


# ============================================================
# Provider Entry
# ============================================================

@dataclass
class ProviderEntry:
    """单个 Provider 的完整配置"""
    name: str
    provider_type: str = "openai_compatible"  # openai_compatible | modelnexus | mock
    secure_key_name: Optional[str] = None      # SecureKeyManager key name
    base_url: Optional[str] = None
    default_model: str = "gpt-3.5-turbo"
    enabled: bool = True
    max_retries: int = 3
    timeout: int = 60
    cost_per_1k_input_tokens: float = 0.0015
    cost_per_1k_output_tokens: float = 0.002

    @property
    def api_key(self) -> str:
        """同步获取 API Key（通过 SecureKeyManager 的 env fallback）"""
        if not self.secure_key_name:
            return ""
        return _get_api_key_sync(self.secure_key_name)


# ============================================================
# Config
# ============================================================

@dataclass
class CoreConfigData:
    """从 providers.yaml 加载的原始配置"""
    providers: Dict[str, ProviderEntry] = field(default_factory=dict)
    detection_priority: list = field(default_factory=list)
    token_aliases: Dict[str, dict] = field(default_factory=dict)


def _load_yaml_config() -> CoreConfigData:
    """加载 providers.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), "providers.yaml")
    try:
        with open(config_path, "r") as f:
            raw = yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Failed to load providers.yaml: {e}, using defaults")
        raw = {}

    data = CoreConfigData()

    # 解析 providers
    providers_raw = raw.get("providers", {})
    for name, cfg in providers_raw.items():
        if not isinstance(cfg, dict):
            continue
        data.providers[name] = ProviderEntry(
            name=name,
            provider_type=cfg.get("provider_type", "openai_compatible"),
            secure_key_name=cfg.get("secure_key_name"),
            base_url=cfg.get("base_url"),
            default_model=cfg.get("default_model", "gpt-3.5-turbo"),
            enabled=cfg.get("enabled", True),
            max_retries=cfg.get("max_retries", 3),
            timeout=cfg.get("timeout", 60),
            cost_per_1k_input_tokens=cfg.get("cost_per_1k_input_tokens", 0.0015),
            cost_per_1k_output_tokens=cfg.get("cost_per_1k_output_tokens", 0.002),
        )

    data.detection_priority = raw.get("detection_priority", [])
    data.token_aliases = raw.get("token_aliases", {})

    # 部署特定 base_url 覆盖（非机密配置，仅 base URL）
    _apply_deployment_overrides(data)

    return data


def _apply_deployment_overrides(data: CoreConfigData):
    """应用部署特定的非机密覆盖（base_url 等）

    这些是基础设施配置（端点 URL），不是密钥。
    仅在 providers.yaml 未指定 base_url 时使用。
    """
    # MIMO: 优先 MIMO_BASE_URL_OPENAI，其次 MIMO_BASE_URL
    if "mimo" in data.providers:
        mimo = data.providers["mimo"]
        if not mimo.base_url:
            mimo.base_url = os.getenv("MIMO_BASE_URL_OPENAI") or os.getenv("MIMO_BASE_URL")
    # MIMO alias base_url
    if "mimo" in data.token_aliases:
        alias = data.token_aliases["mimo"]
        if not alias.get("base_url"):
            url = os.getenv("MIMO_BASE_URL_OPENAI") or os.getenv("MIMO_BASE_URL")
            if url:
                alias["base_url"] = url


# ============================================================
# API Key 获取（通过 SecureKeyManager）
# ============================================================

def _get_api_key_sync(key_name: str) -> str:
    """
    同步获取 API Key

    降级链: secret_keys.yaml (FileKeyProvider) → 环境变量 (最终降级)
    """
    try:
        from packages.modelnexus.security.secure_key_manager import (
            SecureKeyManager, KeyProvider
        )
        mgr = SecureKeyManager.get_instance()

        # 1. 尝试 FileKeyProvider (STATIC) — 开发环境主力
        static_provider = mgr._providers.get(KeyProvider.STATIC)
        if static_provider and hasattr(static_provider, '_keys'):
            if key_name in static_provider._keys:
                return static_provider._keys[key_name]

        # 2. 降级到环境变量
        key_config = mgr._key_configs.get(key_name)
        if key_config and key_config.env_var:
            return os.getenv(key_config.env_var, "")
    except Exception as e:
        pass
    return ""


async def get_api_key(key_name: str) -> Optional[str]:
    """异步获取 API Key（通过 SecureKeyManager，支持 Vault）"""
    try:
        from packages.modelnexus.security.secure_key_manager import SecureKeyManager
        mgr = SecureKeyManager.get_instance()
        return await mgr.get_key(key_name)
    except Exception as e:
        logger.debug(f"SecureKeyManager async key fetch failed for {key_name}: {e}")
        return None


# ============================================================
# 核心 API
# ============================================================

@lru_cache(maxsize=1)
def get_core_config() -> CoreConfigData:
    """获取全局配置单例"""
    return _load_yaml_config()


def reload_config():
    """重新加载配置（清除缓存）"""
    get_core_config.cache_clear()


def detect_available_provider(override_provider: str = None) -> str:
    """
    检测当前可用的 Provider（同步，不写 os.environ）

    优先级:
      1. override_provider 参数（CLI --provider）
      2. providers.yaml detection_priority 顺序
      3. 每个 provider 检查其 secure_key_name 是否有可用的 API Key
      4. 如果都没 key，回退到 mock
    """
    if override_provider:
        cfg = get_core_config()
        if override_provider in cfg.providers:
            return override_provider

    cfg = get_core_config()

    for provider_name in cfg.detection_priority:
        if provider_name == "mock":
            continue  # mock 是最后回退
        entry = cfg.providers.get(provider_name)
        if not entry or not entry.enabled:
            continue

        # 检查 token aliases: 某些 provider 的 key 实际映射到另一个 provider
        # 例如 deepseek → openai
        alias = cfg.token_aliases.get(provider_name, {})
        target_provider = alias.get("target_provider", provider_name)

        # 尝试获取 API Key
        if entry.secure_key_name:
            key = entry.api_key  # 同步获取（env fallback）
            if key:
                return target_provider

        # 对于 token aliases，也检查目标 provider 的 key
        if target_provider != provider_name:
            target_entry = cfg.providers.get(target_provider)
            if target_entry and target_entry.secure_key_name:
                target_key = target_entry.api_key
                if target_key:
                    return target_provider

    # 检查 modelnexus
    mnx_entry = cfg.providers.get("modelnexus")
    if mnx_entry and mnx_entry.enabled:
        return "modelnexus"

    return "mock"


def detect_model(provider: str, override_model: str = None) -> str:
    """
    检测当前可用的模型（同步）

    优先级:
      1. override_model 参数（CLI --model）
      2. ZENA_MODEL env var（CLI --model 设置的覆盖）
      3. providers.yaml 中该 provider 的 default_model
    """
    if override_model:
        return _clean_model_name(override_model)

    # CLI --model 覆盖（通过 ZENA_MODEL env var 传递）
    cli_model = os.getenv("ZENA_MODEL")
    if cli_model:
        return _clean_model_name(cli_model)

    # 从 providers.yaml 获取 default_model
    cfg = get_core_config()
    entry = cfg.providers.get(provider)
    if not entry:
        return "gpt-3.5-turbo"

    # 如果 provider 的 key 来自 token alias（如 openai 的 key 来自 deepseek），
    # 则使用 alias 源 provider 的 model（因为实际调用的是 alias 源的端点）
    if entry.secure_key_name:
        own_key = entry.api_key
        if not own_key:
            # Key 来自 alias，找到是哪个 alias
            for alias_name, alias_cfg in cfg.token_aliases.items():
                if alias_cfg.get("target_provider") == provider:
                    alias_entry = cfg.providers.get(alias_name)
                    if alias_entry and alias_entry.secure_key_name and alias_entry.api_key:
                        return alias_entry.default_model

    return entry.default_model


def _clean_model_name(model: str) -> str:
    """清理模型名: 去掉 [1m] 等 reasoning 标记"""
    return re.sub(r'\[\d+m\]', '', model).strip()


def get_provider_entry(provider: str) -> Optional[ProviderEntry]:
    """获取指定 Provider 的完整配置"""
    cfg = get_core_config()
    return cfg.providers.get(provider)


def resolve_provider_key(provider: str) -> str:
    """
    获取 Provider 的 API Key，考虑 token aliases

    例如: openai 自身没有 key，但 deepseek→openai alias 有 key，
    则返回 deepseek 的 key。
    """
    cfg = get_core_config()
    entry = cfg.providers.get(provider)
    if not entry:
        return ""

    # 1. 先检查自己的 key
    if entry.secure_key_name:
        key = entry.api_key
        if key:
            return key

    # 2. 检查所有指向此 provider 的 token aliases
    for alias_name, alias_cfg in cfg.token_aliases.items():
        if alias_cfg.get("target_provider") == provider:
            alias_entry = cfg.providers.get(alias_name)
            if alias_entry and alias_entry.secure_key_name:
                key = alias_entry.api_key
                if key:
                    return key

    return ""


def resolve_provider_model(provider: str) -> str:
    """获取 Provider 的实际模型名，考虑 token aliases

    如果 provider 的 key 来自 alias（如 openai 的 key 来自 deepseek），
    则使用 alias 源 provider 的 default_model。
    """
    cfg = get_core_config()
    entry = cfg.providers.get(provider)
    if not entry:
        return "gpt-3.5-turbo"

    # 如果 provider 自身有 key，用自己的 model
    if entry.secure_key_name:
        own_key = entry.api_key
        if own_key:
            return entry.default_model

    # Key 来自 alias，用 alias 源的 model
    for alias_name, alias_cfg in cfg.token_aliases.items():
        if alias_cfg.get("target_provider") == provider:
            alias_entry = cfg.providers.get(alias_name)
            if alias_entry and alias_entry.secure_key_name and alias_entry.api_key:
                return alias_entry.default_model

    return entry.default_model


def get_provider_base_url(provider: str) -> Optional[str]:
    """获取 Provider 的 base_url，考虑 token aliases

    如果 provider 的 key 来自 alias（如 openai 的 key 来自 deepseek），
    则优先使用 alias 指定的 base_url。
    """
    cfg = get_core_config()
    entry = cfg.providers.get(provider)
    if not entry:
        return None

    # 1. 检查自己的 key 是否存在，如果存在则用自己的 base_url
    own_key = entry.api_key if entry.secure_key_name else ""
    if own_key and entry.base_url:
        return entry.base_url

    # 2. 检查 token aliases: 如果 key 来自 alias，用 alias 的 base_url
    for alias_name, alias_cfg in cfg.token_aliases.items():
        if alias_cfg.get("target_provider") == provider:
            alias_entry = cfg.providers.get(alias_name)
            if alias_entry and alias_entry.secure_key_name and alias_entry.api_key:
                # Key 来自此 alias，优先用 alias 指定的 base_url
                alias_base = alias_cfg.get("base_url")
                if alias_base:
                    return alias_base
                if alias_entry.base_url:
                    return alias_entry.base_url

    # 3. 自己的 base_url 作为 fallback
    if entry.base_url:
        return entry.base_url

    # 4. 再次检查 aliases（即使没有 active key）
    for alias_name, alias_cfg in cfg.token_aliases.items():
        if alias_cfg.get("target_provider") == provider:
            alias_base = alias_cfg.get("base_url")
            if alias_base:
                return alias_base
            alias_entry = cfg.providers.get(alias_name)
            if alias_entry and alias_entry.base_url:
                return alias_entry.base_url

    return entry.base_url


# ============================================================
# 向后兼容: 转为旧 Settings dataclass
# ============================================================

def to_legacy_settings(provider_override: str = None):
    """
    将集中化配置转为旧的 Settings dataclass（向后兼容）

    所有 Settings() 调用方通过此函数获取配置，无需修改。
    """
    from packages.LLMInfra.config import (
        Settings, ProviderConfig, CacheConfig, RateLimitConfig,
        TokenBudgetConfig, ResponseConfig
    )

    cfg = get_core_config()
    provider = provider_override or detect_available_provider()

    settings = Settings(default_provider=provider)

    # 从 providers.yaml 填充所有 provider 配置
    for name, entry in cfg.providers.items():
        if not entry.enabled:
            continue
        key = resolve_provider_key(name) or entry.api_key
        if key or name in ("mock", "modelnexus"):
            base_url = get_provider_base_url(name) or entry.base_url
            model = resolve_provider_model(name)
            settings.providers[name] = ProviderConfig(
                api_key=key,
                base_url=base_url,
                default_model=model,
                max_retries=entry.max_retries,
                timeout=entry.timeout,
                cost_per_1k_input_tokens=entry.cost_per_1k_input_tokens,
                cost_per_1k_output_tokens=entry.cost_per_1k_output_tokens,
            )

    return settings
