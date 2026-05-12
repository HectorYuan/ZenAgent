"""
审批策略 - Approval Policy

定义和管理审批策略，包括敏感操作识别和风险评估
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import List, Dict, Any, Optional, Callable, Set
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import re


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"           # 低风险
    MEDIUM = "medium"     # 中风险
    HIGH = "high"         # 高风险
    CRITICAL = "critical" # 极高风险


class OperationCategory(Enum):
    """操作类别"""
    DATA_ACCESS = "data_access"       # 数据访问
    DATA_MODIFICATION = "data_modification"  # 数据修改
    SYSTEM_CONFIG = "system_config"   # 系统配置
    USER_MANAGEMENT = "user_management"  # 用户管理
    FINANCIAL = "financial"           # 财务相关
    SECURITY = "security"           # 安全相关
    NETWORK = "network"             # 网络相关
    FILE_OPERATION = "file_operation"  # 文件操作
    EXTERNAL_CALL = "external_call"  # 外部调用
    CUSTOM = "custom"               # 自定义


@dataclass
class ApprovalRule:
    """审批规则"""
    rule_id: str
    name: str
    description: str
    operation_patterns: List[str]  # 支持正则匹配
    operation_category: OperationCategory
    required_risk_level: RiskLevel
    requires_approval: bool
    approvers: List[str] = field(default_factory=list)
    approver_role: Optional[str] = None
    priority_boost: int = 0
    conditions: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    
    def matches(self, operation_type: str) -> bool:
        """检查是否匹配"""
        for pattern in self.operation_patterns:
            if re.match(pattern, operation_type):
                return True
        return False


@dataclass
class RiskAssessment:
    """风险评估结果"""
    risk_level: RiskLevel
    score: float  # 0-100
    factors: List[str]
    recommendations: List[str]
    requires_approval: bool
    suggested_approvers: List[str]
    assessment_time: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "risk_level": self.risk_level.value,
            "score": self.score,
            "factors": self.factors,
            "recommendations": self.recommendations,
            "requires_approval": self.requires_approval,
            "suggested_approvers": self.suggested_approvers,
            "assessment_time": self.assessment_time.isoformat()
        }


class ApprovalPolicy:
    """
    审批策略
    
    定义和管理审批规则。
    """
    
    def __init__(self):
        """初始化审批策略"""
        self._rules: List[ApprovalRule] = []
        self._default_risk_level = RiskLevel.MEDIUM
        self._risk_thresholds = {
            RiskLevel.LOW: 20,
            RiskLevel.MEDIUM: 50,
            RiskLevel.HIGH: 75,
            RiskLevel.CRITICAL: 90
        }
        self._initialize_default_rules()
    
    def _initialize_default_rules(self) -> None:
        """初始化默认规则"""
        # 高风险操作规则
        self.add_rule(ApprovalRule(
            rule_id="rule_001",
            name="数据删除",
            description="涉及数据删除的高风险操作",
            operation_patterns=[r".*delete.*", r".*remove.*", r".*drop.*"],
            operation_category=OperationCategory.DATA_MODIFICATION,
            required_risk_level=RiskLevel.HIGH,
            requires_approval=True,
            approvers=["admin"],
            priority_boost=2
        ))
        
        # 敏感数据访问
        self.add_rule(ApprovalRule(
            rule_id="rule_002",
            name="敏感数据访问",
            description="访问敏感数据的操作",
            operation_patterns=[r".*sensitive.*", r".*password.*", r".*secret.*", r".*credential.*"],
            operation_category=OperationCategory.DATA_ACCESS,
            required_risk_level=RiskLevel.MEDIUM,
            requires_approval=True,
            approver_role="security"
        ))
        
        # 系统配置变更
        self.add_rule(ApprovalRule(
            rule_id="rule_003",
            name="系统配置变更",
            description="修改系统配置的操作",
            operation_patterns=[r".*config.*", r".*setting.*", r".*system.*update.*"],
            operation_category=OperationCategory.SYSTEM_CONFIG,
            required_risk_level=RiskLevel.HIGH,
            requires_approval=True,
            approvers=["admin", "security"],
            priority_boost=1
        ))
        
        # 财务操作
        self.add_rule(ApprovalRule(
            rule_id="rule_004",
            name="财务操作",
            description="涉及财务的操作",
            operation_patterns=[r".*payment.*", r".*transfer.*", r".*refund.*", r".*invoice.*"],
            operation_category=OperationCategory.FINANCIAL,
            required_risk_level=RiskLevel.CRITICAL,
            requires_approval=True,
            approvers=["admin", "finance"],
            priority_boost=3
        ))
        
        # 外部调用
        self.add_rule(ApprovalRule(
            rule_id="rule_005",
            name="外部API调用",
            description="调用外部API的操作",
            operation_patterns=[r".*api.*call.*", r".*http.*request.*", r".*webhook.*"],
            operation_category=OperationCategory.EXTERNAL_CALL,
            required_risk_level=RiskLevel.MEDIUM,
            requires_approval=True,
            approver_role="security"
        ))
    
    def add_rule(self, rule: ApprovalRule) -> None:
        """添加规则"""
        self._rules.append(rule)
    
    def remove_rule(self, rule_id: str) -> bool:
        """移除规则"""
        for i, rule in enumerate(self._rules):
            if rule.rule_id == rule_id:
                del self._rules[i]
                return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[ApprovalRule]:
        """获取规则"""
        for rule in self._rules:
            if rule.rule_id == rule_id:
                return rule
        return None
    
    def get_matching_rules(
        self,
        operation_type: str
    ) -> List[ApprovalRule]:
        """获取匹配的规则"""
        return [r for r in self._rules if r.enabled and r.matches(operation_type)]
    
    def get_rules_by_category(
        self,
        category: OperationCategory
    ) -> List[ApprovalRule]:
        """按类别获取规则"""
        return [r for r in self._rules if r.operation_category == category]
    
    def set_default_risk_level(self, level: RiskLevel) -> None:
        """设置默认风险等级"""
        self._default_risk_level = level
    
    def set_risk_threshold(self, level: RiskLevel, threshold: float) -> None:
        """设置风险阈值"""
        self._risk_thresholds[level] = threshold
    
    def evaluate_operation(
        self,
        operation_type: str,
        operation_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> RiskAssessment:
        """
        评估操作风险
        
        Args:
            operation_type: 操作类型
            operation_data: 操作数据
            context: 上下文信息
            
        Returns:
            RiskAssessment: 风险评估结果
        """
        matching_rules = self.get_matching_rules(operation_type)
        factors = []
        score = 0
        recommendations = []
        suggested_approvers: Set[str] = set()
        
        # 计算风险分数
        if matching_rules:
            for rule in matching_rules:
                # 基于风险等级加分
                level_scores = {
                    RiskLevel.LOW: 10,
                    RiskLevel.MEDIUM: 30,
                    RiskLevel.HIGH: 60,
                    RiskLevel.CRITICAL: 90
                }
                score = max(score, level_scores.get(rule.required_risk_level, 30))
                
                factors.append(f"Matched rule: {rule.name}")
                
                if rule.approvers:
                    suggested_approvers.update(rule.approvers)
                if rule.approver_role:
                    suggested_approvers.add(rule.approver_role)
        
        # 分析操作数据
        data_factors = self._analyze_operation_data(operation_data)
        factors.extend(data_factors["factors"])
        score += data_factors["score_delta"]
        recommendations.extend(data_factors["recommendations"])
        
        # 分析上下文
        if context:
            context_factors = self._analyze_context(context)
            factors.extend(context_factors["factors"])
            score += context_factors["score_delta"]
        
        # 确保分数在有效范围内
        score = min(100, max(0, score))
        
        # 确定风险等级
        risk_level = self._calculate_risk_level(score)
        
        # 评估是否需要审批
        requires_approval = score >= self._risk_thresholds[RiskLevel.MEDIUM] or bool(matching_rules)
        
        return RiskAssessment(
            risk_level=risk_level,
            score=score,
            factors=factors,
            recommendations=recommendations,
            requires_approval=requires_approval,
            suggested_approvers=list(suggested_approvers)
        )
    
    def _analyze_operation_data(
        self,
        operation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析操作数据"""
        factors = []
        score_delta = 0
        recommendations = []
        
        # 检查数据大小
        if "data_size" in operation_data:
            size = operation_data["data_size"]
            if size > 10000:
                score_delta += 10
                factors.append(f"Large data size: {size}")
        
        # 检查是否包含敏感字段
        sensitive_fields = ["password", "secret", "token", "key", "credential"]
        for field in sensitive_fields:
            if any(field in str(k).lower() for k in operation_data.keys()):
                score_delta += 15
                factors.append(f"Sensitive field detected: {field}")
                recommendations.append("Consider masking sensitive data")
        
        # 检查操作范围
        if "scope" in operation_data:
            scope = operation_data["scope"]
            if scope in ["all", "global", "system"]:
                score_delta += 20
                factors.append(f"Global scope operation: {scope}")
        
        return {
            "factors": factors,
            "score_delta": score_delta,
            "recommendations": recommendations
        }
    
    def _analyze_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析上下文"""
        factors = []
        score_delta = 0
        
        # 检查时间因素
        if "hour" in context:
            hour = context["hour"]
            if hour < 6 or hour > 22:
                score_delta += 5
                factors.append("Operation outside business hours")
        
        # 检查频率
        if "frequency" in context:
            freq = context["frequency"]
            if freq > 10:
                score_delta += 10
                factors.append(f"High frequency operation: {freq}")
        
        return {
            "factors": factors,
            "score_delta": score_delta
        }
    
    def _calculate_risk_level(self, score: float) -> RiskLevel:
        """计算风险等级"""
        if score >= self._risk_thresholds[RiskLevel.CRITICAL]:
            return RiskLevel.CRITICAL
        elif score >= self._risk_thresholds[RiskLevel.HIGH]:
            return RiskLevel.HIGH
        elif score >= self._risk_thresholds[RiskLevel.MEDIUM]:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def export_rules(self) -> List[Dict[str, Any]]:
        """导出规则"""
        return [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "description": r.description,
                "operation_patterns": r.operation_patterns,
                "operation_category": r.operation_category.value,
                "required_risk_level": r.required_risk_level.value,
                "requires_approval": r.requires_approval,
                "approvers": r.approvers,
                "approver_role": r.approver_role,
                "priority_boost": r.priority_boost,
                "conditions": r.conditions,
                "enabled": r.enabled
            }
            for r in self._rules
        ]


class PolicyEngine:
    """
    策略引擎
    
    负责策略的匹配和执行。
    """
    
    def __init__(self, policy: Optional[ApprovalPolicy] = None):
        """
        初始化策略引擎
        
        Args:
            policy: 审批策略
        """
        self.policy = policy or ApprovalPolicy()
        self._custom_evaluators: Dict[str, Callable] = {}
    
    def register_evaluator(
        self,
        name: str,
        evaluator: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        """
        注册自定义评估器
        
        Args:
            name: 评估器名称
            evaluator: 评估函数
        """
        self._custom_evaluators[name] = evaluator
    
    def evaluate(
        self,
        operation_type: str,
        operation_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> RiskAssessment:
        """
        评估操作
        
        Args:
            operation_type: 操作类型
            operation_data: 操作数据
            context: 上下文
            
        Returns:
            RiskAssessment: 风险评估
        """
        # 使用策略评估
        assessment = self.policy.evaluate_operation(
            operation_type,
            operation_data,
            context
        )
        
        # 应用自定义评估器
        for evaluator in self._custom_evaluators.values():
            custom_result = evaluator({
                "operation_type": operation_type,
                "operation_data": operation_data,
                "context": context,
                "current_assessment": assessment.to_dict()
            })
            
            # 合并结果
            if custom_result:
                assessment.score = min(100, assessment.score + custom_result.get("score_delta", 0))
                assessment.factors.extend(custom_result.get("factors", []))
                assessment.recommendations.extend(custom_result.get("recommendations", []))
        
        return assessment
    
    def should_require_approval(
        self,
        operation_type: str,
        operation_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        判断是否需要审批
        
        Args:
            operation_type: 操作类型
            operation_data: 操作数据
            context: 上下文
            
        Returns:
            bool: 是否需要审批
        """
        assessment = self.evaluate(operation_type, operation_data, context)
        return assessment.requires_approval
