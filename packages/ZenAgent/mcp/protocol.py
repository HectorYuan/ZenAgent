"""
MCP 协议核心定义
定义 Model Context Protocol 的基础协议结构
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import json
import uuid


class MCPMessageType(Enum):
    """MCP 消息类型枚举"""
    # 请求类
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    
    # 特定类型
    INITIALIZE = "initialize"
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"
    
    # 通知类
    NOTIFICATION = "notification"
    PING = "ping"
    PONG = "pong"
    CANCEL = "cancel"


class MCPErrorCode(Enum):
    """MCP 错误码枚举"""
    PARSE_ERROR = -32700      # JSON 解析错误
    INVALID_REQUEST = -32600  # 无效请求
    METHOD_NOT_FOUND = -32601 # 方法未找到
    INVALID_PARAMS = -32602   # 参数无效
    INTERNAL_ERROR = -32603   # 内部错误
    
    # 业务错误码
    SESSION_NOT_FOUND = -32001    # 会话不存在
    SESSION_EXPIRED = -32002     # 会话已过期
    AGENT_NOT_FOUND = -32003     # Agent 未找到
    CAPABILITY_NOT_SUPPORTED = -32004  # 能力不支持
    RATE_LIMITED = -32005        # 请求限流
    UNAUTHORIZED = -32006         # 未授权


@dataclass
class MCPProtocol:
    """
    MCP 协议核心类
    
    提供协议的版本管理、消息验证、序列化等功能
    """
    version: str = "1.0.0"
    supported_versions: List[str] = field(default_factory=lambda: ["1.0.0", "0.9.0"])
    
    def __post_init__(self):
        """初始化后验证版本兼容性"""
        if self.version not in self.supported_versions:
            raise ValueError(
                f"Protocol version {self.version} not supported. "
                f"Supported versions: {self.supported_versions}"
            )
    
    @property
    def version_info(self) -> Dict[str, str]:
        """获取版本信息"""
        return {
            "protocol_version": self.version,
            "transport": "stdio",
            "encoding": "utf-8",
        }
    
    def validate_message(self, message: Dict[str, Any]) -> bool:
        """
        验证消息格式是否符合 MCP 协议规范
        
        Args:
            message: 待验证的消息字典
            
        Returns:
            bool: 验证是否通过
        """
        required_fields = ["jsonrpc"]
        optional_fields = ["id", "method", "params", "result", "error"]
        
        # 检查必需字段
        for field_name in required_fields:
            if field_name not in message:
                return False
        
        # 验证 jsonrpc 版本
        if message.get("jsonrpc") != "2.0":
            return False
        
        # 消息类型验证
        if "method" in message:
            # 请求或通知
            if not isinstance(message.get("method"), str):
                return False
            if "id" not in message and "method" in message:
                # 通知消息不应该有 id，这是正常的
                pass
        elif "result" in message or "error" in message:
            # 响应消息
            if "id" not in message:
                return False
        
        return True
    
    def create_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建符合 MCP 协议的请求消息
        
        Args:
            method: 方法名
            params: 方法参数
            request_id: 请求 ID（可选，自动生成）
            
        Returns:
            Dict[str, Any]: 符合协议的请求消息
        """
        request = {
            "jsonrpc": "2.0",
            "method": method,
        }
        
        if request_id is None:
            request_id = str(uuid.uuid4())
        request["id"] = request_id
        
        if params is not None:
            request["params"] = params
            
        return request
    
    def create_response(
        self,
        request_id: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建符合 MCP 协议的响应消息
        
        Args:
            request_id: 对应请求的 ID
            result: 请求结果
            error: 错误信息
            
        Returns:
            Dict[str, Any]: 符合协议的响应消息
        """
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
        }
        
        if error is not None:
            response["error"] = error
        else:
            response["result"] = result if result is not None else {}
            
        return response
    
    def create_notification(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建通知消息（不需要响应）
        
        Args:
            method: 通知方法名
            params: 通知参数
            
        Returns:
            Dict[str, Any]: 通知消息
        """
        notification = {
            "jsonrpc": "2.0",
            "method": method,
        }
        
        if params is not None:
            notification["params"] = params
            
        return notification
    
    def create_error_response(
        self,
        request_id: str,
        error_code: MCPErrorCode,
        error_message: str,
        error_data: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        创建错误响应
        
        Args:
            request_id: 对应请求的 ID
            error_code: 错误码
            error_message: 错误消息
            error_data: 错误详情
            
        Returns:
            Dict[str, Any]: 错误响应消息
        """
        error = {
            "code": error_code.value,
            "message": error_message,
        }
        
        if error_data is not None:
            error["data"] = error_data
            
        return self.create_response(
            request_id=request_id,
            error=error
        )
    
    def serialize(self, message: Dict[str, Any]) -> str:
        """
        序列化消息为 JSON 字符串
        
        Args:
            message: 消息字典
            
        Returns:
            str: JSON 字符串
        """
        return json.dumps(message, ensure_ascii=False)
    
    def deserialize(self, message_str: str) -> Dict[str, Any]:
        """
        反序列化 JSON 字符串
        
        Args:
            message_str: JSON 字符串
            
        Returns:
            Dict[str, Any]: 消息字典
            
        Raises:
            ValueError: JSON 解析失败时抛出
        """
        try:
            message = json.loads(message_str)
            if not self.validate_message(message):
                raise ValueError("Invalid MCP message format")
            return message
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON parse error: {e}")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        获取协议支持的能力列表
        
        Returns:
            Dict[str, Any]: 能力描述
        """
        return {
            "tools": {
                "supported": True,
                "listChanged": True,
            },
            "resources": {
                "supported": True,
                "subscribe": True,
                "listChanged": True,
            },
            "prompts": {
                "supported": True,
                "listChanged": True,
            },
            "logging": {
                "supported": True,
            },
        }


# 全局协议实例
_default_protocol: Optional[MCPProtocol] = None


def get_protocol() -> MCPProtocol:
    """获取全局 MCP 协议实例"""
    global _default_protocol
    if _default_protocol is None:
        _default_protocol = MCPProtocol()
    return _default_protocol
