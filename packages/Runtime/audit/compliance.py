"""
合规检查模块

提供审计日志的合规性检查、报告生成和违规检测功能
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from collections import defaultdict
import threading


class ComplianceFramework(Enum):
    """合规框架"""
    GDPR = "gdpr"                    # 通用数据保护条例
    SOC2 = "soc2"                    # SOC 2 合规
    HIPAA = "hipaa"                  # 健康保险流通与责任法案
    PCI_DSS = "pci_dss"             # 支付卡行业数据安全标准
    ISO27001 = "iso27001"           # 信息安全管理体系
    NIST = "nist"                    # 美国国家标准与技术研究院
    CUSTOM = "custom"               # 自定义


class ComplianceStatus(Enum):
    """合规状态"""
    COMPLIANT = "compliant"         # 合规
    NON_COMPLIANT = "non_compliant" # 不合规
    PARTIALLY_COMPLIANT = "partially_compliant"  # 部分合规
    PENDING = "pending"             # 待审核
    NOT_APPLICABLE = "not_applicable"  # 不适用


class ViolationSeverity(Enum):
    """违规严重级别"""
    CRITICAL = "critical"          # 严重
    HIGH = "high"                   # 高
    MEDIUM = "medium"               # 中
    LOW = "low"                     # 低
    INFO = "info"                   # 信息


@dataclass
class ComplianceRule:
    """
    合规规则
    
    定义一个具体的合规检查规则
    """
    rule_id: str
    name: str
    description: str
    framework: ComplianceFramework
    
    # 检查条件
    condition_type: str = ""        # condition, threshold, pattern, relationship
    condition_params: Dict[str, Any] = field(default_factory=dict)
    
    # 违规参数
    severity: ViolationSeverity = ViolationSeverity.MEDIUM
    penalty_description: str = ""
    remediation_steps: List[str] = field(default_factory=list)
    
    # 启用状态
    enabled: bool = True
    tags: Set[str] = field(default_factory=set)
    
    # 关联规则
    related_rules: List[str] = field(default_factory=list)
    parent_rule_id: Optional[str] = None
    
    def check(self, audit_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        检查是否违反规则
        
        Args:
            audit_data: 审计数据
            
        Returns:
            (是否违规, 违规描述)
        """
        if self.condition_type == "threshold":
            return self._check_threshold(audit_data)
        elif self.condition_type == "pattern":
            return self._check_pattern(audit_data)
        elif self.condition_type == "time_window":
            return self._check_time_window(audit_data)
        elif self.condition_type == "required_operation":
            return self._check_required_operation(audit_data)
        elif self.condition_type == "sensitive_access":
            return self._check_sensitive_access(audit_data)
        elif self.condition_type == "data_retention":
            return self._check_data_retention(audit_data)
        elif self.condition_type == "condition":
            return self._check_condition(audit_data)
        return True, None
    
    def _check_threshold(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """检查阈值"""
        field_name = self.condition_params.get("field", "")
        max_value = self.condition_params.get("max", float("inf"))
        min_value = self.condition_params.get("min", 0)
        
        value = data.get(field_name, 0)
        if value > max_value or value < min_value:
            return False, f"{field_name}={value} 超出范围 [{min_value}, {max_value}]"
        return True, None
    
    def _check_pattern(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """检查模式"""
        import re
        field_name = self.condition_params.get("field", "")
        pattern = self.condition_params.get("pattern", "")
        must_match = self.condition_params.get("must_match", True)
        
        value = str(data.get(field_name, ""))
        matched = bool(re.match(pattern, value))
        
        if must_match and not matched:
            return False, f"{field_name} 不符合模式 {pattern}"
        if not must_match and matched:
            return False, f"{field_name} 符合禁止模式 {pattern}"
        return True, None
    
    def _check_time_window(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """检查时间窗口"""
        max_interval = self.condition_params.get("max_interval_hours", 24)
        field_name = self.condition_params.get("timestamp_field", "timestamp")
        
        timestamp_str = data.get(field_name)
        if isinstance(timestamp_str, str):
            timestamp = datetime.fromisoformat(timestamp_str)
        else:
            timestamp = timestamp_str
        
        if timestamp:
            now = datetime.now()
            delta = now - timestamp
            if delta > timedelta(hours=max_interval):
                return False, f"时间戳 {timestamp} 超出 {max_interval} 小时窗口"
        return True, None
    
    def _check_required_operation(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """检查必需操作"""
        required_ops = self.condition_params.get("required_operations", [])
        performed_ops = data.get("operations", [])
        
        for op in required_ops:
            if op not in performed_ops:
                return False, f"缺少必需操作: {op}"
        return True, None
    
    def _check_sensitive_access(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """检查敏感数据访问"""
        require_authorization = self.condition_params.get("require_authorization", True)
        require_audit = self.condition_params.get("require_audit", True)
        
        if require_authorization and not data.get("authorized"):
            return False, "敏感操作缺少授权"
        if require_audit and not data.get("audited"):
            return False, "敏感操作缺少审计记录"
        return True, None
    
    def _check_data_retention(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """检查数据保留"""
        max_days = self.condition_params.get("max_retention_days", 365)
        timestamp_field = self.condition_params.get("timestamp_field", "timestamp")
        
        timestamp_str = data.get(timestamp_field)
        if isinstance(timestamp_str, str):
            timestamp = datetime.fromisoformat(timestamp_str)
        else:
            timestamp = timestamp_str
        
        if timestamp:
            age_days = (datetime.now() - timestamp).days
            if age_days > max_days:
                return False, f"数据保留 {age_days} 天超过最大 {max_days} 天"
        return True, None
    
    def _check_condition(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """检查通用条件"""
        field_name = self.condition_params.get("field", "")
        expected_value = self.condition_params.get("expected")
        operator = self.condition_params.get("operator", "eq")
        
        actual_value = data.get(field_name)
        
        if operator == "eq":
            valid = actual_value == expected_value
        elif operator == "ne":
            valid = actual_value != expected_value
        elif operator == "gt":
            valid = actual_value > expected_value
        elif operator == "lt":
            valid = actual_value < expected_value
        elif operator == "in":
            valid = actual_value in expected_value
        elif operator == "not_in":
            valid = actual_value not in expected_value
        elif operator == "contains":
            valid = expected_value in actual_value
        elif operator == "regex":
            import re
            valid = bool(re.match(expected_value, str(actual_value)))
        else:
            valid = True
        
        if not valid:
            return False, f"{field_name}={actual_value} 不满足条件 {operator} {expected_value}"
        return True, None


@dataclass
class ComplianceViolation:
    """合规违规"""
    violation_id: str
    rule_id: str
    rule_name: str
    severity: ViolationSeverity
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 详情
    description: str = ""
    affected_records: List[str] = field(default_factory=list)
    detected_by: str = ""
    
    # 状态
    status: str = "open"  # open, acknowledged, remediated, waived
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    remediation_notes: str = ""
    
    # 元数据
    framework: ComplianceFramework = ComplianceFramework.CUSTOM
    remediation_steps: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "affected_records": self.affected_records,
            "detected_by": self.detected_by,
            "status": self.status,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "remediation_notes": self.remediation_notes,
            "framework": self.framework.value,
            "remediation_steps": self.remediation_steps,
        }


@dataclass
class ComplianceReport:
    """合规报告"""
    report_id: str
    generated_at: datetime = field(default_factory=datetime.now)
    
    # 范围
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=datetime.now)
    frameworks: List[ComplianceFramework] = field(default_factory=list)
    
    # 结果
    status: ComplianceStatus = ComplianceStatus.PENDING
    overall_score: float = 0.0  # 0-100
    
    # 详情
    rules_checked: int = 0
    rules_passed: int = 0
    rules_failed: int = 0
    violations: List[ComplianceViolation] = field(default_factory=list)
    
    # 统计
    total_records_analyzed: int = 0
    by_severity: Dict[str, int] = field(default_factory=dict)
    by_framework: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # 建议
    recommendations: List[str] = field(default_factory=list)
    executive_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "frameworks": [f.value for f in self.frameworks],
            "status": self.status.value,
            "overall_score": self.overall_score,
            "rules_checked": self.rules_checked,
            "rules_passed": self.rules_passed,
            "rules_failed": self.rules_failed,
            "violations": [v.to_dict() for v in self.violations],
            "total_records_analyzed": self.total_records_analyzed,
            "by_severity": self.by_severity,
            "by_framework": self.by_framework,
            "recommendations": self.recommendations,
            "executive_summary": self.executive_summary,
        }


class ComplianceChecker:
    """
    合规检查器
    
    提供审计日志的合规性检查和违规检测功能
    """
    
    def __init__(self):
        self._rules: Dict[str, ComplianceRule] = {}
        self._violations: List[ComplianceViolation] = []
        self._violation_index: Dict[str, List[int]] = defaultdict(list)
        self._lock = threading.RLock()
        
        # 初始化默认规则
        self._init_default_rules()
    
    def _init_default_rules(self) -> None:
        """初始化默认合规规则"""
        # GDPR 相关规则
        self.add_rule(ComplianceRule(
            rule_id="gdpr_data_access",
            name="数据访问审计",
            description="所有个人数据访问必须被记录",
            framework=ComplianceFramework.GDPR,
            condition_type="required_operation",
            condition_params={"required_operations": ["audit_log"]},
            severity=ViolationSeverity.HIGH,
            remediation_steps=[
                "启用数据访问审计功能",
                "确保所有访问都有日志记录",
                "定期审查访问日志"
            ],
            tags={"gdpr", "data-protection", "audit"},
        ))
        
        self.add_rule(ComplianceRule(
            rule_id="gdpr_retention",
            name="数据保留期限",
            description="个人数据保留不能超过必要期限",
            framework=ComplianceFramework.GDPR,
            condition_type="data_retention",
            condition_params={"max_retention_days": 365, "timestamp_field": "created_at"},
            severity=ViolationSeverity.MEDIUM,
            remediation_steps=[
                "制定数据保留政策",
                "实施自动化数据清理",
                "定期审计数据保留情况"
            ],
            tags={"gdpr", "data-retention"},
        ))
        
        # SOC2 相关规则
        self.add_rule(ComplianceRule(
            rule_id="soc2_authentication",
            name="认证失败监控",
            description="连续认证失败应触发告警",
            framework=ComplianceFramework.SOC2,
            condition_type="threshold",
            condition_params={"field": "failed_attempts", "max": 5},
            severity=ViolationSeverity.HIGH,
            remediation_steps=[
                "实现账户锁定机制",
                "启用多因素认证",
                "设置失败尝试告警"
            ],
            tags={"soc2", "security", "authentication"},
        ))
        
        self.add_rule(ComplianceRule(
            rule_id="soc2_privileged_access",
            name="特权访问审计",
            description="所有特权操作必须有多人审批",
            framework=ComplianceFramework.SOC2,
            condition_type="sensitive_access",
            condition_params={"require_authorization": True, "require_audit": True},
            severity=ViolationSeverity.CRITICAL,
            remediation_steps=[
                "实施特权访问管理",
                "启用操作审计",
                "定期审查权限分配"
            ],
            tags={"soc2", "security", "privileged-access"},
        ))
        
        # 通用安全规则
        self.add_rule(ComplianceRule(
            rule_id="security_key_rotation",
            name="密钥轮换",
            description="加密密钥应定期轮换",
            framework=ComplianceFramework.ISO27001,
            condition_type="time_window",
            condition_params={"max_interval_hours": 2160},  # 90天
            severity=ViolationSeverity.MEDIUM,
            remediation_steps=[
                "制定密钥轮换策略",
                "自动化密钥轮换流程",
                "记录密钥使用情况"
            ],
            tags={"security", "key-management", "iso27001"},
        ))
        
        self.add_rule(ComplianceRule(
            rule_id="security_external_access",
            name="外部访问监控",
            description="来自非信任区域的访问应被标记",
            framework=ComplianceFramework.ISO27001,
            condition_type="pattern",
            condition_params={"field": "source_ip", "pattern": r"^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)", "must_match": False},
            severity=ViolationSeverity.LOW,
            remediation_steps=[
                "配置 IP 白名单",
                "启用地理位置监控",
                "实施访问异常检测"
            ],
            tags={"security", "network", "iso27001"},
        ))
    
    def add_rule(self, rule: ComplianceRule) -> None:
        """添加合规规则"""
        with self._lock:
            self._rules[rule.rule_id] = rule
    
    def remove_rule(self, rule_id: str) -> bool:
        """移除合规规则"""
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                return True
            return False
    
    def get_rule(self, rule_id: str) -> Optional[ComplianceRule]:
        """获取规则"""
        return self._rules.get(rule_id)
    
    def get_rules_by_framework(
        self,
        framework: ComplianceFramework,
    ) -> List[ComplianceRule]:
        """获取框架相关规则"""
        return [r for r in self._rules.values() if r.framework == framework]
    
    def get_rules_by_tag(self, tag: str) -> List[ComplianceRule]:
        """获取标签相关规则"""
        return [r for r in self._rules.values() if tag in r.tags]
    
    def check_compliance(
        self,
        audit_data: Dict[str, Any],
    ) -> List[Tuple[ComplianceRule, bool, Optional[str]]]:
        """
        检查合规性
        
        Args:
            audit_data: 审计数据
            
        Returns:
            [(规则, 是否通过, 违规描述), ...]
        """
        results = []
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            
            passed, violation_desc = rule.check(audit_data)
            results.append((rule, passed, violation_desc))
            
            # 如果违规，记录
            if not passed:
                self.record_violation(rule, violation_desc, audit_data)
        
        return results
    
    def record_violation(
        self,
        rule: ComplianceRule,
        description: str,
        audit_data: Dict[str, Any],
    ) -> str:
        """记录违规"""
        import uuid
        
        violation = ComplianceViolation(
            violation_id=str(uuid.uuid4()),
            rule_id=rule.rule_id,
            rule_name=rule.name,
            severity=rule.severity,
            description=description or rule.penalty_description,
            framework=rule.framework,
            remediation_steps=rule.remediation_steps,
            affected_records=[audit_data.get("record_id", "")],
        )
        
        with self._lock:
            idx = len(self._violations)
            self._violations.append(violation)
            self._violation_index[rule.rule_id].append(idx)
        
        return violation.violation_id
    
    def get_violations(
        self,
        rule_id: Optional[str] = None,
        severity: Optional[ViolationSeverity] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[ComplianceViolation]:
        """查询违规记录"""
        with self._lock:
            violations = list(self._violations)
        
        if rule_id:
            violations = [v for v in violations if v.rule_id == rule_id]
        if severity:
            violations = [v for v in violations if v.severity == severity]
        if status:
            violations = [v for v in violations if v.status == status]
        if start_time:
            violations = [v for v in violations if v.timestamp >= start_time]
        if end_time:
            violations = [v for v in violations if v.timestamp <= end_time]
        
        return violations
    
    def acknowledge_violation(
        self,
        violation_id: str,
        acknowledged_by: str,
        notes: str = "",
    ) -> bool:
        """确认违规"""
        with self._lock:
            for v in self._violations:
                if v.violation_id == violation_id:
                    v.status = "acknowledged"
                    v.acknowledged_by = acknowledged_by
                    v.acknowledged_at = datetime.now()
                    v.remediation_notes = notes
                    return True
        return False
    
    def remediate_violation(
        self,
        violation_id: str,
        notes: str = "",
    ) -> bool:
        """修复违规"""
        with self._lock:
            for v in self._violations:
                if v.violation_id == violation_id:
                    v.status = "remediated"
                    v.remediation_notes = notes
                    return True
        return False
    
    def generate_report(
        self,
        start_time: datetime,
        end_time: datetime,
        frameworks: Optional[List[ComplianceFramework]] = None,
        audit_records: Optional[List[Dict[str, Any]]] = None,
    ) -> ComplianceReport:
        """
        生成合规报告
        
        Args:
            start_time: 报告开始时间
            end_time: 报告结束时间
            frameworks: 要检查的框架列表
            audit_records: 要分析的审计记录
            
        Returns:
            合规报告
        """
        import uuid
        
        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            start_time=start_time,
            end_time=end_time,
            frameworks=frameworks or list(ComplianceFramework),
        )
        
        # 获取要检查的规则
        rules_to_check = list(self._rules.values())
        if frameworks:
            rules_to_check = [r for r in rules_to_check if r.framework in frameworks]
        rules_to_check = [r for r in rules_to_check if r.enabled]
        
        report.rules_checked = len(rules_to_check)
        report.total_records_analyzed = len(audit_records) if audit_records else 0
        
        # 检查每条规则
        for rule in rules_to_check:
            violations = self.get_violations(
                rule_id=rule.rule_id,
                start_time=start_time,
                end_time=end_time,
            )
            
            if violations:
                report.rules_failed += 1
                report.violations.extend(violations)
                
                # 按框架统计
                fw_key = rule.framework.value
                if fw_key not in report.by_framework:
                    report.by_framework[fw_key] = {"passed": 0, "failed": 0}
                report.by_framework[fw_key]["failed"] += 1
            else:
                report.rules_passed += 1
                
                fw_key = rule.framework.value
                if fw_key not in report.by_framework:
                    report.by_framework[fw_key] = {"passed": 0, "failed": 0}
                report.by_framework[fw_key]["passed"] += 1
        
        # 统计违规严重级别
        for v in report.violations:
            sev_key = v.severity.value
            report.by_severity[sev_key] = report.by_severity.get(sev_key, 0) + 1
        
        # 计算总体评分
        if report.rules_checked > 0:
            report.overall_score = (report.rules_passed / report.rules_checked) * 100
        
        # 确定总体状态
        if report.rules_failed == 0:
            report.status = ComplianceStatus.COMPLIANT
        elif report.rules_failed < report.rules_checked * 0.1:
            report.status = ComplianceStatus.PARTIALLY_COMPLIANT
        else:
            report.status = ComplianceStatus.NON_COMPLIANT
        
        # 生成建议
        critical_violations = [v for v in report.violations 
                              if v.severity == ViolationSeverity.CRITICAL]
        if critical_violations:
            report.recommendations.append(
                f"立即处理 {len(critical_violations)} 个严重违规"
            )
        
        high_violations = [v for v in report.violations 
                          if v.severity == ViolationSeverity.HIGH]
        if high_violations:
            report.recommendations.append(
                f"优先处理 {len(high_violations)} 个高危违规"
            )
        
        # 生成执行摘要
        report.executive_summary = (
            f"合规检查完成。共检查 {report.rules_checked} 条规则，"
            f"通过 {report.rules_passed} 条，失败 {report.rules_failed} 条。"
            f"发现 {len(report.violations)} 个违规，"
            f"总体评分为 {report.overall_score:.1f}%。"
        )
        
        return report
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取合规统计"""
        with self._lock:
            return {
                "total_rules": len(self._rules),
                "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
                "total_violations": len(self._violations),
                "open_violations": sum(1 for v in self._violations if v.status == "open"),
                "by_framework": {
                    fw.value: len(self.get_rules_by_framework(fw))
                    for fw in ComplianceFramework
                },
            }
    
    def __len__(self) -> int:
        return len(self._rules)
