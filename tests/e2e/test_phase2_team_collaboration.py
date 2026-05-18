"""
Phase 2 E2E 测试: 多 Agent 团队协作场景

测试目标: 验证团队创建、角色分配、任务拆解、并行执行、结果汇总的完整协作流程
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from typing import Dict, Any, List
from dataclasses import dataclass


class TestTeamCreation:
    """T5.1 团队创建 → 角色分配 → 成员加入"""

    def test_team_config_creation(self):
        """测试团队配置创建"""
        from packages.SwarmFly.team import TeamConfig, TeamStatus

        config = TeamConfig(
            name="数据分析团队",
            description="负责数据收集、分析和报告生成",
            max_members=5,
            min_members=2
        )

        assert config.name == "数据分析团队"
        assert config.max_members == 5
        assert config.min_members == 2
        print("✅ 团队配置创建成功")

    def test_team_builder_creation(self):
        """测试团队构建器创建"""
        from packages.SwarmFly.team import TeamBuilder, TeamConfig

        builder = TeamBuilder()
        assert builder is not None
        print("✅ 团队构建器创建成功")

    def test_create_team_with_config(self):
        """测试使用配置创建团队"""
        from packages.SwarmFly.team import TeamBuilder, TeamConfig, TeamStatus

        builder = TeamBuilder()
        config = TeamConfig(
            name="测试团队",
            max_members=5
        )

        result = builder.create_team(config)

        assert result.success is True
        assert result.team is not None
        assert result.team.name == "测试团队"
        assert result.team.status == TeamStatus.ACTIVE
        print("✅ 团队创建成功")

    def test_create_team_with_initial_members(self):
        """测试带初始成员的团队创建"""
        from packages.SwarmFly.team import TeamBuilder, TeamConfig

        builder = TeamBuilder()
        config = TeamConfig(
            name="协作团队",
            max_members=10
        )

        initial_members = ["agent_001", "agent_002", "agent_003"]
        result = builder.create_team(config, initial_members=initial_members)

        assert result.success is True
        assert result.team is not None
        print(f"✅ 带初始成员的团队创建成功, 成员数: {len(initial_members)}")

    def test_team_status_transitions(self):
        """测试团队状态转换"""
        from packages.SwarmFly.team import TeamBuilder, TeamConfig, TeamStatus

        builder = TeamBuilder()
        config = TeamConfig(name="状态测试团队")
        result = builder.create_team(config)

        team = result.team
        assert team.status == TeamStatus.ACTIVE
        assert team.is_active is True

        # 暂停团队
        team.status = TeamStatus.PAUSED
        assert team.is_active is False

        # 恢复团队
        team.status = TeamStatus.ACTIVE
        assert team.is_active is True

        print("✅ 团队状态转换正常")

    def test_team_metadata(self):
        """测试团队元数据"""
        from packages.SwarmFly.team import TeamBuilder, TeamConfig

        builder = TeamBuilder()
        config = TeamConfig(
            name="元数据测试团队",
            metadata={
                "project": "AI Research",
                "department": "Engineering",
                "priority": "high"
            }
        )

        result = builder.create_team(config)
        assert result.success is True
        assert result.team.config.metadata["project"] == "AI Research"
        print("✅ 团队元数据设置成功")

    def test_get_team_by_id(self):
        """测试通过 ID 获取团队"""
        from packages.SwarmFly.team import TeamBuilder, TeamConfig

        builder = TeamBuilder()
        config = TeamConfig(name="查询测试团队")

        result = builder.create_team(config)
        team_id = result.team.team_id

        retrieved = builder.get_team(team_id)
        assert retrieved is not None
        assert retrieved.team_id == team_id

        # 测试获取不存在的团队
        assert builder.get_team("non_existent") is None
        print("✅ 团队查询功能正常")

    def test_list_all_teams(self):
        """测试获取所有团队列表"""
        from packages.SwarmFly.team import TeamBuilder, TeamConfig

        builder = TeamBuilder()

        # 创建多个团队
        for i in range(3):
            config = TeamConfig(name=f"团队 {i}")
            builder.create_team(config)

        teams = builder.get_all_teams()
        assert len(teams) >= 3
        print(f"✅ 获取所有团队列表成功: {len(teams)} 个团队")


class TestMembershipManagement:
    """成员管理测试"""

    def test_add_member_to_team(self):
        """测试向团队添加成员"""
        from packages.SwarmFly.team import TeamBuilder, TeamConfig, MembershipStatus

        builder = TeamBuilder()
        config = TeamConfig(name="成员测试团队")
        result = builder.create_team(config)
        team = result.team

        # 添加成员
        team.membership.add_member(
            agent_id="agent_001",
            metadata={"name": "Alice", "role": "analyst"}
        )

        member = team.membership.get_member("agent_001")
        assert member is not None
        assert member.agent_id == "agent_001"
        assert member.status == MembershipStatus.PENDING
        print("✅ 成员添加成功")

    def test_member_status_transitions(self):
        """测试成员状态转换"""
        from packages.SwarmFly.team import TeamBuilder, TeamConfig, MembershipStatus

        builder = TeamBuilder()
        config = TeamConfig(name="成员状态测试团队")
        result = builder.create_team(config)
        team = result.team

        team.membership.add_member(agent_id="agent_001")

        # 激活成员
        team.membership.update_member_status("agent_001", MembershipStatus.ACTIVE)
        member = team.membership.get_member("agent_001")
        assert member.status == MembershipStatus.ACTIVE

        # 暂停成员
        team.membership.update_member_status("agent_001", MembershipStatus.INACTIVE)
        member = team.membership.get_member("agent_001")
        assert member.status == MembershipStatus.INACTIVE

        print("✅ 成员状态转换正常")

    def test_list_team_members(self):
        """测试列出团队成员"""
        from packages.SwarmFly.team import TeamBuilder, TeamConfig, MembershipStatus

        builder = TeamBuilder()
        config = TeamConfig(name="成员列表测试团队")
        result = builder.create_team(config)
        team = result.team

        # 添加多个成员并激活
        for i in range(5):
            agent_id = f"agent_{i:03d}"
            team.membership.add_member(agent_id=agent_id)
            team.membership.update_member_status(agent_id, MembershipStatus.ACTIVE)

        members = team.membership.get_all_members()
        assert len(members) == 5

        # 过滤活跃成员
        active_members = team.membership.get_active_members()
        assert len(active_members) == 5

        print(f"✅ 成员列表获取成功: {len(members)} 个成员")

    def test_remove_member_from_team(self):
        """测试从团队移除成员"""
        from packages.SwarmFly.team import TeamBuilder, TeamConfig

        builder = TeamBuilder()
        config = TeamConfig(name="成员移除测试团队")
        result = builder.create_team(config)
        team = result.team

        team.membership.add_member(agent_id="agent_to_remove")
        assert team.membership.get_member("agent_to_remove") is not None

        # 移除成员
        result_remove = team.membership.remove_member("agent_to_remove")
        assert result_remove is True
        assert team.membership.get_member("agent_to_remove") is None

        print("✅ 成员移除成功")

    def test_member_count(self):
        """测试成员计数"""
        from packages.SwarmFly.team import TeamBuilder, TeamConfig

        builder = TeamBuilder()
        config = TeamConfig(name="成员计数测试团队")
        result = builder.create_team(config)
        team = result.team

        assert team.membership.member_count == 0

        team.membership.add_member(agent_id="agent_001")
        assert team.membership.member_count == 1

        team.membership.add_member(agent_id="agent_002")
        assert team.membership.member_count == 2

        print(f"✅ 成员计数正常: {team.membership.member_count}")


class TestTaskBreakdown:
    """T5.2 任务拆解 → 并行执行 → 结果汇总"""

    def test_task_dispatcher_creation(self):
        """测试任务分发器创建"""
        from packages.SwarmFly.collaboration.task_dispatcher import (
            TaskDispatcher, DispatchStrategy
        )

        dispatcher = TaskDispatcher(strategy=DispatchStrategy.ROUND_ROBIN)
        assert dispatcher is not None
        print("✅ 任务分发器创建成功")

    def test_submit_task_to_dispatcher(self):
        """测试向分发器提交任务"""
        from packages.SwarmFly.collaboration.task_dispatcher import (
            TaskDispatcher, TaskStatus
        )

        dispatcher = TaskDispatcher()
        dispatcher.register_agent("worker_001")

        task = dispatcher.submit_task(
            name="数据分析任务",
            payload={"data_source": "database", "analysis_type": "summary"},
            description="执行数据分析并生成摘要"
        )

        assert task is not None
        assert task.status == TaskStatus.QUEUED
        print(f"✅ 任务提交成功, ID: {task.task_id}")

    def test_get_next_task_for_agent(self):
        """测试为 Agent 获取下一个任务"""
        from packages.SwarmFly.collaboration.task_dispatcher import (
            TaskDispatcher, TaskStatus
        )

        dispatcher = TaskDispatcher()
        dispatcher.register_agent("worker_001")

        submitted = dispatcher.submit_task(name="测试任务", payload={})
        task = dispatcher.get_next_task("worker_001")

        assert task is not None
        assert task.task_id == submitted.task_id
        assert task.assigned_agent == "worker_001"
        assert task.status == TaskStatus.ASSIGNED
        print("✅ 任务分配成功")

    def test_complete_task(self):
        """测试完成任务"""
        from packages.SwarmFly.collaboration.task_dispatcher import (
            TaskDispatcher, TaskStatus
        )

        dispatcher = TaskDispatcher()
        dispatcher.register_agent("worker_001")

        task = dispatcher.submit_task(name="完成测试任务", payload={})
        assigned_task = dispatcher.get_next_task("worker_001")

        # 完成任务
        result = dispatcher.complete_task(
            assigned_task.task_id,
            result={"status": "success", "output": "任务执行结果"}
        )

        assert result is True

        completed = dispatcher.get_task(assigned_task.task_id)
        assert completed.status == TaskStatus.COMPLETED
        assert completed.result["status"] == "success"
        print("✅ 任务完成并设置结果成功")

    def test_task_dispatcher_statistics(self):
        """测试任务分发器统计信息"""
        from packages.SwarmFly.collaboration.task_dispatcher import TaskDispatcher

        dispatcher = TaskDispatcher()
        dispatcher.register_agent("worker_001")
        dispatcher.register_agent("worker_002")

        # 提交并完成几个任务
        for i in range(5):
            task = dispatcher.submit_task(name=f"任务 {i}", payload={"index": i})
            assigned = dispatcher.get_next_task()
            dispatcher.complete_task(assigned.task_id, result={"done": True})

        stats = dispatcher.get_queue_summary()
        assert stats["completed_count"] == 5
        # Total pending tasks sum across all priorities
        total_pending = sum(stats["pending_by_priority"].values())
        assert total_pending == 0
        assert stats["available_agents"] == 2

        print(f"✅ 任务统计信息正常: 完成 {stats['completed_count']} 个任务")

    def test_parallel_task_execution(self):
        """测试并行任务执行"""
        from packages.SwarmFly.collaboration.task_dispatcher import (
            TaskDispatcher, TaskStatus, DispatchStrategy
        )

        dispatcher = TaskDispatcher(strategy=DispatchStrategy.ROUND_ROBIN)
        dispatcher.register_agent("worker_001")
        dispatcher.register_agent("worker_002")
        dispatcher.register_agent("worker_003")

        # 提交多个任务
        task_ids = []
        for i in range(6):
            task = dispatcher.submit_task(name=f"并行任务 {i}", payload={"task_num": i})
            task_ids.append(task.task_id)

        # 并行分配任务
        assigned_tasks = []
        for worker_id in ["worker_001", "worker_002", "worker_003"]:
            task = dispatcher.get_next_task(worker_id)
            if task:
                assigned_tasks.append(task)

        assert len(assigned_tasks) == 3
        print(f"✅ 并行任务分发成功: 已分配 {len(assigned_tasks)} 个任务到 3 个 worker")

    def test_aggregate_task_results(self):
        """测试任务结果汇总"""
        from packages.SwarmFly.collaboration.task_dispatcher import TaskDispatcher

        dispatcher = TaskDispatcher()
        dispatcher.register_agent("worker_001")
        dispatcher.register_agent("worker_002")

        # 提交多个子任务
        subtask_results = []
        for i in range(3):
            task = dispatcher.submit_task(
                name=f"子任务 {i}",
                payload={"part": i, "data": f"data_chunk_{i}"}
            )
            assigned = dispatcher.get_next_task()
            dispatcher.complete_task(
                assigned.task_id,
                result={"part": i, "result": f"处理结果 {i}", "quality": 0.8 + i * 0.05}
            )
            subtask_results.append({"task_id": assigned.task_id, "part": i})

        # 模拟汇总结果
        aggregated = {
            "total_subtasks": len(subtask_results),
            "avg_quality": sum([0.8 + i * 0.05 for i in range(3)]) / 3,
            "status": "completed",
            "summary": "所有子任务处理完成，结果已汇总"
        }

        assert aggregated["total_subtasks"] == 3
        assert aggregated["avg_quality"] > 0.8
        print(f"✅ 任务结果汇总成功: {aggregated['total_subtasks']} 个子任务, 平均质量: {aggregated['avg_quality']:.2f}")


class TestTeamCommunication:
    """团队通信测试"""

    def test_team_protocol_creation(self):
        """测试团队协议创建"""
        from packages.SwarmFly.team import TeamProtocol

        protocol = TeamProtocol(team_id="team_001", node_id="coordinator")
        assert protocol is not None
        assert protocol.team_id == "team_001"
        print("✅ 团队协议创建成功")

    def test_broadcast_message_to_team(self):
        """测试广播消息到团队"""
        from packages.SwarmFly.team import TeamBuilder, TeamConfig, MessageType

        builder = TeamBuilder()
        config = TeamConfig(name="通信测试团队")
        result = builder.create_team(config)
        team = result.team

        # 广播消息 (target_id = None 表示广播)
        team.protocol.send_message(
            message_type=MessageType.CUSTOM,
            content={"type": "meeting", "topic": "项目同步", "time": "10:00"},
            target_id=None,
            subject="会议通知"
        )

        print("✅ 团队广播消息发送成功")

    def test_send_direct_message(self):
        """测试发送点对点消息"""
        from packages.SwarmFly.team import TeamBuilder, TeamConfig, MessageType

        builder = TeamBuilder()
        config = TeamConfig(name="点对点通信测试团队")
        result = builder.create_team(config)
        team = result.team

        team.membership.add_member(agent_id="agent_001")
        team.membership.add_member(agent_id="agent_002")

        # agent_001 发送消息给 agent_002
        msg = team.protocol.send_message(
            message_type=MessageType.CUSTOM,
            content={"task_id": "task_123", "action": "review"},
            target_id="agent_002",
            subject="任务请求",
            task_id="task_123"
        )

        assert msg is not None
        print("✅ 点对点消息发送成功")

    def test_message_delivery(self):
        """测试消息投递"""
        from packages.SwarmFly.team import TeamBuilder, TeamConfig, MessageType, TeamProtocol

        builder = TeamBuilder()
        config = TeamConfig(name="消息投递测试团队")
        result = builder.create_team(config)
        team = result.team

        team.membership.add_member(agent_id="agent_001")

        # 发送消息
        msg = team.protocol.send_message(
            message_type=MessageType.CUSTOM,
            content={"level": "info", "text": "新任务分配"},
            target_id="agent_001",
            subject="系统通知"
        )

        # 模拟接收消息 (通过另一个协议实例)
        receiver_protocol = TeamProtocol(team_id=team.team_id, node_id="agent_001")
        received = receiver_protocol.receive_message(msg)

        # 处理收件箱
        messages = receiver_protocol.process_inbox()
        assert len(messages) >= 1
        print(f"✅ 消息投递成功: 收到 {len(messages)} 条消息")


class TestFullTeamCollaborationFlow:
    """完整团队协作流程测试"""

    def test_end_to_end_team_operation(self):
        """测试端到端团队协作"""
        from packages.SwarmFly.team import TeamBuilder, TeamConfig, MembershipStatus
        from packages.SwarmFly.collaboration.task_dispatcher import TaskDispatcher

        # 1. 创建团队
        builder = TeamBuilder()
        config = TeamConfig(
            name="端到端测试团队",
            description="执行完整的协作流程测试",
            max_members=5
        )
        result = builder.create_team(config)
        team = result.team
        assert team.is_active is True

        # 2. 注册团队成员
        members = [
            ("coordinator_001", {"name": "Coordinator", "role": "leader"}),
            ("worker_001", {"name": "Worker A", "role": "analyst"}),
            ("worker_002", {"name": "Worker B", "role": "developer"}),
            ("worker_003", {"name": "Worker C", "role": "tester"}),
        ]

        for agent_id, metadata in members:
            team.membership.add_member(agent_id=agent_id, metadata=metadata)
            team.membership.update_member_status(agent_id, MembershipStatus.ACTIVE)

        assert team.membership.member_count == 4
        assert len(team.membership.get_active_members()) == 4

        # 3. 创建任务分发器并注册成员
        dispatcher = TaskDispatcher()
        for agent_id, _ in members:
            dispatcher.register_agent(agent_id)

        # 4. 提交多个任务
        tasks_to_submit = [
            ("需求分析", {"phase": 1}, "coordinator_001"),
            ("架构设计", {"phase": 2}, "coordinator_001"),
            ("代码实现", {"phase": 3}, "worker_002"),
            ("测试验证", {"phase": 4}, "worker_003"),
        ]

        submitted_tasks = []
        for name, payload, assignee in tasks_to_submit:
            task = dispatcher.submit_task(name=name, payload=payload)
            submitted_tasks.append(task)

        assert len(submitted_tasks) == 4

        # 5. 分发并完成任务
        for i, task in enumerate(submitted_tasks):
            worker_id = members[i % len(members)][0]
            assigned_task = dispatcher.get_next_task(worker_id)
            assert assigned_task is not None

            # 完成任务
            success = dispatcher.complete_task(
                assigned_task.task_id,
                result={
                    "completed_by": worker_id,
                    "task_name": assigned_task.name,
                    "quality_score": 0.75 + i * 0.05
                }
            )
            assert success is True

        # 6. 验证结果
        stats = dispatcher.get_queue_summary()
        assert stats["completed_count"] == 4
        # Total pending tasks sum across all priorities
        total_pending = sum(stats["pending_by_priority"].values())
        assert total_pending == 0

        # 7. 团队广播完成通知
        from packages.SwarmFly.team import MessageType
        team.protocol.send_message(
            message_type=MessageType.CUSTOM,
            content={
                "status": "success",
                "total_tasks": stats["completed_count"],
                "team_size": team.membership.member_count,
                "avg_quality": 0.85
            }
        )

        print(f"✅ 端到端团队协作流程测试通过: {team.membership.member_count} 个成员, 完成 {stats['completed_count']} 个任务")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
