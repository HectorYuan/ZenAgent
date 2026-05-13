"""
协作引擎模块单元测试
"""

import pytest
import sys
import os

PACKAGES_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PACKAGES_DIR)

from SwarmFly.collaboration import (
    CollaborationEngine,
    CollaborationConfig,
    TaskDispatcher,
    Task,
    TaskPriority,
    TaskStatus,
    DispatchStrategy,
    LoadBalancer,
    BalancingStrategy,
    AgentLoad,
    ConsensusMechanism,
    QuorumConsensus,
    WeightedConsensus,
    UnanimousConsensus,
    ConsensusProtocol,
    ConflictResolver,
    ConflictType,
    ResolutionStrategy,
)


class TestTask:
    """任务测试"""
    
    def test_task_creation(self):
        """测试任务创建"""
        task = Task(
            name="Test Task",
            description="A test task",
            priority=TaskPriority.HIGH,
        )
        
        assert task.name == "Test Task"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
        assert task.task_id is not None
    
    def test_task_is_completed(self):
        """测试任务完成状态"""
        task = Task(name="Test")
        
        assert task.is_completed is False
        
        task.status = TaskStatus.COMPLETED
        assert task.is_completed is True
    
    def test_task_can_retry(self):
        """测试任务重试"""
        task = Task(name="Test", max_retries=3)
        
        assert task.can_retry is False
        
        task.status = TaskStatus.FAILED
        task.retry_count = 1
        assert task.can_retry is True
        
        task.retry_count = 3
        assert task.can_retry is False


class TestTaskDispatcher:
    """任务分发器测试"""
    
    def test_dispatcher_creation(self):
        """测试分发器创建"""
        dispatcher = TaskDispatcher()
        
        assert dispatcher.pending_count == 0
        assert dispatcher.strategy == DispatchStrategy.ROUND_ROBIN
    
    def test_register_agent(self):
        """测试注册 Agent"""
        dispatcher = TaskDispatcher()
        
        dispatcher.register_agent("agent-1")
        agents = dispatcher.get_available_agents()
        
        assert "agent-1" in agents
    
    def test_submit_task(self):
        """测试提交任务"""
        dispatcher = TaskDispatcher()
        
        task = dispatcher.submit_task(
            name="Task 1",
            payload={"data": "test"},
            priority=TaskPriority.NORMAL,
        )
        
        assert task is not None
        assert task.name == "Task 1"
        assert task.status == TaskStatus.QUEUED
        assert dispatcher.pending_count == 1
    
    def test_dispatch_task(self):
        """测试分发任务"""
        dispatcher = TaskDispatcher()
        dispatcher.register_agent("agent-1")
        
        task = dispatcher.submit_task(name="Task 1", payload={"data": "test"})
        result = dispatcher.dispatch_task(task.task_id, "agent-1")
        
        assert result is True
        task = dispatcher.get_task(task.task_id)
        assert task.assigned_agent == "agent-1"
    
    def test_complete_task(self):
        """测试完成任务"""
        dispatcher = TaskDispatcher()
        dispatcher.register_agent("agent-1")
        
        task = dispatcher.submit_task(name="Task 1", payload={"data": "test"})
        dispatcher.dispatch_task(task.task_id, "agent-1")
        
        result = dispatcher.complete_task(task.task_id, "success")
        
        assert result is True
        task = dispatcher.get_task(task.task_id)
        assert task.status == TaskStatus.COMPLETED
    
    def test_fail_task(self):
        """测试任务失败"""
        dispatcher = TaskDispatcher()
        
        task = dispatcher.submit_task(name="Task 1", payload={"data": "test"})
        
        result = dispatcher.fail_task(task.task_id, "Error occurred")
        
        assert result is True
    
    def test_priority_ordering(self):
        """测试优先级排序"""
        dispatcher = TaskDispatcher()
        dispatcher.register_agent("agent-1")
        
        # 提交不同优先级的任务
        task_low = dispatcher.submit_task(name="Low", payload={"p": 1}, priority=TaskPriority.LOW)
        task_high = dispatcher.submit_task(name="High", payload={"p": 1}, priority=TaskPriority.HIGH)
        task_normal = dispatcher.submit_task(name="Normal", payload={"p": 1}, priority=TaskPriority.NORMAL)
        
        # 获取下一个任务
        next_task = dispatcher.get_next_task("agent-1")
        
        # 应该是最高优先级
        assert next_task.name == "High"
    
    def test_callbacks(self):
        """测试回调"""
        dispatcher = TaskDispatcher()
        
        assignments = []
        
        def on_assigned(task, agent_id):
            assignments.append((task.task_id, agent_id))
        
        dispatcher.register_callback("task_assigned", on_assigned)
        dispatcher.register_agent("agent-1")
        
        task = dispatcher.submit_task(name="Task 1", payload={"data": "test"})
        dispatcher.dispatch_task(task.task_id, "agent-1")
        
        assert len(assignments) == 1


class TestLoadBalancer:
    """负载均衡器测试"""
    
    def test_balancer_creation(self):
        """测试均衡器创建"""
        balancer = LoadBalancer()
        
        assert balancer.agent_count == 0
        assert balancer.strategy == BalancingStrategy.LEAST_LOADED
    
    def test_register_agent(self):
        """测试注册 Agent"""
        balancer = LoadBalancer()
        
        load = balancer.register_agent("agent-1")
        
        assert load is not None
        assert load.agent_id == "agent-1"
        assert balancer.agent_count == 1
    
    def test_update_load(self):
        """测试更新负载"""
        balancer = LoadBalancer()
        balancer.register_agent("agent-1")
        
        load = balancer.update_load(
            "agent-1",
            cpu_usage=50.0,
            memory_usage=30.0,
            task_count=5,
        )
        
        assert load.cpu_usage == 50.0
        assert load.memory_usage == 30.0
        assert load.task_count == 5
    
    def test_load_calculation(self):
        """测试负载计算"""
        load = AgentLoad(agent_id="test", cpu_usage=50.0, memory_usage=50.0)
        
        # 负载应该 > 0
        assert load.total_load > 0
        assert 0 <= load.normalized_load <= 1
    
    def test_select_least_loaded(self):
        """测试选择最低负载"""
        balancer = LoadBalancer(strategy=BalancingStrategy.LEAST_LOADED)
        
        balancer.register_agent("agent-1")
        balancer.register_agent("agent-2")
        
        balancer.update_load("agent-1", cpu_usage=80.0)
        balancer.update_load("agent-2", cpu_usage=20.0)
        
        selected = balancer.select_agent()
        
        # 应该选择 agent-2
        assert selected == "agent-2"


class TestConsensus:
    """共识机制测试"""
    
    def test_quorum_consensus(self):
        """测试多数决共识"""
        consensus = QuorumConsensus()
        
        participants = ["agent-1", "agent-2", "agent-3"]
        result = consensus.propose(
            round_id="round-1",
            value="decision",
            participants=participants,
        )
        
        assert result.protocol == ConsensusProtocol.QUORUM
        
        # 投票
        consensus.vote("round-1", "agent-1", "decision")
        consensus.vote("round-1", "agent-2", "decision")
        
        # 两票应该超过多数
        decision = consensus.check_decision("round-1")
        assert decision == "decision"
    
    def test_weighted_consensus(self):
        """测试加权共识"""
        consensus = WeightedConsensus()
        
        consensus.set_weight("agent-1", 3.0)
        consensus.set_weight("agent-2", 1.0)
        consensus.set_weight("agent-3", 1.0)
        
        participants = ["agent-1", "agent-2", "agent-3"]
        consensus.propose(
            round_id="round-1",
            value="decision",
            participants=participants,
        )
        
        # agent-1 投同意
        consensus.vote("round-1", "agent-1", "decision")
        
        # agent-2 投反对
        consensus.vote("round-1", "agent-2", "different")
        
        # agent-1 的权重应该使决策通过
        decision = consensus.check_decision("round-1")
        assert decision == "decision"
    
    def test_unanimous_consensus(self):
        """测试全员同意共识"""
        consensus = UnanimousConsensus()
        
        participants = ["agent-1", "agent-2"]
        consensus.propose(
            round_id="round-1",
            value="decision",
            participants=participants,
        )
        
        # 只有一人同意
        consensus.vote("round-1", "agent-1", "decision")
        
        decision = consensus.check_decision("round-1")
        assert decision is None  # 尚未达成共识
        
        # 两人同意
        consensus.vote("round-1", "agent-2", "decision")
        
        decision = consensus.check_decision("round-1")
        assert decision == "decision"


class TestConflictResolver:
    """冲突解决器测试"""
    
    def test_resolver_creation(self):
        """测试解决器创建"""
        resolver = ConflictResolver()
        
        assert resolver.default_strategy == ResolutionStrategy.HIGHEST_PRIORITY
    
    def test_register_conflict(self):
        """测试注册冲突"""
        resolver = ConflictResolver()
        
        conflict = resolver.register_conflict(
            conflict_type=ConflictType.RESOURCE,
            involved_agents=["agent-1", "agent-2"],
            description="Resource conflict",
            positions={"agent-1": "use", "agent-2": "hold"},
        )
        
        assert conflict is not None
        assert conflict.conflict_type == ConflictType.RESOURCE
        assert len(conflict.involved_agents) == 2
    
    def test_resolve_with_priority(self):
        """测试优先级解决策略"""
        resolver = ConflictResolver(
            default_strategy=ResolutionStrategy.HIGHEST_PRIORITY
        )
        
        resolver.set_agent_weight("agent-1", 2.0)
        resolver.set_agent_weight("agent-2", 1.0)
        
        conflict = resolver.register_conflict(
            conflict_type=ConflictType.RESOURCE,
            involved_agents=["agent-1", "agent-2"],
            positions={"agent-1": "use", "agent-2": "hold"},
        )
        
        result = resolver.resolve(conflict.conflict_id)
        
        assert result.success is True
        assert result.winner_id == "agent-1"
    
    def test_resolve_with_voting(self):
        """测试投票解决策略"""
        resolver = ConflictResolver()
        
        conflict = resolver.register_conflict(
            conflict_type=ConflictType.DECISION,
            involved_agents=["agent-1", "agent-2", "agent-3"],
            positions={
                "agent-1": "option_a",
                "agent-2": "option_a",
                "agent-3": "option_b",
            },
        )
        
        result = resolver.resolve(
            conflict.conflict_id,
            strategy=ResolutionStrategy.WEIGHTED_VOTING,
        )
        
        assert result.success is True
        assert result.resolution == "option_a"


class TestCollaborationEngine:
    """协作引擎测试"""
    
    def test_engine_creation(self):
        """测试引擎创建"""
        engine = CollaborationEngine()
        
        assert engine.dispatcher is not None
        assert engine.load_balancer is not None
        assert engine.conflict_resolver is not None
    
    def test_register_agent(self):
        """测试注册 Agent"""
        engine = CollaborationEngine()
        
        engine.register_agent("agent-1", weight=1.0)
        
        agents = engine.get_registered_agents()
        assert "agent-1" in agents
    
    def test_submit_and_dispatch_task(self):
        """测试提交和分发任务"""
        engine = CollaborationEngine()
        engine.register_agent("agent-1")
        
        task = engine.submit_task(
            name="Task 1",
            payload={"data": "test"},
            priority=TaskPriority.HIGH,
        )
        
        assert task is not None
        
        dispatched = engine.dispatch_next_task("agent-1")
        
        assert dispatched is not None
        assert dispatched.task_id == task.task_id
    
    def test_update_load(self):
        """测试更新负载"""
        engine = CollaborationEngine()
        engine.register_agent("agent-1")
        
        load = engine.update_agent_load(
            "agent-1",
            cpu_usage=50.0,
            memory_usage=30.0,
        )
        
        assert load is not None
    
    def test_detect_and_resolve_conflict(self):
        """测试检测和解决冲突"""
        engine = CollaborationEngine()
        
        conflict = engine.detect_conflict(
            involved_agents=["agent-1", "agent-2"],
            conflict_type=ConflictType.RESOURCE,
            positions={"agent-1": "use", "agent-2": "hold"},
        )
        
        assert conflict is not None
        
        result = engine.resolve_conflict(conflict.conflict_id)
        
        assert result.success is True
    
    def test_propose_decision(self):
        """测试提案决策"""
        engine = CollaborationEngine()
        engine.register_agent("agent-1")
        engine.register_agent("agent-2")
        
        round_id = engine.propose_decision(
            value="test_decision",
            participants=["agent-1", "agent-2"],
        )
        
        assert round_id is not None
        
        # 投票
        engine.vote(round_id, "agent-1", "test_decision")
        engine.vote(round_id, "agent-2", "test_decision")
        
        decision = engine.check_consensus(round_id)
        assert decision == "test_decision"
    
    def test_get_status(self):
        """测试获取状态"""
        engine = CollaborationEngine()
        engine.register_agent("agent-1")
        
        status = engine.get_status()
        
        assert "registered_agents" in status
        assert status["registered_agents"] == 1
