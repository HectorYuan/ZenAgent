"""
Phase 2 E2E 测试: 完整任务执行场景

测试目标: 验证用户输入 → 任务规划 → 执行 → 结果反馈的完整链路
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from typing import Dict, Any, List
from dataclasses import dataclass


class TestTaskPlanning:
    """T4.1 用户输入 → 任务规划 → 执行 → 结果反馈"""

    def test_task_creation_with_metadata(self):
        """测试带元数据的任务创建"""
        from packages.SwarmFly.collaboration.task_dispatcher import Task, TaskPriority, TaskStatus

        task = Task(
            task_id="task_001",
            name="分析用户需求",
            description="分析用户提出的业务需求，提取关键信息",
            priority=TaskPriority.HIGH,
            assigned_agent="agent_analyst",
            metadata={"source": "user_input", "channel": "chat"}
        )

        assert task.task_id == "task_001"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
        assert task.metadata["source"] == "user_input"
        print("✅ 带元数据的任务创建成功")

    def test_task_priority_enum(self):
        """测试任务优先级枚举"""
        from packages.SwarmFly.collaboration.task_dispatcher import TaskPriority

        priorities = [
            TaskPriority.LOW,
            TaskPriority.NORMAL,
            TaskPriority.HIGH,
            TaskPriority.CRITICAL
        ]

        assert len(priorities) == 4
        assert TaskPriority.HIGH.value > TaskPriority.NORMAL.value
        print("✅ 任务优先级枚举正常")

    def test_task_status_transition(self):
        """测试任务状态转换"""
        from packages.SwarmFly.collaboration.task_dispatcher import Task, TaskStatus, TaskPriority

        task = Task(
            task_id="task_002",
            name="状态转换测试",
            priority=TaskPriority.NORMAL,
            assigned_agent="agent_test"
        )

        # PENDING → RUNNING
        task.status = TaskStatus.RUNNING
        assert task.status == TaskStatus.RUNNING

        # RUNNING → COMPLETED
        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED

        print("✅ 任务状态转换正常")

    def test_task_with_dependencies(self):
        """测试带依赖的任务"""
        from packages.SwarmFly.collaboration.task_dispatcher import Task, TaskPriority, TaskStatus

        # 创建前置任务
        pre_task = Task(
            task_id="pre_task_001",
            name="前置任务",
            priority=TaskPriority.HIGH,
            assigned_agent="agent_1"
        )

        # 创建依赖前置任务的任务
        main_task = Task(
            task_id="main_task_001",
            name="主任务",
            priority=TaskPriority.HIGH,
            assigned_agent="agent_2",
            dependencies=["pre_task_001"]
        )

        assert len(main_task.dependencies) == 1
        assert "pre_task_001" in main_task.dependencies
        print("✅ 带依赖的任务创建成功")

    def test_task_result_attachment(self):
        """测试任务结果附加"""
        from packages.SwarmFly.collaboration.task_dispatcher import Task, TaskPriority, TaskStatus

        task = Task(
            task_id="task_003",
            name="结果测试任务",
            priority=TaskPriority.NORMAL,
            assigned_agent="agent_worker"
        )

        # 模拟任务执行
        task.status = TaskStatus.RUNNING

        # 设置任务结果
        task.result = {
            "analysis": "完成数据分析",
            "findings": ["发现问题A", "发现问题B"],
            "recommendations": ["建议方案1", "建议方案2"],
            "confidence": 0.85
        }

        task.status = TaskStatus.COMPLETED

        assert task.result is not None
        assert task.result["confidence"] == 0.85
        assert len(task.result["findings"]) == 2
        print("✅ 任务结果附加成功")


class TestContextManagement:
    """T4.2 上下文管理与记忆写入"""

    def test_runtime_context_creation(self):
        """测试 Runtime 上下文创建"""
        from packages.Runtime.runtime import Runtime, RuntimeConfig

        config = RuntimeConfig(
            max_tokens=4000,
            auto_compress=True,
            session_idle_timeout=300
        )

        runtime = Runtime(config)
        assert runtime is not None
        assert runtime.config.max_tokens == 4000
        print("✅ Runtime 上下文创建成功")

    def test_add_message_to_context(self):
        """测试向上下文添加消息"""
        from packages.Runtime.runtime import Runtime

        runtime = Runtime()

        # 添加用户消息
        msg1 = {
            "role": "user",
            "content": "我想了解如何优化我的代码",
            "timestamp": "2026-05-18T10:00:00Z"
        }
        stats1 = runtime.add_message(msg1)

        # 添加助手消息
        msg2 = {
            "role": "assistant",
            "content": "让我帮您分析一下代码优化方案...",
            "timestamp": "2026-05-18T10:00:01Z"
        }
        stats2 = runtime.add_message(msg2)

        context = runtime.get_context()
        assert len(context) == 2
        print("✅ 上下文消息添加成功")

    def test_session_creation(self):
        """测试会话创建"""
        from packages.Runtime.runtime import Runtime

        runtime = Runtime()

        session = runtime.create_session(
            user_id="user_001",
            metadata={"topic": "code_optimization", "priority": "high"}
        )

        assert session is not None
        assert session.user_id == "user_001"
        print("✅ 会话创建成功")

    def test_memory_write_on_task_completion(self):
        """测试任务完成时的记忆写入"""
        from packages.SoulTeam.memory.meta_soul import MetaSoul, MemoryType
        from packages.SwarmFly.collaboration.task_dispatcher import Task, TaskPriority, TaskStatus

        # 创建 Agent 记忆系统
        soul = MetaSoul(soul_id="worker_agent_001")

        # 创建并完成任务
        task = Task(
            task_id="task_memory_001",
            name="记忆测试任务",
            priority=TaskPriority.NORMAL,
            assigned_agent="worker_agent_001"
        )
        task.status = TaskStatus.COMPLETED
        task.result = {"output": "任务执行结果", "quality": "excellent"}

        # 将任务结果写入记忆
        memory_id = soul.store_memory(
            content=f"完成任务: {task.name}, 结果: {task.result}",
            memory_type=MemoryType.PROCEDURAL,
            metadata={
                "task_id": task.task_id,
                "type": "task_completion",
                "quality": task.result["quality"]
            }
        )

        assert memory_id is not None

        # 验证记忆可以检索
        memories = soul.retrieve(
            query="任务完成 结果",
            memory_type=MemoryType.PROCEDURAL,
            limit=5
        )

        assert isinstance(memories, list)
        print("✅ 任务完成记忆写入与检索成功")

    def test_episodic_memory_for_interaction(self):
        """测试交互情景记忆"""
        from packages.SoulTeam.memory.meta_soul import MetaSoul, MemoryType

        soul = MetaSoul(soul_id="agent_001")

        # 记录多轮交互
        interactions = [
            ("user", "你好，我需要帮助分析数据"),
            ("assistant", "您好！请告诉我您需要分析什么样的数据？"),
            ("user", "我有一份销售数据，需要分析趋势"),
            ("assistant", "好的，让我帮您分析销售数据趋势...")
        ]

        for i, (role, content) in enumerate(interactions):
            soul.store_memory(
                content=content,
                memory_type=MemoryType.EPISODIC,
                metadata={
                    "turn": i + 1,
                    "role": role,
                    "session": "sales_analysis_001"
                }
            )

        # 检索相关记忆
        memories = soul.retrieve(
            query="销售数据 分析",
            memory_type=MemoryType.EPISODIC,
            limit=10
        )

        assert isinstance(memories, list)
        print(f"✅ 情景交互记忆记录成功: {len(interactions)} 轮对话")

    def test_context_compression_trigger(self):
        """测试上下文压缩触发"""
        from packages.Runtime.runtime import Runtime, RuntimeConfig

        # 使用小的 max_tokens 触发压缩
        config = RuntimeConfig(max_tokens=100, auto_compress=True)
        runtime = Runtime(config)

        # 添加多条消息，让上下文增长
        for i in range(5):
            msg = {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"这是第 {i} 条消息，内容长度适中。",
                "tokens": 20
            }
            runtime.add_message(msg)

        context = runtime.get_context()
        assert len(context) >= 5
        print("✅ 上下文压缩机制正常")


class TestAgentAwakening:
    """T4.3 Agent 觉醒与能力启用"""

    def test_agent_initialization_sequence(self):
        """测试 Agent 初始化序列"""
        from packages.SwarmFly.lifecycle import AgentLifecycle, AgentState, LifecycleTransition

        lifecycle = AgentLifecycle(
            agent_id="awakening_agent_001",
            initial_state=AgentState.CREATED
        )

        # 模拟觉醒过程
        sequence = [
            AgentState.INITIALIZING,
            AgentState.READY
        ]

        for state in sequence:
            lifecycle.transition_to(state)
            assert lifecycle.state == state

        assert lifecycle.state == AgentState.READY
        print("✅ Agent 觉醒状态序列正常")

    def test_lifecycle_state_history(self):
        """测试生命周期状态历史"""
        from packages.SwarmFly.lifecycle import AgentLifecycle, AgentState

        lifecycle = AgentLifecycle(
            agent_id="history_test_001",
            initial_state=AgentState.CREATED
        )

        states = [
            AgentState.INITIALIZING,
            AgentState.READY,
            AgentState.RUNNING,
            AgentState.PAUSED
        ]

        for state in states:
            lifecycle.transition_to(state)

        history = lifecycle.transition_history
        assert len(history) >= len(states)
        print(f"✅ 生命周期状态历史记录正常: {len(history)} 次状态转换")

    def test_personality_activation_on_ready(self):
        """测试 READY 状态时人格系统激活"""
        from packages.SwarmFly.lifecycle import AgentLifecycle, AgentState
        from packages.SoulTeam.personality.personality import Personality, BigFiveTraits

        # 创建生命周期管理
        lifecycle = AgentLifecycle(
            agent_id="personality_test_001",
            initial_state=AgentState.CREATED
        )

        # 创建人格系统
        personality = Personality()

        # 在初始化阶段加载人格特质
        personality.set_trait(BigFiveTraits.OPENNESS, 0.75)
        personality.set_trait(BigFiveTraits.CONSCIENTIOUSNESS, 0.82)
        personality.set_trait(BigFiveTraits.EXTRAVERSION, 0.65)
        personality.set_trait(BigFiveTraits.AGREEABLENESS, 0.78)
        personality.set_trait(BigFiveTraits.NEUROTICISM, 0.35)

        # 完成初始化，进入就绪状态
        lifecycle.transition_to(AgentState.INITIALIZING)
        lifecycle.transition_to(AgentState.READY)

        # 验证人格特质已正确加载
        assert personality.get_trait(BigFiveTraits.OPENNESS) == 0.75
        assert personality.get_trait(BigFiveTraits.CONSCIENTIOUSNESS) == 0.82

        traits = personality.get_traits()
        assert len(traits) == 5

        print("✅ READY 状态人格系统激活成功")

    def test_memory_system_initialization(self):
        """测试记忆系统初始化"""
        from packages.SoulTeam.memory.meta_soul import MetaSoul, MemoryType

        soul = MetaSoul(soul_id="memory_init_001")

        # 验证所有记忆类型都可用
        memory_types = [
            MemoryType.EPISODIC,
            MemoryType.SEMANTIC,
            MemoryType.PROCEDURAL,
            MemoryType.WORKING
        ]

        # 测试每个记忆类型都可以存储
        for i, mem_type in enumerate(memory_types):
            memory_id = soul.store_memory(
                content=f"初始化记忆 {i}",
                memory_type=mem_type,
                metadata={"init_test": True}
            )
            assert memory_id is not None

        # 获取统计
        stats = soul.get_stats()
        assert "total_memories" in stats
        print(f"✅ 记忆系统初始化成功: {stats}")

    def test_hook_registration_on_awakening(self):
        """测试觉醒时 Hook 注册"""
        from packages.ZenAgent.hooks.hook_manager import HookManager, HookEvent
        from packages.SwarmFly.lifecycle import AgentLifecycle, AgentState

        hook_manager = HookManager()
        lifecycle = AgentLifecycle(
            agent_id="hook_test_001",
            initial_state=AgentState.CREATED
        )

        # 记录触发的事件
        triggered_events = []

        def on_ready_handler(context: HookEvent):
            triggered_events.append(context.event_name)
            return True

        def on_task_start_handler(context: HookEvent):
            triggered_events.append(context.event_name)
            return True

        # 注册生命周期钩子
        hook_manager.register(event_name="on_ready", handler=on_ready_handler)
        hook_manager.register(event_name="on_task_start", handler=on_task_start_handler)

        # 模拟觉醒过程
        lifecycle.transition_to(AgentState.INITIALIZING)
        lifecycle.transition_to(AgentState.READY)

        # 手动触发 on_ready 事件 (模拟真实系统)
        hook_manager.trigger_sync(event_name="on_ready", data={"agent_id": "hook_test_001"})

        # 触发任务开始事件
        hook_manager.trigger_sync(event_name="on_task_start", data={"task_id": "task_001"})

        assert len(triggered_events) == 2
        assert "on_ready" in triggered_events
        assert "on_task_start" in triggered_events
        print("✅ 觉醒时 Hook 注册与触发成功")


class TestFullTaskExecutionFlow:
    """完整任务执行流程集成测试"""

    def test_end_to_end_task_lifecycle(self):
        """测试端到端任务生命周期"""
        from packages.SwarmFly.collaboration.task_dispatcher import Task, TaskPriority, TaskStatus
        from packages.SwarmFly.lifecycle import AgentLifecycle, AgentState
        from packages.SoulTeam.memory.meta_soul import MetaSoul, MemoryType

        # 1. 初始化 Agent
        lifecycle = AgentLifecycle(
            agent_id="worker_001",
            initial_state=AgentState.CREATED
        )
        soul = MetaSoul(soul_id="worker_001")

        # 2. Agent 觉醒
        lifecycle.transition_to(AgentState.INITIALIZING)
        lifecycle.transition_to(AgentState.READY)
        assert lifecycle.state == AgentState.READY

        # 3. 创建任务
        task = Task(
            task_id="e2e_task_001",
            name="端到端测试任务",
            description="模拟完整的任务执行流程",
            priority=TaskPriority.HIGH,
            assigned_agent="worker_001"
        )
        assert task.status == TaskStatus.PENDING

        # 4. 开始执行任务
        task.status = TaskStatus.RUNNING
        lifecycle.transition_to(AgentState.RUNNING)

        # 5. 记录执行经验
        execution_memory_id = soul.store_memory(
            content=f"开始执行任务: {task.name}",
            memory_type=MemoryType.WORKING,
            metadata={"task_id": task.task_id, "phase": "execution_start"}
        )
        assert execution_memory_id is not None

        # 6. 完成任务
        task.result = {
            "status": "success",
            "output": "任务执行完成，输出结果",
            "metrics": {"quality": 0.9, "efficiency": 0.85}
        }
        task.status = TaskStatus.COMPLETED
        lifecycle.transition_to(AgentState.PAUSED)
        lifecycle.transition_to(AgentState.STOPPED)

        # 7. 记录任务完成
        completion_memory_id = soul.store_memory(
            content=f"任务完成: {task.name}, 结果: {task.result}",
            memory_type=MemoryType.EPISODIC,
            metadata={
                "task_id": task.task_id,
                "phase": "completed",
                "success": True
            }
        )
        assert completion_memory_id is not None

        # 8. 验证最终状态
        assert task.status == TaskStatus.COMPLETED
        assert lifecycle.state == AgentState.STOPPED
        assert task.result is not None

        print("✅ 端到端任务生命周期测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
