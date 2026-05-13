"""
审计日志记录器

提供操作审计、敏感操作标记、日志持久化等功能
"""

from .logger import AuditLogger, AuditLevel, AuditEvent, SensitiveOperation, get_default_logger, set_default_logger
from .audit_trail import AuditTrail, AuditRecord, AuditRecordType, AuditQuery, get_default_trail, set_default_trail
from .compliance import ComplianceChecker, ComplianceRule, ComplianceStatus, ViolationSeverity, ComplianceFramework, ComplianceReport

__all__ = [
    # Logger
    "AuditLogger",
    "AuditLevel",
    "AuditEvent",
    "SensitiveOperation",
    "get_default_logger",
    "set_default_logger",
    # Trail
    "AuditTrail",
    "AuditRecord",
    "AuditQuery",
    "get_default_trail",
    "set_default_trail",
    # Compliance
    "ComplianceChecker",
    "ComplianceRule",
    "ComplianceStatus",
    "ViolationSeverity",
    "ComplianceFramework",
    "ComplianceReport",
]
