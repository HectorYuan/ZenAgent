import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from mcp.protocol import MCPProtocol, MCPMessageType, MCPErrorCode
from mcp.message import MCPMessage, MCPRequest, MCPResponse, MCPNotification, MCPErrorResponse
from mcp.session import MCPSession, MCPSessionState, MCPSessionManager
from mcp.handlers import MCPHandler, MCPHandlerRegistry
from mcp.registry import AgentRegistry, AgentCapability, RegisteredAgent

class TestMCPProtocol:
    """MCP协议测试"""
    
    def test_protocol_creation(self):
        """测试协议创建"""
        protocol = MCPProtocol()
        assert protocol.version == "1.0.0"
        assert "1.0.0" in protocol.supported_versions
    
    def test_validate_message_valid(self):
        """测试有效消息验证"""
        protocol = MCPProtocol()
        message = {
            "jsonrpc": "2.0",
            "method": "test",
            "params": {"arg": "value"},
            "id": "1"
        }
        assert protocol.validate_message(message) is True
    
    def test_create_request(self):
        """测试创建请求"""
        protocol = MCPProtocol()
        request = protocol.create_request("test.method", {"arg": "value"})
        assert request["jsonrpc"] == "2.0"
        assert request["method"] == "test.method"
        assert request["params"] == {"arg": "value"}
        assert "id" in request

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
