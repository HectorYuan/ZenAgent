"""
compliance.py 单元测试

覆盖 ComplianceRule、ComplianceViolation、ComplianceReport、ComplianceChecker 全部 API
"""

import pytest
from datetime import datetime, timedelta

from packages.Runtime.audit.compliance import (
    ComplianceFramework,
    ComplianceStatus,
    ViolationSeverity,
    ComplianceRule,
    ComplianceViolation,
    ComplianceReport,
    ComplianceChecker,
)


# ─────────────────────────────────────────────
# ComplianceRule — threshold 条件类型
# ─────────────────────────────────────────────

class TestComplianceRuleThreshold:
    """阈值条件类型测试"""

    def setup_method(self):
        """初始化阈值规则"""
        self.rule = ComplianceRule(
            rule_id="t1",
            name="阈值规则",
            description="测试阈值",
            framework=ComplianceFramework.CUSTOM,
            condition_type="threshold",
            condition_params={"field": "count", "max": 10, "min": 1},
        )

    def test_threshold_within_range(self):
        """值在范围内应通过"""
        passed, desc = self.rule.check({"count": 5})
        assert passed is True
        assert desc is None

    def test_threshold_exceed_max(self):
        """值超过最大值应违规"""
        passed, desc = self.rule.check({"count": 15})
        assert passed is False
        assert "超出范围" in desc

    def test_threshold_below_min(self):
        """值低于最小值应违规"""
        passed, desc = self.rule.check({"count": 0})
        assert passed is False
        assert "超出范围" in desc


# ─────────────────────────────────────────────
# ComplianceRule — pattern 条件类型
# ─────────────────────────────────────────────

class TestComplianceRulePattern:
    """模式匹配条件类型测试"""

    def setup_method(self):
        """初始化模式规则"""
        self.rule = ComplianceRule(
            rule_id="p1",
            name="模式规则",
            description="测试模式匹配",
            framework=ComplianceFramework.CUSTOM,
            condition_type="pattern",
            condition_params={
                "field": "email",
                "pattern": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
                "must_match": True,
            },
        )

    def test_pattern_match_pass(self):
        """匹配模式时应通过"""
        passed, desc = self.rule.check({"email": "user@example.com"})
        assert passed is True
        assert desc is None

    def test_pattern_match_fail(self):
        """不匹配模式时应违规"""
        passed, desc = self.rule.check({"email": "invalid"})
        assert passed is False
        assert "不符合模式" in desc

    def test_pattern_must_not_match(self):
        """must_match=False 时匹配则违规"""
        rule = ComplianceRule(
            rule_id="p2",
            name="禁止模式",
            description="不应匹配内网 IP",
            framework=ComplianceFramework.CUSTOM,
            condition_type="pattern",
            condition_params={
                "field": "ip",
                "pattern": r"^10\.",
                "must_match": False,
            },
        )
        passed, desc = rule.check({"ip": "10.0.0.1"})
        assert passed is False
        assert "符合禁止模式" in desc


# ─────────────────────────────────────────────
# ComplianceRule — time_window 条件类型
# ─────────────────────────────────────────────

class TestComplianceRuleTimeWindow:
    """时间窗口条件类型测试"""

    def setup_method(self):
        """初始化时间窗口规则"""
        self.rule = ComplianceRule(
            rule_id="tw1",
            name="时间窗口规则",
            description="测试时间窗口",
            framework=ComplianceFramework.CUSTOM,
            condition_type="time_window",
            condition_params={"max_interval_hours": 24, "timestamp_field": "ts"},
        )

    def test_time_window_within(self):
        """时间在窗口内应通过"""
        now = datetime.now()
        passed, desc = self.rule.check({"ts": now.isoformat()})
        assert passed is True
        assert desc is None

    def test_time_window_exceeded(self):
        """时间超出窗口应违规"""
        old = datetime.now() - timedelta(hours=48)
        passed, desc = self.rule.check({"ts": old.isoformat()})
        assert passed is False
        assert "超出" in desc

    def test_time_window_datetime_object(self):
        """接受 datetime 对象（非字符串）"""
        now = datetime.now()
        passed, desc = self.rule.check({"ts": now})
        assert passed is True


# ─────────────────────────────────────────────
# ComplianceRule — required_operation 条件类型
# ─────────────────────────────────────────────

class TestComplianceRuleRequiredOperation:
    """必需操作条件类型测试"""

    def setup_method(self):
        """初始化必需操作规则"""
        self.rule = ComplianceRule(
            rule_id="ro1",
            name="必需操作规则",
            description="测试必需操作",
            framework=ComplianceFramework.CUSTOM,
            condition_type="required_operation",
            condition_params={"required_operations": ["audit_log", "approval"]},
        )

    def test_required_operation_all_present(self):
        """所有必需操作都存在时应通过"""
        passed, desc = self.rule.check({"operations": ["audit_log", "approval", "review"]})
        assert passed is True
        assert desc is None

    def test_required_operation_missing(self):
        """缺少必需操作时应违规"""
        passed, desc = self.rule.check({"operations": ["audit_log"]})
        assert passed is False
        assert "缺少必需操作" in desc
        assert "approval" in desc


# ─────────────────────────────────────────────
# ComplianceRule — sensitive_access 条件类型
# ─────────────────────────────────────────────

class TestComplianceRuleSensitiveAccess:
    """敏感数据访问条件类型测试"""

    def setup_method(self):
        """初始化敏感访问规则"""
        self.rule = ComplianceRule(
            rule_id="sa1",
            name="敏感访问规则",
            description="测试敏感访问",
            framework=ComplianceFramework.CUSTOM,
            condition_type="sensitive_access",
            condition_params={"require_authorization": True, "require_audit": True},
        )

    def test_sensitive_access_authorized_and_audited(self):
        """已授权且已审计时应通过"""
        passed, desc = self.rule.check({"authorized": True, "audited": True})
        assert passed is True
        assert desc is None

    def test_sensitive_access_not_authorized(self):
        """未授权时应违规"""
        passed, desc = self.rule.check({"authorized": False, "audited": True})
        assert passed is False
        assert "缺少授权" in desc

    def test_sensitive_access_not_audited(self):
        """未审计时应违规"""
        passed, desc = self.rule.check({"authorized": True, "audited": False})
        assert passed is False
        assert "缺少审计" in desc


# ─────────────────────────────────────────────
# ComplianceRule — data_retention 条件类型
# ─────────────────────────────────────────────

class TestComplianceRuleDataRetention:
    """数据保留条件类型测试"""

    def setup_method(self):
        """初始化数据保留规则"""
        self.rule = ComplianceRule(
            rule_id="dr1",
            name="数据保留规则",
            description="测试数据保留",
            framework=ComplianceFramework.CUSTOM,
            condition_type="data_retention",
            condition_params={"max_retention_days": 30, "timestamp_field": "created_at"},
        )

    def test_data_retention_within(self):
        """数据在保留期内应通过"""
        recent = datetime.now() - timedelta(days=10)
        passed, desc = self.rule.check({"created_at": recent.isoformat()})
        assert passed is True
        assert desc is None

    def test_data_retention_exceeded(self):
        """数据超出保留期应违规"""
        old = datetime.now() - timedelta(days=60)
        passed, desc = self.rule.check({"created_at": old.isoformat()})
        assert passed is False
        assert "超过最大" in desc


# ─────────────────────────────────────────────
# ComplianceRule — condition 条件类型
# ─────────────────────────────────────────────

class TestComplianceRuleCondition:
    """通用条件类型测试"""

    def setup_method(self):
        """初始化通用条件规则"""
        self.rule = ComplianceRule(
            rule_id="c1",
            name="通用条件规则",
            description="测试通用条件",
            framework=ComplianceFramework.CUSTOM,
            condition_type="condition",
            condition_params={"field": "level", "operator": "eq", "expected": "admin"},
        )

    def test_condition_eq_pass(self):
        """eq 操作符 — 值相等应通过"""
        passed, desc = self.rule.check({"level": "admin"})
        assert passed is True
        assert desc is None

    def test_condition_eq_fail(self):
        """eq 操作符 — 值不等应违规"""
        passed, desc = self.rule.check({"level": "user"})
        assert passed is False
        assert "不满足条件" in desc

    def test_condition_ne(self):
        """ne 操作符 — 值不等应通过"""
        rule = ComplianceRule(
            rule_id="c2", name="ne", description="",
            framework=ComplianceFramework.CUSTOM,
            condition_type="condition",
            condition_params={"field": "status", "operator": "ne", "expected": "banned"},
        )
        passed, _ = rule.check({"status": "active"})
        assert passed is True

    def test_condition_gt(self):
        """gt 操作符 — 大于时应通过"""
        rule = ComplianceRule(
            rule_id="c3", name="gt", description="",
            framework=ComplianceFramework.CUSTOM,
            condition_type="condition",
            condition_params={"field": "score", "operator": "gt", "expected": 80},
        )
        passed, _ = rule.check({"score": 90})
        assert passed is True
        passed, _ = rule.check({"score": 70})
        assert passed is False

    def test_condition_lt(self):
        """lt 操作符 — 小于时应通过"""
        rule = ComplianceRule(
            rule_id="c4", name="lt", description="",
            framework=ComplianceFramework.CUSTOM,
            condition_type="condition",
            condition_params={"field": "errors", "operator": "lt", "expected": 5},
        )
        passed, _ = rule.check({"errors": 2})
        assert passed is True
        passed, _ = rule.check({"errors": 10})
        assert passed is False

    def test_condition_in(self):
        """in 操作符 — 值在列表中应通过"""
        rule = ComplianceRule(
            rule_id="c5", name="in", description="",
            framework=ComplianceFramework.CUSTOM,
            condition_type="condition",
            condition_params={"field": "role", "operator": "in", "expected": ["admin", "root"]},
        )
        passed, _ = rule.check({"role": "admin"})
        assert passed is True
        passed, _ = rule.check({"role": "guest"})
        assert passed is False

    def test_condition_not_in(self):
        """not_in 操作符 — 值不在列表中应通过"""
        rule = ComplianceRule(
            rule_id="c6", name="not_in", description="",
            framework=ComplianceFramework.CUSTOM,
            condition_type="condition",
            condition_params={"field": "country", "operator": "not_in", "expected": ["XX", "YY"]},
        )
        passed, _ = rule.check({"country": "CN"})
        assert passed is True
        passed, _ = rule.check({"country": "XX"})
        assert passed is False

    def test_condition_contains(self):
        """contains 操作符 — 包含子串应通过"""
        rule = ComplianceRule(
            rule_id="c7", name="contains", description="",
            framework=ComplianceFramework.CUSTOM,
            condition_type="condition",
            condition_params={"field": "msg", "operator": "contains", "expected": "error"},
        )
        passed, _ = rule.check({"msg": "an error occurred"})
        assert passed is True
        passed, _ = rule.check({"msg": "all good"})
        assert passed is False

    def test_condition_regex(self):
        """regex 操作符 — 匹配正则应通过"""
        rule = ComplianceRule(
            rule_id="c8", name="regex", description="",
            framework=ComplianceFramework.CUSTOM,
            condition_type="condition",
            condition_params={"field": "code", "operator": "regex", "expected": r"^[A-Z]{3}\d+$"},
        )
        passed, _ = rule.check({"code": "ABC123"})
        assert passed is True
        passed, _ = rule.check({"code": "abc"})
        assert passed is False

    def test_condition_unknown_operator(self):
        """未知操作符应默认通过"""
        rule = ComplianceRule(
            rule_id="c9", name="unknown", description="",
            framework=ComplianceFramework.CUSTOM,
            condition_type="condition",
            condition_params={"field": "x", "operator": "unknown_op", "expected": 1},
        )
        passed, _ = rule.check({"x": 2})
        assert passed is True


# ─────────────────────────────────────────────
# ComplianceRule — 未知 condition_type
# ─────────────────────────────────────────────

class TestComplianceRuleUnknownType:
    """未知条件类型测试"""

    def test_unknown_condition_type_defaults_pass(self):
        """未知 condition_type 应默认通过（不触发违规）"""
        rule = ComplianceRule(
            rule_id="u1", name="未知", description="",
            framework=ComplianceFramework.CUSTOM,
            condition_type="nonexistent",
        )
        passed, desc = rule.check({"anything": 1})
        assert passed is True
        assert desc is None


# ─────────────────────────────────────────────
# ComplianceViolation — to_dict 序列化
# ─────────────────────────────────────────────

class TestComplianceViolation:
    """违规记录序列化测试"""

    def test_to_dict_basic(self):
        """to_dict 应返回包含所有关键字段的字典"""
        ts = datetime(2025, 1, 15, 10, 30, 0)
        v = ComplianceViolation(
            violation_id="v1",
            rule_id="r1",
            rule_name="规则一",
            severity=ViolationSeverity.HIGH,
            timestamp=ts,
            description="测试违规",
            affected_records=["rec-001"],
            detected_by="checker",
            status="open",
            framework=ComplianceFramework.GDPR,
            remediation_steps=["步骤一"],
        )
        d = v.to_dict()
        assert d["violation_id"] == "v1"
        assert d["rule_id"] == "r1"
        assert d["severity"] == "high"
        assert d["timestamp"] == ts.isoformat()
        assert d["status"] == "open"
        assert d["framework"] == "gdpr"
        assert d["affected_records"] == ["rec-001"]
        assert d["acknowledged_by"] is None
        assert d["acknowledged_at"] is None

    def test_to_dict_with_acknowledgment(self):
        """已确认的违规序列化应包含确认信息"""
        ack_time = datetime(2025, 6, 1, 12, 0, 0)
        v = ComplianceViolation(
            violation_id="v2",
            rule_id="r2",
            rule_name="规则二",
            severity=ViolationSeverity.LOW,
            acknowledged_by="admin",
            acknowledged_at=ack_time,
            remediation_notes="已处理",
        )
        d = v.to_dict()
        assert d["acknowledged_by"] == "admin"
        assert d["acknowledged_at"] == ack_time.isoformat()
        assert d["remediation_notes"] == "已处理"


# ─────────────────────────────────────────────
# ComplianceReport — to_dict 序列化
# ─────────────────────────────────────────────

class TestComplianceReport:
    """合规报告序列化测试"""

    def test_to_dict_basic(self):
        """to_dict 应返回包含所有关键字段的字典"""
        now = datetime(2025, 6, 1)
        v = ComplianceViolation(
            violation_id="vr1",
            rule_id="r1",
            rule_name="规则一",
            severity=ViolationSeverity.CRITICAL,
            timestamp=now,
            framework=ComplianceFramework.SOC2,
        )
        report = ComplianceReport(
            report_id="rep1",
            generated_at=now,
            start_time=now - timedelta(days=30),
            end_time=now,
            frameworks=[ComplianceFramework.SOC2],
            status=ComplianceStatus.NON_COMPLIANT,
            overall_score=75.0,
            rules_checked=10,
            rules_passed=8,
            rules_failed=2,
            violations=[v],
            total_records_analyzed=100,
            by_severity={"critical": 1},
            by_framework={"soc2": {"passed": 8, "failed": 2}},
            recommendations=["修复严重违规"],
            executive_summary="测试摘要",
        )
        d = report.to_dict()
        assert d["report_id"] == "rep1"
        assert d["status"] == "non_compliant"
        assert d["overall_score"] == 75.0
        assert d["rules_checked"] == 10
        assert len(d["violations"]) == 1
        assert d["violations"][0]["violation_id"] == "vr1"
        assert d["frameworks"] == ["soc2"]
        assert d["recommendations"] == ["修复严重违规"]

    def test_to_dict_empty(self):
        """空报告序列化应返回空违规列表和默认值"""
        report = ComplianceReport(report_id="rep_empty")
        d = report.to_dict()
        assert d["violations"] == []
        assert d["overall_score"] == 0.0
        assert d["recommendations"] == []


# ─────────────────────────────────────────────
# ComplianceChecker — add_rule / remove_rule
# ─────────────────────────────────────────────

class TestComplianceCheckerRuleManagement:
    """规则管理测试"""

    def setup_method(self):
        """初始化检查器"""
        self.checker = ComplianceChecker()

    def test_add_rule(self):
        """添加规则后应可检索"""
        rule = ComplianceRule(
            rule_id="custom_1",
            name="自定义规则",
            description="测试",
            framework=ComplianceFramework.CUSTOM,
        )
        self.checker.add_rule(rule)
        retrieved = self.checker.get_rule("custom_1")
        assert retrieved is not None
        assert retrieved.name == "自定义规则"

    def test_remove_rule_existing(self):
        """移除已存在的规则应返回 True"""
        rule = ComplianceRule(
            rule_id="removable",
            name="可移除",
            description="",
            framework=ComplianceFramework.CUSTOM,
        )
        self.checker.add_rule(rule)
        assert self.checker.remove_rule("removable") is True
        assert self.checker.get_rule("removable") is None

    def test_remove_rule_nonexistent(self):
        """移除不存在的规则应返回 False"""
        assert self.checker.remove_rule("nonexistent") is False

    def test_len_includes_default_rules(self):
        """检查器应包含默认规则"""
        # 默认有 6 条规则
        assert len(self.checker) >= 6

    def test_get_rules_by_framework(self):
        """按框架筛选规则"""
        gdpr_rules = self.checker.get_rules_by_framework(ComplianceFramework.GDPR)
        assert len(gdpr_rules) >= 2
        for r in gdpr_rules:
            assert r.framework == ComplianceFramework.GDPR

    def test_get_rules_by_tag(self):
        """按标签筛选规则"""
        security_rules = self.checker.get_rules_by_tag("security")
        assert len(security_rules) >= 1
        for r in security_rules:
            assert "security" in r.tags


# ─────────────────────────────────────────────
# ComplianceChecker — check_compliance
# ─────────────────────────────────────────────

class TestComplianceCheckerCheckCompliance:
    """合规检查测试"""

    def setup_method(self):
        """初始化检查器并添加可控规则"""
        self.checker = ComplianceChecker()

    def test_check_compliance_all_pass(self):
        """合规数据应全部通过"""
        # 构造满足所有默认规则的数据
        # source_ip: 公网 IP 才能通过 security_external_access 规则
        data = {
            "operations": ["audit_log", "approval"],
            "authorized": True,
            "audited": True,
            "failed_attempts": 2,
            "source_ip": "8.8.8.8",
            "timestamp": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat(),
        }
        results = self.checker.check_compliance(data)
        for rule, passed, desc in results:
            assert passed is True, f"规则 {rule.rule_id} 未通过: {desc}"

    def test_check_compliance_records_violation(self):
        """违规数据应被记录"""
        data = {
            "operations": [],
            "authorized": False,
            "audited": False,
            "failed_attempts": 10,
            "source_ip": "8.8.8.8",
            "created_at": (datetime.now() - timedelta(days=400)).isoformat(),
            "timestamp": (datetime.now() - timedelta(hours=100)).isoformat(),
        }
        results = self.checker.check_compliance(data)
        violations = self.checker.get_violations()
        assert len(violations) > 0

    def test_check_compliance_skips_disabled_rules(self):
        """禁用的规则不应被检查"""
        rule = ComplianceRule(
            rule_id="disabled_1",
            name="已禁用",
            description="",
            framework=ComplianceFramework.CUSTOM,
            condition_type="threshold",
            condition_params={"field": "x", "max": 1},
            enabled=False,
        )
        self.checker.add_rule(rule)
        results = self.checker.check_compliance({"x": 999})
        checked_ids = [r.rule_id for r, _, _ in results]
        assert "disabled_1" not in checked_ids


# ─────────────────────────────────────────────
# ComplianceChecker — record_violation / get_violations
# ─────────────────────────────────────────────

class TestComplianceCheckerViolations:
    """违规记录与查询测试"""

    def setup_method(self):
        """初始化检查器"""
        self.checker = ComplianceChecker()

    def test_record_violation_returns_id(self):
        """记录违规应返回违规 ID"""
        rule = ComplianceRule(
            rule_id="vr_rule", name="VR", description="",
            framework=ComplianceFramework.CUSTOM,
            severity=ViolationSeverity.HIGH,
        )
        vid = self.checker.record_violation(rule, "描述", {"record_id": "r1"})
        assert isinstance(vid, str)
        assert len(vid) > 0

    def test_get_violations_all(self):
        """无筛选条件应返回全部违规"""
        rule = ComplianceRule(
            rule_id="g_rule", name="G", description="",
            framework=ComplianceFramework.CUSTOM,
            severity=ViolationSeverity.LOW,
        )
        self.checker.record_violation(rule, "d1", {})
        self.checker.record_violation(rule, "d2", {})
        assert len(self.checker.get_violations()) == 2

    def test_get_violations_by_rule_id(self):
        """按 rule_id 筛选违规"""
        rule_a = ComplianceRule(
            rule_id="a", name="A", description="",
            framework=ComplianceFramework.CUSTOM,
            severity=ViolationSeverity.LOW,
        )
        rule_b = ComplianceRule(
            rule_id="b", name="B", description="",
            framework=ComplianceFramework.CUSTOM,
            severity=ViolationSeverity.HIGH,
        )
        self.checker.record_violation(rule_a, "a1", {})
        self.checker.record_violation(rule_b, "b1", {})
        assert len(self.checker.get_violations(rule_id="a")) == 1

    def test_get_violations_by_severity(self):
        """按严重级别筛选违规"""
        rule = ComplianceRule(
            rule_id="s_rule", name="S", description="",
            framework=ComplianceFramework.CUSTOM,
            severity=ViolationSeverity.CRITICAL,
        )
        self.checker.record_violation(rule, "crit", {})
        assert len(self.checker.get_violations(severity=ViolationSeverity.CRITICAL)) >= 1

    def test_get_violations_by_status(self):
        """按状态筛选违规"""
        rule = ComplianceRule(
            rule_id="st_rule", name="ST", description="",
            framework=ComplianceFramework.CUSTOM,
            severity=ViolationSeverity.MEDIUM,
        )
        vid = self.checker.record_violation(rule, "open", {})
        assert len(self.checker.get_violations(status="open")) >= 1
        self.checker.acknowledge_violation(vid, "admin")
        assert len(self.checker.get_violations(status="acknowledged")) >= 1

    def test_get_violations_by_time_range(self):
        """按时间范围筛选违规"""
        rule = ComplianceRule(
            rule_id="tr_rule", name="TR", description="",
            framework=ComplianceFramework.CUSTOM,
            severity=ViolationSeverity.LOW,
        )
        self.checker.record_violation(rule, "t1", {})
        now = datetime.now()
        assert len(self.checker.get_violations(
            start_time=now - timedelta(minutes=1),
            end_time=now + timedelta(minutes=1),
        )) >= 1
        assert len(self.checker.get_violations(
            start_time=now + timedelta(hours=1),
        )) == 0


# ─────────────────────────────────────────────
# ComplianceChecker — acknowledge_violation
# ─────────────────────────────────────────────

class TestComplianceCheckerAcknowledge:
    """违规确认测试"""

    def setup_method(self):
        """初始化检查器并记录违规"""
        self.checker = ComplianceChecker()
        rule = ComplianceRule(
            rule_id="ack_rule", name="ACK", description="",
            framework=ComplianceFramework.CUSTOM,
            severity=ViolationSeverity.HIGH,
        )
        self.vid = self.checker.record_violation(rule, "待确认", {})

    def test_acknowledge_existing_violation(self):
        """确认已存在的违规应返回 True 并更新状态"""
        result = self.checker.acknowledge_violation(self.vid, "admin", "已确认")
        assert result is True
        violations = [v for v in self.checker.get_violations() if v.violation_id == self.vid]
        assert len(violations) == 1
        v = violations[0]
        assert v.status == "acknowledged"
        assert v.acknowledged_by == "admin"
        assert v.acknowledged_at is not None
        assert v.remediation_notes == "已确认"

    def test_acknowledge_nonexistent_violation(self):
        """确认不存在的违规应返回 False"""
        result = self.checker.acknowledge_violation("fake_id", "admin")
        assert result is False


# ─────────────────────────────────────────────
# ComplianceChecker — remediate_violation
# ─────────────────────────────────────────────

class TestComplianceCheckerRemediate:
    """违规修复测试"""

    def setup_method(self):
        """初始化检查器并记录违规"""
        self.checker = ComplianceChecker()
        rule = ComplianceRule(
            rule_id="rem_rule", name="REM", description="",
            framework=ComplianceFramework.CUSTOM,
            severity=ViolationSeverity.MEDIUM,
        )
        self.vid = self.checker.record_violation(rule, "待修复", {})

    def test_remediate_existing_violation(self):
        """修复已存在的违规应返回 True 并更新状态"""
        result = self.checker.remediate_violation(self.vid, "已修复")
        assert result is True
        violations = [v for v in self.checker.get_violations() if v.violation_id == self.vid]
        assert violations[0].status == "remediated"
        assert violations[0].remediation_notes == "已修复"

    def test_remediate_nonexistent_violation(self):
        """修复不存在的违规应返回 False"""
        result = self.checker.remediate_violation("fake_id")
        assert result is False


# ─────────────────────────────────────────────
# ComplianceChecker — generate_report
# ─────────────────────────────────────────────

class TestComplianceCheckerReport:
    """报告生成测试"""

    def setup_method(self):
        """初始化检查器"""
        self.checker = ComplianceChecker()

    def test_generate_report_no_violations(self):
        """无违规时报告应显示合规"""
        now = datetime.now()
        report = self.checker.generate_report(
            start_time=now - timedelta(days=30),
            end_time=now,
            frameworks=[ComplianceFramework.CUSTOM],
        )
        assert report.rules_checked >= 0
        assert report.rules_failed == 0
        assert report.status == ComplianceStatus.COMPLIANT or report.rules_checked == 0

    def test_generate_report_with_violations(self):
        """有违规时报告应包含违规信息"""
        rule = ComplianceRule(
            rule_id="report_rule", name="报告规则", description="",
            framework=ComplianceFramework.CUSTOM,
            severity=ViolationSeverity.CRITICAL,
        )
        self.checker.add_rule(rule)
        self.checker.record_violation(rule, "严重违规", {})

        now = datetime.now()
        report = self.checker.generate_report(
            start_time=now - timedelta(days=1),
            end_time=now + timedelta(days=1),
            frameworks=[ComplianceFramework.CUSTOM],
        )
        assert report.rules_failed >= 1
        assert len(report.violations) >= 1
        assert report.overall_score < 100

    def test_generate_report_with_audit_records(self):
        """传入 audit_records 应更新 total_records_analyzed"""
        now = datetime.now()
        records = [{"id": i} for i in range(50)]
        report = self.checker.generate_report(
            start_time=now - timedelta(days=1),
            end_time=now,
            audit_records=records,
        )
        assert report.total_records_analyzed == 50

    def test_generate_report_score_calculation(self):
        """评分应按 通过/总数 * 100 计算"""
        # 添加一个必违规的规则
        rule = ComplianceRule(
            rule_id="score_rule", name="评分规则", description="",
            framework=ComplianceFramework.CUSTOM,
            condition_type="threshold",
            condition_params={"field": "v", "max": 0},
            severity=ViolationSeverity.LOW,
        )
        self.checker.add_rule(rule)
        self.checker.check_compliance({"v": 999})

        now = datetime.now()
        report = self.checker.generate_report(
            start_time=now - timedelta(days=1),
            end_time=now + timedelta(days=1),
        )
        assert report.rules_checked > 0
        expected_score = (report.rules_passed / report.rules_checked) * 100
        assert abs(report.overall_score - expected_score) < 0.01

    def test_generate_report_executive_summary(self):
        """报告应包含执行摘要"""
        now = datetime.now()
        report = self.checker.generate_report(
            start_time=now - timedelta(days=1),
            end_time=now,
        )
        assert "合规检查完成" in report.executive_summary
        assert "总体评分" in report.executive_summary

    def test_generate_report_recommendations_critical(self):
        """有严重违规时应生成修复建议"""
        rule = ComplianceRule(
            rule_id="crit_rule", name="严重规则", description="",
            framework=ComplianceFramework.CUSTOM,
            severity=ViolationSeverity.CRITICAL,
        )
        self.checker.add_rule(rule)
        self.checker.record_violation(rule, "严重", {})

        now = datetime.now()
        report = self.checker.generate_report(
            start_time=now - timedelta(days=1),
            end_time=now + timedelta(days=1),
        )
        recs = report.recommendations
        assert any("严重" in r for r in recs)


# ─────────────────────────────────────────────
# ComplianceChecker — get_statistics
# ─────────────────────────────────────────────

class TestComplianceCheckerStatistics:
    """统计数据测试"""

    def setup_method(self):
        """初始化检查器"""
        self.checker = ComplianceChecker()

    def test_statistics_initial(self):
        """初始统计应包含默认规则数量"""
        stats = self.checker.get_statistics()
        assert stats["total_rules"] >= 6
        assert stats["enabled_rules"] >= 6
        assert stats["total_violations"] == 0
        assert stats["open_violations"] == 0

    def test_statistics_after_violations(self):
        """记录违规后统计应更新"""
        rule = ComplianceRule(
            rule_id="stat_rule", name="统计规则", description="",
            framework=ComplianceFramework.CUSTOM,
            severity=ViolationSeverity.HIGH,
        )
        self.checker.add_rule(rule)
        self.checker.record_violation(rule, "v1", {})
        self.checker.record_violation(rule, "v2", {})

        stats = self.checker.get_statistics()
        assert stats["total_violations"] >= 2
        assert stats["open_violations"] >= 2

    def test_statistics_by_framework(self):
        """按框架统计规则数"""
        stats = self.checker.get_statistics()
        assert "gdpr" in stats["by_framework"]
        assert stats["by_framework"]["gdpr"] >= 2
        assert "soc2" in stats["by_framework"]

    def test_statistics_after_acknowledge(self):
        """确认违规后 open_violations 应减少"""
        rule = ComplianceRule(
            rule_id="stat_ack", name="统计确认", description="",
            framework=ComplianceFramework.CUSTOM,
            severity=ViolationSeverity.LOW,
        )
        self.checker.add_rule(rule)
        vid = self.checker.record_violation(rule, "ack1", {})

        before = self.checker.get_statistics()["open_violations"]
        self.checker.acknowledge_violation(vid, "admin")
        after = self.checker.get_statistics()["open_violations"]
        assert after == before - 1
