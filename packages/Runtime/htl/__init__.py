# HiTL - 人工审批流程模块
"""
HiTL (Human-in-the-Loop) 模块，提供高风险操作的人工审批能力

包含:
- approval_flow: 审批流程
- policy: 审批策略
- handler: 处理器
"""

from .approval_flow import ApprovalFlow, ApprovalRequest, ApprovalResult, ApprovalStatus, ApprovalPriority
from .policy import ApprovalPolicy, PolicyEngine, RiskLevel, ApprovalRule, RiskAssessment
from .handler import HTLHandler, HTLConfig, HTLOperationMode, HTLOperation

__all__ = [
    "ApprovalFlow",
    "ApprovalRequest",
    "ApprovalResult",
    "ApprovalStatus",
    "ApprovalPriority",
    "ApprovalPolicy",
    "PolicyEngine",
    "RiskLevel",
    "ApprovalRule",
    "RiskAssessment",
    "HTLHandler",
    "HTLConfig",
    "HTLOperationMode",
    "HTLOperation",
]
