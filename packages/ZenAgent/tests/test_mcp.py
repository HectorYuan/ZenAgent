"""
MCP 模块单元测试
覆盖: AgentRegistry、MCPProtocol、MCPMessage、MCPSession、MCPHandler
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import json
from mcp.protocol import MCPProtocol, MCPMessageType, MCPErrorCode
from mcp.message import (
    MCPMessage, MCPRequest, MCPResponse,
    MCPErrorResponse, MCPNotification, MessageBuilder,
)
from mcp.session import MCPSession, MCPSessionState, MCPSessionContext, MCPSessionManager
from mcp.handlers import MCPHandler, MCPHandlerRegistry, MCPProtocolHandler, mcp_handler
from mcp.registry import (
    AgentRegistry, RegisteredAgent, AgentMetadata,
    AgentStatus, AgentCapability, get_registry,
)


# ── AgentRegistry 测试 ─────────────────────────────────────────────

class TestAgentRegistry:
    """Agent 注册表测试"""

    def setup_method(self):
        """每个测试前创建新的注册表"""
        self.registry = AgentRegistry()

    def _make_metadata(self, name="test-agent", category="general", caps=None, tags=None):
        """辅助方法：创建 AgentMetadata"""
        return AgentMetadata(
            name=name,
            description=f"{name} description",
            category=category,
            capabilities=set(caps or []),
            tags=tags or [],
        )

    def test_register_and_get(self):
        """注册 Agent 后可以通过 ID 获取"""
        meta = self._make_metadata()
        agent = self.registry.register(meta, endpoint="tcp://localhost:9000")
        assert agent.metadata.agent_id == meta.agent_id
        assert agent.status == AgentStatus.ONLINE
        assert agent.endpoint == "tcp://localhost:9000"

        fetched = self.registry.get(meta.agent_id)
        assert fetched is agent

    def test_unregister(self):
        """注销 Agent 后无法再获取"""
        meta = self._make_metadata()
        self.registry.register(meta)
        assert self.registry.unregister(meta.agent_id) is True
        assert self.registry.get(meta.agent_id) is None
        # 重复注销返回 False
        assert self.registry.unregister(meta.agent_id) is False

    def test_list_all(self):
        """列出所有已注册 Agent"""
        m1 = self._make_metadata("agent-1")
        m2 = self._make_metadata("agent-2")
        self.registry.register(m1)
        self.registry.register(m2)
        all_agents = self.registry.list_all()
        assert len(all_agents) == 2

    def test_list_by_status(self):
        """按状态筛选 Agent"""
        meta = self._make_metadata()
        agent = self.registry.register(meta)
        online = self.registry.list_by_status(AgentStatus.ONLINE)
        assert len(online) == 1
        offline = self.registry.list_by_status(AgentStatus.OFFLINE)
        assert len(offline) == 0

    def test_list_by_category(self):
        """按类别筛选 Agent"""
        m1 = self._make_metadata("a1", category="coordinator")
        m2 = self._make_metadata("a2", category="specialist")
        self.registry.register(m1)
        self.registry.register(m2)
        coordinators = self.registry.list_by_category("coordinator")
        assert len(coordinators) == 1
        assert coordinators[0].metadata.name == "a1"

    def test_list_by_capabilities(self):
        """按能力筛选 Agent（match_any / match_all）"""
        m1 = self._make_metadata("a1", caps=[AgentCapability.TEXT_GENERATION, AgentCapability.REASONING])
        m2 = self._make_metadata("a2", caps=[AgentCapability.CODE_GENERATION])
        self.registry.register(m1)
        self.registry.register(m2)

        # match_any: 任一匹配即可
        any_match = self.registry.list_by_capabilities(
            [AgentCapability.TEXT_GENERATION, AgentCapability.CODE_GENERATION],
            match_all=False,
        )
        assert len(any_match) == 2

        # match_all: 必须全部匹配
        all_match = self.registry.list_by_capabilities(
            [AgentCapability.TEXT_GENERATION, AgentCapability.REASONING],
            match_all=True,
        )
        assert len(all_match) == 1

    def test_search_by_query(self):
        """按关键词搜索 Agent"""
        m1 = self._make_metadata("code-helper", category="specialist")
        m2 = self._make_metadata("chat-bot", category="general")
        self.registry.register(m1)
        self.registry.register(m2)
        results = self.registry.search("code")
        assert len(results) == 1
        assert results[0].metadata.name == "code-helper"

    def test_search_by_tags(self):
        """按标签搜索 Agent"""
        m1 = self._make_metadata("a1", tags=["python", "ml"])
        m2 = self._make_metadata("a2", tags=["java"])
        self.registry.register(m1)
        self.registry.register(m2)
        results = self.registry.search("", tags=["python"])
        assert len(results) == 1

    def test_heartbeat_and_stats(self):
        """心跳更新和统计信息"""
        meta = self._make_metadata()
        agent = self.registry.register(meta)
        assert self.registry.heartbeat(meta.agent_id) is True
        assert self.registry.heartbeat("nonexistent") is False

        stats = self.registry.get_stats()
        assert stats["total_agents"] == 1
        assert stats["available_agents"] == 1


# ── RegisteredAgent 任务计数测试 ─────────────────────────────────────

class TestRegisteredAgent:
    """已注册 Agent 行为测试"""

    def test_task_limit_and_status_change(self):
        """任务计数达到上限后状态变为 BUSY，结束后恢复"""
        meta = AgentMetadata(
            name="limited-agent",
            max_concurrent_tasks=1,
        )
        agent = RegisteredAgent(metadata=meta, status=AgentStatus.ONLINE)
        assert agent.start_task() is True
        assert agent.status == AgentStatus.BUSY
        assert agent.start_task() is False  # 已满
        agent.end_task()
        assert agent.status == AgentStatus.ONLINE

    def test_success_rate(self):
        """成功率计算"""
        meta = AgentMetadata(name="sr-agent")
        agent = RegisteredAgent(metadata=meta)
        assert agent.success_rate == 0.0
        agent.increment_request(success=True)
        agent.increment_request(success=True)
        agent.increment_request(success=False)
        assert abs(agent.success_rate - 2 / 3) < 1e-9

    def test_to_dict(self):
        """序列化为字典包含关键字段"""
        meta = AgentMetadata(name="dict-agent", category="test")
        agent = RegisteredAgent(metadata=meta)
        d = agent.to_dict()
        assert d["name"] == "dict-agent"
        assert d["category"] == "test"
        assert "status" in d
        assert "success_rate" in d


# ── MCPProtocol 测试 ──────────────────────────────────────────────

class TestMCPProtocol:
    """MCP 协议核心测试"""

    def setup_method(self):
        self.protocol = MCPProtocol()

    def test_create_request(self):
        """创建符合 JSON-RPC 2.0 的请求"""
        req = self.protocol.create_request("tools/list", {"filter": "all"})
        assert req["jsonrpc"] == "2.0"
        assert req["method"] == "tools/list"
        assert req["params"] == {"filter": "all"}
        assert "id" in req

    def test_create_response(self):
        """创建响应消息"""
        resp = self.protocol.create_response("req-1", result={"tools": []})
        assert resp["id"] == "req-1"
        assert resp["result"] == {"tools": []}

    def test_create_notification(self):
        """创建通知消息（无 id）"""
        ntf = self.protocol.create_notification("ping", {"ts": 123})
        assert "id" not in ntf
        assert ntf["method"] == "ping"
        assert ntf["params"] == {"ts": 123}

    def test_create_error_response(self):
        """创建错误响应"""
        err = self.protocol.create_error_response(
            "req-2", MCPErrorCode.METHOD_NOT_FOUND, "no such method",
        )
        assert err["error"]["code"] == MCPErrorCode.METHOD_NOT_FOUND.value
        assert err["error"]["message"] == "no such method"

    def test_validate_message_valid(self):
        """验证合法消息"""
        msg = {"jsonrpc": "2.0", "method": "test", "id": "1"}
        assert self.protocol.validate_message(msg) is True

    def test_validate_message_invalid(self):
        """验证非法消息（缺少 jsonrpc / 版本不对）"""
        assert self.protocol.validate_message({}) is False
        assert self.protocol.validate_message({"jsonrpc": "1.0"}) is False

    def test_serialize_deserialize_roundtrip(self):
        """序列化 → 反序列化往返一致"""
        original = self.protocol.create_request("echo", {"text": "你好"})
        json_str = self.protocol.serialize(original)
        restored = self.protocol.deserialize(json_str)
        assert restored["method"] == "echo"
        assert restored["params"]["text"] == "你好"

    def test_deserialize_invalid_json(self):
        """反序列化非法 JSON 抛出 ValueError"""
        with pytest.raises(ValueError):
            self.protocol.deserialize("not-json")

    def test_capabilities(self):
        """协议能力包含 tools / resources / prompts"""
        caps = self.protocol.get_capabilities()
        assert caps["tools"]["supported"] is True
        assert caps["resources"]["supported"] is True


# ── MCPMessage 序列化测试 ─────────────────────────────────────────

class TestMCPMessage:
    """MCP 消息对象序列化 / 反序列化测试"""

    def test_request_roundtrip(self):
        """MCPRequest to_dict → from_dict 往返"""
        req = MCPRequest.create("tools/call", {"name": "search"}, request_id="r1")
        d = req.to_dict()
        assert d["method"] == "tools/call"
        assert d["id"] == "r1"
        restored = MCPRequest.from_dict(d)
        assert restored.method == "tools/call"
        assert restored.id == "r1"

    def test_response_roundtrip(self):
        """MCPResponse to_dict → from_dict 往返"""
        resp = MCPResponse.create("r1", result={"ok": True})
        d = resp.to_dict()
        restored = MCPResponse.from_dict(d)
        assert restored.result == {"ok": True}

    def test_error_response_roundtrip(self):
        """MCPErrorResponse to_dict → from_dict 往返"""
        err = MCPErrorResponse.create("r1", MCPErrorCode.INVALID_PARAMS, "bad param", {"field": "x"})
        d = err.to_dict()
        assert "error" in d
        restored = MCPErrorResponse.from_dict(d)
        assert restored.code == MCPErrorCode.INVALID_PARAMS.value
        assert restored.data == {"field": "x"}

    def test_notification_roundtrip(self):
        """MCPNotification to_dict → from_dict 往返"""
        ntf = MCPNotification.create("progress", {"percent": 50})
        d = ntf.to_dict()
        assert "id" not in d
        restored = MCPNotification.from_dict(d)
        assert restored.method == "progress"

    def test_from_dict_auto_detect(self):
        """MCPMessage.from_dict 自动检测消息类型"""
        req = MCPMessage.from_dict({"jsonrpc": "2.0", "id": "1", "method": "m"})
        assert isinstance(req, MCPRequest)
        resp = MCPMessage.from_dict({"jsonrpc": "2.0", "id": "1", "result": {}})
        assert isinstance(resp, MCPResponse)
        err = MCPMessage.from_dict({"jsonrpc": "2.0", "id": "1", "error": {"code": -1, "message": "e"}})
        assert isinstance(err, MCPErrorResponse)
        ntf = MCPMessage.from_dict({"jsonrpc": "2.0", "method": "n"})
        assert isinstance(ntf, MCPNotification)


# ── MCPSession 测试 ───────────────────────────────────────────────

class TestMCPSession:
    """MCP 会话生命周期测试"""

    def setup_method(self):
        self.session = MCPSession()

    def test_initial_state(self):
        """新建会话处于 INITIAL 状态"""
        assert self.session.state == MCPSessionState.INITIAL
        assert self.session.is_alive is True
        assert self.session.is_ready is False

    def test_initialize(self):
        """初始化会话后状态变为 READY"""
        result = self.session.initialize(
            client_info={"name": "test-client", "version": "0.1"},
            protocol_version="1.0.0",
        )
        assert self.session.state == MCPSessionState.READY
        assert result["protocolVersion"] == "1.0.0"
        assert result["serverInfo"]["name"] == "ZenAgent MCP Server"

    def test_processing_lifecycle(self):
        """READY → BUSY → IDLE 处理流程"""
        self.session.initialize(client_info={"name": "c"})
        self.session.begin_processing()
        assert self.session.state == MCPSessionState.BUSY
        self.session.end_processing()
        assert self.session.state == MCPSessionState.IDLE

    def test_close(self):
        """关闭会话后状态为 CLOSED，is_alive 为 False"""
        self.session.close()
        assert self.session.state == MCPSessionState.CLOSED
        assert self.session.is_alive is False

    def test_state_change_callback(self):
        """状态变更触发回调"""
        transitions = []
        self.session.on_state_change(lambda old, new: transitions.append((old, new)))
        self.session.change_state(MCPSessionState.READY)
        assert len(transitions) == 1
        assert transitions[0] == (MCPSessionState.INITIAL, MCPSessionState.READY)

    def test_message_callback(self):
        """接收消息触发回调"""
        received = []
        self.session.on_message(lambda msg: received.append(msg))
        self.session.receive_message({"jsonrpc": "2.0", "method": "test"})
        assert len(received) == 1

    def test_export_and_restore_context(self):
        """导出上下文后可恢复会话"""
        self.session.initialize(client_info={"name": "c"})
        self.session.context.set_metadata("key", "value")
        exported = self.session.export_context()
        assert exported["metadata"]["key"] == "value"

        restored = MCPSession.from_context(exported)
        assert restored.state == MCPSessionState.READY
        assert restored.context.metadata["key"] == "value"


# ── MCPSessionManager 测试 ────────────────────────────────────────

class TestMCPSessionManager:
    """会话管理器测试"""

    def setup_method(self):
        self.manager = MCPSessionManager()

    def test_create_and_get_session(self):
        """创建会话后可通过 ID 获取"""
        session = self.manager.create_session(idle_timeout=60)
        assert self.manager.get_session(session.session_id) is session

    def test_list_sessions(self):
        """列出所有会话"""
        self.manager.create_session()
        self.manager.create_session()
        assert len(self.manager.list_sessions()) == 2

    def test_remove_session(self):
        """移除会话后无法获取"""
        session = self.manager.create_session()
        sid = session.session_id
        assert self.manager.remove_session(sid) is True
        assert self.manager.get_session(sid) is None
        assert self.manager.remove_session(sid) is False

    def test_list_active_sessions(self):
        """列出活跃会话（排除已关闭的）"""
        s1 = self.manager.create_session()
        s2 = self.manager.create_session()
        s2.close()
        active = self.manager.list_active_sessions()
        assert len(active) == 1
        assert active[0].session_id == s1.session_id

    def test_get_stats(self):
        """统计信息正确"""
        self.manager.create_session()
        stats = self.manager.get_stats()
        assert stats["total_sessions"] == 1
        assert stats["active_sessions"] == 1


# ── MCPHandlerRegistry 测试 ───────────────────────────────────────

class TestMCPHandlerRegistry:
    """处理器注册表测试"""

    def setup_method(self):
        self.registry = MCPHandlerRegistry()

    def test_register_and_get(self):
        """注册处理器后可获取"""
        async def dummy(req, sess):
            return MCPResponse.create(req.id)

        self.registry.register("test.method", dummy, description="测试方法")
        handler = self.registry.get_handler("test.method")
        assert handler is not None
        assert handler.description == "测试方法"

    def test_has_handler(self):
        """has_handler 检查"""
        async def dummy(req, sess):
            return MCPResponse.create(req.id)

        self.registry.register("foo", dummy)
        assert self.registry.has_handler("foo") is True
        assert self.registry.has_handler("bar") is False

    def test_list_methods(self):
        """列出所有已注册方法"""
        async def d(req, sess):
            return MCPResponse.create(req.id)

        self.registry.register("a", d)
        self.registry.register("b", d)
        methods = self.registry.list_methods()
        assert set(methods) == {"a", "b"}

    def test_get_method_info(self):
        """获取方法元信息"""
        async def d(req, sess):
            return MCPResponse.create(req.id)

        self.registry.register("calc", d, description="计算", input_schema={"type": "object"})
        info = self.registry.get_method_info("calc")
        assert info["name"] == "calc"
        assert info["description"] == "计算"
        assert info["inputSchema"]["type"] == "object"

    def test_nonexistent_handler(self):
        """获取不存在的处理器返回 None"""
        assert self.registry.get_handler("nope") is None
        assert self.registry.get_method_info("nope") is None


# ── MCPProtocolHandler 集成测试 ───────────────────────────────────

class TestMCPProtocolHandler:
    """协议处理器集成测试"""

    def setup_method(self):
        self.session = MCPSession()
        self.handler = MCPProtocolHandler(self.session)

    @pytest.mark.asyncio
    async def test_handle_initialize(self):
        """处理 initialize 请求"""
        request = self.handler.protocol.create_request("initialize", {
            "protocolVersion": "1.0.0",
            "clientInfo": {"name": "test"},
        })
        resp = await self.handler.handle_message(request)
        assert resp is not None
        assert resp["result"]["protocolVersion"] == "1.0.0"
        assert self.session.state == MCPSessionState.READY

    @pytest.mark.asyncio
    async def test_handle_ping(self):
        """处理 ping 请求"""
        self.session.initialize(client_info={"name": "c"})
        request = self.handler.protocol.create_request("ping")
        resp = await self.handler.handle_message(request)
        assert resp["result"]["alive"] is True

    @pytest.mark.asyncio
    async def test_handle_tools_list(self):
        """处理 tools/list 请求"""
        self.session.initialize(client_info={"name": "c"})
        request = self.handler.protocol.create_request("tools/list")
        resp = await self.handler.handle_message(request)
        assert "tools" in resp["result"]

    @pytest.mark.asyncio
    async def test_method_not_found(self):
        """调用未注册方法返回 METHOD_NOT_FOUND 错误"""
        self.session.initialize(client_info={"name": "c"})
        request = self.handler.protocol.create_request("nonexistent")
        resp = await self.handler.handle_message(request)
        assert resp["error"]["code"] == MCPErrorCode.METHOD_NOT_FOUND.value

    @pytest.mark.asyncio
    async def test_invalid_message(self):
        """无效消息返回 INVALID_REQUEST 错误"""
        resp = await self.handler.handle_message({"bad": "message"})
        assert resp["error"]["code"] == MCPErrorCode.INVALID_REQUEST.value

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="已知 bug: MCPProtocolHandler.handle_message 使用 self._notification_handlers "
               "但该属性在 self.registry._notification_handlers 上",
        raises=AttributeError,
        strict=True,
    )
    async def test_notification_returns_none(self):
        """通知消息（无 id）不返回响应"""
        self.session.initialize(client_info={"name": "c"})
        notification = {"jsonrpc": "2.0", "method": "ping"}
        resp = await self.handler.handle_message(notification)
        assert resp is None
