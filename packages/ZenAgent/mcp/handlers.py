"""
MCP 协议处理器
提供方法处理器注册和消息路由功能
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Awaitable
from abc import ABC, abstractmethod
import asyncio

from .protocol import MCPErrorCode, MCPProtocol
from .message import (
    MCPMessage, MCPRequest, MCPResponse, MCPErrorResponse, MCPNotification
)
from .session import MCPSession


# 类型别名
HandlerFunc = Callable[[MCPRequest, MCPSession], Awaitable[MCPResponse]]
NotificationHandlerFunc = Callable[[MCPNotification, MCPSession], Awaitable[None]]


@dataclass
class MCPHandler:
    """
    MCP 方法处理器
    
    封装单个方法的处理逻辑
    """
    name: str
    handler: HandlerFunc
    description: str = ""
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    
    async def __call__(self, request: MCPRequest, session: MCPSession) -> MCPResponse:
        """
        执行处理器
        
        Args:
            request: MCP 请求
            session: MCP 会话
            
        Returns:
            MCPResponse: 处理结果
        """
        try:
            result = await self.handler(request, session)
            return result
        except Exception as e:
            return MCPErrorResponse.create(
                request_id=request.id,
                error_code=MCPErrorCode.INTERNAL_ERROR,
                error_message=f"Handler error: {str(e)}",
                error_data={"handler": self.name},
            )


@dataclass
class MCPHandlerRegistry:
    """
    MCP 处理器注册表
    
    管理所有已注册的方法处理器
    """
    _handlers: Dict[str, MCPHandler] = field(default_factory=dict)
    _notification_handlers: Dict[str, NotificationHandlerFunc] = field(default_factory=dict)
    
    def register(
        self,
        method: str,
        handler: HandlerFunc,
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        注册请求处理器
        
        Args:
            method: 方法名
            handler: 处理函数
            description: 方法描述
            input_schema: 输入 schema
            output_schema: 输出 schema
        """
        self._handlers[method] = MCPHandler(
            name=method,
            handler=handler,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
        )
    
    def register_notification(
        self,
        method: str,
        handler: NotificationHandlerFunc
    ) -> None:
        """
        注册通知处理器
        
        Args:
            method: 通知方法名
            handler: 处理函数
        """
        self._notification_handlers[method] = handler
    
    def get_handler(self, method: str) -> Optional[MCPHandler]:
        """
        获取处理器
        
        Args:
            method: 方法名
            
        Returns:
            Optional[MCPHandler]: 处理器对象
        """
        return self._handlers.get(method)
    
    def has_handler(self, method: str) -> bool:
        """
        检查是否存在处理器
        
        Args:
            method: 方法名
            
        Returns:
            bool: 是否存在
        """
        return method in self._handlers
    
    def list_methods(self) -> List[str]:
        """
        列出所有已注册的方法
        
        Returns:
            List[str]: 方法名列表
        """
        return list(self._handlers.keys())
    
    def get_method_info(self, method: str) -> Optional[Dict[str, Any]]:
        """
        获取方法信息
        
        Args:
            method: 方法名
            
        Returns:
            Optional[Dict[str, Any]]: 方法信息
        """
        handler = self._handlers.get(method)
        if handler is None:
            return None
        
        return {
            "name": handler.name,
            "description": handler.description,
            "inputSchema": handler.input_schema,
            "outputSchema": handler.output_schema,
        }
    
    def list_all_methods(self) -> List[Dict[str, Any]]:
        """
        列出所有方法信息
        
        Returns:
            List[Dict[str, Any]]: 所有方法信息
        """
        return [
            self.get_method_info(method)
            for method in self._handlers.keys()
        ]


class MCPProtocolHandler:
    """
    MCP 协议处理器
    
    处理完整的协议交互流程
    """
    
    def __init__(self, session: MCPSession):
        """
        初始化协议处理器
        
        Args:
            session: MCP 会话
        """
        self.session = session
        self.protocol = MCPProtocol()
        self.registry = MCPHandlerRegistry()
        self._setup_default_handlers()
    
    def _setup_default_handlers(self) -> None:
        """设置默认处理器"""
        # Initialize 处理器
        self.registry.register(
            "initialize",
            self._handle_initialize,
            description="Initialize the MCP session",
            input_schema={
                "type": "object",
                "properties": {
                    "protocolVersion": {"type": "string"},
                    "clientInfo": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "version": {"type": "string"},
                        },
                    },
                },
            },
        )
        
        # Tools list 处理器
        self.registry.register(
            "tools/list",
            self._handle_tools_list,
            description="List available tools",
        )
        
        # Resources list 处理器
        self.registry.register(
            "resources/list",
            self._handle_resources_list,
            description="List available resources",
        )
        
        # Ping 处理器
        self.registry.register(
            "ping",
            self._handle_ping,
            description="Ping the server",
        )
    
    async def _handle_initialize(
        self,
        request: MCPRequest,
        session: MCPSession
    ) -> MCPResponse:
        """处理 initialize 请求"""
        params = request.params or {}
        protocol_version = params.get("protocolVersion", "1.0.0")
        client_info = params.get("clientInfo", {})
        
        result = session.initialize(client_info, protocol_version)
        
        return MCPResponse.create(request_id=request.id, result=result)
    
    async def _handle_tools_list(
        self,
        request: MCPRequest,
        session: MCPSession
    ) -> MCPResponse:
        """处理 tools/list 请求"""
        result = {
            "tools": [
                {"name": method, **self.registry.get_method_info(method)}
                for method in self.registry.list_methods()
            ],
        }
        return MCPResponse.create(request_id=request.id, result=result)
    
    async def _handle_resources_list(
        self,
        request: MCPRequest,
        session: MCPSession
    ) -> MCPResponse:
        """处理 resources/list 请求"""
        result = {
            "resources": [],
        }
        return MCPResponse.create(request_id=request.id, result=result)
    
    async def _handle_ping(
        self,
        request: MCPRequest,
        session: MCPSession
    ) -> MCPResponse:
        """处理 ping 请求"""
        is_alive = session.ping()
        result = {"alive": is_alive}
        return MCPResponse.create(request_id=request.id, result=result)
    
    async def handle_message(
        self,
        message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        处理接收到的消息
        
        Args:
            message: 消息字典
            
        Returns:
            Optional[Dict[str, Any]]: 响应消息
        """
        # 验证消息格式
        if not self.protocol.validate_message(message):
            return self.protocol.create_error_response(
                request_id=message.get("id", ""),
                error_code=MCPErrorCode.INVALID_REQUEST,
                error_message="Invalid MCP message format",
            )
        
        # 接收消息到会话
        self.session.receive_message(message)
        
        # 根据消息类型处理
        if "method" in message:
            method = message["method"]
            
            # 检查是否是通知
            if "id" not in message:
                # 通知消息
                handler = self._notification_handlers.get(method)
                if handler:
                    notification = MCPNotification.from_dict(message)
                    await handler(notification, self.session)
                return None
            
            # 请求消息
            request = MCPRequest.from_dict(message)
            handler = self.registry.get_handler(method)
            
            if handler is None:
                return self.protocol.create_error_response(
                    request_id=request.id,
                    error_code=MCPErrorCode.METHOD_NOT_FOUND,
                    error_message=f"Method not found: {method}",
                )
            
            try:
                self.session.begin_processing()
                response = await handler(request, self.session)
                self.session.end_processing()
                return response.to_dict()
            except Exception as e:
                self.session.end_processing()
                return self.protocol.create_error_response(
                    request_id=request.id,
                    error_code=MCPErrorCode.INTERNAL_ERROR,
                    error_message=f"Handler error: {str(e)}",
                )
        elif "result" in message or "error" in message:
            # 响应消息（通常由调用方处理）
            return message
        
        return None


# 便捷装饰器
def mcp_handler(
    method: str,
    description: str = "",
    input_schema: Optional[Dict[str, Any]] = None,
    output_schema: Optional[Dict[str, Any]] = None
):
    """
    MCP 处理器装饰器
    
    用法:
        @mcp_handler("myMethod", description="My method")
        async def handle_my_method(request: MCPRequest, session: MCPSession) -> MCPResponse:
            ...
    """
    def decorator(func: HandlerFunc) -> HandlerFunc:
        func._mcp_method = method
        func._mcp_description = description
        func._mcp_input_schema = input_schema
        func._mcp_output_schema = output_schema
        return func
    
    return decorator
