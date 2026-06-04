"""
规则引擎核心模块单元测试

覆盖 RuleParser / RuleExecutor / RuleValidator / RuleCache 四个组件。
"""

import asyncio
import pytest
from datetime import datetime

from packages.SwarmFly.fly2rules.Core.RuleEngine.rule_parser import (
    RuleParser, Rule, RuleCondition, RuleAction, RuleType,
    ConditionOperator, RuleParseResult, RuleGraph,
)
from packages.SwarmFly.fly2rules.Core.RuleEngine.rule_executor import (
    RuleExecutor, ExecutionContext, ExecutionStatus, ExecutionResult,
)
from packages.SwarmFly.fly2rules.Core.RuleEngine.rule_validator import (
    RuleValidator, ValidationLevel, ValidationResult,
)
from packages.SwarmFly.fly2rules.Core.RuleEngine.rule_cache import (
    RuleCache, RuleCacheManager, CacheEntry,
)


# ==================== 辅助工厂 ====================

def _make_rule(**overrides) -> Rule:
    """快速创建一条用于测试的规则"""
    defaults = dict(
        id="test_rule_001",
        name="test_priority_rule",
        description="测试用规则",
        version="1.0",
        rule_type=RuleType.COLLABORATION,
        conditions=[
            RuleCondition(field="agent.priority", operator=ConditionOperator.GE, value=50),
        ],
        actions=[
            RuleAction(action_type="allocate_resources", parameters={"cpu": 2}, priority=10),
        ],
        priority=80,
        enabled=True,
    )
    defaults.update(overrides)
    return Rule(**defaults)


def _yaml_content() -> str:
    return """
name: yaml_test_rule
type: collaboration
version: "1.0"
priority: 70
conditions:
  - field: agent.level
    operator: gt
    value: 3
actions:
  - type: notify
    parameters:
      message: hello
"""


def _json_content() -> str:
    return """{
    "name": "json_test_rule",
    "type": "resource",
    "version": "1.0",
    "priority": 60,
    "conditions": [
        {"field": "cpu.usage", "operator": "lt", "value": 80}
    ],
    "actions": [
        {"type": "allocate_resources", "parameters": {"memory": 512}}
    ]
}"""


# ================================================================
#  RuleParser 测试
# ================================================================

class TestRuleParser:
    """RuleParser 解析器测试"""

    def setup_method(self):
        self.parser = RuleParser()

    def test_parse_yaml(self):
        """解析 YAML 格式规则"""
        result = self.parser.parse(_yaml_content(), format="yaml")
        assert result.success is True
        assert len(result.rules) == 1
        assert result.rules[0].name == "yaml_test_rule"
        assert result.rules[0].rule_type == RuleType.COLLABORATION

    def test_parse_json(self):
        """解析 JSON 格式规则"""
        result = self.parser.parse(_json_content(), format="json")
        assert result.success is True
        assert len(result.rules) == 1
        assert result.rules[0].name == "json_test_rule"

    def test_auto_detect_yaml(self):
        """自动检测 YAML 格式"""
        result = self.parser.parse(_yaml_content())
        assert result.success is True

    def test_auto_detect_json(self):
        """自动检测 JSON 格式（以 { 开头）"""
        result = self.parser.parse(_json_content())
        assert result.success is True

    def test_invalid_format_returns_error(self):
        """不支持的格式返回错误"""
        result = self.parser.parse("data", format="xml")
        assert result.success is False
        assert any("Unsupported format" in e for e in result.errors)

    def test_missing_required_field(self):
        """缺少 name 字段时解析失败"""
        bad = '{"type": "collaboration", "version": "1.0"}'
        result = self.parser.parse(bad, format="json")
        assert result.success is False
        assert any("Missing required field: name" in e for e in result.errors)

    def test_invalid_rule_type(self):
        """无效的规则类型"""
        bad = '{"name": "x", "type": "nonexistent"}'
        result = self.parser.parse(bad, format="json")
        assert result.success is False
        assert any("Invalid rule type" in e for e in result.errors)

    def test_validate_schema_valid(self):
        """validate_schema 对合法数据返回空错误列表"""
        data = {
            "name": "ok_rule",
            "type": "collaboration",
            "priority": 50,
            "conditions": [
                {"field": "x", "operator": "eq", "value": 1}
            ],
            "actions": [
                {"type": "notify"}
            ],
        }
        errors = self.parser.validate_schema(data)
        assert errors == []

    def test_validate_schema_invalid_priority(self):
        """validate_schema 捕获越界优先级"""
        data = {"name": "r", "type": "collaboration", "priority": 200}
        errors = self.parser.validate_schema(data)
        assert any("Priority" in e for e in errors)

    def test_rule_graph_topological_order(self):
        """RuleGraph 拓扑排序保证依赖在前"""
        g = RuleGraph()
        r_a = _make_rule(id="a", name="rule_a", dependencies=[])
        r_b = _make_rule(id="b", name="rule_b", dependencies=["a"])
        g.add_rule(r_a)
        g.add_rule(r_b)
        order = g.get_execution_order()
        assert order.index("a") < order.index("b")

    def test_rule_graph_circular_dependency(self):
        """RuleGraph 检测循环依赖"""
        g = RuleGraph()
        r_a = _make_rule(id="a", name="rule_a", dependencies=["b"])
        r_b = _make_rule(id="b", name="rule_b", dependencies=["a"])
        g.add_rule(r_a)
        g.add_rule(r_b)
        with pytest.raises(ValueError, match="Circular dependency"):
            g.get_execution_order()


# ================================================================
#  RuleExecutor 测试
# ================================================================

class TestRuleExecutor:
    """RuleExecutor 执行器测试"""

    def setup_method(self):
        self.executor = RuleExecutor()

    def test_add_and_remove_rule(self):
        """添加和移除规则"""
        rule = _make_rule()
        assert self.executor.add_rule(rule) is True
        assert rule.id in self.executor.rules
        assert self.executor.remove_rule(rule.id) is True
        assert rule.id not in self.executor.rules

    def test_add_rule_without_name_fails(self):
        """缺少名称的规则添加失败"""
        rule = _make_rule(name="")
        assert self.executor.add_rule(rule) is False

    @pytest.mark.asyncio
    async def test_execute_rule_conditions_met(self):
        """条件满足时执行成功"""
        rule = _make_rule()
        self.executor.add_rule(rule)
        result = await self.executor.execute_rule(rule, {"agent": {"priority": 80}})
        assert result.status == ExecutionStatus.SUCCESS
        assert result.conditions_matched == 1

    @pytest.mark.asyncio
    async def test_execute_rule_conditions_not_met(self):
        """条件不满足时跳过"""
        rule = _make_rule()
        self.executor.add_rule(rule)
        result = await self.executor.execute_rule(rule, {"agent": {"priority": 10}})
        assert result.status == ExecutionStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_execute_disabled_rule_skipped(self):
        """禁用的规则直接跳过"""
        rule = _make_rule(enabled=False)
        result = await self.executor.execute_rule(rule, {"agent": {"priority": 80}})
        assert result.status == ExecutionStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_execute_rule_condition_evaluate(self):
        """RuleCondition.evaluate 支持多种操作符"""
        cond_eq = RuleCondition(field="x", operator=ConditionOperator.EQ, value=1)
        assert cond_eq.evaluate({"x": 1}) is True
        assert cond_eq.evaluate({"x": 2}) is False

        cond_gt = RuleCondition(field="x", operator=ConditionOperator.GT, value=5)
        assert cond_gt.evaluate({"x": 10}) is True
        assert cond_gt.evaluate({"x": 3}) is False

        cond_in = RuleCondition(field="x", operator=ConditionOperator.IN, value=[1, 2, 3])
        assert cond_in.evaluate({"x": 2}) is True
        assert cond_in.evaluate({"x": 9}) is False

    @pytest.mark.asyncio
    async def test_execute_batch(self):
        """批量执行多条规则"""
        r1 = _make_rule(id="r1", name="batch_rule_1")
        r2 = _make_rule(id="r2", name="batch_rule_2")
        results = await self.executor.execute_batch(
            [r1, r2], {"agent": {"priority": 80}}
        )
        assert len(results) == 2
        assert all(r.status == ExecutionStatus.SUCCESS for r in results)


# ================================================================
#  RuleValidator 测试
# ================================================================

class TestRuleValidator:
    """RuleValidator 验证器测试"""

    def setup_method(self):
        self.validator = RuleValidator()

    def test_validate_syntax_valid_rule(self):
        """合法规则语法验证通过"""
        rule = _make_rule()
        result = self.validator.validate_syntax(rule)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_syntax_empty_name(self):
        """空名称触发错误"""
        rule = _make_rule(name="")
        result = self.validator.validate_syntax(rule)
        assert result.is_valid is False
        assert any("name" in e.field for e in result.errors)

    def test_validate_syntax_invalid_name_pattern(self):
        """名称不符合正则规则时触发错误（数字开头）"""
        rule = _make_rule(name="123_bad")
        result = self.validator.validate_syntax(rule)
        assert result.is_valid is False
        assert any("name" in e.field for e in result.errors)

    def test_validate_syntax_empty_version(self):
        """空版本号触发错误"""
        rule = _make_rule(version="")
        result = self.validator.validate_syntax(rule)
        assert result.is_valid is False
        assert any("version" in e.field for e in result.errors)

    def test_validate_syntax_priority_out_of_range(self):
        """优先级越界触发错误"""
        rule = _make_rule(priority=150)
        result = self.validator.validate_syntax(rule)
        assert result.is_valid is False
        assert any("priority" in e.field for e in result.errors)

    def test_validate_syntax_no_actions(self):
        """没有动作的规则触发错误"""
        rule = _make_rule(actions=[])
        result = self.validator.validate_syntax(rule)
        assert result.is_valid is False
        assert any("actions" in e.field for e in result.errors)

    def test_validate_semantics_contradictory_conditions(self):
        """矛盾条件检测"""
        rule = _make_rule(conditions=[
            RuleCondition(field="x", operator=ConditionOperator.GT, value=100),
            RuleCondition(field="x", operator=ConditionOperator.LT, value=50),
        ])
        result = self.validator.validate_semantics(rule)
        assert any("Contradictory" in e.message for e in result.errors)

    def test_validate_conflicts_same_priority(self):
        """相同优先级同类型规则检测冲突"""
        r1 = _make_rule(id="a", name="conflict_a", priority=50)
        r2 = _make_rule(id="b", name="conflict_b", priority=50)
        conflicts = self.validator.validate_conflicts([r1, r2])
        assert len(conflicts) >= 1
        assert any(c.conflict_type == "priority" for c in conflicts)

    def test_validate_all_full_pipeline(self):
        """validate_all 全流程验证"""
        rule = _make_rule()
        result = self.validator.validate_all([rule])
        assert isinstance(result, ValidationResult)
        assert "total_rules" in result.metadata


# ================================================================
#  RuleCache 测试
# ================================================================

class TestRuleCache:
    """RuleCache 缓存测试"""

    def setup_method(self):
        self.cache = RuleCache(max_size=100, l1_ttl_seconds=60, enable_versioning=True)

    def test_put_and_get(self):
        """基本存取"""
        rule = _make_rule()
        self.cache.set("r1", rule)
        assert self.cache.get("r1") is rule

    def test_get_miss_returns_none(self):
        """缓存未命中返回 None"""
        assert self.cache.get("nonexistent") is None

    def test_invalidate(self):
        """使缓存条目失效"""
        self.cache.set("r1", _make_rule())
        self.cache.invalidate("r1")
        assert self.cache.get("r1") is None

    def test_lru_eviction(self):
        """LRU 驱逐：超过 max_size 后最旧条目被驱逐"""
        small_cache = RuleCache(max_size=3, l1_ttl_seconds=60)
        for i in range(5):
            small_cache.set(f"k{i}", f"v{i}")
        assert small_cache.get("k0") is None  # 被驱逐
        assert small_cache.get("k4") == "v4"  # 最新仍在

    def test_clear(self):
        """清空缓存"""
        self.cache.set("a", 1)
        self.cache.set("b", 2)
        self.cache.clear()
        assert self.cache.get("a") is None
        assert self.cache.get("b") is None

    def test_version_create_and_get(self):
        """创建版本快照并取回"""
        rule = _make_rule()
        rules = {rule.id: rule}
        vid = self.cache.create_version(rules, "v1.0", description="初始版本")
        assert vid is not None
        snap = self.cache.get_version(vid)
        assert snap is not None
        assert snap.version_name == "v1.0"

    def test_rollback_to_version(self):
        """回滚到指定版本"""
        rule = _make_rule()
        rules = {rule.id: rule}
        vid = self.cache.create_version(rules, "v1.0")
        success, msg = self.cache.rollback_to_version(vid)
        assert success is True
        assert self.cache.current_version == vid

    def test_stats_tracking(self):
        """统计信息正确追踪"""
        self.cache.set("x", 1)
        self.cache.get("x")  # hit
        self.cache.get("y")  # miss
        stats = self.cache.get_stats()
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1

    def test_invalidate_pattern(self):
        """按模式批量失效"""
        self.cache.set("rule_1", 1)
        self.cache.set("rule_2", 2)
        self.cache.set("other", 3)
        self.cache.invalidate_pattern("rule_.*")
        assert self.cache.get("rule_1") is None
        assert self.cache.get("rule_2") is None
        assert self.cache.get("other") == 3


class TestRuleCacheManager:
    """RuleCacheManager 测试"""

    def setup_method(self):
        self.manager = RuleCacheManager()

    def test_get_default_cache(self):
        """获取默认缓存实例"""
        cache = self.manager.get_cache()
        assert isinstance(cache, RuleCache)

    def test_create_named_cache(self):
        """创建命名缓存"""
        cache = self.manager.create_cache("special", max_size=500)
        assert self.manager.get_cache("special") is cache

    def test_record_access_and_hot_keys(self):
        """记录访问并生成热门 key"""
        for _ in range(200):
            self.manager.record_access("hot_rule")
        hot = self.manager.get_hot_keys()
        assert "hot_rule" in hot
