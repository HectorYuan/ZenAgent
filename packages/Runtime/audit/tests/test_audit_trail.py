"""
audit_trail 模块的单元测试

覆盖 AuditRecord、AuditQuery、AuditTrail 及全局实例管理
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from packages.Runtime.audit.audit_trail import (
    AuditRecord,
    AuditRecordType,
    AuditQuery,
    AuditTrail,
    RecordStatus,
    get_default_trail,
    set_default_trail,
)


class TestAuditRecord:
    """AuditRecord 数据类测试"""

    def setup_method(self):
        """每个测试前创建基础记录"""
        self.now = datetime.now()
        self.record = AuditRecord(
            record_id="test-record-001",
            record_type=AuditRecordType.EVENT,
            timestamp=self.now,
            actor_id="user-1",
            actor_type="human",
            session_id="session-abc",
            resource_type="file",
            resource_id="file-001",
            operation="read",
            action="download",
            status="success",
            details={"key": "value"},
            input_data={"query": "hello"},
            output_data={"result": "ok"},
            correlation_id="trace-001",
            parent_record_id=None,
            child_record_ids=["child-001"],
            status_flag=RecordStatus.ACTIVE,
            tags={"security", "read"},
            retention_days=365,
            checksum=None,
            source_ip="127.0.0.1",
            source_location="local",
        )

    def test_record_default_values(self):
        """验证 AuditRecord 默认值"""
        rec = AuditRecord()
        assert rec.record_type == AuditRecordType.EVENT
        assert rec.actor_type == "system"
        assert rec.session_id is None
        assert rec.status == "success"
        assert rec.details == {}
        assert rec.input_data is None
        assert rec.output_data is None
        assert rec.correlation_id is None
        assert rec.parent_record_id is None
        assert rec.child_record_ids == []
        assert rec.status_flag == RecordStatus.ACTIVE
        assert rec.tags == set()
        assert rec.retention_days == 365
        assert rec.checksum is None
        assert rec.source_ip is None
        assert rec.source_location is None

    def test_record_to_dict(self):
        """验证 to_dict 序列化输出正确"""
        d = self.record.to_dict()
        assert d["record_id"] == "test-record-001"
        assert d["record_type"] == "event"
        assert d["timestamp"] == self.now.isoformat()
        assert d["actor_id"] == "user-1"
        assert d["actor_type"] == "human"
        assert d["session_id"] == "session-abc"
        assert d["resource_type"] == "file"
        assert d["resource_id"] == "file-001"
        assert d["operation"] == "read"
        assert d["action"] == "download"
        assert d["status"] == "success"
        assert d["details"] == {"key": "value"}
        assert d["input_data"] == {"query": "hello"}
        assert d["output_data"] == {"result": "ok"}
        assert d["correlation_id"] == "trace-001"
        assert d["parent_record_id"] is None
        assert d["child_record_ids"] == ["child-001"]
        assert d["status_flag"] == "active"
        assert set(d["tags"]) == {"security", "read"}
        assert d["retention_days"] == 365
        assert d["source_ip"] == "127.0.0.1"
        assert d["source_location"] == "local"

    def test_record_from_dict(self):
        """验证 from_dict 反序列化还原对象"""
        d = self.record.to_dict()
        restored = AuditRecord.from_dict(d)
        assert restored.record_id == self.record.record_id
        assert restored.record_type == AuditRecordType.EVENT
        assert restored.timestamp == self.record.timestamp
        assert restored.actor_id == self.record.actor_id
        assert restored.session_id == self.record.session_id
        assert restored.resource_type == self.record.resource_type
        assert restored.operation == self.record.operation
        assert restored.status == self.record.status
        assert restored.details == self.record.details
        assert restored.input_data == self.record.input_data
        assert restored.output_data == self.record.output_data
        assert restored.correlation_id == self.record.correlation_id
        assert restored.child_record_ids == self.record.child_record_ids
        assert restored.status_flag == RecordStatus.ACTIVE
        assert restored.tags == self.record.tags
        assert restored.retention_days == self.record.retention_days
        assert restored.source_ip == self.record.source_ip
        assert restored.source_location == self.record.source_location

    def test_record_roundtrip(self):
        """验证 to_dict -> from_dict 往返一致"""
        d = self.record.to_dict()
        restored = AuditRecord.from_dict(d)
        d2 = restored.to_dict()
        assert d == d2

    def test_record_to_dict_tags_list(self):
        """验证 to_dict 将 tags set 转为 list"""
        d = self.record.to_dict()
        assert isinstance(d["tags"], list)
        assert sorted(d["tags"]) == ["read", "security"]

    def test_record_from_dict_tags_set(self):
        """验证 from_dict 将 tags list 转回 set"""
        d = self.record.to_dict()
        restored = AuditRecord.from_dict(d)
        assert isinstance(restored.tags, set)

    def test_record_is_expired_true(self):
        """验证过期记录返回 True"""
        old_record = AuditRecord(
            timestamp=datetime.now() - timedelta(days=400),
            retention_days=365,
        )
        assert old_record.is_expired() is True

    def test_record_is_expired_false(self):
        """验证未过期记录返回 False"""
        recent_record = AuditRecord(
            timestamp=datetime.now() - timedelta(days=1),
            retention_days=365,
        )
        assert recent_record.is_expired() is False

    def test_record_is_expired_boundary(self):
        """验证边界情况：刚过期"""
        with patch("packages.Runtime.audit.audit_trail.datetime") as mock_dt:
            fixed_now = datetime(2026, 6, 4, 12, 0, 0)
            mock_dt.now.return_value = fixed_now
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            rec = AuditRecord(
                timestamp=fixed_now - timedelta(days=366),
                retention_days=365,
            )
            assert rec.is_expired() is True

    def test_record_from_dict_minimal(self):
        """验证 from_dict 使用最少字段"""
        d = {
            "record_id": "min-001",
            "record_type": "session",
            "timestamp": datetime.now().isoformat(),
            "status_flag": "archived",
            "tags": ["tag1"],
        }
        rec = AuditRecord.from_dict(d)
        assert rec.record_id == "min-001"
        assert rec.record_type == AuditRecordType.SESSION
        assert rec.status_flag == RecordStatus.ARCHIVED
        assert rec.tags == {"tag1"}


class TestAuditQuery:
    """AuditQuery 查询条件测试"""

    def test_query_default_values(self):
        """验证 AuditQuery 默认值"""
        q = AuditQuery()
        assert q.start_time is None
        assert q.end_time is None
        assert q.actor_id is None
        assert q.actor_type is None
        assert q.session_id is None
        assert q.resource_type is None
        assert q.resource_id is None
        assert q.operation is None
        assert q.action is None
        assert q.status is None
        assert q.correlation_id is None
        assert q.record_id is None
        assert q.parent_record_id is None
        assert q.tags is None
        assert q.any_tags is False
        assert q.status_flags is None
        assert q.limit == 100
        assert q.offset == 0
        assert q.order_by == "timestamp"
        assert q.order_desc is True

    def test_query_custom_values(self):
        """验证 AuditQuery 自定义字段"""
        now = datetime.now()
        q = AuditQuery(
            start_time=now - timedelta(hours=1),
            end_time=now,
            actor_id="user-1",
            actor_type="human",
            session_id="sess-1",
            resource_type="file",
            resource_id="f-1",
            operation="read",
            action="download",
            status="success",
            correlation_id="trace-1",
            record_id="rec-1",
            parent_record_id="parent-1",
            tags={"tag1", "tag2"},
            any_tags=True,
            status_flags={RecordStatus.ACTIVE, RecordStatus.ARCHIVED},
            limit=50,
            offset=10,
            order_by="record_id",
            order_desc=False,
        )
        assert q.actor_id == "user-1"
        assert q.actor_type == "human"
        assert q.any_tags is True
        assert q.status_flags == {RecordStatus.ACTIVE, RecordStatus.ARCHIVED}
        assert q.limit == 50
        assert q.offset == 10
        assert q.order_by == "record_id"
        assert q.order_desc is False


class TestAuditTrailAdd:
    """AuditTrail 添加记录相关测试"""

    def setup_method(self):
        """每个测试前创建新的 trail 实例"""
        self.trail = AuditTrail()

    def test_add_record(self):
        """验证添加记录返回 record_id"""
        rec = AuditRecord(record_id="r-001", actor_id="user-1")
        rid = self.trail.add(rec)
        assert rid == "r-001"
        assert len(self.trail) == 1

    def test_add_duplicate_record(self):
        """验证重复添加同一记录不会增加数量"""
        rec = AuditRecord(record_id="r-001")
        self.trail.add(rec)
        self.trail.add(rec)
        assert len(self.trail) == 1

    def test_add_computes_checksum(self):
        """验证添加记录时自动计算 checksum"""
        rec = AuditRecord(record_id="r-001", checksum=None)
        self.trail.add(rec, compute_checksum=True)
        assert rec.checksum is not None
        assert len(rec.checksum) == 16

    def test_add_no_checksum_when_disabled(self):
        """验证关闭 checksum 计算时不自动填充"""
        rec = AuditRecord(record_id="r-001", checksum=None)
        self.trail.add(rec, compute_checksum=False)
        assert rec.checksum is None

    def test_add_no_overwrite_existing_checksum(self):
        """验证已有 checksum 不会被覆盖"""
        rec = AuditRecord(record_id="r-001", checksum="my-checksum")
        self.trail.add(rec, compute_checksum=True)
        assert rec.checksum == "my-checksum"

    def test_add_multiple_records(self):
        """验证连续添加多条记录"""
        for i in range(10):
            rec = AuditRecord(record_id=f"r-{i:03d}", actor_id=f"user-{i}")
            self.trail.add(rec)
        assert len(self.trail) == 10


class TestAuditTrailQuery:
    """AuditTrail 查询相关测试"""

    def setup_method(self):
        """每个测试前准备带有多条记录的 trail"""
        self.trail = AuditTrail()
        self.now = datetime.now()

        records = [
            AuditRecord(
                record_id="r-001",
                record_type=AuditRecordType.EVENT,
                timestamp=self.now - timedelta(hours=5),
                actor_id="user-alice",
                actor_type="human",
                session_id="session-1",
                resource_type="file",
                resource_id="file-a",
                operation="read",
                action="view",
                status="success",
                tags={"security", "read"},
                correlation_id="trace-1",
                status_flag=RecordStatus.ACTIVE,
            ),
            AuditRecord(
                record_id="r-002",
                record_type=AuditRecordType.TRANSACTION,
                timestamp=self.now - timedelta(hours=3),
                actor_id="user-bob",
                actor_type="human",
                session_id="session-1",
                resource_type="file",
                resource_id="file-b",
                operation="write",
                action="upload",
                status="failure",
                tags={"security", "write"},
                correlation_id="trace-1",
                status_flag=RecordStatus.ACTIVE,
            ),
            AuditRecord(
                record_id="r-003",
                record_type=AuditRecordType.EVENT,
                timestamp=self.now - timedelta(hours=1),
                actor_id="user-alice",
                actor_type="human",
                session_id="session-2",
                resource_type="db",
                resource_id="db-001",
                operation="read",
                action="query",
                status="success",
                tags={"database"},
                correlation_id="trace-2",
                status_flag=RecordStatus.ACTIVE,
            ),
            AuditRecord(
                record_id="r-004",
                record_type=AuditRecordType.SESSION,
                timestamp=self.now - timedelta(minutes=30),
                actor_id="system",
                actor_type="system",
                session_id="session-2",
                resource_type="db",
                resource_id="db-002",
                operation="delete",
                action="purge",
                status="failure",
                tags={"database", "danger"},
                correlation_id="trace-2",
                parent_record_id="r-003",
                status_flag=RecordStatus.ACTIVE,
            ),
        ]

        for rec in records:
            self.trail.add(rec)

    def test_query_by_actor_id(self):
        """验证按 actor_id 查询"""
        q = AuditQuery(actor_id="user-alice")
        results = self.trail.query(q)
        assert len(results) == 2
        assert all(r.actor_id == "user-alice" for r in results)

    def test_query_by_session_id(self):
        """验证按 session_id 查询"""
        q = AuditQuery(session_id="session-1")
        results = self.trail.query(q)
        assert len(results) == 2
        assert all(r.session_id == "session-1" for r in results)

    def test_query_by_resource_type(self):
        """验证按 resource_type 查询"""
        q = AuditQuery(resource_type="db")
        results = self.trail.query(q)
        assert len(results) == 2
        assert all(r.resource_type == "db" for r in results)

    def test_query_by_operation(self):
        """验证按 operation 查询"""
        q = AuditQuery(operation="read")
        results = self.trail.query(q)
        assert len(results) == 2
        assert all(r.operation == "read" for r in results)

    def test_query_by_status(self):
        """验证按 status 字段查询"""
        q = AuditQuery(status="failure")
        results = self.trail.query(q)
        assert len(results) == 2
        assert all(r.status == "failure" for r in results)

    def test_query_by_actor_type(self):
        """验证按 actor_type 查询"""
        q = AuditQuery(actor_type="system")
        results = self.trail.query(q)
        assert len(results) == 1
        assert results[0].actor_id == "system"

    def test_query_by_action(self):
        """验证按 action 查询"""
        q = AuditQuery(action="upload")
        results = self.trail.query(q)
        assert len(results) == 1
        assert results[0].record_id == "r-002"

    def test_query_by_correlation_id(self):
        """验证按 correlation_id (trace) 查询"""
        q = AuditQuery(correlation_id="trace-1")
        results = self.trail.query(q)
        assert len(results) == 2
        assert all(r.correlation_id == "trace-1" for r in results)

    def test_query_by_record_id(self):
        """验证按 record_id 查询"""
        q = AuditQuery(record_id="r-003")
        results = self.trail.query(q)
        assert len(results) == 1
        assert results[0].record_id == "r-003"

    def test_query_by_parent_record_id(self):
        """验证按 parent_record_id 查询"""
        q = AuditQuery(parent_record_id="r-003")
        results = self.trail.query(q)
        assert len(results) == 1
        assert results[0].record_id == "r-004"

    def test_query_by_status_flags(self):
        """验证按 status_flags 查询"""
        q = AuditQuery(status_flags={RecordStatus.ACTIVE})
        results = self.trail.query(q)
        assert len(results) == 4
        assert all(r.status_flag == RecordStatus.ACTIVE for r in results)

    def test_query_by_tags_all(self):
        """验证按 tags 查询 (any_tags=False，匹配所有标签)"""
        q = AuditQuery(tags={"security", "read"}, any_tags=False)
        results = self.trail.query(q)
        assert len(results) == 1
        assert results[0].record_id == "r-001"

    def test_query_by_tags_any(self):
        """验证按 tags 查询 (any_tags=True，匹配任一标签)"""
        q = AuditQuery(tags={"read", "danger"}, any_tags=True)
        results = self.trail.query(q)
        assert len(results) == 2
        ids = {r.record_id for r in results}
        assert "r-001" in ids
        assert "r-004" in ids

    def test_query_time_range(self):
        """验证按时间范围查询"""
        q = AuditQuery(
            start_time=self.now - timedelta(hours=2),
            end_time=self.now,
        )
        results = self.trail.query(q)
        assert len(results) == 2
        ids = {r.record_id for r in results}
        assert ids == {"r-003", "r-004"}

    def test_query_multi_condition(self):
        """验证多条件组合查询"""
        q = AuditQuery(
            actor_id="user-alice",
            operation="read",
        )
        results = self.trail.query(q)
        assert len(results) == 2
        assert all(r.actor_id == "user-alice" and r.operation == "read" for r in results)

    def test_query_multi_condition_intersection(self):
        """验证多条件交叉缩小范围"""
        q = AuditQuery(
            actor_id="user-alice",
            session_id="session-2",
        )
        results = self.trail.query(q)
        assert len(results) == 1
        assert results[0].record_id == "r-003"

    def test_query_pagination_limit(self):
        """验证分页 limit"""
        q = AuditQuery(limit=2)
        results = self.trail.query(q)
        assert len(results) == 2

    def test_query_pagination_offset(self):
        """验证分页 offset"""
        q = AuditQuery(limit=100, offset=3)
        results = self.trail.query(q)
        assert len(results) == 1

    def test_query_order_asc(self):
        """验证升序排列"""
        q = AuditQuery(order_by="timestamp", order_desc=False)
        results = self.trail.query(q)
        timestamps = [r.timestamp for r in results]
        assert timestamps == sorted(timestamps)

    def test_query_order_desc(self):
        """验证降序排列（默认）"""
        q = AuditQuery(order_by="timestamp", order_desc=True)
        results = self.trail.query(q)
        timestamps = [r.timestamp for r in results]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_query_order_by_record_id(self):
        """验证按 record_id 排序"""
        q = AuditQuery(order_by="record_id", order_desc=False)
        results = self.trail.query(q)
        ids = [r.record_id for r in results]
        assert ids == sorted(ids)

    def test_query_no_results(self):
        """验证无匹配时返回空列表"""
        q = AuditQuery(actor_id="nonexistent")
        results = self.trail.query(q)
        assert results == []

    def test_query_no_indexing(self):
        """验证关闭索引时查询仍正常"""
        trail = AuditTrail(enable_indexing=False)
        rec = AuditRecord(record_id="r-001", actor_id="user-1", status="success")
        trail.add(rec)
        q = AuditQuery(actor_id="user-1")
        results = trail.query(q)
        assert len(results) == 1


class TestAuditTrailGetMethods:
    """AuditTrail 便捷查询方法测试"""

    def setup_method(self):
        """准备 trail 和测试数据"""
        self.trail = AuditTrail()
        self.now = datetime.now()

        self.trail.add(AuditRecord(
            record_id="r-001",
            session_id="session-1",
            actor_id="user-alice",
            status="success",
            correlation_id="trace-1",
            timestamp=self.now - timedelta(hours=2),
        ))
        self.trail.add(AuditRecord(
            record_id="r-002",
            session_id="session-1",
            actor_id="user-bob",
            status="failure",
            correlation_id="trace-1",
            timestamp=self.now - timedelta(hours=1),
        ))
        self.trail.add(AuditRecord(
            record_id="r-003",
            session_id="session-2",
            actor_id="user-alice",
            status="failure",
            correlation_id="trace-2",
            timestamp=self.now - timedelta(minutes=30),
        ))

    def test_get_trace(self):
        """验证 get_trace 获取同一 trace 下的全部记录"""
        results = self.trail.get_trace("trace-1")
        assert len(results) == 2
        assert all(r.correlation_id == "trace-1" for r in results)

    def test_get_session_records(self):
        """验证 get_session_records 获取同一 session 下的全部记录"""
        results = self.trail.get_session_records("session-1")
        assert len(results) == 2
        assert all(r.session_id == "session-1" for r in results)

    def test_get_actor_activity(self):
        """验证 get_actor_activity 获取同一 actor 的全部记录"""
        results = self.trail.get_actor_activity("user-alice")
        assert len(results) == 2
        assert all(r.actor_id == "user-alice" for r in results)

    def test_get_failed_operations(self):
        """验证 get_failed_operations 获取 status=failure 的记录"""
        results = self.trail.get_failed_operations()
        assert len(results) == 2
        assert all(r.status == "failure" for r in results)

    def test_get_failed_operations_with_time_range(self):
        """验证 get_failed_operations 结合时间范围过滤"""
        results = self.trail.get_failed_operations(
            start_time=self.now - timedelta(minutes=45),
            end_time=self.now,
        )
        assert len(results) == 1
        assert results[0].record_id == "r-003"


class TestAuditTrailMutation:
    """AuditTrail 状态变更方法测试"""

    def setup_method(self):
        self.trail = AuditTrail()
        self.trail.add(AuditRecord(record_id="r-001", status="success"))
        self.trail.add(AuditRecord(record_id="r-002", status="failure"))

    def test_mark_compromised(self):
        """验证标记记录为已泄露"""
        result = self.trail.mark_compromised("r-001")
        assert result is True
        rec = self.trail.get("r-001")
        assert rec.status_flag == RecordStatus.COMPROMISED

    def test_mark_compromised_nonexistent(self):
        """验证标记不存在的记录返回 False"""
        result = self.trail.mark_compromised("nonexistent")
        assert result is False

    def test_archive(self):
        """验证归档记录"""
        result = self.trail.archive("r-002")
        assert result is True
        rec = self.trail.get("r-002")
        assert rec.status_flag == RecordStatus.ARCHIVED

    def test_archive_nonexistent(self):
        """验证归档不存在的记录返回 False"""
        result = self.trail.archive("nonexistent")
        assert result is False


class TestAuditTrailStats:
    """AuditTrail 统计与清理测试"""

    def setup_method(self):
        self.trail = AuditTrail()

    def test_get_stats_initial(self):
        """验证初始状态统计为空"""
        stats = self.trail.get_stats()
        assert stats["total_records"] == 0
        assert stats["by_type"] == {}
        assert stats["by_status"] == {}
        assert stats["by_actor"] == {}

    def test_get_stats_after_adds(self):
        """验证添加记录后统计正确"""
        self.trail.add(AuditRecord(
            record_id="r-001",
            record_type=AuditRecordType.EVENT,
            actor_id="user-1",
            status="success",
            status_flag=RecordStatus.ACTIVE,
        ))
        self.trail.add(AuditRecord(
            record_id="r-002",
            record_type=AuditRecordType.TRANSACTION,
            actor_id="user-2",
            status="failure",
            status_flag=RecordStatus.ACTIVE,
        ))
        self.trail.add(AuditRecord(
            record_id="r-003",
            record_type=AuditRecordType.EVENT,
            actor_id="user-1",
            status="success",
            status_flag=RecordStatus.ACTIVE,
        ))
        stats = self.trail.get_stats()
        assert stats["total_records"] == 3
        assert stats["by_type"]["event"] == 2
        assert stats["by_type"]["transaction"] == 1
        assert stats["by_status"]["active"] == 3
        assert stats["by_actor"]["user-1"] == 2
        assert stats["by_actor"]["user-2"] == 1

    def test_cleanup_old_records_max_limit(self):
        """验证超过 max_records 时自动清理旧记录"""
        trail = AuditTrail(max_records=5)
        for i in range(10):
            trail.add(AuditRecord(
                record_id=f"r-{i:03d}",
                timestamp=datetime.now() + timedelta(seconds=i),
            ))
        assert len(trail) == 5
        # 最早的 5 条应被清理
        assert trail.get("r-000") is None
        assert trail.get("r-004") is None
        # 最新的 5 条应保留
        assert trail.get("r-009") is not None
        assert trail.get("r-005") is not None

    def test_cleanup_updates_stats(self):
        """验证清理旧记录时更新统计"""
        trail = AuditTrail(max_records=3)
        for i in range(5):
            trail.add(AuditRecord(
                record_id=f"r-{i:03d}",
                record_type=AuditRecordType.EVENT,
                status_flag=RecordStatus.ACTIVE,
                timestamp=datetime.now() + timedelta(seconds=i),
            ))
        stats = trail.get_stats()
        assert stats["total_records"] == 3


class TestAuditTrailUtility:
    """AuditTrail 工具方法测试"""

    def setup_method(self):
        self.trail = AuditTrail()

    def test_len(self):
        """验证 __len__"""
        assert len(self.trail) == 0
        self.trail.add(AuditRecord(record_id="r-001"))
        assert len(self.trail) == 1

    def test_iter(self):
        """验证 __iter__ 迭代所有记录"""
        for i in range(5):
            self.trail.add(AuditRecord(record_id=f"r-{i:03d}"))
        records = list(self.trail)
        assert len(records) == 5
        assert records[0].record_id == "r-000"

    def test_getitem(self):
        """验证 __getitem__ 通过 record_id 获取"""
        rec = AuditRecord(record_id="r-001", actor_id="user-1")
        self.trail.add(rec)
        assert self.trail["r-001"].actor_id == "user-1"
        assert self.trail["nonexistent"] is None

    def test_get(self):
        """验证 get 方法"""
        rec = AuditRecord(record_id="r-001")
        self.trail.add(rec)
        assert self.trail.get("r-001") is rec
        assert self.trail.get("nonexistent") is None

    def test_get_active_sessions(self):
        """验证 get_active_sessions"""
        self.trail.add(AuditRecord(record_id="r-001", session_id="sess-1"))
        self.trail.add(AuditRecord(record_id="r-002", session_id="sess-2"))
        self.trail.add(AuditRecord(record_id="r-003", session_id="sess-1"))
        self.trail.add(AuditRecord(record_id="r-004", session_id=None))
        sessions = self.trail.get_active_sessions()
        assert sessions == {"sess-1", "sess-2"}


class TestGlobalTrail:
    """全局 trail 实例管理测试"""

    def setup_method(self):
        """每个测试前重置全局实例"""
        set_default_trail(None)

    def teardown_method(self):
        """每个测试后重置全局实例"""
        set_default_trail(None)

    def test_get_default_trail_creates_instance(self):
        """验证首次调用 get_default_trail 创建新实例"""
        trail = get_default_trail()
        assert trail is not None
        assert isinstance(trail, AuditTrail)

    def test_get_default_trail_returns_same_instance(self):
        """验证多次调用 get_default_trail 返回同一实例"""
        trail1 = get_default_trail()
        trail2 = get_default_trail()
        assert trail1 is trail2

    def test_set_default_trail(self):
        """验证 set_default_trail 替换全局实例"""
        custom = AuditTrail(max_records=500)
        set_default_trail(custom)
        assert get_default_trail() is custom
        assert get_default_trail().max_records == 500
