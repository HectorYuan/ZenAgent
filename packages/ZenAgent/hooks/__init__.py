"""
Hooks 钩子系统
提供 Agent 生命周期事件钩子和内置钩子实现
"""

from .hook_manager import HookManager, get_hook_manager, HookPriority, HookEvent
from .lifecycle import (
    LifecycleHook,
    LifecycleEvent,
    LifecycleManager,
    on_create,
    on_start,
    on_message,
    on_response,
    on_error,
    on_shutdown,
)
from .builtin_hooks import (
    LoggingHook,
    MetricsHook,
    RateLimitHook,
    MonitoringHook,
    get_logging_hook,
    get_metrics_hook,
    get_rate_limit_hook,
    get_monitoring_hook,
)

__all__ = [
    # Hook Manager
    "HookManager",
    "get_hook_manager",
    "HookPriority",
    "HookEvent",
    # Lifecycle
    "LifecycleHook",
    "LifecycleEvent",
    "LifecycleManager",
    "on_create",
    "on_start",
    "on_message",
    "on_response",
    "on_error",
    "on_shutdown",
    # Builtin Hooks
    "LoggingHook",
    "MetricsHook",
    "RateLimitHook",
    "MonitoringHook",
    "get_logging_hook",
    "get_metrics_hook",
    "get_rate_limit_hook",
    "get_monitoring_hook",
]
