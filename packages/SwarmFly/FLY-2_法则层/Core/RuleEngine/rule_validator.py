"""
规则验证器 (Rule Validator)

提供规则语法验证、语义验证、冲突检测和依赖验证功能。
确保规则的正确性、一致性和可执行性。
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re

from .rule_parser import Rule, RuleCondition, RuleAction, RuleType, RuleGraph

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """验证级别"""
    SYNTAX = "syntax"           # 语法验证
    SEMANTIC = "semantic"       # 语义验证
    CONFLICT = "conflict"       # 冲突检测
    DEPENDENCY = "dependency"   # 依赖验证


@dataclass
class ValidationError:
    """验证错误"""
    level: ValidationLevel
    rule_id: str
    rule_name: str
    message: str
    field: Optional[str] = None
    position: Optional[Tuple[int, int]] = None
    suggestion: Optional[str] = None


@dataclass
class Conflict:
    """规则冲突"""
    conflict_id: str
    conflict_type: str
    rules_involved: List[str]
    severity: str  # critical, high, medium, low
    description: str
    resolution_suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: ValidationError):
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        self.warnings.append(warning)
    
    def add_conflict(self, conflict: Conflict):
        self.conflicts.append(conflict)


class RuleValidator:
    """
    规则验证器
    
    执行多层次规则验证:
    1. 语法验证: 规则格式、字段完整性
    2. 语义验证: 条件逻辑、动作有效性
    3. 冲突检测: 规则间冲突识别
    4. 依赖验证: 规则依赖关系
    """
    
    # 规则字段约束
    RULE_NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{2,49}$')
    VERSION_PATTERN = re.compile(r'^\d+\.\d+(\.\d+)?$')
    
    # 优先级范围
    MIN_PRIORITY = 0
    MAX_PRIORITY = 100
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.rule_graph = RuleGraph()
        
        # 验证配置
        self.strict_mode = self.config.get('strict_mode', False)
        self.allow_circular_dependency = self.config.get('allow_circular_dependency', False)
        
        # 冲突检测配置
        self.conflict_detection_enabled = self.config.get('conflict_detection', True)
    
    def validate_syntax(self, rule: Rule) -> ValidationResult:
        """
        语法验证
        
        检查规则的语法正确性:
        - 必需字段存在性
        - 字段格式正确性
        - 字段值范围
        """
        result = ValidationResult(is_valid=True)
        
        # 验证规则名称
        if not rule.name:
            result.add_error(ValidationError(
                level=ValidationLevel.SYNTAX,
                rule_id=rule.id,
                rule_name=rule.name or 'unknown',
                message="Rule name is required",
                field="name"
            ))
        elif not self.RULE_NAME_PATTERN.match(rule.name):
            result.add_error(ValidationError(
                level=ValidationLevel.SYNTAX,
                rule_id=rule.id,
                rule_name=rule.name,
                message="Rule name must start with letter, contain only alphanumeric and underscore, 3-50 characters",
                field="name",
                suggestion="Use format: agent_priority_rule"
            ))
        
        # 验证版本格式
        if not rule.version:
            result.add_error(ValidationError(
                level=ValidationLevel.SYNTAX,
                rule_id=rule.id,
                rule_name=rule.name,
                message="Rule version is required",
                field="version"
            ))
        elif not self.VERSION_PATTERN.match(rule.version):
            result.add_error(ValidationError(
                level=ValidationLevel.SYNTAX,
                rule_id=rule.id,
                rule_name=rule.name,
                message="Version must follow semantic versioning (e.g., 1.0, 1.0.0)",
                field="version",
                suggestion="Use format: X.Y or X.Y.Z"
            ))
        
        # 验证优先级范围
        if not (self.MIN_PRIORITY <= rule.priority <= self.MAX_PRIORITY):
            result.add_error(ValidationError(
                level=ValidationLevel.SYNTAX,
                rule_id=rule.id,
                rule_name=rule.name,
                message=f"Priority must be between {self.MIN_PRIORITY} and {self.MAX_PRIORITY}",
                field="priority"
            ))
        
        # 验证条件列表
        if not rule.conditions:
            result.add_warning(f"Rule '{rule.name}' has no conditions - will always execute")
        
        for idx, condition in enumerate(rule.conditions):
            cond_error = self._validate_condition(condition, idx)
            if cond_error:
                result.add_error(cond_error)
        
        # 验证动作列表
        if not rule.actions:
            result.add_error(ValidationError(
                level=ValidationLevel.SYNTAX,
                rule_id=rule.id,
                rule_name=rule.name,
                message="Rule must have at least one action",
                field="actions"
            ))
        
        for idx, action in enumerate(rule.actions):
            action_error = self._validate_action(action, idx)
            if action_error:
                result.add_error(action_error)
        
        return result
    
    def _validate_condition(self, condition: RuleCondition, index: int) -> Optional[ValidationError]:
        """验证单个条件"""
        if not condition.field:
            return ValidationError(
                level=ValidationLevel.SYNTAX,
                rule_id="",
                rule_name="",
                message=f"Condition {index}: field is required",
                field=f"conditions[{index}].field"
            )
        
        # 验证字段路径格式
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$', condition.field):
            return ValidationError(
                level=ValidationLevel.SYNTAX,
                rule_id="",
                rule_name="",
                message=f"Condition {index}: invalid field path format",
                field=f"conditions[{index}].field",
                suggestion="Use dot notation: agent.priority"
            )
        
        if condition.value is None:
            return ValidationError(
                level=ValidationLevel.SYNTAX,
                rule_id="",
                rule_name="",
                message=f"Condition {index}: value is required",
                field=f"conditions[{index}].value"
            )
        
        return None
    
    def _validate_action(self, action: RuleAction, index: int) -> Optional[ValidationError]:
        """验证单个动作"""
        if not action.action_type:
            return ValidationError(
                level=ValidationLevel.SYNTAX,
                rule_id="",
                rule_name="",
                message=f"Action {index}: action_type is required",
                field=f"actions[{index}].type"
            )
        
        # 验证动作类型格式
        if not re.match(r'^[a-z_][a-z0-9_]*$', action.action_type):
            return ValidationError(
                level=ValidationLevel.SYNTAX,
                rule_id="",
                rule_name="",
                message=f"Action {index}: invalid action_type format",
                field=f"actions[{index}].type",
                suggestion="Use lowercase with underscores: allocate_resources"
            )
        
        return None
    
    def validate_semantics(self, rule: Rule, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        语义验证
        
        检查规则的语义正确性:
        - 条件逻辑一致性
        - 动作可行性
        - 引用的字段存在性
        """
        result = ValidationResult(is_valid=True)
        context = context or {}
        
        # 验证条件之间的逻辑关系
        if len(rule.conditions) > 1:
            logical_groups = {}
            for cond in rule.conditions:
                group = cond.logical_group or '_default'
                if group not in logical_groups:
                    logical_groups[group] = []
                logical_groups[group].append(cond)
            
            # 检查同一逻辑组内的条件数量
            for group, conds in logical_groups.items():
                if len(conds) == 1 and group != '_default':
                    result.add_warning(
                        f"Logical group '{group}' contains only one condition"
                    )
        
        # 验证条件引用的字段
        referenced_fields = set()
        for cond in rule.conditions:
            referenced_fields.add(cond.field)
        
        # 验证动作引用的字段
        for action in rule.actions:
            for param_key, param_value in action.parameters.items():
                if isinstance(param_value, str) and '$' in param_value:
                    # 提取变量引用
                    matches = re.findall(r'\$\{?([a-zA-Z][a-zA-Z0-9_.]*)\}?', param_value)
                    referenced_fields.update(matches)
        
        # 检查条件之间的矛盾
        contradictions = self._find_condition_contradictions(rule.conditions)
        for contradiction in contradictions:
            result.add_error(ValidationError(
                level=ValidationLevel.SEMANTIC,
                rule_id=rule.id,
                rule_name=rule.name,
                message=f"Contradictory conditions detected: {contradiction}",
                field="conditions"
            ))
        
        return result
    
    def _find_condition_contradictions(self, conditions: List[RuleCondition]) -> List[str]:
        """检测条件矛盾"""
        contradictions = []
        
        # 按字段分组条件
        by_field: Dict[str, List[RuleCondition]] = {}
        for cond in conditions:
            if cond.field not in by_field:
                by_field[cond.field] = []
            by_field[cond.field].append(cond)
        
        # 检查同一字段内的矛盾
        for field, field_conditions in by_field.items():
            if len(field_conditions) < 2:
                continue
            
            # 检查 x > 10 和 x < 5 这类明显矛盾
            gt_values = []
            lt_values = []
            
            for cond in field_conditions:
                if cond.operator.value in ('gt', 'ge'):
                    gt_values.append(cond.value)
                elif cond.operator.value in ('lt', 'le'):
                    lt_values.append(cond.value)
            
            for gt_val in gt_values:
                for lt_val in lt_values:
                    if gt_val >= lt_val:
                        contradictions.append(
                            f"{field}: condition '>={gt_val}' conflicts with '<{lt_val}'"
                        )
            
            # 检查 x == 1 和 x == 2 这类矛盾
            eq_values = []
            for cond in field_conditions:
                if cond.operator.value == 'eq':
                    eq_values.append(cond.value)
            
            if len(eq_values) > 1 and len(set(eq_values)) > 1:
                contradictions.append(
                    f"{field}: mutually exclusive equality conditions"
                )
        
        return contradictions
    
    def validate_conflicts(self, rules: List[Rule]) -> List[Conflict]:
        """
        冲突检测
        
        检测规则之间的冲突:
        - 优先级冲突
        - 资源竞争冲突
        - 效果冲突
        """
        conflicts = []
        
        for i, rule1 in enumerate(rules):
            for rule2 in rules[i+1:]:
                # 检测相同触发条件的冲突
                rule_conflicts = self._detect_rule_conflicts(rule1, rule2)
                conflicts.extend(rule_conflicts)
        
        return conflicts
    
    def _detect_rule_conflicts(self, rule1: Rule, rule2: Rule) -> List[Conflict]:
        """检测两条规则之间的冲突"""
        conflicts = []
        
        # 检查条件重叠性
        if self._conditions_overlap(rule1.conditions, rule2.conditions):
            # 检查动作冲突
            action_conflicts = self._check_action_conflicts(rule1, rule2)
            conflicts.extend(action_conflicts)
        
        # 检查优先级冲突
        if rule1.priority == rule2.priority and rule1.rule_type == rule2.rule_type:
            conflicts.append(Conflict(
                conflict_id=f"priority_conflict_{rule1.id}_{rule2.id}",
                conflict_type="priority",
                rules_involved=[rule1.id, rule2.id],
                severity="medium",
                description=f"Rules '{rule1.name}' and '{rule2.name}' have same priority",
                resolution_suggestion="Adjust priority values to establish clear precedence"
            ))
        
        return conflicts
    
    def _conditions_overlap(self, conditions1: List[RuleCondition], conditions2: List[RuleCondition]) -> bool:
        """检查条件是否有重叠"""
        fields1 = {c.field for c in conditions1}
        fields2 = {c.field for c in conditions2}
        return bool(fields1 & fields2)
    
    def _check_action_conflicts(self, rule1: Rule, rule2: Rule) -> List[Conflict]:
        """检查动作冲突"""
        conflicts = []
        
        # 获取动作类型
        actions1 = {a.action_type for a in rule1.actions}
        actions2 = {a.action_type for a in rule2.actions}
        
        # 相同动作类型
        common_actions = actions1 & actions2
        
        # 检测资源分配冲突
        if 'allocate_resources' in common_actions:
            resources1 = {a.parameters.get('resource_type') for a in rule1.actions}
            resources2 = {a.parameters.get('resource_type') for a in rule2.actions}
            
            common_resources = resources1 & resources2
            if common_resources:
                conflicts.append(Conflict(
                    conflict_id=f"resource_conflict_{rule1.id}_{rule2.id}",
                    conflict_type="resource",
                    rules_involved=[rule1.id, rule2.id],
                    severity="high",
                    description=f"Both rules allocate same resources: {common_resources}",
                    resolution_suggestion="Use priority-based allocation or split resources"
                ))
        
        # 检测互斥动作
        mutex_pairs = [
            ({'allow', 'deny'}, 'permission'),
            ({'start', 'stop'}, 'lifecycle'),
            ({'scale_up', 'scale_down'}, 'scaling'),
        ]
        
        for action_pair, conflict_type in mutex_pairs:
            if action_pair.issubset(actions1 | actions2):
                conflicts.append(Conflict(
                    conflict_id=f"{conflict_type}_conflict_{rule1.id}_{rule2.id}",
                    conflict_type=conflict_type,
                    rules_involved=[rule1.id, rule2.id],
                    severity="critical",
                    description=f"Mutually exclusive actions detected: {action_pair}",
                    resolution_suggestion="Only one rule should handle this lifecycle stage"
                ))
        
        return conflicts
    
    def validate_dependencies(self, rule: Rule, rule_graph: RuleGraph) -> Tuple[bool, List[str]]:
        """
        依赖验证
        
        检查规则依赖的有效性:
        - 依赖规则是否存在
        - 是否存在循环依赖
        """
        errors = []
        
        # 检查依赖规则是否存在
        for dep_id in rule.dependencies:
            if dep_id not in rule_graph.rules:
                errors.append(f"Dependency rule '{dep_id}' does not exist")
        
        # 检查循环依赖
        if self._has_circular_dependency(rule, rule_graph):
            if not self.allow_circular_dependency:
                errors.append(f"Circular dependency detected involving rule '{rule.id}'")
            else:
                logger.warning(f"Circular dependency detected: {rule.id}")
        
        return len(errors) == 0, errors
    
    def _has_circular_dependency(self, rule: Rule, rule_graph: RuleGraph) -> bool:
        """检查是否存在循环依赖"""
        visited = set()
        path = set()
        
        def dfs(current_id: str) -> bool:
            if current_id in path:
                return True
            if current_id in visited:
                return False
            
            visited.add(current_id)
            path.add(current_id)
            
            current_rule = rule_graph.rules.get(current_id)
            if current_rule:
                for dep_id in current_rule.dependencies:
                    if dfs(dep_id):
                        return True
            
            path.remove(current_id)
            return False
        
        return dfs(rule.id)
    
    def validate_all(self, rules: List[Rule], context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        执行完整验证
        
        对所有规则执行多层次验证:
        1. 语法验证
        2. 语义验证
        3. 冲突检测
        4. 依赖验证
        """
        result = ValidationResult(is_valid=True)
        
        # 更新规则图
        for rule in rules:
            self.rule_graph.add_rule(rule)
        
        # 逐个规则语法验证
        for rule in rules:
            syntax_result = self.validate_syntax(rule)
            if not syntax_result.is_valid:
                result.errors.extend(syntax_result.errors)
            result.warnings.extend(syntax_result.warnings)
        
        # 语义验证
        for rule in rules:
            semantic_result = self.validate_semantics(rule, context)
            if not semantic_result.is_valid:
                result.errors.extend(semantic_result.errors)
            result.warnings.extend(semantic_result.warnings)
        
        # 冲突检测
        if self.conflict_detection_enabled:
            conflicts = self.validate_conflicts(rules)
            result.conflicts.extend(conflicts)
            
            # 严重冲突视为验证失败
            critical_conflicts = [c for c in conflicts if c.severity == 'critical']
            if critical_conflicts:
                result.is_valid = False
        
        # 依赖验证
        for rule in rules:
            dep_valid, dep_errors = self.validate_dependencies(rule, self.rule_graph)
            if not dep_valid:
                for error in dep_errors:
                    result.add_error(ValidationError(
                        level=ValidationLevel.DEPENDENCY,
                        rule_id=rule.id,
                        rule_name=rule.name,
                        message=error
                    ))
        
        # 更新元数据
        result.metadata = {
            'total_rules': len(rules),
            'syntax_errors': sum(1 for e in result.errors if e.level == ValidationLevel.SYNTAX),
            'semantic_errors': sum(1 for e in result.errors if e.level == ValidationLevel.SEMANTIC),
            'dependency_errors': sum(1 for e in result.errors if e.level == ValidationLevel.DEPENDENCY),
            'total_conflicts': len(result.conflicts),
            'critical_conflicts': sum(1 for c in result.conflicts if c.severity == 'critical'),
            'validation_timestamp': datetime.now().isoformat()
        }
        
        return result
