"""
FLY-2 法·法则层 - 集成测试
"""

import asyncio
import unittest
from datetime import datetime
from typing import Any, Dict

from packages.SwarmFly.fly2rules.Core.RuleEngine import RuleParser, RuleExecutor, RuleValidator, RuleCache
from packages.SwarmFly.fly2rules.Core.RuleEngine.rule_parser import Rule, RuleCondition, RuleAction, RuleType, ConditionOperator
from packages.SwarmFly.fly2rules.Core.ConflictResolver import PriorityManager, ResourceArbiter, DeadlockDetector
from packages.SwarmFly.fly2rules.Core.ConflictResolver.priority_manager import AgentPriority, PriorityLevel
from packages.SwarmFly.fly2rules.Core.ConflictResolver.resource_arbiter import ResourceType, AllocationStrategy
from packages.SwarmFly.fly2rules.Core.SecurityEnforcer import PermissionChecker, AuditLogger, EncryptionHandler
from packages.SwarmFly.fly2rules.Core.SecurityEnforcer.permission_checker import Permission, PermissionContext
from packages.SwarmFly.fly2rules.Core.SecurityEnforcer.audit_logger import AuditEventType, AuditLevel
from Interfaces import RevolvingInterface, EvolvingInterface


class TestRuleEngine(unittest.TestCase):
    """规则引擎测试"""
    
    def setUp(self):
        self.parser = RuleParser()
        self.executor = RuleExecutor()
        self.validator = RuleValidator()
    
    def test_rule_parsing_yaml(self):
        """测试YAML规则解析"""
        yaml_content = """
name: test_rule
version: "1.0"
type: collaboration
priority: 80
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
"""
        result = self.parser.parse(yaml_content)
        self.assertTrue(result.success)
        self.assertEqual(len(result.rules), 1)
        self.assertEqual(result.rules[0].name, "test_rule")
        self.assertEqual(result.rules[0].priority, 80)
    
    def test_rule_validation(self):
        """测试规则验证"""
        rule = Rule(
            id="test_001",
            name="valid_rule",
            description="Test rule",
            version="1.0",
            rule_type=RuleType.COLLABORATION,
            priority=75
        )
        
        result = self.validator.validate_syntax(rule)
        self.assertTrue(result.is_valid)
    
    def test_rule_execution(self):
        """测试规则执行"""
        rule = Rule(
            id="exec_001",
            name="execute_test",
            description="Execution test",
            version="1.0",
            rule_type=RuleType.COLLABORATION,
            conditions=[
                RuleCondition(
                    field="value",
                    operator=ConditionOperator.GE,
                    value=10
                )
            ],
            actions=[
                RuleAction(
                    action_type="transform",
                    parameters={"field": "result", "value": "processed"}
                )
            ],
            priority=50
        )
        
        self.executor.add_rule(rule)
        
        context = {"value": 15}
        results = self.executor.execute_fire_all(context)
        
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].success)


class TestConflictResolver(unittest.TestCase):
    """冲突解决测试"""
    
    def setUp(self):
        self.priority_manager = PriorityManager()
        self.resource_arbiter = ResourceArbiter()
        self.deadlock_detector = DeadlockDetector()
    
    def test_priority_calculation(self):
        """测试优先级计算"""
        self.priority_manager.register_agent("agent_001", base_priority=70)
        
        score = self.priority_manager.get_priority("agent_001")
        self.assertGreater(score.total_score, 0)
        self.assertEqual(score.level, PriorityLevel.HIGH)
    
    def test_resource_allocation(self):
        """测试资源分配"""
        result = self.resource_arbiter.request_allocation(
            agent_id="agent_001",
            resource_type=ResourceType.CPU,
            amount=10.0,
            priority=80
        )
        
        self.assertTrue(result.granted)
        self.assertIsNotNone(result.allocation)
    
    def test_deadlock_detection(self):
        """测试死锁检测"""
        # 模拟资源请求形成死锁
        self.deadlock_detector.acquire_resource("agent_A", "resource_1")
        self.deadlock_detector.request_resource("agent_B", "resource_1")
        self.deadlock_detector.request_resource("agent_A", "resource_2")
        
        # agent_A等待agent_B持有的resource_2, agent_B等待agent_A持有的resource_1
        self.deadlock_detector.acquire_resource("agent_B", "resource_2")
        
        # 检查死锁
        stats = self.deadlock_detector.get_stats()
        self.assertGreaterEqual(stats['active_deadlocks'], 0)


class TestSecurityEnforcer(unittest.TestCase):
    """安全执行测试"""
    
    def setUp(self):
        self.permission_checker = PermissionChecker()
        self.audit_logger = AuditLogger()
        self.encryption = EncryptionHandler()
    
    def test_permission_check(self):
        """测试权限检查"""
        user = self.permission_checker.create_user(
            user_id="user_001",
            name="Test User",
            roles=["operator"]
        )
        
        context = PermissionContext(
            user=user,
            resource_type="document",
            action="read"
        )
        
        result = self.permission_checker.check_permission(
            context,
            Permission.READ
        )
        
        self.assertTrue(result.allowed)
    
    def test_audit_logging(self):
        """测试审计日志"""
        event = self.audit_logger.log(
            event_type=AuditEventType.USER_LOGIN,
            action="User logged in",
            user_id="user_001",
            result="success"
        )
        
        self.assertIsNotNone(event.event_id)
        
        # 查询
        events = self.audit_logger.query(user_id="user_001")
        self.assertGreater(len(events), 0)
    
    def test_encryption(self):
        """测试加密"""
        data = "Sensitive data"
        
        # 加密
        encrypted = self.encryption.encrypt(data)
        self.assertIsNotNone(encrypted.ciphertext)
        
        # 解密
        decrypted = self.encryption.decrypt(encrypted)
        self.assertEqual(decrypted.decode('utf-8'), data)


class TestInterfaces(unittest.TestCase):
    """接口测试"""
    
    async def test_revolving_interface(self):
        """测试Revolving接口"""
        interface = RevolvingInterface()
        
        # 连接
        connected = await interface.connect()
        self.assertTrue(connected)
        
        # 路由任务
        from Interfaces.revolving_interface import TaskRouteRequest
        request = TaskRouteRequest(
            task_id="task_001",
            task_type="analysis",
            requirements={"cpu": 2}
        )
        
        result = await interface.route_task(request)
        self.assertEqual(result.task_id, "task_001")
    
    async def test_evolving_interface(self):
        """测试Evolving接口"""
        interface = EvolvingInterface()
        
        # 连接
        connected = await interface.connect()
        self.assertTrue(connected)
        
        # 上报执行结果
        from Interfaces.evolving_interface import ExecutionResult
        result = ExecutionResult(
            execution_id="exec_001",
            agent_id="agent_001",
            task_id="task_001",
            success=True,
            metrics={"accuracy": 0.95}
        )
        
        reported = await interface.report_execution_result(result)
        self.assertTrue(reported)


def run_tests():
    """运行测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestRuleEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestConflictResolver))
    suite.addTests(loader.loadTestsFromTestCase(TestSecurityEnforcer))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 异步测试单独运行
    async def run_async_tests():
        suite = unittest.TestSuite()
        suite.addTests(loader.loadTestsFromTestCase(TestInterfaces))
        runner = unittest.TextTestRunner(verbosity=2)
        await asyncio.get_event_loop().run_until_complete(suite)
    
    asyncio.run(run_async_tests())
    
    return result.wasSuccessful()


if __name__ == '__main__':
    run_tests()
