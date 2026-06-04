"""
冲突解决模块单元测试

覆盖 PriorityManager / ResourceArbiter / DeadlockDetector 三个组件。
"""

import pytest
from datetime import datetime, timedelta

from packages.SwarmFly.fly2rules.Core.ConflictResolver.priority_manager import (
    PriorityManager, PriorityLevel, PriorityScore, AgentPriority, PriorityCalculator,
)
from packages.SwarmFly.fly2rules.Core.ConflictResolver.resource_arbiter import (
    ResourceArbiter, ResourceType, AllocationStrategy, ArbitrationResult,
)
from packages.SwarmFly.fly2rules.Core.ConflictResolver.deadlock_detector import (
    DeadlockDetector, WaitGraph, WaitEdge, DeadlockState,
)


# ================================================================
#  PriorityManager 测试
# ================================================================

class TestPriorityManager:
    """PriorityManager 优先级管理器测试"""

    def setup_method(self):
        self.pm = PriorityManager()

    def test_register_and_get_priority(self):
        """注册智能体后可获取优先级"""
        self.pm.register_agent("agent_a", base_priority=70)
        score = self.pm.get_priority("agent_a")
        assert isinstance(score, PriorityScore)
        assert score.total_score > 0

    def test_get_priority_auto_registers(self):
        """未注册的智能体自动注册"""
        score = self.pm.get_priority("new_agent")
        assert score is not None
        assert "new_agent" in self.pm.agent_priorities

    def test_compare_priority_scores(self):
        """高优先级智能体得分高于低优先级"""
        self.pm.register_agent("high", base_priority=90)
        self.pm.register_agent("low", base_priority=20)
        score_high = self.pm.get_priority("high")
        score_low = self.pm.get_priority("low")
        assert score_high > score_low

    def test_resolve_contest_winner(self):
        """竞争解决返回得分最高者"""
        self.pm.register_agent("a1", base_priority=80)
        self.pm.register_agent("a2", base_priority=40)
        winner = self.pm.resolve_contest(["a1", "a2"])
        assert winner == "a1"

    def test_resolve_contest_empty_returns_none(self):
        """空竞争列表返回 None"""
        assert self.pm.resolve_contest([]) is None

    def test_resolve_contest_single_returns_self(self):
        """单个竞争者返回自身"""
        assert self.pm.resolve_contest(["solo"]) == "solo"

    def test_update_base_priority(self):
        """更新基础优先级"""
        self.pm.register_agent("agent_x", base_priority=50)
        self.pm.update_base_priority("agent_x", 90)
        assert self.pm.agent_priorities["agent_x"].base_priority == 90

    def test_unregister_agent(self):
        """注销智能体"""
        self.pm.register_agent("to_remove")
        self.pm.unregister_agent("to_remove")
        assert "to_remove" not in self.pm.agent_priorities

    def test_priority_level_mapping(self):
        """不同分数映射到正确的优先级级别"""
        self.pm.register_agent("critical_agent", base_priority=100)
        self.pm.update_load("critical_agent", 0)
        score = self.pm.get_priority("critical_agent", task_importance=2.0)
        assert score.level in (
            PriorityLevel.CRITICAL, PriorityLevel.URGENT, PriorityLevel.HIGH
        )

    def test_get_top_agents(self):
        """获取优先级最高的 N 个智能体"""
        for i in range(5):
            self.pm.register_agent(f"agent_{i}", base_priority=i * 20)
        top = self.pm.get_top_agents(n=3)
        assert len(top) == 3
        # 降序排列
        assert top[0][1].total_score >= top[1][1].total_score

    def test_stats_tracking(self):
        """统计信息包含计算次数"""
        self.pm.register_agent("s1")
        self.pm.get_priority("s1")
        stats = self.pm.get_stats()
        assert stats["total_calculations"] >= 1
        assert stats["registered_agents"] >= 1


# ================================================================
#  ResourceArbiter 测试
# ================================================================

class TestResourceArbiter:
    """ResourceArbiter 资源仲裁器测试"""

    def setup_method(self):
        self.arbiter = ResourceArbiter()

    def test_request_allocation_granted(self):
        """资源充足时分配成功"""
        result = self.arbiter.request_allocation(
            agent_id="agent_1",
            resource_type=ResourceType.CPU,
            amount=10,
        )
        assert result.granted is True
        assert result.allocation is not None

    def test_request_allocation_denied_when_exhausted(self):
        """资源不足时分配失败并入队"""
        # 耗尽 CPU
        self.arbiter.request_allocation("a1", ResourceType.CPU, 100)
        result = self.arbiter.request_allocation("a2", ResourceType.CPU, 10)
        assert result.granted is False
        assert result.queue_position is not None

    def test_release_allocation(self):
        """释放分配后资源恢复"""
        r = self.arbiter.request_allocation("a1", ResourceType.GPU, 2)
        assert r.granted is True
        alloc_id = r.allocation.allocation_id
        assert self.arbiter.release_allocation(alloc_id) is True

    def test_release_nonexistent_returns_false(self):
        """释放不存在的分配返回 False"""
        assert self.arbiter.release_allocation("fake_id") is False

    def test_get_agent_allocations(self):
        """获取指定智能体的所有分配"""
        self.arbiter.request_allocation("agent_b", ResourceType.MEMORY, 128)
        self.arbiter.request_allocation("agent_b", ResourceType.CPU, 4)
        allocs = self.arbiter.get_agent_allocations("agent_b")
        assert len(allocs) == 2

    def test_get_resource_status(self):
        """获取资源池状态"""
        status = self.arbiter.get_resource_status(ResourceType.CPU)
        assert "total" in status
        assert "used" in status
        assert "available" in status

    def test_release_agent_resources(self):
        """释放智能体所有资源"""
        self.arbiter.request_allocation("agent_c", ResourceType.CPU, 5)
        self.arbiter.request_allocation("agent_c", ResourceType.MEMORY, 64)
        released = self.arbiter.release_agent_resources("agent_c")
        assert len(released) == 2

    def test_multiple_resource_types(self):
        """不同资源类型独立管理"""
        self.arbiter.request_allocation("a", ResourceType.CPU, 50)
        self.arbiter.request_allocation("a", ResourceType.MEMORY, 512)
        cpu_status = self.arbiter.get_resource_status(ResourceType.CPU)
        mem_status = self.arbiter.get_resource_status(ResourceType.MEMORY)
        assert cpu_status["used"] == 50
        assert mem_status["used"] == 512


# ================================================================
#  DeadlockDetector 测试
# ================================================================

class TestDeadlockDetector:
    """DeadlockDetector 死锁检测器测试"""

    def setup_method(self):
        self.detector = DeadlockDetector(config={"enable_auto_resolution": False})

    def test_add_dependency_and_detect_cycle(self):
        """添加依赖后检测到循环"""
        self.detector.acquire_resource("agent_a", "res_1")
        self.detector.acquire_resource("agent_b", "res_2")
        # agent_a 等 res_2（被 agent_b 持有）
        self.detector.request_resource("agent_a", "res_2")
        # agent_b 等 res_1（被 agent_a 持有）→ 形成死锁
        has_deadlock = self.detector.request_resource("agent_b", "res_1")
        assert has_deadlock is True

    def test_no_deadlock_linear_wait(self):
        """线性等待不构成死锁"""
        self.detector.acquire_resource("a", "r1")
        self.detector.acquire_resource("b", "r2")
        # a 等 r2，但 b 不等 r1 → 无环
        result = self.detector.request_resource("a", "res_2")
        assert result is False

    def test_release_resource_breaks_cycle(self):
        """释放资源打破循环"""
        self.detector.acquire_resource("a", "r1")
        self.detector.acquire_resource("b", "r2")
        self.detector.request_resource("a", "r2")
        self.detector.request_resource("b", "r1")  # 死锁
        # 释放后消除
        self.detector.release_resource("b", "r1")
        has_cycle = self.detector.wait_graph.has_cycle()[0]
        assert has_cycle is False

    def test_wait_graph_nodes(self):
        """等待图正确记录节点"""
        self.detector.acquire_resource("x", "res")
        self.detector.request_resource("y", "res")
        graph = self.detector.get_wait_graph()
        assert "y" in graph or any("y" in str(v) for v in graph.values())

    def test_stats_tracking(self):
        """统计信息正确"""
        stats = self.detector.get_stats()
        assert "active_deadlocks" in stats
        assert "is_running" in stats

    def test_acquire_and_release_resource(self):
        """获取和释放资源的完整流程"""
        self.detector.acquire_resource("agent_z", "resource_1")
        assert self.detector.resource_holders["resource_1"] == "agent_z"
        self.detector.release_resource("agent_z", "resource_1")
        assert "resource_1" not in self.detector.resource_holders
