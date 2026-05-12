"""
规则解析器 (Rule Parser)

支持YAML/JSON格式的规则定义，解析为内部规则对象。
使用PyYAML进行YAML解析，JSON Schema进行规则验证。
"""

import json
import yaml
import hashlib
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re


class RuleType(Enum):
    """规则类型枚举"""
    COLLABORATION = "collaboration"        # 协作规则
    RESOURCE = "resource"                  # 资源规则
    SECURITY = "security"                 # 安全规则
    EVOLUTION = "evolution"                # 进化规则
    CUSTOM = "custom"                      # 自定义规则


class ConditionOperator(Enum):
    """条件操作符"""
    EQ = "eq"              # 等于
    NE = "ne"              # 不等于
    GT = "gt"              # 大于
    GE = "ge"              # 大于等于
    LT = "lt"              # 小于
    LE = "le"              # 小于等于
    IN = "in"              # 包含
    NOT_IN = "not_in"      # 不包含
    CONTAINS = "contains"  # 字符串包含
    MATCHES = "matches"    # 正则匹配
    AND = "and"             # 逻辑与
    OR = "or"              # 逻辑或
    NOT = "not"            # 逻辑非


@dataclass
class RuleCondition:
    """规则条件"""
    field: str
    operator: ConditionOperator
    value: Any
    logical_group: Optional[str] = None
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """评估条件是否满足"""
        context_value = self._get_nested_value(context, self.field)
        
        if context_value is None:
            return False
        
        return self._compare(context_value, self.operator, self.value)
    
    def _get_nested_value(self, obj: Any, path: str) -> Any:
        """获取嵌套属性值"""
        keys = path.split('.')
        value = obj
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif hasattr(value, key):
                value = getattr(value, key)
            else:
                return None
            if value is None:
                return None
        return value
    
    def _compare(self, left: Any, op: ConditionOperator, right: Any) -> bool:
        """执行比较操作"""
        if op == ConditionOperator.EQ:
            return left == right
        elif op == ConditionOperator.NE:
            return left != right
        elif op == ConditionOperator.GT:
            return left > right
        elif op == ConditionOperator.GE:
            return left >= right
        elif op == ConditionOperator.LT:
            return left < right
        elif op == ConditionOperator.LE:
            return left <= right
        elif op == ConditionOperator.IN:
            return left in right if isinstance(right, (list, tuple, set)) else False
        elif op == ConditionOperator.NOT_IN:
            return left not in right if isinstance(right, (list, tuple, set)) else True
        elif op == ConditionOperator.CONTAINS:
            return str(right) in str(left)
        elif op == ConditionOperator.MATCHES:
            return bool(re.match(str(right), str(left)))
        else:
            return False


@dataclass
class RuleAction:
    """规则动作"""
    action_type: str
    parameters: Dict[str, Any]
    priority: int = 0
    condition: Optional[str] = None  # 执行条件表达式


@dataclass
class Rule:
    """规则对象"""
    id: str
    name: str
    description: str
    version: str
    rule_type: RuleType
    conditions: List[RuleCondition] = field(default_factory=list)
    actions: List[RuleAction] = field(default_factory=list)
    priority: int = 50  # 默认优先级 0-100
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    author: str = "system"
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他规则ID
    
    def __post_init__(self):
        """后置初始化"""
        if isinstance(self.rule_type, str):
            self.rule_type = RuleType(self.rule_type)
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """生成规则ID"""
        content = f"{self.name}:{self.version}:{self.created_at.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get_checksum(self) -> str:
        """获取规则校验和"""
        content = json.dumps({
            'name': self.name,
            'version': self.version,
            'rule_type': self.rule_type.value,
            'conditions': [(c.field, c.operator.value, c.value) for c in self.conditions],
            'actions': [(a.action_type, a.parameters) for a in self.actions],
            'priority': self.priority
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class RuleParseResult:
    """规则解析结果"""
    success: bool
    rules: List[Rule] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RuleParser:
    """
    规则解析器
    
    支持从YAML/JSON格式解析规则定义，验证规则语法，
    并转换为内部Rule对象。
    """
    
    SUPPORTED_FORMATS = ['yaml', 'json']
    
    # YAML规则模板示例
    RULE_TEMPLATE = """
# SwarmFly规则定义示例
rule_id: collaboration_agent_priority
name: 智能体优先级协作规则
description: 根据智能体优先级协调任务分配
version: "1.0"
type: collaboration
priority: 80
enabled: true
tags:
  - collaboration
  - priority
conditions:
  - field: agent.priority
    operator: ge
    value: 50
  - field: task.urgent
    operator: eq
    value: true
actions:
  - type: allocate_resources
    parameters:
      cpu: 2
      memory: 4096
    priority: 10
"""
    
    def __init__(self):
        self.operators = {op.value: op for op in ConditionOperator}
        self.rule_types = {rt.value: rt for rt in RuleType}
    
    def parse(self, content: str, format: Optional[str] = None) -> RuleParseResult:
        """
        解析规则内容
        
        Args:
            content: 规则定义内容(YAML或JSON字符串)
            format: 格式类型，'yaml'或'json'，如果为None则自动检测
            
        Returns:
            RuleParseResult: 解析结果
        """
        result = RuleParseResult(success=False)
        
        try:
            # 自动检测格式
            if format is None:
                format = self._detect_format(content)
            
            # 解析内容
            if format == 'yaml':
                data = yaml.safe_load(content)
            elif format == 'json':
                data = json.loads(content)
            else:
                result.errors.append(f"Unsupported format: {format}")
                return result
            
            # 处理单个规则或规则列表
            if isinstance(data, dict):
                data = [data]
            
            # 解析每个规则
            for idx, rule_data in enumerate(data):
                try:
                    rule = self._parse_single_rule(rule_data)
                    result.rules.append(rule)
                except Exception as e:
                    result.errors.append(f"Rule {idx}: {str(e)}")
            
            result.success = len(result.errors) == 0
            
        except Exception as e:
            result.errors.append(f"Parse error: {str(e)}")
        
        return result
    
    def _detect_format(self, content: str) -> str:
        """检测内容格式"""
        content = content.strip()
        if content.startswith('{') or content.startswith('['):
            return 'json'
        return 'yaml'
    
    def _parse_single_rule(self, data: Dict[str, Any]) -> Rule:
        """解析单个规则"""
        # 验证必需字段
        required_fields = ['name', 'type']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # 解析规则类型
        rule_type = self.rule_types.get(data.get('type', 'custom'))
        if rule_type is None:
            raise ValueError(f"Invalid rule type: {data.get('type')}")
        
        # 解析条件
        conditions = []
        for cond_data in data.get('conditions', []):
            condition = self._parse_condition(cond_data)
            conditions.append(condition)
        
        # 解析动作
        actions = []
        for action_data in data.get('actions', []):
            action = self._parse_action(action_data)
            actions.append(action)
        
        # 创建规则对象
        rule = Rule(
            id=data.get('rule_id', ''),
            name=data['name'],
            description=data.get('description', ''),
            version=data.get('version', '1.0.0'),
            rule_type=rule_type,
            conditions=conditions,
            actions=actions,
            priority=data.get('priority', 50),
            enabled=data.get('enabled', True),
            tags=data.get('tags', []),
            metadata=data.get('metadata', {}),
            author=data.get('author', 'system'),
            dependencies=data.get('dependencies', [])
        )
        
        return rule
    
    def _parse_condition(self, data: Dict[str, Any]) -> RuleCondition:
        """解析规则条件"""
        operator_str = data.get('operator', 'eq')
        operator = self.operators.get(operator_str)
        if operator is None:
            raise ValueError(f"Invalid operator: {operator_str}")
        
        return RuleCondition(
            field=data['field'],
            operator=operator,
            value=data['value'],
            logical_group=data.get('logical_group')
        )
    
    def _parse_action(self, data: Dict[str, Any]) -> RuleAction:
        """解析规则动作"""
        return RuleAction(
            action_type=data['type'],
            parameters=data.get('parameters', {}),
            priority=data.get('priority', 0),
            condition=data.get('condition')
        )
    
    def validate_schema(self, data: Dict[str, Any]) -> List[str]:
        """
        验证规则数据是否符合Schema
        
        Returns:
            List[str]: 验证错误列表，空列表表示验证通过
        """
        errors = []
        
        # 必需字段检查
        if 'name' not in data:
            errors.append("Missing required field: name")
        if 'type' not in data:
            errors.append("Missing required field: type")
        
        # 类型检查
        if 'type' in data and data['type'] not in self.rule_types:
            errors.append(f"Invalid type: {data['type']}")
        
        # 优先级检查
        if 'priority' in data:
            priority = data['priority']
            if not isinstance(priority, int) or priority < 0 or priority > 100:
                errors.append("Priority must be integer between 0 and 100")
        
        # 条件格式检查
        for idx, cond in enumerate(data.get('conditions', [])):
            if 'field' not in cond:
                errors.append(f"Condition {idx}: missing 'field'")
            if 'operator' not in cond:
                errors.append(f"Condition {idx}: missing 'operator'")
            elif cond['operator'] not in self.operators:
                errors.append(f"Condition {idx}: invalid operator '{cond['operator']}'")
            if 'value' not in cond:
                errors.append(f"Condition {idx}: missing 'value'")
        
        # 动作格式检查
        for idx, action in enumerate(data.get('actions', [])):
            if 'type' not in action:
                errors.append(f"Action {idx}: missing 'type'")
        
        return errors
    
    def parse_from_file(self, file_path: str) -> RuleParseResult:
        """从文件解析规则"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return self.parse(content)
    
    def generate_template(self, format: str = 'yaml') -> str:
        """生成规则模板"""
        if format == 'yaml':
            return self.RULE_TEMPLATE
        elif format == 'json':
            return json.dumps(yaml.safe_load(self.RULE_TEMPLATE), indent=2)
        return self.RULE_TEMPLATE


class RuleGraph:
    """规则依赖图"""
    
    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self.dependencies: Dict[str, Set[str]] = {}
        self.dependents: Dict[str, Set[str]] = {}
    
    def add_rule(self, rule: Rule):
        """添加规则到依赖图"""
        self.rules[rule.id] = rule
        self.dependencies[rule.id] = set(rule.dependencies)
        
        # 更新反向依赖
        for dep_id in rule.dependencies:
            if dep_id not in self.dependents:
                self.dependents[dep_id] = set()
            self.dependents[dep_id].add(rule.id)
    
    def get_execution_order(self) -> List[str]:
        """获取拓扑排序的执行顺序"""
        visited = set()
        order = []
        
        def dfs(rule_id: str, path: Set[str]):
            if rule_id in path:
                raise ValueError(f"Circular dependency detected: {path}")
            if rule_id in visited:
                return
            
            visited.add(rule_id)
            path.add(rule_id)
            
            for dep_id in self.dependencies.get(rule_id, []):
                dfs(dep_id, path)
            
            path.remove(rule_id)
            order.append(rule_id)
        
        for rule_id in self.rules:
            dfs(rule_id, set())
        
        return order
    
    def find_affected_rules(self, rule_id: str) -> List[str]:
        """查找受影响的规则(依赖该规则的规则)"""
        affected = []
        
        def dfs(current_id: str):
            for dependent_id in self.dependents.get(current_id, []):
                if dependent_id not in affected:
                    affected.append(dependent_id)
                    dfs(dependent_id)
        
        dfs(rule_id)
        return affected
