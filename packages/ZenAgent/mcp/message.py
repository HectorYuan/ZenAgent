"""
MCP 消息格式和序列化
提供消息对象的类型化封装
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import uuid
from .protocol import MCPErrorCode


@dataclass
class MCPMessage:
    """
    MCP 消息基类
    
    所有 MCP 消息的公共结构
    """
    jsonrpc: str = "2.0"
    
    @property
    def message_type(self) -> str:
        """获取消息类型"""
        raise NotImplementedError("Subclasses must implement message_type property")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {"jsonrpc": self.jsonrpc}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPMessage":
        """
        从字典创建消息对象
        
        Args:
            data: 消息字典
            
        Returns:
            MCPMessage: 消息对象
        """
        if "error" in data:
            return MCPErrorResponse.from_dict(data)
        elif "result" in data:
            return MCPResponse.from_dict(data)
        elif "id" in data:
            return MCPRequest.from_dict(data)
        else:
            return MCPNotification.from_dict(data)


@dataclass
class MCPRequest(MCPMessage):
    """
    MCP 请求消息
    
    需要服务器响应的消息
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    method: str = ""
    params: Optional[Dict[str, Any]] = None
    
    @property
    def message_type(self) -> str:
        return "request"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = super().to_dict()
        result["id"] = self.id
        result["method"] = self.method
        if self.params is not None:
            result["params"] = self.params
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPRequest":
        """从字典创建请求"""
        return cls(
            id=str(data.get("id", uuid.uuid4())),
            method=data.get("method", ""),
            params=data.get("params"),
        )
    
    @classmethod
    def create(
        cls,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> "MCPRequest":
        """
        创建请求消息的工厂方法
        
        Args:
            method: 方法名
            params: 参数
            request_id: 请求 ID
            
        Returns:
            MCPRequest: 请求消息对象
        """
        return cls(
            id=request_id or str(uuid.uuid4()),
            method=method,
            params=params,
        )


@dataclass
class MCPResponse(MCPMessage):
    """
    MCP 响应消息
    
    对请求的成功响应
    """
    id: str = ""
    result: Optional[Dict[str, Any]] = None
    
    @property
    def message_type(self) -> str:
        return "response"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = super().to_dict()
        result["id"] = self.id
        result["result"] = self.result if self.result is not None else {}
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPResponse":
        """从字典创建响应"""
        return cls(
            id=str(data.get("id", "")),
            result=data.get("result"),
        )
    
    @classmethod
    def create(
        cls,
        request_id: str,
        result: Optional[Dict[str, Any]] = None
    ) -> "MCPResponse":
        """
        创建响应消息的工厂方法
        
        Args:
            request_id: 对应请求的 ID
            result: 响应结果
            
        Returns:
            MCPResponse: 响应消息对象
        """
        return cls(
            id=request_id,
            result=result,
        )


@dataclass 
class MCPErrorResponse(MCPMessage):
    """
    MCP 错误响应
    
    对请求的错误响应
    """
    id: str = ""
    code: int = 0
    message: str = ""
    data: Optional[Any] = None
    
    @property
    def message_type(self) -> str:
        return "error"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = super().to_dict()
        result["id"] = self.id
        result["error"] = {
            "code": self.code,
            "message": self.message,
        }
        if self.data is not None:
            result["error"]["data"] = self.data
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPErrorResponse":
        """从字典创建错误响应"""
        error = data.get("error", {})
        return cls(
            id=str(data.get("id", "")),
            code=error.get("code", 0),
            message=error.get("message", ""),
            data=error.get("data"),
        )
    
    @classmethod
    def create(
        cls,
        request_id: str,
        error_code: MCPErrorCode,
        error_message: str,
        error_data: Optional[Any] = None
    ) -> "MCPErrorResponse":
        """
        创建错误响应的工厂方法
        
        Args:
            request_id: 对应请求的 ID
            error_code: 错误码
            error_message: 错误消息
            error_data: 错误详情
            
        Returns:
            MCPErrorResponse: 错误响应对象
        """
        return cls(
            id=request_id,
            code=error_code.value,
            message=error_message,
            data=error_data,
        )


@dataclass
class MCPNotification(MCPMessage):
    """
    MCP 通知消息
    
    不需要响应的单向消息
    """
    method: str = ""
    params: Optional[Dict[str, Any]] = None
    
    @property
    def message_type(self) -> str:
        return "notification"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = super().to_dict()
        result["method"] = self.method
        if self.params is not None:
            result["params"] = self.params
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPNotification":
        """从字典创建通知"""
        return cls(
            method=data.get("method", ""),
            params=data.get("params"),
        )
    
    @classmethod
    def create(
        cls,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> "MCPNotification":
        """
        创建通知消息的工厂方法
        
        Args:
            method: 通知方法名
            params: 通知参数
            
        Returns:
            MCPNotification: 通知消息对象
        """
        return cls(
            method=method,
            params=params,
        )


class MessageBuilder:
    """
    消息构建器
    
    提供 fluent API 构建各种类型的消息
    """
    
    @staticmethod
    def request(
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> MCPRequest:
        """构建请求消息"""
        return MCPRequest.create(method=method, params=params)
    
    @staticmethod
    def response(
        request_id: str,
        result: Optional[Dict[str, Any]] = None
    ) -> MCPResponse:
        """构建响应消息"""
        return MCPResponse.create(request_id=request_id, result=result)
    
    @staticmethod
    def error(
        request_id: str,
        error_code: MCPErrorCode,
        error_message: str,
        error_data: Optional[Any] = None
    ) -> MCPErrorResponse:
        """构建错误响应"""
        return MCPErrorResponse.create(
            request_id=request_id,
            error_code=error_code,
            error_message=error_message,
            error_data=error_data,
        )
    
    @staticmethod
    def notification(
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> MCPNotification:
        """构建通知消息"""
        return MCPNotification.create(method=method, params=params)
