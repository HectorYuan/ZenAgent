"""
协作模块单元测试
覆盖 protocols / negotiator / task_router 三大组件
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta

from collaboration.protocols import (
    ProtocolType,
    MessagePriority,
    CollaborationMessage,
    CollaborationRequest,
    CollaborationResponse,
    CollaborationProtocol,
)
from collaboration.negotiator import (
    CollaborationNegotiator,
    NegotiationResult,
    NegotiationStatus,
    NegotiationResponse,
)
from collaboration.task_router import (
    TaskRouter,
    TaskRoute,
    RouteStrategy,
    RoutingRule,
)
from mcp.registry import (
    AgentRegistry,
    AgentMetadata,
    AgentCapability,
    AgentStatus,
    RegisteredAgent,
)


# ============================================================
# 协议层 (protocols.py)
# ============================================================

class TestProtocolEnums:
    """协议枚举测试"""

    def test_protocol_type_values(self):
        """测试协议类型枚举包含所有预期值"""
        expected = {"direct", "broadcast", "anycast", "multicast", "hierarchical"}
        actual = {pt.value for pt in ProtocolType}
        assert expected == actual

    def test_message_priority_ordering(self):
        """测试消息优先级数值递增"""
        assert MessagePriority.LOW.value < MessagePriority.NORMAL.value
        assert MessagePriority.NORMAL.value < MessagePriority.HIGH.value
        assert MessagePriority.HIGH.value < MessagePriority.URGENT.value


class TestCollaborationMessage:
    """协作消息测试"""

    def test_message_creation_and_to_dict(self):
        """测试消息创建及序列化"""
        msg = CollaborationMessage(
            sender_id="s1",
            sender_name="Sender",
            content="hello",
            receiver_id="r1",
        )
        d = msg.to_dict()
        assert d["sender_id"] == "s1"
        assert d["content"] == "hello"
        assert d["receiver_id"] == "r1"
        assert d["protocol"] == "direct"

    def test_message_broadcast_property(self):
        """测试广播消息属性"""
        msg = CollaborationMessage(protocol=ProtocolType.BROADCAST)
        assert msg.is_broadcast is True
        msg2 = CollaborationMessage(protocol=ProtocolType.DIRECT)
        assert msg2.is_broadcast is False

    def test_message_reply_property(self):
        """测试回复消息属性"""
        msg = CollaborationMessage(reply_to="some_msg_id")
        assert msg.is_reply is True
        assert CollaborationMessage().is_reply is False

    def test_message_expiry(self):
        """测试消息过期逻辑"""
        msg = CollaborationMessage()
        assert msg.is_expired is False
        msg.set_expiry(-1)  # 已过期
        assert msg.is_expired is True

    def test_message_from_dict_roundtrip(self):
        """测试消息字典往返序列化"""
        original = CollaborationMessage(
            sender_id="s1",
            sender_name="Sender",
            content="test",
            protocol=ProtocolType.MULTICAST,
            priority=MessagePriority.HIGH,
            metadata={"key": "val"},
        )
        restored = CollaborationMessage.from_dict(original.to_dict())
        assert restored.sender_id == "s1"
        assert restored.protocol == ProtocolType.MULTICAST
        assert restored.priority == MessagePriority.HIGH
        assert restored.metadata == {"key": "val"}


class TestCollaborationRequest:
    """协作请求测试"""

    def test_request_creation_and_to_dict(self):
        """测试请求创建及序列化"""
        req = CollaborationRequest(
            requester_id="a1",
            requester_name="Agent1",
            task_type="analysis",
            task_description="分析数据",
            required_capabilities=["text_generation"],
            max_participants=3,
        )
        d = req.to_dict()
        assert d["task_type"] == "analysis"
        assert d["max_participants"] == 3

    def test_request_from_dict_roundtrip(self):
        """测试请求字典往返序列化"""
        original = CollaborationRequest(
            requester_id="a1",
            task_type="generation",
            timeout_seconds=120,
        )
        restored = CollaborationRequest.from_dict(original.to_dict())
        assert restored.requester_id == "a1"
        assert restored.timeout_seconds == 120


class TestCollaborationResponse:
    """协作响应测试"""

    def test_response_creation_and_to_dict(self):
        """测试响应创建及序列化"""
        resp = CollaborationResponse(
            request_id="req-1",
            responder_id="a2",
            responder_name="Agent2",
            accepted=True,
            status="accepted",
            result={"answer": 42},
        )
        d = resp.to_dict()
        assert d["accepted"] is True
        assert d["result"]["answer"] == 42

    def test_response_from_dict_roundtrip(self):
        """测试响应字典往返序列化"""
        original = CollaborationResponse(
            request_id="req-1",
            responder_id="a2",
            accepted=False,
            status="declined",
            error="busy",
        )
        restored = CollaborationResponse.from_dict(original.to_dict())
        assert restored.accepted is False
        assert restored.error == "busy"


class TestCollaborationProtocol:
    """协作协议工具类测试"""

    def test_validate_task_type(self):
        """测试任务类型校验"""
        assert CollaborationProtocol.validate_task_type("analysis") is True
        assert CollaborationProtocol.validate_task_type("unknown_type") is False

    def test_create_request(self):
        """测试协议层创建请求"""
        req = CollaborationProtocol.create_request(
            requester_id="a1",
            requester_name="Agent1",
            task_type="review",
            task_description="代码审查",
        )
        assert isinstance(req, CollaborationRequest)
        assert req.task_type == "review"

    def test_create_response(self):
        """测试协议层创建响应"""
        resp = CollaborationProtocol.create_response(
            request_id="r1",
            responder_id="a2",
            responder_name="Agent2",
            accepted=True,
        )
        assert isinstance(resp, CollaborationResponse)
        assert resp.accepted is True

    def test_create_message(self):
        """测试协议层创建消息"""
        msg = CollaborationProtocol.create_message(
            sender_id="s1",
            sender_name="Sender",
            content="ping",
        )
        assert isinstance(msg, CollaborationMessage)
        assert msg.content == "ping"


# ============================================================
# 协商器 (negotiator.py)
# ============================================================

class TestNegotiator:
    """协作协商器测试"""

    def setup_method(self):
        """每个测试前重置协商器"""
        self.negotiator = CollaborationNegotiator()
        self.sample_request = CollaborationRequest(
            requester_id="initiator-1",
            requester_name="发起者",
            task_type="analysis",
            task_description="数据清洗",
            required_capabilities=["text_generation"],
            timeout_seconds=30,
        )

    def test_create_negotiation(self):
        """测试创建协商并验证初始状态"""
        neg = self.negotiator.create_negotiation(self.sample_request)
        assert isinstance(neg, NegotiationResult)
        assert neg.status == NegotiationStatus.PENDING
        assert neg.initiator_id == "initiator-1"
        assert neg.expires_at is not None

    def test_accept_request(self):
        """测试接受请求后协商状态变更"""
        neg = self.negotiator.create_negotiation(self.sample_request)
        resp = self.negotiator.accept_request(
            request_id=self.sample_request.request_id,
            responder_id="responder-1",
            responder_name="响应者",
            agreed_capabilities=["text_generation", "code_generation"],
        )
        assert resp is not None
        assert resp.accepted is True
        # 协商状态应更新为 ACCEPTED
        updated = self.negotiator.get_negotiation(neg.negotiation_id)
        assert updated.status == NegotiationStatus.ACCEPTED
        assert "responder-1" in updated.participants

    def test_decline_request(self):
        """测试拒绝请求并记录原因"""
        self.negotiator.create_negotiation(self.sample_request)
        ok = self.negotiator.decline_request(
            request_id=self.sample_request.request_id,
            responder_id="responder-2",
            reason="能力不足",
        )
        assert ok is True
        neg = self.negotiator.get_negotiation(
            list(self.negotiator._negotiations.keys())[0]
        )
        assert "responder-2" in neg.declined_by
        assert neg.error == "能力不足"

    def test_complete_negotiation(self):
        """测试完成协商并验证最终结果"""
        neg = self.negotiator.create_negotiation(self.sample_request)
        self.negotiator.accept_request(
            request_id=self.sample_request.request_id,
            responder_id="r1",
            responder_name="R1",
        )
        ok = self.negotiator.complete_negotiation(
            negotiation_id=neg.negotiation_id,
            result={"output": "cleaned_data"},
        )
        assert ok is True
        updated = self.negotiator.get_negotiation(neg.negotiation_id)
        assert updated.status == NegotiationStatus.COMPLETED
        assert updated.final_result == {"output": "cleaned_data"}
        assert updated.is_completed is True

    def test_cancel_negotiation(self):
        """测试取消协商"""
        neg = self.negotiator.create_negotiation(self.sample_request)
        ok = self.negotiator.cancel_negotiation(
            negotiation_id=neg.negotiation_id,
            reason="用户取消",
        )
        assert ok is True
        updated = self.negotiator.get_negotiation(neg.negotiation_id)
        assert updated.status == NegotiationStatus.CANCELLED

    def test_check_timeouts(self):
        """测试超时检测"""
        # 创建一个已经过期的协商
        req = CollaborationRequest(
            requester_id="a1",
            requester_name="A1",
            task_type="analysis",
            task_description="t",
            timeout_seconds=1,
        )
        neg = self.negotiator.create_negotiation(req)
        # 手动将过期时间设为过去
        neg.expires_at = datetime.now() - timedelta(seconds=10)
        timed_out = self.negotiator.check_timeouts()
        assert neg.negotiation_id in timed_out
        assert neg.status == NegotiationStatus.TIMEOUT

    def test_get_stats(self):
        """测试统计信息"""
        self.negotiator.create_negotiation(self.sample_request)
        stats = self.negotiator.get_stats()
        assert stats["total_negotiations"] == 1
        assert stats["by_status"]["pending"] == 1
        assert stats["success_rate"] == 0.0


# ============================================================
# 任务路由器 (task_router.py)
# ============================================================

def _make_registry_with_agents():
    """辅助函数：创建包含两个 Agent 的注册表"""
    registry = AgentRegistry()

    meta1 = AgentMetadata(
        agent_id="agent-text",
        name="TextAgent",
        category="specialist",
        capabilities={AgentCapability.TEXT_GENERATION, AgentCapability.REASONING},
        max_concurrent_tasks=5,
    )
    meta2 = AgentMetadata(
        agent_id="agent-code",
        name="CodeAgent",
        category="specialist",
        capabilities={AgentCapability.CODE_GENERATION, AgentCapability.TOOL_USE},
        max_concurrent_tasks=3,
    )
    registry.register(meta1)
    registry.register(meta2)
    return registry


class TestTaskRouter:
    """任务路由器测试"""

    def setup_method(self):
        """每个测试前创建路由器和注册表"""
        self.registry = _make_registry_with_agents()
        self.router = TaskRouter()
        self.router.set_registry(self.registry)

    def test_route_returns_valid_target(self):
        """测试路由返回有效目标 Agent"""
        route = self.router.route(
            task_type="analysis",
            required_capabilities=[AgentCapability.TEXT_GENERATION],
        )
        assert isinstance(route, TaskRoute)
        assert route.is_valid is True
        assert route.target_agent_id == "agent-text"

    def test_route_without_registry(self):
        """测试无注册表时路由返回无效结果"""
        router = TaskRouter()
        route = router.route(task_type="analysis")
        assert route.is_valid is False
        assert "registry" in route.reason.lower()

    def test_routing_rule_priority(self):
        """测试路由规则优先级排序"""
        rule = RoutingRule(
            name="high-priority",
            task_type="analysis",
            target_agent_id="agent-code",
            priority=10,
        )
        self.router.add_rule(rule)
        # 高优先级规则应覆盖默认规则
        route = self.router.route(task_type="analysis")
        assert route.target_agent_id == "agent-code"

    def test_remove_rule(self):
        """测试移除路由规则"""
        rule = RoutingRule(name="temp", task_type="review", priority=5)
        self.router.add_rule(rule)
        rule_id = rule.rule_id
        assert self.router.remove_rule(rule_id) is True
        assert self.router.get_rule(rule_id) is None

    def test_routing_stats(self):
        """测试路由统计记录"""
        self.router.route(
            task_type="analysis",
            required_capabilities=[AgentCapability.TEXT_GENERATION],
        )
        self.router.route(
            task_type="analysis",
            required_capabilities=[AgentCapability.TEXT_GENERATION],
        )
        stats = self.router.get_stats()
        assert stats["total_routes"] >= 2
