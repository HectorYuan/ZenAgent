"""
内置钩子实现
提供常用的内置钩子：日志、监控、限流等
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import time
import asyncio

from .hook_manager import HookManager, HookPriority, HookEvent


@dataclass
class LoggingHook:
    """
    日志钩子
    
    记录所有生命周期事件的日志
    """
    logger_name: str = "ZenAgent"
    log_level: int = logging.INFO
    include_timestamp: bool = True
    include_source: bool = True
    
    def __post_init__(self):
        """初始化日志钩子"""
        self._logger = logging.getLogger(self.logger_name)
        self._logger.setLevel(self.log_level)
        
        # 注册到钩子管理器
        from .lifecycle import LifecycleEvent
        manager = HookManager()
        
        for event in LifecycleEvent:
            manager.register(
                event_name=event.value,
                handler=self._handle_log,
                name=f"logging_{event.value}",
                priority=HookPriority.LOWEST,  # 日志钩子最后执行
            )
    
    def _handle_log(self, event: HookEvent) -> None:
        """处理日志记录"""
        parts = []
        
        if self.include_timestamp:
            parts.append(f"[{event.timestamp.isoformat()}]")
        
        parts.append(f"[{event.event_name}]")
        
        if self.include_source and event.source:
            parts.append(f"[{event.source}]")
        
        if event.data:
            parts.append(str(event.data))
        
        message = " ".join(parts)
        
        # 根据事件类型选择日志级别
        if "error" in event.event_name.lower():
            self._logger.error(message)
        elif "warning" in event.event_name.lower():
            self._logger.warning(message)
        else:
            self._logger.info(message)


@dataclass
class MetricsHook:
    """
    指标钩子
    
    收集和统计 Agent 运行指标
    """
    _event_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _event_timestamps: Dict[str, List[datetime]] = field(
        default_factory=lambda: defaultdict(list)
    )
    _error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _start_time: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """初始化指标钩子"""
        from .lifecycle import LifecycleEvent
        manager = HookManager()
        
        for event in LifecycleEvent:
            manager.register(
                event_name=event.value,
                handler=self._handle_metrics,
                name=f"metrics_{event.value}",
            )
    
    def _handle_metrics(self, event: HookEvent) -> None:
        """处理指标收集"""
        # 计数
        self._event_counts[event.event_name] += 1
        
        # 时间戳
        self._event_timestamps[event.event_name].append(event.timestamp)
        
        # 错误计数
        if "error" in event.event_name.lower():
            error_type = event.data.get("error_type", "unknown")
            self._error_counts[error_type] += 1
    
    def get_counts(self) -> Dict[str, int]:
        """获取事件计数"""
        return dict(self._event_counts)
    
    def get_error_counts(self) -> Dict[str, int]:
        """获取错误计数"""
        return dict(self._error_counts)
    
    def get_event_rate(
        self,
        event_name: str,
        window_seconds: int = 60
    ) -> float:
        """
        获取事件速率（每秒事件数）
        
        Args:
            event_name: 事件名称
            window_seconds: 时间窗口（秒）
            
        Returns:
            float: 事件速率
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=window_seconds)
        
        timestamps = self._event_timestamps.get(event_name, [])
        recent_count = sum(1 for ts in timestamps if ts > cutoff)
        
        return recent_count / window_seconds if window_seconds > 0 else 0.0
    
    def get_uptime(self) -> float:
        """获取运行时间（秒）"""
        return (datetime.now() - self._start_time).total_seconds()
    
    def get_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        total_events = sum(self._event_counts.values())
        total_errors = sum(self._error_counts.values())
        
        return {
            "uptime_seconds": self.get_uptime(),
            "total_events": total_events,
            "total_errors": total_errors,
            "error_rate": total_errors / total_events if total_events > 0 else 0.0,
            "event_counts": self.get_counts(),
            "error_counts": self.get_error_counts(),
        }
    
    def reset(self) -> None:
        """重置所有指标"""
        self._event_counts.clear()
        self._event_timestamps.clear()
        self._error_counts.clear()
        self._start_time = datetime.now()


@dataclass
class RateLimitHook:
    """
    限流钩子
    
    控制事件触发的频率
    """
    max_events_per_window: int = 100
    window_seconds: int = 60
    
    _event_counts: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    _blocked_events: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """初始化限流钩子"""
        from .lifecycle import LifecycleEvent
        manager = HookManager()
        
        for event in LifecycleEvent:
            manager.register(
                event_name=event.value,
                handler=self._handle_rate_limit,
                name=f"rate_limit_{event.value}",
                priority=HookPriority.HIGHEST,  # 限流最先执行
            )
    
    def _handle_rate_limit(self, event: HookEvent) -> Optional[Dict[str, Any]]:
        """
        处理限流检查
        
        Returns:
            Optional[Dict[str, Any]]: 如果被限流返回阻止信息，否则返回 None
        """
        key = event.event_name
        now = time.time()
        
        if key not in self._event_counts:
            self._event_counts[key] = {
                "count": 0,
                "window_start": now,
            }
        
        window_info = self._event_counts[key]
        
        # 检查时间窗口
        if now - window_info["window_start"] >= self.window_seconds:
            # 重置窗口
            window_info["count"] = 0
            window_info["window_start"] = now
        
        # 增加计数
        window_info["count"] += 1
        
        # 检查是否超过限制
        if window_info["count"] > self.max_events_per_window:
            block_info = {
                "event": event.event_name,
                "timestamp": now,
                "reason": "rate_limit_exceeded",
                "current_count": window_info["count"],
                "limit": self.max_events_per_window,
            }
            self._blocked_events.append(block_info)
            return block_info
        
        return None
    
    def is_allowed(self, event_name: str) -> bool:
        """检查事件是否允许触发"""
        if event_name not in self._event_counts:
            return True
        
        info = self._event_counts[event_name]
        return info["count"] <= self.max_events_per_window
    
    def get_remaining(self, event_name: str) -> int:
        """获取剩余配额"""
        if event_name not in self._event_counts:
            return self.max_events_per_window
        
        info = self._event_counts[event_name]
        return max(0, self.max_events_per_window - info["count"])
    
    def get_blocked_events(self) -> List[Dict[str, Any]]:
        """获取被阻止的事件列表"""
        return list(self._blocked_events)
    
    def reset(self) -> None:
        """重置限流状态"""
        self._event_counts.clear()
        self._blocked_events.clear()


@dataclass
class MonitoringHook:
    """
    监控钩子
    
    监控系统健康状态和性能指标
    """
    _health_status: Dict[str, bool] = field(default_factory=dict)
    _performance_metrics: Dict[str, List[float]] = field(
        default_factory=lambda: defaultdict(list)
    )
    _alerts: List[Dict[str, Any]] = field(default_factory=list)
    
    # 健康检查阈值
    error_rate_threshold: float = 0.1  # 10%
    response_time_threshold: float = 5.0  # 5秒
    
    def __post_init__(self):
        """初始化监控钩子"""
        from .lifecycle import LifecycleEvent
        manager = HookManager()
        
        # 错误事件高优先级监控
        manager.register(
            event_name=LifecycleEvent.ON_ERROR.value,
            handler=self._handle_error,
            name="monitoring_error",
            priority=HookPriority.HIGH,
        )
        
        # 响应事件监控性能
        manager.register(
            event_name=LifecycleEvent.ON_RESPONSE.value,
            handler=self._handle_response,
            name="monitoring_response",
            priority=HookPriority.NORMAL,
        )
        
        # 定期健康检查
        manager.register(
            event_name="system.health_check",
            handler=self._handle_health_check,
            name="monitoring_health",
            priority=HookPriority.NORMAL,
        )
    
    def _handle_error(self, event: HookEvent) -> None:
        """处理错误监控"""
        error_type = event.data.get("error_type", "unknown")
        error_msg = event.data.get("error", "Unknown error")
        
        # 记录错误
        if error_type not in self._performance_metrics:
            self._performance_metrics[error_type] = []
        
        # 检查是否触发告警
        if self._should_alert(error_type):
            self._alerts.append({
                "timestamp": datetime.now().isoformat(),
                "level": "error",
                "message": f"Error rate threshold exceeded for {error_type}",
                "error": error_msg,
                "source": event.source,
            })
    
    def _handle_response(self, event: HookEvent) -> None:
        """处理响应监控"""
        response_time = event.data.get("response_time", 0)
        
        if response_time > 0:
            self._performance_metrics["response_time"].append(response_time)
            
            # 检查响应时间阈值
            if response_time > self.response_time_threshold:
                self._alerts.append({
                    "timestamp": datetime.now().isoformat(),
                    "level": "warning",
                    "message": f"Slow response detected: {response_time}s",
                    "source": event.source,
                })
    
    def _handle_health_check(self, event: HookEvent) -> Dict[str, Any]:
        """处理健康检查"""
        health = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "checks": {},
        }
        
        # 检查各项指标
        for check_name, status in self._health_status.items():
            health["checks"][check_name] = "ok" if status else "degraded"
            if not status:
                health["status"] = "degraded"
        
        return health
    
    def _should_alert(self, error_type: str) -> bool:
        """检查是否应该告警"""
        error_times = self._performance_metrics.get(error_type, [])
        
        if not error_times:
            return False
        
        # 简单检查：错误次数是否超过阈值
        return len(error_times) > 10
    
    def update_health_status(self, component: str, healthy: bool) -> None:
        """更新组件健康状态"""
        self._health_status[component] = healthy
    
    def record_response_time(self, response_time: float) -> None:
        """记录响应时间"""
        self._performance_metrics["response_time"].append(response_time)
    
    def get_average_response_time(self) -> float:
        """获取平均响应时间"""
        times = self._performance_metrics.get("response_time", [])
        return sum(times) / len(times) if times else 0.0
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        healthy_count = sum(1 for v in self._health_status.values() if v)
        total_count = len(self._health_status)
        
        return {
            "overall": "healthy" if healthy_count == total_count else "degraded",
            "components": self._health_status.copy(),
            "healthy_count": healthy_count,
            "total_count": total_count,
        }
    
    def get_alerts(self, level: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取告警列表"""
        if level:
            return [a for a in self._alerts if a.get("level") == level]
        return list(self._alerts)
    
    def clear_alerts(self) -> None:
        """清除告警"""
        self._alerts.clear()
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取监控指标"""
        return {
            "health_status": self.get_health_status(),
            "average_response_time": self.get_average_response_time(),
            "error_types": len(self._performance_metrics) - 1,  # 减去 response_time
            "pending_alerts": len(self._alerts),
        }


# 全局内置钩子实例
_logging_hook: Optional[LoggingHook] = None
_metrics_hook: Optional[MetricsHook] = None
_rate_limit_hook: Optional[RateLimitHook] = None
_monitoring_hook: Optional[MonitoringHook] = None


def get_logging_hook() -> LoggingHook:
    """获取日志钩子单例"""
    global _logging_hook
    if _logging_hook is None:
        _logging_hook = LoggingHook()
    return _logging_hook


def get_metrics_hook() -> MetricsHook:
    """获取指标钩子单例"""
    global _metrics_hook
    if _metrics_hook is None:
        _metrics_hook = MetricsHook()
    return _metrics_hook


def get_rate_limit_hook() -> RateLimitHook:
    """获取限流钩子单例"""
    global _rate_limit_hook
    if _rate_limit_hook is None:
        _rate_limit_hook = RateLimitHook()
    return _rate_limit_hook


def get_monitoring_hook() -> MonitoringHook:
    """获取监控钩子单例"""
    global _monitoring_hook
    if _monitoring_hook is None:
        _monitoring_hook = MonitoringHook()
    return _monitoring_hook
