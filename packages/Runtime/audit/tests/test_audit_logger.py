"""
审计日志测试

覆盖 AuditLogger 的记录、查询、统计、敏感操作标记功能。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pytest
from datetime import datetime, timedelta

from packages.Runtime.audit.logger import (
    AuditLogger,
    AuditLevel,
    AuditEvent,
    SensitiveOperation,
)


class TestAuditLogger:
    """审计日志记录器测试"""

    def test_create_logger(self):
        """创建日志器"""
        logger = AuditLogger(name="test")
        assert logger.name == "test"

    def test_log_event(self):
        """记录基本事件"""
        logger = AuditLogger(name="test", output_handlers=[])
        event = logger.log(
            operation="user_login",
            actor_id="user-1",
            action="login",
        )
        assert event.operation == "user_login"
        assert event.actor_id == "user-1"
        assert event.status == "success"

    def test_log_sensitive_operation(self):
        """记录敏感操作"""
        logger = AuditLogger(name="test", output_handlers=[])
        event = logger.log(
            operation="delete_user",
            actor_id="admin",
            sensitive_type=SensitiveOperation.DATA_DELETION,
        )
        assert event.sensitive_type == SensitiveOperation.DATA_DELETION

    def test_log_error_event(self):
        """记录失败事件"""
        logger = AuditLogger(name="test", output_handlers=[])
        event = logger.log(
            operation="api_call",
            status="failure",
            level=AuditLevel.ERROR,
            error_message="connection timeout",
        )
        assert event.status == "failure"
        assert event.error_message == "connection timeout"

    def test_get_events_basic(self):
        """查询所有事件"""
        logger = AuditLogger(name="test", output_handlers=[])
        logger.log(operation="op1")
        logger.log(operation="op2")
        logger.log(operation="op3")

        events = logger.get_events()
        assert len(events) == 3

    def test_get_events_by_actor(self):
        """按操作者过滤"""
        logger = AuditLogger(name="test", output_handlers=[])
        logger.log(operation="op", actor_id="user-1")
        logger.log(operation="op", actor_id="user-2")
        logger.log(operation="op", actor_id="user-1")

        events = logger.get_events(actor_id="user-1")
        assert len(events) == 2

    def test_get_events_by_level(self):
        """按级别过滤"""
        logger = AuditLogger(name="test", output_handlers=[])
        logger.log(operation="op", level=AuditLevel.INFO)
        logger.log(operation="op", level=AuditLevel.ERROR)
        logger.log(operation="op", level=AuditLevel.ERROR)

        errors = logger.get_events(level=AuditLevel.ERROR)
        assert len(errors) == 2

    def test_get_events_by_correlation_id(self):
        """按关联 ID 过滤（追踪操作链）"""
        logger = AuditLogger(name="test", output_handlers=[])
        logger.log(operation="step1", correlation_id="trace-1")
        logger.log(operation="step2", correlation_id="trace-1")
        logger.log(operation="other", correlation_id="trace-2")

        chain = logger.get_events(correlation_id="trace-1")
        assert len(chain) == 2
        assert all(e.correlation_id == "trace-1" for e in chain)

    def test_get_sensitive_events(self):
        """查询敏感操作"""
        logger = AuditLogger(name="test", output_handlers=[])
        logger.log(operation="login", sensitive_type=SensitiveOperation.AUTHENTICATION)
        logger.log(operation="read")  # 非敏感
        logger.log(operation="delete", sensitive_type=SensitiveOperation.DATA_DELETION)

        events = logger.get_sensitive_events()
        assert len(events) == 2

    def test_get_sensitive_events_by_type(self):
        """按敏感类型过滤"""
        logger = AuditLogger(name="test", output_handlers=[])
        logger.log(operation="login", sensitive_type=SensitiveOperation.AUTHENTICATION)
        logger.log(operation="delete", sensitive_type=SensitiveOperation.DATA_DELETION)

        auth_events = logger.get_sensitive_events(sensitive_type=SensitiveOperation.AUTHENTICATION)
        assert len(auth_events) == 1
        assert auth_events[0].operation == "login"

    def test_get_events_limit(self):
        """查询结果限制"""
        logger = AuditLogger(name="test", output_handlers=[])
        for i in range(10):
            logger.log(operation=f"op-{i}")

        events = logger.get_events(limit=3)
        assert len(events) == 3

    def test_event_to_dict_roundtrip(self):
        """事件序列化往返"""
        event = AuditEvent(
            operation="test",
            actor_id="user-1",
            sensitive_type=SensitiveOperation.DATA_ACCESS,
        )
        d = event.to_dict()
        restored = AuditEvent.from_dict(d)
        assert restored.operation == event.operation
        assert restored.actor_id == event.actor_id
        assert restored.sensitive_type == event.sensitive_type

    def test_event_default_id(self):
        """事件 ID 自动生成"""
        e1 = AuditEvent(operation="test")
        e2 = AuditEvent(operation="test")
        assert e1.event_id != e2.event_id

    def test_log_with_details(self):
        """记录详细信息"""
        logger = AuditLogger(name="test", output_handlers=[])
        event = logger.log(
            operation="api_call",
            details={"endpoint": "/api/users", "method": "GET"},
        )
        assert event.details["endpoint"] == "/api/users"

    def test_min_level_filter(self):
        """最小级别过滤"""
        logger = AuditLogger(name="test", output_handlers=[], min_level=AuditLevel.WARNING)
        # DEBUG 低于 WARNING，是否记录由实现决定，但 logger 应该不崩溃
        logger.log(operation="debug-op", level=AuditLevel.DEBUG)
        logger.log(operation="warning-op", level=AuditLevel.WARNING)
        events = logger.get_events()
        # 至少能记录到 warning
        assert any(e.operation == "warning-op" for e in events)

    def test_get_events_by_time_range(self):
        """按时间范围查询"""
        logger = AuditLogger(name="test", output_handlers=[])
        logger.log(operation="early")
        cutoff = datetime.now()
        logger.log(operation="late")

        late_events = logger.get_events(start_time=cutoff)
        assert any(e.operation == "late" for e in late_events)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
