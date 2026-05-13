"""
审计日志记录器

提供操作审计、敏感操作标记、日志持久化等功能
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Any, Optional, Callable, Set
from collections import defaultdict
import json
import threading
import uuid


class AuditLevel(Enum):
    """审计日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    SENSITIVE = "SENSITIVE"  # 敏感操作专用级别


class SensitiveOperation(Enum):
    """敏感操作类型"""
    AUTHENTICATION = auto()      # 认证操作
    AUTHORIZATION = auto()       # 授权变更
    DATA_ACCESS = auto()          # 数据访问
    DATA_MODIFICATION = auto()   # 数据修改
    DATA_DELETION = auto()       # 数据删除
    SYSTEM_CONFIG = auto()       # 系统配置
    KEY_MANAGEMENT = auto()      # 密钥管理
    AGENT_CREATION = auto()      # Agent 创建
    AGENT_TERMINATION = auto()   # Agent 终止
    CROSS_AGENT_COMMUNICATION = auto()  # 跨 Agent 通信
    EXTERNAL_API_CALL = auto()   # 外部 API 调用


@dataclass
class AuditEvent:
    """审计事件"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    level: AuditLevel = AuditLevel.INFO
    operation: str = ""
    actor_id: str = ""           # 操作者 ID
    actor_type: str = "system"   # 操作者类型: user, agent, system
    resource_type: str = ""      # 资源类型
    resource_id: str = ""        # 资源 ID
    action: str = ""             # 具体动作
    status: str = "success"      # success, failure, partial
    details: Dict[str, Any] = field(default_factory=dict)
    sensitive_type: Optional[SensitiveOperation] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    correlation_id: Optional[str] = None  # 关联 ID，用于追踪操作链
    parent_event_id: Optional[str] = None  # 父事件 ID
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None   # 操作耗时(毫秒)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "operation": self.operation,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "status": self.status,
            "details": self.details,
            "sensitive_type": self.sensitive_type.name if self.sensitive_type else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "correlation_id": self.correlation_id,
            "parent_event_id": self.parent_event_id,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        """从字典创建"""
        data = data.copy()
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if "level" in data:
            data["level"] = AuditLevel(data["level"])
        if "sensitive_type" in data and data["sensitive_type"]:
            data["sensitive_type"] = SensitiveOperation[data["sensitive_type"]]
        return cls(**data)


class AuditLogger:
    """
    审计日志记录器
    
    提供线程安全的审计日志记录，支持敏感操作标记和多种输出格式
    """
    
    def __init__(
        self,
        name: str = "ZenAgent",
        output_handlers: Optional[List[Callable[[AuditEvent], None]]] = None,
        sensitive_operations: Optional[Set[SensitiveOperation]] = None,
        min_level: AuditLevel = AuditLevel.INFO,
        enable_correlation: bool = True,
    ):
        self.name = name
        self.output_handlers = output_handlers or []
        self.sensitive_operations = sensitive_operations or set()
        self.min_level = min_level
        self.enable_correlation = enable_correlation
        
        # 内存存储
        self._events: List[AuditEvent] = []
        self._max_memory_events = 10000
        self._lock = threading.RLock()
        
        # 统计信息
        self._stats = defaultdict(int)
        self._stats_lock = threading.Lock()
        
        # 默认处理器
        self._add_default_handlers()
    
    def _add_default_handlers(self) -> None:
        """添加默认处理器"""
        # 控制台输出处理器
        def console_handler(event: AuditEvent) -> None:
            prefix = "[SENSITIVE]" if event.sensitive_type else ""
            print(f"{prefix}{event.timestamp.isoformat()} [{event.level.value}] "
                  f"{event.actor_type}:{event.actor_id} - {event.operation} - {event.status}")
        
        self._output_handlers.append(console_handler)
    
    @property
    def _output_handlers(self) -> List[Callable[[AuditEvent], None]]:
        return self.output_handlers
    
    def log(
        self,
        operation: str,
        level: AuditLevel = AuditLevel.INFO,
        actor_id: str = "",
        actor_type: str = "system",
        resource_type: str = "",
        resource_id: str = "",
        action: str = "",
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
        sensitive_type: Optional[SensitiveOperation] = None,
        correlation_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditEvent:
        """
        记录审计事件
        
        Args:
            operation: 操作名称
            level: 日志级别
            actor_id: 操作者 ID
            actor_type: 操作者类型
            resource_type: 资源类型
            resource_id: 资源 ID
            action: 具体动作
            status: 操作状态
            details: 详细信息
            sensitive_type: 敏感操作类型
            correlation_id: 关联 ID
            parent_event_id: 父事件 ID
            error_message: 错误信息
            duration_ms: 操作耗时
            ip_address: IP 地址
            user_agent: 用户代理
            
        Returns:
            创建的审计事件
        """
        # 确定最终级别
        final_level = level
        if sensitive_type:
            final_level = AuditLevel.SENSITIVE
            if sensitive_type not in self.sensitive_operations:
                self.sensitive_operations.add(sensitive_type)
        
        # 检查最小级别
        level_values = {
            AuditLevel.DEBUG: 0,
            AuditLevel.INFO: 1,
            AuditLevel.WARNING: 2,
            AuditLevel.ERROR: 3,
            AuditLevel.CRITICAL: 4,
            AuditLevel.SENSITIVE: 5,
        }
        if level_values.get(final_level, 0) < level_values.get(self.min_level, 0):
            return None
        
        # 生成关联 ID
        if self.enable_correlation and not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        event = AuditEvent(
            level=final_level,
            operation=operation,
            actor_id=actor_id,
            actor_type=actor_type,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status=status,
            details=details or {},
            sensitive_type=sensitive_type,
            correlation_id=correlation_id,
            parent_event_id=parent_event_id,
            error_message=error_message,
            duration_ms=duration_ms,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        # 存储事件
        with self._lock:
            self._events.append(event)
            # 清理旧事件
            if len(self._events) > self._max_memory_events:
                self._events = self._events[-self._max_memory_events:]
        
        # 更新统计
        with self._stats_lock:
            self._stats[f"level_{event.level.value}"] += 1
            self._stats["total"] += 1
        
        # 输出到处理器
        for handler in self._output_handlers:
            try:
                handler(event)
            except Exception:
                pass
        
        return event
    
    def debug(self, **kwargs) -> Optional[AuditEvent]:
        """记录 DEBUG 级别事件"""
        return self.log(level=AuditLevel.DEBUG, **kwargs)
    
    def info(self, **kwargs) -> Optional[AuditEvent]:
        """记录 INFO 级别事件"""
        return self.log(level=AuditLevel.INFO, **kwargs)
    
    def warning(self, **kwargs) -> Optional[AuditEvent]:
        """记录 WARNING 级别事件"""
        return self.log(level=AuditLevel.WARNING, **kwargs)
    
    def error(self, **kwargs) -> Optional[AuditEvent]:
        """记录 ERROR 级别事件"""
        return self.log(level=AuditLevel.ERROR, **kwargs)
    
    def critical(self, **kwargs) -> Optional[AuditEvent]:
        """记录 CRITICAL 级别事件"""
        return self.log(level=AuditLevel.CRITICAL, **kwargs)
    
    def sensitive(
        self,
        sensitive_type: SensitiveOperation,
        **kwargs
    ) -> Optional[AuditEvent]:
        """记录敏感操作"""
        return self.log(
            level=AuditLevel.SENSITIVE,
            sensitive_type=sensitive_type,
            **kwargs
        )
    
    def log_authentication(
        self,
        actor_id: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[AuditEvent]:
        """记录认证操作"""
        return self.sensitive(
            sensitive_type=SensitiveOperation.AUTHENTICATION,
            operation="authentication",
            actor_id=actor_id,
            actor_type="user",
            status="success" if success else "failure",
            details=details,
            **kwargs
        )
    
    def log_authorization(
        self,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        granted: bool,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[AuditEvent]:
        """记录授权操作"""
        return self.sensitive(
            sensitive_type=SensitiveOperation.AUTHORIZATION,
            operation="authorization",
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status="success" if granted else "denied",
            details=details,
            **kwargs
        )
    
    def log_data_access(
        self,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        action: str = "read",
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[AuditEvent]:
        """记录数据访问"""
        return self.sensitive(
            sensitive_type=SensitiveOperation.DATA_ACCESS,
            operation="data_access",
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details,
            **kwargs
        )
    
    def log_agent_action(
        self,
        agent_id: str,
        action: str,
        target_id: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[AuditEvent]:
        """记录 Agent 操作"""
        return self.log(
            operation="agent_action",
            actor_id=agent_id,
            actor_type="agent",
            resource_type="agent",
            resource_id=target_id or agent_id,
            action=action,
            status="success" if success else "failure",
            details=details,
            **kwargs
        )
    
    def get_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        level: Optional[AuditLevel] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 1000,
    ) -> List[AuditEvent]:
        """查询审计事件"""
        with self._lock:
            events = list(self._events)
        
        # 时间过滤
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        # 级别过滤
        if level:
            events = [e for e in events if e.level == level]
        
        # 操作者过滤
        if actor_id:
            events = [e for e in events if e.actor_id == actor_id]
        
        # 关联 ID 过滤
        if correlation_id:
            events = [e for e in events if e.correlation_id == correlation_id]
        
        return events[-limit:]
    
    def get_sensitive_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        sensitive_type: Optional[SensitiveOperation] = None,
    ) -> List[AuditEvent]:
        """获取敏感事件"""
        events = self.get_events(start_time=start_time, end_time=end_time)
        events = [e for e in events if e.sensitive_type is not None]
        
        if sensitive_type:
            events = [e for e in events if e.sensitive_type == sensitive_type]
        
        return events
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        with self._stats_lock:
            return dict(self._stats)
    
    def export_json(self, filepath: str, **kwargs) -> None:
        """导出为 JSON 文件"""
        events = self.get_events(**kwargs)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in events], f, indent=2, ensure_ascii=False)
    
    def export_csv(self, filepath: str, **kwargs) -> None:
        """导出为 CSV 文件"""
        import csv
        
        events = self.get_events(**kwargs)
        if not events:
            return
        
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            fieldnames = list(events[0].to_dict().keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for event in events:
                writer.writerow(event.to_dict())


# 全局审计日志实例
_default_logger: Optional[AuditLogger] = None
_logger_lock = threading.Lock()


def get_default_logger() -> AuditLogger:
    """获取默认审计日志实例"""
    global _default_logger
    with _logger_lock:
        if _default_logger is None:
            _default_logger = AuditLogger()
        return _default_logger


def set_default_logger(logger: AuditLogger) -> None:
    """设置默认审计日志实例"""
    global _default_logger
    with _logger_lock:
        _default_logger = logger
