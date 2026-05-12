"""
审计日志 (Audit Logger)

记录系统操作和事件:
- 操作审计
- 安全事件
- 合规报告
- 日志查询与分析
"""

import time
import json
import hashlib
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import logging
import threading

logger = logging.getLogger(__name__)


class AuditLevel(Enum):
    """审计级别"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class AuditEventType(Enum):
    """审计事件类型"""
    # 用户/智能体事件
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_CREATE = "user.create"
    USER_DELETE = "user.delete"
    USER_UPDATE = "user.update"
    
    # 权限事件
    PERMISSION_CHECK = "permission.check"
    PERMISSION_GRANT = "permission.grant"
    PERMISSION_DENY = "permission.deny"
    ROLE_ASSIGN = "role.assign"
    ROLE_REVOKE = "role.revoke"
    
    # 资源事件
    RESOURCE_ALLOCATE = "resource.allocate"
    RESOURCE_RELEASE = "resource.release"
    RESOURCE_ACCESS = "resource.access"
    RESOURCE_DELETE = "resource.delete"
    
    # 规则事件
    RULE_CREATE = "rule.create"
    RULE_UPDATE = "rule.update"
    RULE_DELETE = "rule.delete"
    RULE_EXECUTE = "rule.execute"
    RULE_CONFLICT = "rule.conflict"
    
    # 安全事件
    SECURITY_ALERT = "security.alert"
    AUTH_FAILURE = "auth.failure"
    INTRUSION_DETECTED = "intrusion.detected"
    
    # 系统事件
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    SYSTEM_ERROR = "system.error"
    CONFIG_CHANGE = "config.change"


@dataclass
class AuditEvent:
    """审计事件"""
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    user_id: Optional[str]
    agent_id: Optional[str]
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    result: str = "success"  # success, failure, partial
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    level: AuditLevel = AuditLevel.INFO
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None  # 用于关联相关事件
    duration_ms: Optional[float] = None  # 操作耗时
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['level'] = self.level.name
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def get_checksum(self) -> str:
        """计算校验和"""
        content = json.dumps({
            'event_type': self.event_type.value,
            'user_id': self.user_id,
            'action': self.action,
            'timestamp': self.timestamp.isoformat()
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


class AuditLogger:
    """
    审计日志管理器
    
    功能和特性:
    - 结构化审计事件记录
    - 多级别日志
    - 日志持久化接口
    - 查询和分析功能
    - 合规报告生成
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 事件存储
        self.events: List[AuditEvent] = []
        self.events_lock = threading.RLock()
        
        # 内存存储限制
        self.max_events_in_memory = self.config.get('max_events', 100000)
        
        # 事件索引
        self.event_index: Dict[str, List[int]] = defaultdict(list)  # type -> indices
        self.user_index: Dict[str, List[int]] = defaultdict(list)  # user_id -> indices
        self.resource_index: Dict[str, List[int]] = defaultdict(list)  # resource -> indices
        
        # 日志持久化回调
        self.persistence_handlers: List[Callable[[AuditEvent], None]] = []
        
        # 告警回调
        self.alert_handlers: List[Callable[[AuditEvent], None]] = []
        
        # 过滤规则
        self.filters: List[Callable[[AuditEvent], bool]] = []
        
        # 配置
        self.min_level = AuditLevel[self.config.get('min_level', 'INFO')]
        self.retention_days = self.config.get('retention_days', 90)
        
        # 统计
        self.stats = {
            'total_events': 0,
            'events_by_type': defaultdict(int),
            'events_by_level': defaultdict(int),
            'failed_events': 0,
            'alert_triggered': 0
        }
    
    def log(
        self,
        event_type: AuditEventType,
        action: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        result: str = "success",
        details: Optional[Dict[str, Any]] = None,
        level: AuditLevel = AuditLevel.INFO,
        **kwargs
    ) -> AuditEvent:
        """
        记录审计事件
        
        Args:
            event_type: 事件类型
            action: 操作描述
            user_id: 用户ID
            agent_id: 智能体ID
            resource_type: 资源类型
            resource_id: 资源ID
            result: 操作结果
            details: 详细信息
            level: 审计级别
            
        Returns:
            AuditEvent: 创建的事件
        """
        # 检查过滤规则
        details = details or {}
        
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=event_type,
            timestamp=datetime.now(),
            user_id=user_id,
            agent_id=agent_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            details=details,
            level=level,
            **kwargs
        )
        
        # 检查级别
        if event.level.value < self.min_level.value:
            return event
        
        # 检查过滤器
        for f in self.filters:
            if not f(event):
                return event
        
        # 存储事件
        with self.events_lock:
            index = len(self.events)
            self.events.append(event)
            
            # 更新索引
            self.event_index[event_type.value].append(index)
            if user_id:
                self.user_index[user_id].append(index)
            if resource_id:
                self.resource_index[resource_id].append(index)
            
            # 清理过期事件
            self._cleanup_old_events()
        
        # 更新统计
        self._update_stats(event)
        
        # 持久化
        for handler in self.persistence_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Persistence handler error: {e}")
        
        # 告警检查
        if self._should_alert(event):
            for handler in self.alert_handlers:
                try:
                    handler(event)
                    self.stats['alert_triggered'] += 1
                except Exception as e:
                    logger.error(f"Alert handler error: {e}")
        
        return event
    
    def _generate_event_id(self) -> str:
        """生成事件ID"""
        content = f"{time.time()}:{len(self.events)}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _cleanup_old_events(self):
        """清理过期事件"""
        if len(self.events) > self.max_events_in_memory:
            # 保留最近的50%
            keep_count = self.max_events_in_memory // 2
            removed = self.events[:len(self.events) - keep_count]
            self.events = self.events[-keep_count:]
            
            # 重建索引(简化处理)
            self._rebuild_index()
            
            logger.info(f"Cleaned up {len(removed)} old audit events")
    
    def _rebuild_index(self):
        """重建索引"""
        self.event_index.clear()
        self.user_index.clear()
        self.resource_index.clear()
        
        for idx, event in enumerate(self.events):
            self.event_index[event.event_type.value].append(idx)
            if event.user_id:
                self.user_index[event.user_id].append(idx)
            if event.resource_id:
                self.resource_index[event.resource_id].append(idx)
    
    def _update_stats(self, event: AuditEvent):
        """更新统计"""
        self.stats['total_events'] += 1
        self.stats['events_by_type'][event.event_type.value] += 1
        self.stats['events_by_level'][event.level.name] += 1
        
        if event.result == 'failure':
            self.stats['failed_events'] += 1
    
    def _should_alert(self, event: AuditEvent) -> bool:
        """判断是否需要告警"""
        # 严重级别事件
        if event.level in (AuditLevel.ERROR, AuditLevel.CRITICAL):
            return True
        
        # 安全相关事件
        if event.event_type in (
            AuditEventType.AUTH_FAILURE,
            AuditEventType.INTRUSION_DETECTED,
            AuditEventType.SECURITY_ALERT
        ):
            return True
        
        # 失败事件过多
        if self.stats['failed_events'] > 100:
            return True
        
        return False
    
    # ==================== 查询方法 ====================
    
    def query(
        self,
        event_types: Optional[List[AuditEventType]] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        level: Optional[AuditLevel] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        result: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditEvent]:
        """查询审计事件"""
        results = []
        
        # 确定搜索范围
        if user_id:
            indices = self.user_index.get(user_id, [])
        elif resource_id:
            indices = self.resource_index.get(resource_id, [])
        elif event_types:
            indices = []
            for et in event_types:
                indices.extend(self.event_index.get(et.value, []))
        else:
            indices = list(range(len(self.events)))
        
        # 过滤
        for idx in indices:
            if idx >= len(self.events):
                continue
            
            event = self.events[idx]
            
            # 类型过滤
            if event_types and event.event_type not in event_types:
                continue
            
            # 级别过滤
            if level and event.level.value < level.value:
                continue
            
            # 时间过滤
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            
            # 结果过滤
            if result and event.result != result:
                continue
            
            results.append(event)
        
        # 排序(时间倒序)
        results.sort(key=lambda e: e.timestamp, reverse=True)
        
        # 分页
        return results[offset:offset + limit]
    
    def get_user_activity(
        self,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[AuditEvent]:
        """获取用户活动记录"""
        return self.query(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time
        )
    
    def get_resource_history(
        self,
        resource_id: str,
        limit: int = 100
    ) -> List[AuditEvent]:
        """获取资源操作历史"""
        return self.query(resource_id=resource_id, limit=limit)
    
    def get_failed_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """获取失败事件"""
        return self.query(
            result='failure',
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
    
    def get_security_events(
        self,
        limit: int = 100
    ) -> List[AuditEvent]:
        """获取安全相关事件"""
        security_types = [
            AuditEventType.AUTH_FAILURE,
            AuditEventType.INTRUSION_DETECTED,
            AuditEventType.SECURITY_ALERT,
            AuditEventType.PERMISSION_DENY
        ]
        return self.query(event_types=security_types, limit=limit)
    
    # ==================== 统计分析 ====================
    
    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取统计信息"""
        events = self.query(
            start_time=start_time,
            end_time=end_time,
            limit=1000000
        )
        
        return {
            'total_events': len(events),
            'failed_events': sum(1 for e in events if e.result == 'failure'),
            'by_type': {
                et.value: sum(1 for e in events if e.event_type == et)
                for et in AuditEventType
            },
            'by_level': {
                level.name: sum(1 for e in events if e.level == level)
                for level in AuditLevel
            },
            'unique_users': len(set(e.user_id for e in events if e.user_id)),
            'unique_agents': len(set(e.agent_id for e in events if e.agent_id)),
            'time_range': {
                'earliest': min(e.timestamp for e in events).isoformat() if events else None,
                'latest': max(e.timestamp for e in events).isoformat() if events else None
            }
        }
    
    def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """生成合规报告"""
        events = self.query(
            start_time=start_date,
            end_time=end_date,
            limit=1000000
        )
        
        # 访问控制审计
        permission_events = [e for e in events if e.event_type in (
            AuditEventType.PERMISSION_CHECK,
            AuditEventType.PERMISSION_GRANT,
            AuditEventType.PERMISSION_DENY
        )]
        
        # 敏感操作审计
        sensitive_operations = [e for e in events if e.resource_type in ('user', 'permission', 'config')]
        
        # 失败操作审计
        failed_operations = [e for e in events if e.result == 'failure']
        
        return {
            'report_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'summary': {
                'total_events': len(events),
                'permission_checks': len(permission_events),
                'sensitive_operations': len(sensitive_operations),
                'failed_operations': len(failed_operations)
            },
            'access_control': {
                'granted': sum(1 for e in permission_events if e.event_type == AuditEventType.PERMISSION_GRANT),
                'denied': sum(1 for e in permission_events if e.event_type == AuditEventType.PERMISSION_DENY)
            },
            'top_users_by_activity': self._get_top_users(events, 10),
            'failed_operations_by_type': self._aggregate_by_type(failed_operations),
            'generated_at': datetime.now().isoformat()
        }
    
    def _get_top_users(self, events: List[AuditEvent], n: int) -> List[Dict[str, Any]]:
        """获取最活跃用户"""
        user_counts = defaultdict(int)
        for e in events:
            if e.user_id:
                user_counts[e.user_id] += 1
        
        return [
            {'user_id': uid, 'count': count}
            for uid, count in sorted(user_counts.items(), key=lambda x: -x[1])[:n]
        ]
    
    def _aggregate_by_type(self, events: List[AuditEvent]) -> Dict[str, int]:
        """按类型聚合"""
        result = defaultdict(int)
        for e in events:
            result[e.event_type.value] += 1
        return dict(result)
    
    # ==================== 工具方法 ====================
    
    def add_filter(self, filter_func: Callable[[AuditEvent], bool]):
        """添加过滤器"""
        self.filters.append(filter_func)
    
    def add_persistence_handler(self, handler: Callable[[AuditEvent], None]):
        """添加持久化处理器"""
        self.persistence_handlers.append(handler)
    
    def add_alert_handler(self, handler: Callable[[AuditEvent], None]):
        """添加告警处理器"""
        self.alert_handlers.append(handler)
    
    def clear_old_events(self, before_date: datetime) -> int:
        """清理指定日期之前的日志"""
        with self.events_lock:
            original_count = len(self.events)
            self.events = [
                e for e in self.events
                if e.timestamp >= before_date
            ]
            
            removed = original_count - len(self.events)
            if removed > 0:
                self._rebuild_index()
            
            return removed
    
    def export_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        format: str = 'json'
    ) -> str:
        """导出事件"""
        events = self.query(
            start_time=start_time,
            end_time=end_time,
            limit=1000000
        )
        
        if format == 'json':
            return json.dumps([e.to_dict() for e in events], indent=2)
        elif format == 'csv':
            # 简化的CSV导出
            lines = ['event_id,event_type,timestamp,user_id,action,result']
            for e in events:
                lines.append(
                    f"{e.event_id},{e.event_type.value},{e.timestamp.isoformat()},"
                    f"{e.user_id or ''},{e.action},{e.result}"
                )
            return '\n'.join(lines)
        
        return json.dumps([e.to_dict() for e in events])
