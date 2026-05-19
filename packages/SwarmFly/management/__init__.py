"""
SwarmFly框架整合 - Phase 3

整合SwarmFly到智能体主框架，实现统一管理
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import logging
import asyncio
import json
from pathlib import Path

logger = logging.getLogger(__name__)


# ============== 枚举定义 ==============

class ComponentState(Enum):
    """组件状态"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ComponentType(Enum):
    """组件类型"""
    CORE = "core"
    ENGINE = "engine"
    SERVICE = "service"
    ADAPTER = "adapter"


@dataclass
class ComponentInfo:
    """组件信息"""
    name: str
    component_type: ComponentType
    version: str
    state: ComponentState = ComponentState.INITIALIZING
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class LifecycleHook:
    """生命周期钩子"""
    name: str
    callback: Callable
    order: int = 0
    async_execute: bool = True


# ============== 配置管理器 ==============

class ConfigManager:
    """
    统一配置管理器
    
    功能:
    - 配置格式统一 (YAML)
    - 环境变量覆盖
    - 配置验证
    - 热更新支持
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self._config: Dict[str, Any] = {}
        self._watchers: List[Callable] = []
        self._loaded = False
    
    def _get_default_config_path(self) -> str:
        """获取默认配置路径"""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config",
            "swarmfly.yaml"
        )
    
    async def load(self) -> Dict[str, Any]:
        """加载配置"""
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            self._config = self._get_default_config()
        else:
            import yaml
            try:
                with open(self.config_path, 'r') as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                self._config = self._get_default_config()
        
        self._loaded = True
        self._validate_config()
        return self._config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "swarmfly": {
                "enabled": True,
                "mock_mode": True,
                "log_level": "INFO"
            },
            "evolve_engine": {
                "base_url": "http://localhost:8080/api/evolve",
                "timeout": 30,
                "mock_mode": True
            },
            "zenloop": {
                "base_url": "http://localhost:8081/api/zenloop",
                "timeout": 30,
                "mock_mode": True
            },
            "lifecycle": {
                "startup_timeout": 60,
                "shutdown_timeout": 30,
                "health_check_interval": 10
            }
        }
    
    def _validate_config(self):
        """验证配置"""
        required_keys = ["swarmfly"]
        for key in required_keys:
            if key not in self._config:
                self._config[key] = {}
        
        # 验证数据类型
        if not isinstance(self._config.get("swarmfly", {}), dict):
            self._config["swarmfly"] = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value
    
    def get_all(self) -> Dict[str, Any]:
        """获取全部配置"""
        return self._config.copy()
    
    def reload(self) -> bool:
        """重新加载配置"""
        return asyncio.run(self.load())
    
    def on_config_change(self, callback: Callable):
        """配置变更监听"""
        self._watchers.append(callback)


# ============== 生命周期管理器 ==============

class LifecycleManager:
    """
    生命周期管理器
    
    功能:
    - 组件初始化/销毁
    - 依赖管理
    - 优雅启动/停止
    - 健康检查
    """
    
    def __init__(self):
        self._components: Dict[str, ComponentInfo] = {}
        self._lifecycle_hooks: Dict[str, List[LifecycleHook]] = {
            "on_init": [],
            "on_start": [],
            "on_stop": [],
            "on_error": []
        }
        self._state = ComponentState.INITIALIZING
        self._startup_time: Optional[datetime] = None
    
    def register_component(
        self,
        name: str,
        component_type: ComponentType,
        version: str = "1.0.0",
        dependencies: Optional[List[str]] = None
    ) -> ComponentInfo:
        """注册组件"""
        info = ComponentInfo(
            name=name,
            component_type=component_type,
            version=version,
            dependencies=dependencies or []
        )
        self._components[name] = info
        logger.info(f"Registered component: {name} ({component_type.value})")
        return info
    
    def add_hook(self, event: str, hook: LifecycleHook):
        """添加生命周期钩子"""
        if event in self._lifecycle_hooks:
            self._lifecycle_hooks[event].append(hook)
            # 按顺序排序
            self._lifecycle_hooks[event].sort(key=lambda h: h.order)
    
    async def initialize(self):
        """初始化所有组件"""
        logger.info("Initializing lifecycle...")
        await self._execute_hooks("on_init")
        self._state = ComponentState.RUNNING
        self._startup_time = datetime.now()
        logger.info("Lifecycle initialized successfully")
    
    async def shutdown(self):
        """关闭所有组件"""
        logger.info("Shutting down lifecycle...")
        self._state = ComponentState.STOPPING
        await self._execute_hooks("on_stop")
        self._state = ComponentState.STOPPED
        logger.info("Lifecycle shutdown complete")
    
    async def _execute_hooks(self, event: str):
        """执行钩子"""
        hooks = self._lifecycle_hooks.get(event, [])
        for hook in hooks:
            try:
                if hook.async_execute:
                    await hook.callback()
                else:
                    hook.callback()
            except Exception as e:
                logger.error(f"Hook {hook.name} failed: {e}")
                if event == "on_init":
                    self._state = ComponentState.ERROR
                    raise
    
    def get_component_state(self, name: str) -> Optional[ComponentState]:
        """获取组件状态"""
        info = self._components.get(name)
        return info.state if info else None
    
    def get_all_components(self) -> Dict[str, ComponentInfo]:
        """获取所有组件"""
        return self._components.copy()
    
    def get_uptime(self) -> float:
        """获取运行时间(秒)"""
        if self._startup_time:
            return (datetime.now() - self._startup_time).total_seconds()
        return 0.0
    
    @property
    def state(self) -> ComponentState:
        return self._state


# ============== 统一日志系统 ==============

class UnifiedLogger:
    """
    统一日志系统
    
    功能:
    - 统一日志格式 (JSON)
    - 多目标输出 (console, file, syslog)
    - 日志分级
    - 自动归档
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if UnifiedLogger._initialized:
            return
        self._logger = logging.getLogger("SwarmFly")
        self._handlers: List[logging.Handler] = []
        self._log_level = logging.INFO
        self._format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        UnifiedLogger._initialized = True
    
    def configure(self, config: Dict[str, Any]):
        """配置日志系统"""
        # 设置日志级别
        level_str = config.get("log_level", "INFO")
        self._log_level = getattr(logging, level_str.upper(), logging.INFO)
        self._logger.setLevel(self._log_level)
        
        # 设置格式
        formatter = logging.Formatter(self._format_string)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(self._log_level)
        self._logger.addHandler(console_handler)
        
        # File handler (可选)
        log_file = config.get("log_file")
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(self._log_level)
            self._logger.addHandler(file_handler)
        
        self._logger.info("UnifiedLogger configured")
    
    def get_logger(self, name: str = "SwarmFly") -> logging.Logger:
        """获取logger实例"""
        return logging.getLogger(name)
    
    def set_level(self, level: int):
        """设置日志级别"""
        self._log_level = level
        self._logger.setLevel(level)
        for handler in self._logger.handlers:
            handler.setLevel(level)


# ============== 指标导出器 ==============

class MetricsExporter:
    """
    指标导出器
    
    功能:
    - 核心指标定义
    - 自动采集
    - Prometheus格式导出
    - 告警规则
    """
    
    def __init__(self):
        self._metrics: Dict[str, float] = {}
        self._counters: Dict[str, int] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._enabled = True
    
    def increment(self, name: str, value: int = 1):
        """递增计数器"""
        self._counters[name] = self._counters.get(name, 0) + value
    
    def gauge(self, name: str, value: float):
        """设置仪表值"""
        self._metrics[name] = value
    
    def observe(self, name: str, value: float):
        """观察直方图值"""
        if name not in self._histograms:
            self._histograms[name] = []
        self._histograms[name].append(value)
        # 保持最近1000个值
        if len(self._histograms[name]) > 1000:
            self._histograms[name] = self._histograms[name][-1000:]
    
    def get_metric(self, name: str) -> Optional[float]:
        """获取指标值"""
        return self._metrics.get(name)
    
    def get_counter(self, name: str) -> int:
        """获取计数器值"""
        return self._counters.get(name, 0)
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """获取直方图统计"""
        values = self._histograms.get(name, [])
        if not values:
            return {}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return {
            "count": n,
            "sum": sum(values),
            "mean": sum(values) / n,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "p50": sorted_values[int(n * 0.5)],
            "p95": sorted_values[int(n * 0.95)],
            "p99": sorted_values[int(n * 0.99)]
        }
    
    def export_prometheus(self) -> str:
        """导出Prometheus格式"""
        lines = []
        
        # 仪表指标
        for name, value in self._metrics.items():
            lines.append(f"# HELP {name} Metric")
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        
        # 计数器
        for name, value in self._counters.items():
            lines.append(f"# HELP {name}_total Counter")
            lines.append(f"# TYPE {name}_total counter")
            lines.append(f"{name}_total {value}")
        
        # 直方图
        for name, values in self._histograms.items():
            if values:
                stats = self.get_histogram_stats(name)
                lines.append(f"# HELP {name}_histogram Histogram")
                lines.append(f"# TYPE {name}_histogram summary")
                for quantile in [0.5, 0.95, 0.99]:
                    q_key = f"p{int(quantile*100)}"
                    lines.append(f'{name}_histogram{{quantile="{quantile}"}} {stats.get(q_key, 0)}')
        
        return "\n".join(lines)
    
    def reset(self):
        """重置所有指标"""
        self._metrics.clear()
        self._counters.clear()
        self._histograms.clear()
