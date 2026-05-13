# SwarmFly 单元测试
"""
阶段三测试套件 - FLY层深化测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from datetime import datetime

# 导入待测试模块
from packages.SwarmFly.core.fly_layers import (
    Fly0Master, Fly1Mission, Fly2Rules, Fly3Trends, Fly4Skills, Fly5Tools,
    FLYLevel, TaskStatus, AgentRole
)

from packages.SwarmFly.core.controller import SwarmFlyController

from packages.SwarmFly.team.sub_agent_manager import (
    SubAgent, SubAgentManager, SubAgentStatus, SubAgentType
)

from packages.SwarmFly.team.team_collaboration import (
    Team, TeamCollaborationManager, CollaborationMode, TeamRole
)

from packages.SwarmFly.layers.collaboration import (
    AgentCollaborationFramework, TaskDistributor, ResultAggregator,
    ConflictResolver, TaskDistributionStrategy, ConflictResolutionStrategy
)


# ============================================================================
# FLY层测试
# ============================================================================

class TestFly0Master(unittest.TestCase):
    """FLY-0 主智能体层测试"""
    
    def setUp(self):
        self.fly0 = Fly0Master()
    
    def test_submit_task(self):
        """测试任务提交"""
        task = {
            "description": "测试任务",
            "priority": 8,
            "requirements": ["skill1", "skill2"]
        }
        task_id = self.fly0.submit_task(task)
        
        self.assertIsNotNone(task_id)
        self.assertTrue(task_id.startswith("task_"))
    
    def test_dispatch_task(self):
        """测试任务分发"""
        task = {"description": "测试任务", "priority": 5}
        task_id = self.fly0.submit_task(task)
        
        success = self.fly0.dispatch_task(task_id, "agent_001")
        self.assertTrue(success)
    
    def test_complete_task(self):
        """测试任务完成"""
        task = {"description": "测试任务"}
        task_id = self.fly0.submit_task(task)
        self.fly0.dispatch_task(task_id, "agent_001")
        
        result = {"output": "test result"}
        success = self.fly0.complete_task(task_id, result)
        
        self.assertTrue(success)
        task_status = self.fly0.get_task_status(task_id)
        self.assertEqual(task_status["status"], TaskStatus.COMPLETED.value)
    
    def test_fail_task(self):
        """测试任务失败"""
        task = {"description": "测试任务"}
        task_id = self.fly0.submit_task(task)
        self.fly0.dispatch_task(task_id, "agent_001")
        
        # 任务现在在active_tasks中
        task_obj = self.fly0.active_tasks.get(task_id)
        self.assertIsNotNone(task_obj)
        
        success = self.fly0.fail_task(task_id, "Test error")
        
        self.assertTrue(success)
        task_status = self.fly0.get_task_status(task_id)
        self.assertEqual(task_status["status"], TaskStatus.FAILED.value)
    
    def test_get_stats(self):
        """测试统计信息"""
        self.fly0.submit_task({"description": "task1"})
        self.fly0.submit_task({"description": "task2"})
        
        stats = self.fly0.get_stats()
        
        self.assertEqual(stats["pending"], 2)


class TestFly1Mission(unittest.TestCase):
    """FLY-1 使命层测试"""
    
    def setUp(self):
        self.fly1 = Fly1Mission()
    
    def test_get_mission(self):
        """测试获取使命"""
        mission = self.fly1.get_mission()
        self.assertIsNotNone(mission)
        self.assertIn("协作网络", mission)
    
    def test_get_values(self):
        """测试获取价值体系"""
        values = self.fly1.get_values()
        self.assertEqual(len(values), 3)
    
    def test_align_agent(self):
        """测试智能体对齐"""
        result = self.fly1.align_agent(
            "agent_001",
            self.fly1.CORE_MISSION,
            ["用户中心", "效率优先", "持续进化"]
        )
        
        self.assertEqual(result["agent_id"], "agent_001")
        self.assertGreaterEqual(result["alignment_score"], 70)


class TestFly2Rules(unittest.TestCase):
    """FLY-2 法则层测试"""
    
    def setUp(self):
        self.fly2 = Fly2Rules()
    
    def test_validate_interaction(self):
        """测试交互验证"""
        message = {
            "agent_id": "agent_001",
            "task_id": "task_001",
            "timestamp": datetime.now().isoformat()
        }
        
        valid, msg = self.fly2.validate_interaction("system", "agent_001", message)
        self.assertTrue(valid)
    
    def test_resolve_conflict(self):
        """测试冲突解决"""
        agents = [
            {"agent_id": "a1", "priority": 5, "has_core_task": True},
            {"agent_id": "a2", "priority": 8, "has_core_task": False}
        ]
        
        winner = self.fly2.resolve_conflict(agents, "resource_1")
        self.assertEqual(winner, "a1")


class TestFly3Trends(unittest.TestCase):
    """FLY-3 趋势层测试"""
    
    def setUp(self):
        self.fly3 = Fly3Trends()
    
    def test_add_trend(self):
        """测试添加趋势"""
        trend = {
            "type": "technology",
            "name": "AI大模型",
            "impact": "high"
        }
        
        trend_id = self.fly3.add_trend(trend)
        self.assertIsNotNone(trend_id)
    
    def test_get_trends_by_type(self):
        """测试按类型获取趋势"""
        self.fly3.add_trend({"type": "technology", "name": "tech1"})
        self.fly3.add_trend({"type": "market", "name": "market1"})
        
        tech_trends = self.fly3.get_technology_trends()
        self.assertEqual(len(tech_trends), 1)


class TestFly4Skills(unittest.TestCase):
    """FLY-4 技能层测试"""
    
    def setUp(self):
        self.fly4 = Fly4Skills()
    
    def test_register_skill(self):
        """测试技能注册"""
        metadata = {
            "name": "web_search",
            "description": "网页搜索",
            "tags": ["search", "web"]
        }
        
        def dummy_impl(**params):
            return {"results": ["result1", "result2"]}
        
        skill_id = self.fly4.register_skill(metadata, dummy_impl)
        self.assertIsNotNone(skill_id)
    
    def test_call_skill(self):
        """测试技能调用"""
        metadata = {"name": "test_skill"}
        
        def test_impl(query):
            return f"processed: {query}"
        
        skill_id = self.fly4.register_skill(metadata, test_impl)
        result = self.fly4.call_skill(skill_id, {"query": "test"})
        
        self.assertEqual(result["status"], "success")


class TestFly5Tools(unittest.TestCase):
    """FLY-5 工具层测试"""
    
    def setUp(self):
        self.fly5 = Fly5Tools()
    
    def test_send_message(self):
        """测试发送消息"""
        msg_id = self.fly5.send_message(
            "agent_001",
            "agent_002",
            {"content": "hello"}
        )
        
        self.assertIsNotNone(msg_id)
    
    def test_cache_operations(self):
        """测试缓存操作"""
        self.fly5.cache_set("key1", "value1", ttl=60)
        
        value = self.fly5.cache_get("key1")
        self.assertEqual(value, "value1")


# ============================================================================
# 主控制器测试
# ============================================================================

class TestSwarmFlyController(unittest.TestCase):
    """SwarmFly 主控制器测试"""
    
    def setUp(self):
        self.controller = SwarmFlyController()
    
    def test_register_agent(self):
        """测试注册智能体"""
        config = {
            "name": "测试智能体",
            "role": AgentRole.TEAM_MEMBER.value,
            "type": "executor"
        }
        
        success = self.controller.register_agent("agent_001", config)
        self.assertTrue(success)
    
    def test_submit_and_dispatch_task(self):
        """测试提交和分发任务"""
        # 注册智能体
        self.controller.register_agent("agent_001", {"name": "test"})
        
        # 提交任务
        task = {"description": "测试任务", "priority": 5}
        task_id = self.controller.submit_task(task)
        
        # 分发任务
        success = self.controller.dispatch_task(task_id, "agent_001")
        self.assertTrue(success)
    
    def test_complete_task_flow(self):
        """测试完整任务流程"""
        self.controller.register_agent("agent_001", {"name": "test"})
        
        task_id = self.controller.submit_task({"description": "task"})
        self.controller.dispatch_task(task_id, "agent_001")
        
        result = self.controller.complete_task(task_id, {"output": "done"})
        self.assertTrue(result)
    
    def test_create_team(self):
        """测试创建团队"""
        config = {
            "name": "测试团队",
            "leader": "leader_001",
            "members": ["member_001", "member_002"]
        }
        
        success = self.controller.create_team("team_001", config)
        self.assertTrue(success)


# ============================================================================
# 子智能体测试
# ============================================================================

class TestSubAgentManager(unittest.TestCase):
    """子智能体管理器测试"""
    
    def setUp(self):
        self.manager = SubAgentManager()
    
    def test_create_sub_agent(self):
        """测试创建子智能体"""
        config = {
            "name": "执行器",
            "parent_id": "parent_001",
            "capabilities": ["execute", "process"]
        }
        
        agent_id = self.manager.create_agent(SubAgentType.EXECUTOR, config)
        self.assertIsNotNone(agent_id)
    
    def test_execute_task(self):
        """测试执行任务"""
        agent_id = self.manager.create_agent(
            SubAgentType.EXECUTOR,
            {"name": "test"}
        )
        
        result = self.manager.execute_task(agent_id, {
            "task_id": "task_001",
            "action": "execute"
        })
        
        self.assertEqual(result["status"], "success")


# ============================================================================
# 团队协作测试
# ============================================================================

class TestTeamCollaborationManager(unittest.TestCase):
    """团队协作管理器测试"""
    
    def setUp(self):
        self.manager = TeamCollaborationManager()
    
    def test_create_team(self):
        """测试创建团队"""
        team = self.manager.create_team("team_001", "测试团队")
        self.assertIsNotNone(team)
    
    def test_add_member(self):
        """测试添加成员"""
        team = self.manager.create_team("team_001", "测试团队")
        team.add_member("member_001", TeamRole.MEMBER)
        
        member = team.get_member("member_001")
        self.assertIsNotNone(member)
    
    def test_assign_task(self):
        """测试分配任务"""
        team = self.manager.create_team("team_001", "测试团队")
        team.add_member("member_001", TeamRole.MEMBER)
        
        task_id = team.assign_task(
            {"description": "测试任务"},
            "member_001"
        )
        
        self.assertIsNotNone(task_id)


# ============================================================================
# 协作框架测试
# ============================================================================

class TestAgentCollaborationFramework(unittest.TestCase):
    """智能体协作框架测试"""
    
    def setUp(self):
        self.framework = AgentCollaborationFramework()
    
    def test_distribute_task(self):
        """测试任务分发"""
        agents = [
            {"agent_id": "a1", "status": "idle"},
            {"agent_id": "a2", "status": "busy"}
        ]
        
        winner = self.framework.distribute_task({}, agents)
        self.assertEqual(winner, "a1")
    
    def test_aggregate_results(self):
        """测试结果聚合"""
        results = [
            {"finding": "finding1"},
            {"finding": "finding2"}
        ]
        
        aggregated = self.framework.aggregate_results(results, "summarize")
        self.assertEqual(aggregated["status"], "success")
    
    def test_resolve_conflict(self):
        """测试冲突解决"""
        agents = [
            {"agent_id": "a1", "priority": 5},
            {"agent_id": "a2", "priority": 8}
        ]
        
        winner, details = self.framework.resolve_conflict(agents, "resource_1")
        self.assertEqual(winner, "a2")


class TestResultAggregator(unittest.TestCase):
    """结果聚合器测试"""
    
    def setUp(self):
        self.aggregator = ResultAggregator()
    
    def test_merge_strategy(self):
        """测试合并策略"""
        results = [
            {"key1": "value1"},
            {"key2": "value2"}
        ]
        
        aggregated = self.aggregator.aggregate(results, "merge")
        self.assertEqual(aggregated["status"], "success")
    
    def test_average_strategy(self):
        """测试平均策略"""
        results = [
            {"value": 10},
            {"value": 20}
        ]
        
        aggregated = self.aggregator.aggregate(results, "average")
        self.assertEqual(aggregated["aggregated"]["average"], 15)


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
