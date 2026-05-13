"""
MCP (Model Context Protocol) 模块
提供 Agent 间上下文协议交互能力
"""

from .protocol import MCPProtocol, MCPMessageType, MCPErrorCode
from .message import MCPMessage, MCPRequest, MCPResponse, MCPNotification
from .session import MCPSession, MCPSessionState, MCPSessionContext, MCPSessionManager
from .handlers import MCPHandler, MCPHandlerRegistry
from .registry import AgentRegistry, RegisteredAgent, AgentMetadata, AgentStatus, AgentCapability

__all__ = [
    # Protocol
    "MCPProtocol",
    "MCPMessageType",
    "MCPErrorCode",
    # Message
    "MCPMessage",
    "MCPRequest",
    "MCPResponse",
    "MCPNotification",
    # Session
    "MCPSession",
    "MCPSessionState",
    "MCPSessionContext",
    "MCPSessionManager",
    # Handler
    "MCPHandler",
    "MCPHandlerRegistry",
    # Registry
    "AgentRegistry",
    "RegisteredAgent",
    "AgentMetadata",
    "AgentStatus",
    "AgentCapability",
]
