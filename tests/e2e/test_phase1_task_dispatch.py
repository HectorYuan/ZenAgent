"""
Phase 1 E2E 测试: 任务分发与协作流程

测试目标: 验证任务从创建、分发、执行到完成的完整协作流程
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import asyncio
from typing import Dict, Any, List


class TestTaskCreation:
    """T2.1 单任务创建 → 分发 → 执行 → 完成"""

    def test_task_router_creation(self):
        """测试任务路由器创建"""
        from packages.ZenAgent.collaboration.task_router import TaskRouter, RouteStrategy

        router = TaskRouter()
        assert router is not None
        assert len(router._rules) >= 1  # 默认规则
        print("✅ 任务路由器创建成功")

    def test_task_route_creation(self):
        """测试路由结果对象创建"""
        from packages.ZenAgent.collaboration.task_router import TaskRoute, RouteStrategy

        route = TaskRoute(
            target_agent_id="agent_001",
            strategy=RouteStrategy.BEST_CAPABILITY,
            confidence=0.8,
            reason="Test routing",
            task_type="analysis"
        )
        assert route.target_agent_id == "agent_001"
        assert route.is_valid is True
        print("✅ 任务路由对象创建成功")

    def test_routing_rule_creation(self):
        """测试路由规则创建"""
        from packages.ZenAgent.collaboration.task_router import (
            RoutingRule, RouteStrategy, AgentCapability
        )

        rule = RoutingRule(
            name="analysis_rule",
            description="Analysis tasks",
            task_type="analysis",
            required_capabilities=[AgentCapability.TEXT_GENERATION],
            strategy=RouteStrategy.BEST_CAPABILITY,
            priority=10
        )
        assert rule.name == "analysis_rule"
        assert rule.priority == 10
        print("✅ 路由规则创建成功")

    def test_routing_rule_matching(self):
        """测试路由规则匹配"""
        from packages.ZenAgent.collaboration.task_router import (
            RoutingRule, AgentCapability
        )

        rule = RoutingRule(
            name="analysis_rule",
            task_type="analysis",
            required_capabilities=[AgentCapability.TEXT_GENERATION],
        )

        # 匹配的情况
        assert rule.matches(
            task_type="analysis",
            capabilities=[AgentCapability.TEXT_GENERATION],
            tags=[]
        ) is True

        # 不匹配的情况（任务类型不同）
        assert rule.matches(
            task_type="generation",
            capabilities=[AgentCapability.TEXT_GENERATION],
            tags=[]
        ) is False

        print("✅ 路由规则匹配成功")

    def test_add_remove_rule(self):
        """测试添加和移除规则"""
        from packages.ZenAgent.collaboration.task_router import TaskRouter, RoutingRule

        router = TaskRouter()
        initial_count = len(router._rules)

        rule = RoutingRule(name="test_rule", priority=100)
        router.add_rule(rule)

        assert len(router._rules) == initial_count + 1
        assert router.get_rule(rule.rule_id) is not None

        # 移除规则
        result = router.remove_rule(rule.rule_id)
        assert result is True
        assert len(router._rules) == initial_count

        print("✅ 添加和移除规则成功")


class TestAgentRegistryIntegration:
    """测试任务路由器与 Agent 注册表集成"""

    def test_set_registry(self):
        """测试设置注册表"""
        from packages.ZenAgent.collaboration.task_router import TaskRouter
        from packages.ZenAgent.mcp.registry import AgentRegistry

        router = TaskRouter()
        registry = AgentRegistry()

        router.set_registry(registry)
        assert router._registry is not None
        print("✅ 设置注册表成功")

    def test_route_without_registry(self):
        """测试无注册表时的路由"""
        from packages.ZenAgent.collaboration.task_router import TaskRouter

        router = TaskRouter()
        route = router.route(task_type="analysis")

        assert route.is_valid is False  # 没有可用的 Agent
        print("✅ 无注册表时路由处理正确")

    def test_route_with_agents(self):
        """测试有 Agent 时的路由"""
        from packages.ZenAgent.collaboration.task_router import TaskRouter, RouteStrategy
        from packages.ZenAgent.mcp.registry import AgentRegistry, AgentMetadata, AgentCapability

        router = TaskRouter()
        registry = AgentRegistry()
        router.set_registry(registry)

        # 注册 Agent
        metadata = AgentMetadata(
            agent_id="agent_001",
            name="Test Agent",
            capabilities=[AgentCapability.TEXT_GENERATION],
            version="1.0.0"
        )
        registry.register(metadata)

        # 路由任务
        route = router.route(
            task_type="analysis",
            required_capabilities=[AgentCapability.TEXT_GENERATION],
            strategy=RouteStrategy.BEST_CAPABILITY
        )

        assert route.is_valid is True
        assert route.target_agent_id == "agent_001"
        print(f"✅ 任务路由成功: {route.target_agent_id}, 置信度: {route.confidence:.2f}")

    def test_random_routing_strategy(self):
        """测试随机路由策略"""
        from packages.ZenAgent.collaboration.task_router import TaskRouter, RouteStrategy
        from packages.ZenAgent.mcp.registry import AgentRegistry, AgentMetadata, AgentCapability

        router = TaskRouter()
        registry = AgentRegistry()
        router.set_registry(registry)

        # 注册多个 Agent
        for i in range(3):
            metadata = AgentMetadata(
                agent_id=f"agent_{i:03d}",
                name=f"Agent {i}",
                capabilities=[AgentCapability.TEXT_GENERATION],
                version="1.0.0"
            )
            registry.register(metadata)

        # 多次路由验证随机性
        targets = set()
        for _ in range(10):
            route = router.route(
                task_type="analysis",
                strategy=RouteStrategy.RANDOM
            )
            targets.add(route.target_agent_id)

        assert len(targets) > 1  # 应该有多个不同的目标
        print(f"✅ 随机路由策略正常: {len(targets)} 个不同的 Agent")

    def test_round_robin_routing(self):
        """测试轮询路由策略"""
        from packages.ZenAgent.collaboration.task_router import TaskRouter, RouteStrategy
        from packages.ZenAgent.mcp.registry import AgentRegistry, AgentMetadata, AgentCapability

        router = TaskRouter()
        registry = AgentRegistry()
        router.set_registry(registry)

        # 注册多个 Agent
        for i in range(3):
            metadata = AgentMetadata(
                agent_id=f"agent_{i:03d}",
                name=f"Agent {i}",
                capabilities=[AgentCapability.TEXT_GENERATION],
                version="1.0.0"
            )
            registry.register(metadata)

        # 轮询多次
        targets = []
        for _ in range(6):
            route = router.route(
                task_type="analysis",
                strategy=RouteStrategy.ROUND_ROBIN
            )
            targets.append(route.target_agent_id)

        assert len(targets) == 6
        print(f"✅ 轮询路由策略正常: {targets}")


class TestTaskPriority:
    """T2.3 任务优先级排序"""

    def test_message_priority_enum(self):
        """测试消息优先级枚举"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessagePriority

        assert MessagePriority.CRITICAL.value == 0
        assert MessagePriority.URGENT.value == 1
        assert MessagePriority.NORMAL.value == 2
        assert MessagePriority.LOW.value == 3
        print("✅ 消息优先级枚举正常")

    def test_message_with_priority(self):
        """测试带优先级的消息"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import Message, MessageType, MessagePriority

        message = Message(
            message_id="msg_001",
            message_type=MessageType.TASK,
            sender="agent_001",
            receiver="agent_002",
            content={"task": "analysis"},
            priority=MessagePriority.URGENT
        )

        assert message.priority == MessagePriority.URGENT
        print("✅ 带优先级的消息创建成功")


class TestCollaborationProtocols:
    """测试协作协议"""

    def test_collaboration_message_creation(self):
        """测试协作消息创建"""
        from packages.ZenAgent.collaboration.protocols import (
            CollaborationMessage, ProtocolType, MessagePriority
        )

        message = CollaborationMessage(
            sender_id="agent_001",
            sender_name="Agent 1",
            receiver_id="agent_002",
            content="Hello, let's collaborate!",
            priority=MessagePriority.NORMAL
        )

        assert message.sender_id == "agent_001"
        assert message.receiver_id == "agent_002"
        assert message.is_broadcast is False
        print("✅ 协作消息创建成功")

    def test_broadcast_message(self):
        """测试广播消息"""
        from packages.ZenAgent.collaboration.protocols import (
            CollaborationMessage, ProtocolType
        )

        message = CollaborationMessage(
            sender_id="agent_001",
            sender_name="Agent 1",
            content="Broadcast to all",
            protocol=ProtocolType.BROADCAST
        )

        assert message.is_broadcast is True
        print("✅ 广播消息创建成功")

    def test_message_expiry(self):
        """测试消息过期"""
        from packages.ZenAgent.collaboration.protocols import CollaborationMessage

        message = CollaborationMessage(
            sender_id="agent_001",
            sender_name="Agent 1",
            content="Test expiry"
        )

        assert message.is_expired is False

        # 设置立即过期
        message.set_expiry(0)
        import asyncio
        asyncio.run(asyncio.sleep(0.01))  # 等待一小段时间

        assert message.is_expired is True
        print("✅ 消息过期机制正常")

    def test_collaboration_request_creation(self):
        """测试协作请求创建"""
        from packages.ZenAgent.collaboration.protocols import (
            CollaborationProtocol, MessagePriority
        )

        request = CollaborationProtocol.create_request(
            requester_id="agent_001",
            requester_name="Agent 1",
            task_type="analysis",
            task_description="Analyze this data",
            required_capabilities=["text_generation"],
            priority=MessagePriority.HIGH,
            timeout_seconds=120
        )

        assert request.requester_id == "agent_001"
        assert request.task_type == "analysis"
        assert request.timeout_seconds == 120
        print("✅ 协作请求创建成功")

    def test_collaboration_response_creation(self):
        """测试协作响应创建"""
        from packages.ZenAgent.collaboration.protocols import CollaborationProtocol

        response = CollaborationProtocol.create_response(
            request_id="req_001",
            responder_id="agent_002",
            responder_name="Agent 2",
            accepted=True,
            status="completed",
            result={"output": "analysis result"}
        )

        assert response.request_id == "req_001"
        assert response.accepted is True
        assert response.status == "completed"
        print("✅ 协作响应创建成功")

    def test_protocol_task_type_validation(self):
        """测试协议任务类型验证"""
        from packages.ZenAgent.collaboration.protocols import CollaborationProtocol

        # 有效的任务类型
        assert CollaborationProtocol.validate_task_type("analysis") is True
        assert CollaborationProtocol.validate_task_type("generation") is True

        # 无效的任务类型
        assert CollaborationProtocol.validate_task_type("invalid_type") is False

        supported = CollaborationProtocol.get_supported_task_types()
        assert len(supported) >= 6
        print(f"✅ 协议任务类型验证正常: {len(supported)} 种支持的任务类型")

    def test_message_to_dict_and_back(self):
        """测试消息序列化和反序列化"""
        from packages.ZenAgent.collaboration.protocols import (
            CollaborationMessage, ProtocolType, MessagePriority
        )

        original = CollaborationMessage(
            sender_id="agent_001",
            sender_name="Agent 1",
            receiver_id="agent_002",
            content="Test message",
            priority=MessagePriority.HIGH
        )

        # 序列化
        data = original.to_dict()
        assert data["sender_id"] == "agent_001"

        # 反序列化
        restored = CollaborationMessage.from_dict(data)
        assert restored.message_id == original.message_id
        assert restored.content == original.content
        print("✅ 消息序列化和反序列化成功")

    def test_request_to_dict_and_back(self):
        """测试请求序列化和反序列化"""
        from packages.ZenAgent.collaboration.protocols import CollaborationProtocol, CollaborationRequest

        original = CollaborationProtocol.create_request(
            requester_id="agent_001",
            requester_name="Agent 1",
            task_type="analysis",
            task_description="Test task",
            timeout_seconds=60
        )

        # 序列化
        data = original.to_dict()
        assert data["requester_id"] == "agent_001"

        # 反序列化
        restored = CollaborationRequest.from_dict(data)
        assert restored.request_id == original.request_id
        assert restored.task_type == original.task_type
        print("✅ 请求序列化和反序列化成功")


class TestFullTaskFlow:
    """完整任务流测试"""

    def test_complete_task_lifecycle(self):
        """测试完整的任务生命周期"""
        from packages.ZenAgent.collaboration.task_router import TaskRouter, RouteStrategy
        from packages.ZenAgent.mcp.registry import AgentRegistry, AgentMetadata, AgentCapability
        from packages.ZenAgent.collaboration.protocols import CollaborationProtocol

        # 1. 初始化路由器和注册表
        router = TaskRouter()
        registry = AgentRegistry()
        router.set_registry(registry)

        # 2. 注册执行 Agent
        worker_metadata = AgentMetadata(
            agent_id="worker_001",
            name="Worker Agent 1",
            capabilities=[AgentCapability.TEXT_GENERATION, AgentCapability.COLLABORATION],
            version="1.0.0"
        )
        registry.register(worker_metadata)

        # 3. 创建协作请求
        request = CollaborationProtocol.create_request(
            requester_id="client_001",
            requester_name="Client Agent",
            task_type="analysis",
            task_description="Analyze user input data",
            required_capabilities=["text_generation"],
            timeout_seconds=60
        )

        # 4. 路由任务
        route = router.route(
            task_type=request.task_type,
            required_capabilities=[AgentCapability.TEXT_GENERATION],
            strategy=RouteStrategy.BEST_CAPABILITY
        )

        assert route.is_valid is True
        assert route.target_agent_id == "worker_001"

        # 5. 创建协作响应
        response = CollaborationProtocol.create_response(
            request_id=request.request_id,
            responder_id=route.target_agent_id,
            responder_name="Worker Agent 1",
            accepted=True,
            status="completed",
            result={"analysis": "Data analyzed successfully"}
        )

        assert response.accepted is True
        assert response.status == "completed"

        # 6. 记录成功路由
        router.record_success(route.target_agent_id)
        stats = router.get_stats(route.target_agent_id)
        assert stats["successful_routes"] == 1

        print("✅ 完整任务生命周期测试通过")

    def test_routing_stats(self):
        """测试路由统计"""
        from packages.ZenAgent.collaboration.task_router import TaskRouter, RouteStrategy
        from packages.ZenAgent.mcp.registry import AgentRegistry, AgentMetadata, AgentCapability

        router = TaskRouter()
        registry = AgentRegistry()
        router.set_registry(registry)

        # 注册 Agent
        for i in range(2):
            metadata = AgentMetadata(
                agent_id=f"agent_{i:03d}",
                name=f"Agent {i}",
                capabilities=[AgentCapability.TEXT_GENERATION],
                version="1.0.0"
            )
            registry.register(metadata)

        # 执行多次路由
        for _ in range(5):
            route = router.route(task_type="analysis")
            if route.target_agent_id:
                router.record_success(route.target_agent_id)

        # 获取统计
        stats = router.get_stats()
        assert stats["total_routes"] == 5
        assert stats["successful_routes"] == 5
        assert stats["success_rate"] == 1.0

        print(f"✅ 路由统计正常: 成功率 {stats['success_rate']:.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
