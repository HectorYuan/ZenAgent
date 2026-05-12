"""
规则执行器 (Rule Executor)

基于向前链推理(Forward Chaining)的规则执行引擎。
使用Rete算法优化实现，支持并行执行和条件缓存。
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
import hashlib
import json

from .rule_parser import Rule, RuleCondition, RuleAction, RuleType, RuleParseResult

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"


@dataclass
class ExecutionContext:
    """执行上下文"""
    data: Dict[str, Any]
    working_memory: Dict[str, Any] = field(default_factory=dict)
    facts: Set[Any] = field(default_factory=set)
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """获取值(支持嵌套路径)"""
        keys = key.split('.')
        value = self.data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value
    
    def set_value(self, key: str, value: Any):
        """设置值(支持嵌套路径)"""
        keys = key.split('.')
        current = self.data
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value


@dataclass
class ExecutionResult:
    """执行结果"""
    rule_id: str
    rule_name: str
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    actions_executed: List[Dict[str, Any]] = field(default_factory=list)
    conditions_matched: int = 0
    conditions_total: int = 0
    error_message: Optional[str] = None
    output_data: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS


class ReteNode:
    """Rete网络节点基类"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.children: List['ReteNode'] = []
        self.activations: List[Any] = []
    
    def add_child(self, child: 'ReteNode'):
        self.children.append(child)
    
    def activate(self, token: Any):
        raise NotImplementedError


class AlphaNode(ReteNode):
    """Alpha节点 - 测试单条件"""
    
    def __init__(self, node_id: str, condition: RuleCondition):
        super().__init__(node_id)
        self.condition = condition
    
    def test(self, context: ExecutionContext) -> bool:
        """测试条件是否满足"""
        return self.condition.evaluate(context.data)


class BetaNode(ReteNode):
    """Beta节点 - 连接两个子节点"""
    
    def __init__(self, node_id: str, left: ReteNode, right: ReteNode):
        super().__init__(node_id)
        self.left = left
        self.right = right
        left.add_child(self)
        right.add_child(self)
        self.join_memory: Dict[str, List[Any]] = defaultdict(list)
    
    def activate(self, token: Any):
        """激活节点"""
        other_activations = self.join_memory.get('other', [])
        for other_token in other_activations:
            combined = self._combine_tokens(token, other_token)
            if combined:
                for child in self.children:
                    child.activate(combined)
    
    def _combine_tokens(self, token1: Any, token2: Any) -> Optional[Any]:
        """合并token"""
        if isinstance(token1, dict) and isinstance(token2, dict):
            return {**token1, **token2}
        return (token1, token2)


class TerminalNode(ReteNode):
    """终端节点 - 触发规则执行"""
    
    def __init__(self, node_id: str, rule: Rule, executor: 'RuleExecutor'):
        super().__init__(node_id)
        self.rule = rule
        self.executor = executor
    
    def activate(self, token: Any):
        """激活规则"""
        asyncio.create_task(self.executor.execute_rule(self.rule, token))


class RuleExecutor:
    """
    规则执行器
    
    使用Rete算法实现高效的规则匹配和执行。
    支持同步/异步执行，条件缓存和并行执行。
    
    性能优化:
    - Alpha节点索引快速查找
    - 条件短路评估(快速失败)
    - 并行执行支持
    - 条件结果缓存
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.rules: Dict[str, Rule] = {}
        self.rete_network: Dict[str, ReteNode] = {}
        self.alpha_memory: Dict[str, Any] = {}  # Alpha节点记忆
        self.beta_memory: Dict[str, Any] = {}   # Beta节点记忆
        
        # 性能优化：条件索引
        self.condition_index: Dict[str, Dict[str, List[str]]] = {}  # field -> operator -> [rule_ids]
        self.field_values_index: Dict[str, Dict[Any, List[str]]] = {}  # field -> value -> [rule_ids]
        
        # 性能优化：条件结果缓存
        self.condition_cache: Dict[str, bool] = {}
        self.condition_cache_max_size = self.config.get('condition_cache_size', 10000)
        
        # 执行配置
        self.max_parallel_execution = self.config.get('max_parallel', 10)
        self.execution_timeout = self.config.get('timeout', 30)
        self.enable_caching = self.config.get('enable_caching', True)
        
        # 执行钩子
        self.pre_execution_hooks: List[Callable] = []
        self.post_execution_hooks: List[Callable] = []
        
        # 执行统计
        self.stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'skipped_executions': 0,
            'avg_execution_time_ms': 0,
            'condition_cache_hits': 0,
            'condition_cache_misses': 0,
            'index_hits': 0,
            'short_circuit_count': 0
        }
    
    def _build_condition_index(self, rule: Rule):
        """构建条件索引用于快速查找"""
        for idx, condition in enumerate(rule.conditions):
            field = condition.field
            operator = condition.operator
            
            # 按 field + operator 索引
            if field not in self.condition_index:
                self.condition_index[field] = {}
            if operator not in self.condition_index[field]:
                self.condition_index[field][operator] = []
            if rule.id not in self.condition_index[field][operator]:
                self.condition_index[field][operator].append(rule.id)
    
    def _build_field_value_index(self, rule: Rule):
        """构建字段值索引用于快速匹配"""
        for idx, condition in enumerate(rule.conditions):
            field = condition.field
            # 对常量值建立索引
            if hasattr(condition, 'value') and not callable(condition.value):
                value = condition.value
                if field not in self.field_values_index:
                    self.field_values_index[field] = {}
                if value not in self.field_values_index[field]:
                    self.field_values_index[field][value] = []
                if rule.id not in self.field_values_index[field][value]:
                    self.field_values_index[field][value].append(rule.id)
    
    def _get_candidate_rules_fast(self, context_data: Dict[str, Any]) -> List[str]:
        """使用索引快速获取候选规则"""
        candidates = set()
        
        # 遍历上下文数据中的字段
        for field, value in context_data.items():
            # 检查字段值索引
            if field in self.field_values_index:
                for indexed_value, rule_ids in self.field_values_index[field].items():
                    # 值相等或范围包含
                    if indexed_value == value or self._is_value_in_range(value, indexed_value):
                        candidates.update(rule_ids)
                        self.stats['index_hits'] += 1
            
            # 检查操作符索引
            if field in self.condition_index:
                for operator, rule_ids in self.condition_index[field].items():
                    # 如果上下文有这个字段的值，参与比较
                    if value is not None:
                        candidates.update(rule_ids)
        
        return list(candidates)
    
    def _is_value_in_range(self, value: Any, condition_value: Any) -> bool:
        """检查值是否在条件范围内"""
        if isinstance(condition_value, (int, float)):
            return isinstance(value, (int, float))
        return False
    
    def _get_condition_cache_key(self, condition: RuleCondition, data: Dict[str, Any]) -> str:
        """生成条件缓存键"""
        value = data.get(condition.field, '<MISSING>')
        return f"{condition.field}:{condition.operator}:{condition.value}:{value}"
    
    def add_rule(self, rule: Rule) -> bool:
        """
        添加规则到执行器
        
        Args:
            rule: 规则对象
            
        Returns:
            bool: 添加是否成功
        """
        try:
            # 验证规则
            if not self._validate_rule(rule):
                return False
            
            # 添加到规则库
            self.rules[rule.id] = rule
            
            # 构建Rete网络
            self._build_rete_network(rule)
            
            # 构建性能优化索引
            self._build_condition_index(rule)
            self._build_field_value_index(rule)
            
            logger.info(f"Rule added: {rule.id} - {rule.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add rule {rule.id}: {e}")
            return False
    
    def remove_rule(self, rule_id: str) -> bool:
        """移除规则"""
        if rule_id not in self.rules:
            return False
        
        del self.rules[rule_id]
        
        # 清理Rete网络
        if rule_id in self.rete_network:
            del self.rete_network[rule_id]
        
        return True
    
    def _validate_rule(self, rule: Rule) -> bool:
        """验证规则"""
        if not rule.name:
            logger.error("Rule name is required")
            return False
        if not rule.conditions and not rule.actions:
            logger.warning(f"Rule {rule.id} has no conditions or actions")
        return True
    
    def _build_rete_network(self, rule: Rule):
        """构建Rete网络"""
        if not rule.conditions:
            # 无条件规则，直接创建终端节点
            terminal = TerminalNode(f"terminal_{rule.id}", rule, self)
            self.rete_network[rule.id] = terminal
            return
        
        # 创建Alpha节点链
        alpha_nodes = []
        for idx, condition in enumerate(rule.conditions):
            alpha = AlphaNode(f"alpha_{rule.id}_{idx}", condition)
            alpha_nodes.append(alpha)
            self.alpha_memory[alpha.node_id] = None
        
        # 创建Beta节点连接
        if len(alpha_nodes) == 1:
            current = alpha_nodes[0]
        else:
            # 逐个连接Alpha节点
            current = BetaNode(
                f"beta_{rule.id}_0",
                alpha_nodes[0],
                alpha_nodes[1]
            )
            self.beta_memory[current.node_id] = []
            
            for idx in range(2, len(alpha_nodes)):
                new_beta = BetaNode(
                    f"beta_{rule.id}_{idx-1}",
                    current,
                    alpha_nodes[idx]
                )
                self.beta_memory[new_beta.node_id] = []
                current = new_beta
        
        # 创建终端节点
        terminal = TerminalNode(f"terminal_{rule.id}", rule, self)
        current.add_child(terminal)
        self.rete_network[rule.id] = terminal
    
    async def execute_rule(self, rule: Rule, context_data: Any = None) -> ExecutionResult:
        """
        执行单条规则
        
        Args:
            rule: 规则对象
            context_data: 执行上下文数据
            
        Returns:
            ExecutionResult: 执行结果
        """
        start_time = datetime.now()
        result = ExecutionResult(
            rule_id=rule.id,
            rule_name=rule.name,
            status=ExecutionStatus.PENDING,
            start_time=start_time,
            conditions_total=len(rule.conditions)
        )
        
        # 检查规则是否启用
        if not rule.enabled:
            result.status = ExecutionStatus.SKIPPED
            result.end_time = datetime.now()
            return result
        
        try:
            # 构建执行上下文
            if context_data is None:
                context_data = {}
            context = ExecutionContext(data=context_data)
            
            # 执行前置钩子
            for hook in self.pre_execution_hooks:
                await hook(rule, context)
            
            # 评估条件
            conditions_met = await self._evaluate_conditions(rule.conditions, context)
            result.conditions_matched = sum(1 for met in conditions_met if met)
            
            if not all(conditions_met):
                result.status = ExecutionStatus.SKIPPED
                result.end_time = datetime.now()
                return result
            
            # 执行动作
            for action in rule.actions:
                action_result = await self._execute_action(action, context)
                result.actions_executed.append(action_result)
            
            result.status = ExecutionStatus.SUCCESS
            result.output_data = context.data
            
            # 执行后置钩子
            for hook in self.post_execution_hooks:
                await hook(rule, context, result)
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            logger.error(f"Rule execution failed: {rule.id} - {e}")
        
        result.end_time = datetime.now()
        result.execution_time_ms = (result.end_time - start_time).total_seconds() * 1000
        
        # 更新统计
        self._update_stats(result)
        
        return result
    
    async def _evaluate_conditions(
        self, 
        conditions: List[RuleCondition], 
        context: ExecutionContext
    ) -> List[bool]:
        """
        评估条件列表
        
        优化特性:
        - 短路评估: 一旦条件失败立即返回
        - 条件缓存: 避免重复评估相同的条件
        - 并行评估: 可配置的并行评估模式
        """
        results = []
        
        for condition in conditions:
            try:
                # 尝试从缓存获取结果
                if self.enable_caching:
                    cache_key = self._get_condition_cache_key(condition, context.data)
                    if cache_key in self.condition_cache:
                        met = self.condition_cache[cache_key]
                        self.stats['condition_cache_hits'] += 1
                        results.append(met)
                        # 短路: 如果缓存中为False，后续条件无需评估
                        if not met:
                            self.stats['short_circuit_count'] += 1
                            # 填充剩余条件为False
                            results.extend([False] * (len(conditions) - len(results)))
                            break
                        continue
                    else:
                        self.stats['condition_cache_misses'] += 1
                
                # 执行条件评估
                met = condition.evaluate(context.data)
                results.append(met)
                
                # 缓存结果
                if self.enable_caching:
                    self.condition_cache[cache_key] = met
                    # 缓存大小控制
                    if len(self.condition_cache) > self.condition_cache_max_size:
                        # 简单策略: 删除最旧的1/3条目
                        keys_to_remove = list(self.condition_cache.keys())[:self.condition_cache_max_size // 3]
                        for key in keys_to_remove:
                            del self.condition_cache[key]
                
                # 短路评估优化
                if not met:
                    self.stats['short_circuit_count'] += 1
                    # 填充剩余条件为False (避免后续评估)
                    results.extend([False] * (len(conditions) - len(results)))
                    break
                    
            except Exception as e:
                logger.warning(f"Condition evaluation error: {e}")
                results.append(False)
                # 短路: 评估失败也停止后续条件评估
                results.extend([False] * (len(conditions) - len(results)))
                break
        
        return results
    
    async def _execute_action(
        self, 
        action: RuleAction, 
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """执行动作"""
        action_result = {
            'type': action.action_type,
            'parameters': action.parameters,
            'success': False,
            'output': None,
            'error': None
        }
        
        try:
            # 根据动作类型执行
            handler = self._action_handlers.get(action.action_type)
            if handler:
                output = await handler(action.parameters, context)
                action_result['output'] = output
                action_result['success'] = True
            else:
                action_result['error'] = f"Unknown action type: {action.action_type}"
                
        except Exception as e:
            action_result['error'] = str(e)
            logger.error(f"Action execution error: {action.action_type} - {e}")
        
        return action_result
    
    # 动作处理器注册表
    _action_handlers: Dict[str, Callable] = {}
    
    @classmethod
    def register_action_handler(cls, action_type: str, handler: Callable):
        """注册动作处理器"""
        cls._action_handlers[action_type] = handler
    
    async def execute_batch(
        self, 
        rules: List[Rule], 
        context_data: Dict[str, Any]
    ) -> List[ExecutionResult]:
        """批量执行规则"""
        results = []
        
        # 使用信号量控制并行度
        semaphore = asyncio.Semaphore(self.max_parallel_execution)
        
        async def execute_with_limit(rule: Rule):
            async with semaphore:
                return await self.execute_rule(rule, context_data)
        
        # 创建任务
        tasks = [execute_with_limit(rule) for rule in rules]
        
        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ExecutionResult(
                    rule_id=rules[idx].id,
                    rule_name=rules[idx].name,
                    status=ExecutionStatus.FAILED,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def execute_fire_all(
        self, 
        context_data: Dict[str, Any],
        rule_filter: Optional[Callable[[Rule], bool]] = None
    ) -> List[ExecutionResult]:
        """触发所有匹配规则的执行"""
        context = ExecutionContext(data=context_data)
        
        # 筛选要执行的规则
        rules_to_execute = []
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            if rule_filter and not rule_filter(rule):
                continue
            rules_to_execute.append(rule)
        
        # 按优先级排序
        rules_to_execute.sort(key=lambda r: r.priority, reverse=True)
        
        # 异步执行
        return asyncio.run(self.execute_batch(rules_to_execute, context_data))
    
    def _update_stats(self, result: ExecutionResult):
        """更新执行统计"""
        self.stats['total_executions'] += 1
        
        if result.status == ExecutionStatus.SUCCESS:
            self.stats['successful_executions'] += 1
        elif result.status == ExecutionStatus.FAILED:
            self.stats['failed_executions'] += 1
        elif result.status == ExecutionStatus.SKIPPED:
            self.stats['skipped_executions'] += 1
        
        # 计算平均执行时间
        total = self.stats['total_executions']
        current_avg = self.stats['avg_execution_time_ms']
        self.stats['avg_execution_time_ms'] = (
            (current_avg * (total - 1) + result.execution_time_ms) / total
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        return self.stats.copy()
    
    def get_matching_rules(self, context_data: Dict[str, Any]) -> List[Rule]:
        """获取匹配当前上下文的规则"""
        context = ExecutionContext(data=context_data)
        matching = []
        
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            conditions_met = asyncio.run(
                self._evaluate_conditions(rule.conditions, context)
            )
            
            if all(conditions_met):
                matching.append(rule)
        
        return matching


# 注册默认动作处理器
async def _default_allocate_handler(params: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
    """默认资源分配处理器"""
    resource_type = params.get('resource_type', 'generic')
    amount = params.get('amount', 1)
    
    # 更新工作内存
    allocation_id = hashlib.md5(
        json.dumps({'type': resource_type, 'amount': amount}, sort_keys=True).encode()
    ).hexdigest()[:8]
    
    context.working_memory[f'allocation_{allocation_id}'] = {
        'type': resource_type,
        'amount': amount,
        'timestamp': datetime.now().isoformat()
    }
    
    return {'allocation_id': allocation_id, 'resource_type': resource_type}


async def _default_notify_handler(params: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
    """默认通知处理器"""
    message = params.get('message', '')
    recipients = params.get('recipients', [])
    
    logger.info(f"Notification: {message} -> {recipients}")
    
    return {'sent': True, 'recipient_count': len(recipients)}


async def _default_transform_handler(params: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
    """默认数据转换处理器"""
    field = params.get('field')
    transform = params.get('transform', 'uppercase')
    value = context.get_value(field)
    
    if value is None:
        return {'original': None, 'transformed': None}
    
    if transform == 'uppercase':
        transformed = str(value).upper()
    elif transform == 'lowercase':
        transformed = str(value).lower()
    elif transform == 'md5':
        transformed = hashlib.md5(str(value).encode()).hexdigest()
    else:
        transformed = value
    
    # 更新上下文
    context.set_value(field, transformed)
    
    return {'original': value, 'transformed': transformed}


# 注册默认处理器
RuleExecutor.register_action_handler('allocate_resources', _default_allocate_handler)
RuleExecutor.register_action_handler('notify', _default_notify_handler)
RuleExecutor.register_action_handler('transform', _default_transform_handler)
