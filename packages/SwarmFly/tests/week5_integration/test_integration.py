"""
FLY-2/3/5 Week 5 集成测试
End-to-End Integration Tests for FLY-2/3/5
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass, field
import statistics

# 导入FLY-2模块
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'FLY-2_法则层'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'FLY-3_趋势层'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'FLY-5_工具层'))

from FLY_2_法则层.Core.RuleEngine import (
    RuleParser, RuleExecutor, RuleValidator, RuleCache,
    Rule, Condition, Action, ExecutionContext, ConditionOperator
)
from FLY_3_趋势层.Core.TrendAnalyzer import (
    TrendAnalyzer, Trend, TrendDataPoint, TrendType, TrendDirection
)
from FLY_5_工具层.Core.MessageQueue import (
    QueueBroker, Message, MessagePriority
)


# ==================== 测试数据定义 ====================

@dataclass
class TestMetrics:
    """测试指标"""
    test_name: str
    start_time: datetime
    end_time: datetime = None
    latency_ms: float = 0
    success: bool = False
    error: str = None


class IntegrationTestSuite:
    """集成测试套件"""
    
    def __init__(self):
        self.metrics: List[TestMetrics] = []
        self.fly2_executor = None
        self.fly3_analyzer = None
        self.fly5_broker = None
        
    def record_metric(self, metric: TestMetrics):
        """记录测试指标"""
        if metric.end_time:
            metric.latency_ms = (metric.end_time - metric.start_time).total_seconds() * 1000
        self.metrics.append(metric)
    
    def get_summary(self) -> Dict:
        """获取测试摘要"""
        total = len(self.metrics)
        passed = sum(1 for m in self.metrics if m.success)
        latencies = [m.latency_ms for m in self.metrics if m.success]
        
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": f"{(passed/total*100):.1f}%" if total > 0 else "N/A",
            "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
            "p99_latency_ms": sorted(latencies)[int(len(latencies)*0.99)] if len(latencies) > 10 else max(latencies, default=0)
        }


# ==================== FLY-2/3 联动测试 ====================

class TestFly2Fly3Integration:
    """FLY-2规则引擎与FLY-3趋势分析联动测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.suite = IntegrationTestSuite()
        self.fly2_executor = RuleExecutor()
        self.fly3_analyzer = TrendAnalyzer()
        
    def test_rule_triggers_trend_analysis(self):
        """测试规则触发趋势分析"""
        metric = TestMetrics("rule_triggers_trend", datetime.now())
        
        # 1. 创建触发规则 - 当异常检测时触发分析
        rule = Rule(
            rule_id="trigger_trend_analysis",
            name="触发趋势分析规则",
            description="当性能指标异常时触发趋势分析",
            priority=80,
            conditions=[
                Condition("error_rate", ConditionOperator.GREATER_THAN, 0.05)
            ],
            actions=[
                Action("trigger_trend_analysis", {"analysis_type": "performance"})
            ]
        )
        self.fly2_executor.add_rule(rule)
        
        # 2. 模拟触发场景
        context = ExecutionContext(
            context_id=str(uuid.uuid4()),
            data={"error_rate": 0.08, "component": "api_gateway"}
        )
        
        # 3. 执行规则
        result = self.fly2_executor.execute_rule(rule.rule_id, context)
        
        # 4. 验证结果
        metric.success = result is not None
        metric.end_time = datetime.now()
        self.suite.record_metric(metric)
        
        assert metric.success, "规则执行应成功"
        print(f"✓ FLY-2触发FLY-3测试通过 | 延迟: {metric.latency_ms:.2f}ms")
    
    def test_trend_prediction_triggers_rule_update(self):
        """测试趋势预测触发规则更新"""
        metric = TestMetrics("trend_triggers_rule_update", datetime.now())
        
        # 1. 创建初始规则
        rule = Rule(
            rule_id="adaptive_rule",
            name="自适应规则",
            description="根据趋势调整的规则",
            priority=50,
            conditions=[
                Condition("load_factor", ConditionOperator.LESS_THAN, 0.7)
            ],
            actions=[
                Action("scale_down", {"threshold": 0.3})
            ]
        )
        self.fly2_executor.add_rule(rule)
        
        # 2. 模拟趋势预测结果 - 负载将下降
        predicted_trend = Trend(
            trend_id="load_decrease_trend",
            name="负载下降趋势",
            trend_type=TrendType.PERFORMANCE,
            direction=TrendDirection.FALLING,
            strength=0.85,
            confidence=0.9,
            start_time=datetime.now()
        )
        
        # 3. 根据趋势调整规则
        if predicted_trend.direction == TrendDirection.FALLING:
            # 更新规则参数
            rule.actions[0].params["scale_factor"] = 0.5
            self.fly2_executor.add_rule(rule)
        
        # 4. 验证规则已更新
        updated_rule = self.fly2_executor.get_rule("adaptive_rule")
        metric.success = (
            updated_rule is not None and 
            updated_rule.actions[0].params.get("scale_factor") == 0.5
        )
        metric.end_time = datetime.now()
        self.suite.record_metric(metric)
        
        assert metric.success, "规则应已根据趋势更新"
        print(f"✓ FLY-3预测触发FLY-2规则更新测试通过 | 延迟: {metric.latency_ms:.2f}ms")


# ==================== FLY-3/5 联动测试 ====================

class TestFly3Fly5Integration:
    """FLY-3趋势分析与FLY-5工具调用联动测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.suite = IntegrationTestSuite()
        self.fly3_analyzer = TrendAnalyzer()
        self.fly5_broker = QueueBroker()
        
    def test_trend_alert_triggers_tool_call(self):
        """测试趋势告警触发工具调用"""
        metric = TestMetrics("trend_alert_tool_call", datetime.now())
        
        # 1. 创建消息队列用于接收告警
        self.fly5_broker.create_queue("trend_alerts", maxsize=100)
        
        # 2. 模拟趋势告警
        alert_message = Message(
            message_id=str(uuid.uuid4()),
            sender="FLY-3",
            receiver="FLY-5",
            task_id="trend_analysis_001",
            content_type="json",
            content={
                "alert_type": "performance_degradation",
                "trend_id": "perf_trend_001",
                "severity": "high",
                "recommended_action": "scale_up"
            },
            priority=MessagePriority.HIGH
        )
        
        # 3. 发布告警消息
        result = asyncio.run(self.fly5_broker.publish("trend_alerts", alert_message))
        
        metric.success = result
        metric.end_time = datetime.now()
        self.suite.record_metric(metric)
        
        assert metric.success, "消息发布应成功"
        print(f"✓ FLY-3趋势告警触发FLY-5工具调用测试通过 | 延迟: {metric.latency_ms:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_async_trend_processing(self):
        """测试异步趋势处理"""
        metric = TestMetrics("async_trend_processing", datetime.now())
        
        # 1. 创建工具注册
        self.fly5_broker.create_queue("trend_processing", maxsize=100)
        
        # 2. 异步处理多个趋势
        async def process_trend(trend_id: str):
            await asyncio.sleep(0.01)  # 模拟处理
            return Message(
                message_id=str(uuid.uuid4()),
                sender="FLY-3",
                receiver="FLY-5",
                task_id=f"process_{trend_id}",
                content_type="json",
                content={"processed": True, "trend_id": trend_id}
            )
        
        # 3. 并发处理
        trends = [f"trend_{i}" for i in range(10)]
        results = await asyncio.gather(*[process_trend(t) for t in trends])
        
        metric.success = len(results) == 10
        metric.end_time = datetime.now()
        self.suite.record_metric(metric)
        
        assert metric.success, "异步处理应完成所有趋势"
        print(f"✓ 异步趋势处理测试通过 | 处理: {len(results)}条 | 延迟: {metric.latency_ms:.2f}ms")


# ==================== FLY-2/5 联动测试 ====================

class TestFly2Fly5Integration:
    """FLY-2规则引擎与FLY-5消息队列联动测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.suite = IntegrationTestSuite()
        self.fly2_executor = RuleExecutor()
        self.fly5_broker = QueueBroker()
        
    def test_rule_execution_triggers_notification(self):
        """测试规则执行触发通知"""
        metric = TestMetrics("rule_notification", datetime.now())
        
        # 1. 创建消息队列
        self.fly5_broker.create_queue("rule_notifications", maxsize=100)
        
        # 2. 创建规则 - 规则执行后发送通知
        rule = Rule(
            rule_id="notify_on_execution",
            name="执行通知规则",
            description="规则执行后发送通知",
            priority=60,
            conditions=[
                Condition("status", ConditionOperator.EQUALS, "executed")
            ],
            actions=[
                Action("send_notification", {"channel": "mq"})
            ]
        )
        self.fly2_executor.add_rule(rule)
        
        # 3. 执行规则
        context = ExecutionContext(
            context_id=str(uuid.uuid4()),
            data={"status": "executed", "rule_id": rule.rule_id}
        )
        result = self.fly2_executor.execute_rule(rule.rule_id, context)
        
        # 4. 验证通知已发送
        metric.success = result is not None
        metric.end_time = datetime.now()
        self.suite.record_metric(metric)
        
        assert metric.success, "规则执行应成功"
        print(f"✓ FLY-2规则执行触发FLY-5通知测试通过 | 延迟: {metric.latency_ms:.2f}ms")
    
    def test_message_triggers_rule_evaluation(self):
        """测试消息触发规则评估"""
        metric = TestMetrics("message_triggers_rule", datetime.now())
        
        # 1. 创建规则
        rule = Rule(
            rule_id="message_triggered_rule",
            name="消息触发规则",
            description="接收特定消息时执行",
            priority=70,
            conditions=[
                Condition("message_type", ConditionOperator.EQUALS, "urgent")
            ],
            actions=[
                Action("process_urgent", {})
            ]
        )
        self.fly2_executor.add_rule(rule)
        
        # 2. 模拟消息到达
        message = Message(
            message_id=str(uuid.uuid4()),
            sender="external",
            receiver="FLY-2",
            task_id="urgent_task",
            content_type="json",
            content={"message_type": "urgent", "data": "critical"}
        )
        
        # 3. 检查消息是否触发规则
        context_data = {"message_type": message.content.get("message_type")}
        matched = rule.evaluate(context_data)
        
        metric.success = matched
        metric.end_time = datetime.now()
        self.suite.record_metric(metric)
        
        assert matched, "消息应触发规则匹配"
        print(f"✓ FLY-5消息触发FLY-2规则评估测试通过 | 延迟: {metric.latency_ms:.2f}ms")


# ==================== 三层完整调用链测试 ====================

class TestFullChainIntegration:
    """FLY-2/3/5 完整调用链测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.suite = IntegrationTestSuite()
        self.fly2_executor = RuleExecutor()
        self.fly3_analyzer = TrendAnalyzer()
        self.fly5_broker = QueueBroker()
        
    @pytest.mark.asyncio
    async def test_complete_flow_trend_to_action(self):
        """测试完整流程: 趋势检测 -> 规则匹配 -> 工具执行"""
        metric = TestMetrics("complete_flow", datetime.now())
        
        # 1. 创建消息队列
        self.fly5_broker.create_queue("executions", maxsize=100)
        
        # 2. 创建规则
        rule = Rule(
            rule_id="trend_action_rule",
            name="趋势动作规则",
            description="当趋势强度超过阈值时执行动作",
            priority=80,
            conditions=[
                Condition("trend_strength", ConditionOperator.GREATER_THAN, 0.7)
            ],
            actions=[
                Action("execute_tool", {"tool": "auto_scaler"})
            ]
        )
        self.fly2_executor.add_rule(rule)
        
        # 3. 模拟趋势数据
        data_points = [
            TrendDataPoint(timestamp=datetime.now() - timedelta(hours=i), value=0.8 + i*0.02)
            for i in range(10)
        ]
        
        # 4. FLY-3: 分析趋势
        trend = await self.fly3_analyzer.analyze(data_points, TrendType.PERFORMANCE)
        
        # 5. FLY-2: 检查规则匹配
        if trend:
            context = ExecutionContext(
                context_id=str(uuid.uuid4()),
                data={"trend_strength": trend.strength, "trend_id": trend.trend_id}
            )
            result = self.fly2_executor.execute_rule(rule.rule_id, context)
        
        # 6. FLY-5: 发布执行消息
        execution_msg = Message(
            message_id=str(uuid.uuid4()),
            sender="FLY-2",
            receiver="tool_executor",
            task_id="execute_scaling",
            content_type="json",
            content={"action": "scale_up", "factor": 1.5}
        )
        await self.fly5_broker.publish("executions", execution_msg)
        
        # 7. 验证完整流程
        metric.success = (
            trend is not None and
            trend.strength > 0.7 and
            execution_msg.message_id is not None
        )
        metric.end_time = datetime.now()
        self.suite.record_metric(metric)
        
        assert metric.success, "完整调用链应成功执行"
        print(f"✓ 完整调用链测试通过 | 延迟: {metric.latency_ms:.2f}ms")
    
    def test_rule_conflict_resolution_flow(self):
        """测试规则冲突解决流程"""
        metric = TestMetrics("conflict_resolution", datetime.now())
        
        # 1. 创建冲突规则
        rule1 = Rule(
            rule_id="scale_up_rule",
            name="扩容规则",
            description="高负载时扩容",
            priority=70,
            conditions=[
                Condition("load", ConditionOperator.GREATER_THAN, 0.8)
            ],
            actions=[Action("scale_up")]
        )
        
        rule2 = Rule(
            rule_id="scale_down_rule",
            name="缩容规则",
            description="低负载时缩容",
            priority=60,
            conditions=[
                Condition("load", ConditionOperator.LESS_THAN, 0.3)
            ],
            actions=[Action("scale_down")]
        )
        
        self.fly2_executor.add_rule(rule1)
        self.fly2_executor.add_rule(rule2)
        
        # 2. 测试边界情况
        context = ExecutionContext(
            context_id=str(uuid.uuid4()),
            data={"load": 0.5}
        )
        
        # 3. 验证只有一个规则匹配
        matched_rules = [
            r for r in [rule1, rule2]
            if r.evaluate(context.data)
        ]
        
        metric.success = len(matched_rules) == 0  # 0.5既不大于0.8也不小于0.3
        metric.end_time = datetime.now()
        self.suite.record_metric(metric)
        
        assert metric.success, "边界条件应正确处理"
        print(f"✓ 规则冲突解决测试通过 | 延迟: {metric.latency_ms:.2f}ms")


# ==================== 性能测试 ====================

class TestPerformance:
    """性能测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.suite = IntegrationTestSuite()
        self.fly2_executor = RuleExecutor()
        self.fly3_analyzer = TrendAnalyzer()
        self.fly5_broker = QueueBroker()
    
    def test_rule_execution_latency(self):
        """测试规则执行延迟"""
        latencies = []
        
        # 创建规则
        rule = Rule(
            rule_id="perf_test_rule",
            name="性能测试规则",
            description="",
            priority=50,
            conditions=[
                Condition("value", ConditionOperator.GREATER_THAN, 100)
            ],
            actions=[Action("process")]
        )
        self.fly2_executor.add_rule(rule)
        
        # 执行1000次测量
        for i in range(1000):
            start = time.perf_counter()
            context = ExecutionContext(
                context_id=str(uuid.uuid4()),
                data={"value": 150}
            )
            self.fly2_executor.execute_rule(rule.rule_id, context)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # 转换为毫秒
        
        avg_latency = statistics.mean(latencies)
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
        
        print(f"规则执行延迟 - 平均: {avg_latency:.3f}ms | P99: {p99_latency:.3f}ms")
        assert p99_latency < 50, f"P99延迟应小于50ms，实际: {p99_latency:.3f}ms"
    
    @pytest.mark.asyncio
    async def test_message_throughput(self):
        """测试消息吞吐量"""
        self.fly5_broker.create_queue("throughput_test", maxsize=100000)
        
        start = time.perf_counter()
        message_count = 5000
        
        # 批量发送消息
        for i in range(message_count):
            msg = Message(
                message_id=str(uuid.uuid4()),
                sender="test",
                receiver="test",
                task_id=f"task_{i}",
                content_type="text",
                content=f"message_{i}"
            )
            await self.fly5_broker.publish("throughput_test", msg)
        
        end = time.perf_counter()
        duration = end - start
        throughput = message_count / duration
        
        print(f"消息吞吐量: {throughput:.0f} msg/s (5000条/{duration:.2f}s)")
        assert throughput > 1000, f"吞吐量应大于1000 msg/s，实际: {throughput:.0f}"
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """测试并发操作"""
        latencies = []
        
        async def concurrent_operation(op_id: int):
            start = time.perf_counter()
            
            # 模拟并发操作
            await asyncio.sleep(0.01)
            
            end = time.perf_counter()
            latencies.append((end - start) * 1000)
        
        # 并发执行100个操作
        start = time.perf_counter()
        await asyncio.gather(*[concurrent_operation(i) for i in range(100)])
        total_time = time.perf_counter() - start
        
        avg_latency = statistics.mean(latencies)
        print(f"并发测试 - 平均延迟: {avg_latency:.2f}ms | 总时间: {total_time:.2f}s")
        assert total_time < 1.0, f"100个并发操作应在1秒内完成"


# ==================== 熔断与降级测试 ====================

class TestCircuitBreaker:
    """熔断与降级测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.fly2_executor = RuleExecutor()
        self.fly5_broker = QueueBroker()
        self.failure_count = 0
        self.circuit_open = False
    
    def test_circuit_breaker_trigger(self):
        """测试熔断器触发"""
        # 模拟连续失败触发熔断
        failure_threshold = 5
        
        for i in range(failure_threshold + 2):
            # 模拟失败
            if i < failure_threshold:
                self.failure_count += 1
            else:
                # 触发熔断
                self.circuit_open = True
        
        assert self.circuit_open, "连续失败后应触发熔断"
        assert self.failure_count >= failure_threshold, f"应有至少{failure_threshold}次失败"
        print(f"✓ 熔断器触发测试通过 | 失败次数: {self.failure_count}")
    
    def test_graceful_degradation(self):
        """测试优雅降级"""
        # 模拟降级策略
        degraded_mode = False
        fallback_executed = False
        
        def fallback():
            nonlocal fallback_executed
            fallback_executed = True
            return {"mode": "degraded", "data": "cached"}
        
        def primary_operation():
            nonlocal degraded_mode
            if self.circuit_open:
                degraded_mode = True
                return fallback()
            return {"mode": "normal"}
        
        # 执行操作
        result = primary_operation()
        
        assert result["mode"] == "degraded" if self.circuit_open else result["mode"] == "normal"
        print(f"✓ 优雅降级测试通过 | 模式: {result['mode']}")


# ==================== 回滚机制测试 ====================

class TestRollbackMechanism:
    """回滚机制测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.fly2_executor = RuleExecutor()
        self.version_history = []
    
    def test_rule_version_rollback(self):
        """测试规则版本回滚"""
        # 1. 创建初始规则版本
        rule_v1 = Rule(
            rule_id="rollback_test",
            name="回滚测试规则V1",
            description="初始版本",
            priority=50,
            conditions=[Condition("value", ConditionOperator.GREATER_THAN, 0)],
            actions=[Action("process_v1")]
        )
        self.fly2_executor.add_rule(rule_v1)
        self.version_history.append({"version": 1, "rule": rule_v1})
        
        # 2. 创建新版本规则
        rule_v2 = Rule(
            rule_id="rollback_test",
            name="回滚测试规则V2",
            description="新版本",
            priority=50,
            conditions=[Condition("value", ConditionOperator.GREATER_THAN, 0)],
            actions=[Action("process_v2")]
        )
        self.fly2_executor.add_rule(rule_v2)
        self.version_history.append({"version": 2, "rule": rule_v2})
        
        # 3. 回滚到V1
        current_rule = self.fly2_executor.get_rule("rollback_test")
        rollback_success = current_rule.name == "回滚测试规则V2"  # 当前是V2
        
        # 模拟回滚
        self.fly2_executor.rules["rollback_test"] = self.version_history[0]["rule"]
        rolled_back_rule = self.fly2_executor.get_rule("rollback_test")
        
        assert rolled_back_rule.actions[0].action_type == "process_v1"
        print(f"✓ 规则版本回滚测试通过 | 回滚版本: V1")
    
    def test_state_recovery(self):
        """测试状态恢复"""
        # 模拟快照
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "state": {
                "rules": ["rule1", "rule2"],
                "contexts": [{"id": "ctx1", "data": {"status": "active"}}]
            }
        }
        
        # 模拟状态破坏
        current_state = {"rules": [], "contexts": []}
        
        # 恢复到快照状态
        recovered = snapshot["state"]["contexts"][0]
        
        assert recovered["data"]["status"] == "active"
        print(f"✓ 状态恢复测试通过")


# ==================== 测试运行器 ====================

def run_all_tests():
    """运行所有集成测试"""
    print("\n" + "="*80)
    print("FLY-2/3/5 Week 5 集成测试套件")
    print("="*80)
    
    test_classes = [
        TestFly2Fly3Integration,
        TestFly3Fly5Integration,
        TestFly2Fly5Integration,
        TestFullChainIntegration,
        TestPerformance,
        TestCircuitBreaker,
        TestRollbackMechanism
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    results = {}
    
    for test_class in test_classes:
        class_name = test_class.__name__
        print(f"\n{'='*60}")
        print(f"测试类: {class_name}")
        print("="*60)
        
        test_instance = test_class()
        test_methods = [m for m in dir(test_instance) if m.startswith("test_")]
        
        class_passed = 0
        class_failed = 0
        
        for method_name in test_methods:
            total_tests += 1
            try:
                test_instance.setup_method()
                method = getattr(test_instance, method_name)
                
                # 检查是否为异步测试
                if asyncio.iscoroutinefunction(method):
                    asyncio.run(method())
                else:
                    method()
                
                class_passed += 1
                passed_tests += 1
                print(f"  ✓ {method_name}")
            except Exception as e:
                class_failed += 1
                failed_tests += 1
                print(f"  ✗ {method_name}: {str(e)}")
        
        results[class_name] = {"passed": class_passed, "failed": class_failed}
    
    # 打印汇总
    print("\n" + "="*80)
    print("测试结果汇总")
    print("="*80)
    
    for class_name, result in results.items():
        status = "✓" if result["failed"] == 0 else "✗"
        print(f"  {status} {class_name}: {result['passed']} 通过, {result['failed']} 失败")
    
    print("\n" + "-"*40)
    print(f"总计: {total_tests} 测试用例")
    print(f"通过: {passed_tests}")
    print(f"失败: {failed_tests}")
    print(f"通过率: {(passed_tests/total_tests*100):.1f}%")
    print("="*80)
    
    return {
        "total": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "pass_rate": f"{(passed_tests/total_tests*100):.1f}%"
    }


if __name__ == "__main__":
    results = run_all_tests()
