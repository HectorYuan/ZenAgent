"""
协作协商器
处理 Agent 间的协作协商过程
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime, timedelta
import uuid

from .protocols import (
    CollaborationRequest,
    CollaborationResponse,
    CollaborationProtocol,
    MessagePriority,
)


class NegotiationStatus(Enum):
    """协商状态枚举"""
    PENDING = "pending"       # 等待中
    NEGOTIATING = "negotiating"  # 协商中
    ACCEPTED = "accepted"     # 已接受
    DECLINED = "declined"     # 已拒绝
    TIMEOUT = "timeout"       # 超时
    CANCELLED = "cancelled"   # 已取消
    COMPLETED = "completed"  # 已完成


@dataclass
class NegotiationResponse:
    """协商响应"""
    response_id: str
    request_id: str
    responder_id: str
    responder_name: str
    accepted: bool
    status: str
    agreed_capabilities: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "response_id": self.response_id,
            "request_id": self.request_id,
            "responder_id": self.responder_id,
            "responder_name": self.responder_name,
            "accepted": self.accepted,
            "status": self.status,
            "agreed_capabilities": self.agreed_capabilities,
        }


@dataclass
class NegotiationResult:
    """协商结果"""
    negotiation_id: str
    request: CollaborationRequest
    
    # 协商状态
    status: NegotiationStatus = NegotiationStatus.PENDING
    
    # 参与方
    initiator_id: str = ""
    participants: List[str] = field(default_factory=list)  # 参与者 ID 列表
    declined_by: List[str] = field(default_factory=list)   # 拒绝的参与者
    
    # 最终协议
    agreed_capabilities: List[str] = field(default_factory=list)
    agreed_timeout: int = 60
    final_result: Optional[Dict[str, Any]] = None
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # 错误信息
    error: Optional[str] = None
    
    @property
    def is_successful(self) -> bool:
        """协商是否成功"""
        return self.status in [
            NegotiationStatus.ACCEPTED,
            NegotiationStatus.COMPLETED,
        ]
    
    @property
    def is_completed(self) -> bool:
        """协商是否完成"""
        return self.status == NegotiationStatus.COMPLETED
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "negotiation_id": self.negotiation_id,
            "request": self.request.to_dict(),
            "status": self.status.value,
            "initiator_id": self.initiator_id,
            "participants": self.participants,
            "declined_by": self.declined_by,
            "agreed_capabilities": self.agreed_capabilities,
            "agreed_timeout": self.agreed_timeout,
            "final_result": self.final_result,
            "created_at": self.created_at.isoformat(),
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "error": self.error,
        }


class CollaborationNegotiator:
    """
    协作协商器
    
    处理 Agent 间的协作协商逻辑
    """
    
    def __init__(self):
        """初始化协商器"""
        # 协商记录
        self._negotiations: Dict[str, NegotiationResult] = {}
        
        # 待处理的请求
        self._pending_requests: Dict[str, CollaborationRequest] = {}
        
        # 协商回调
        self._on_negotiation_start: List[Callable[[NegotiationResult], None]] = []
        self._on_negotiation_complete: List[Callable[[NegotiationResult], None]] = []
        self._on_request_received: List[Callable[[CollaborationRequest], None]] = []
    
    def create_negotiation(
        self,
        request: CollaborationRequest
    ) -> NegotiationResult:
        """
        创建协商
        
        Args:
            request: 协作请求
            
        Returns:
            NegotiationResult: 协商结果对象
        """
        negotiation = NegotiationResult(
            negotiation_id=str(uuid.uuid4()),
            request=request,
            initiator_id=request.requester_id,
        )
        
        # 设置过期时间
        negotiation.expires_at = datetime.now() + timedelta(
            seconds=request.timeout_seconds
        )
        
        self._negotiations[negotiation.negotiation_id] = negotiation
        self._pending_requests[request.request_id] = request
        
        # 触发回调
        for callback in self._on_negotiation_start:
            try:
                callback(negotiation)
            except Exception:
                pass
        
        return negotiation
    
    def get_negotiation(self, negotiation_id: str) -> Optional[NegotiationResult]:
        """获取协商"""
        return self._negotiations.get(negotiation_id)
    
    def get_request(self, request_id: str) -> Optional[CollaborationRequest]:
        """获取请求"""
        return self._pending_requests.get(request_id)
    
    def accept_request(
        self,
        request_id: str,
        responder_id: str,
        responder_name: str,
        agreed_capabilities: Optional[List[str]] = None
    ) -> Optional[NegotiationResponse]:
        """
        接受请求
        
        Args:
            request_id: 请求 ID
            responder_id: 响应者 ID
            responder_name: 响应者名称
            agreed_capabilities: 协商后的能力列表
            
        Returns:
            Optional[NegotiationResponse]: 协商响应
        """
        request = self._pending_requests.get(request_id)
        if request is None:
            return None
        
        # 创建响应
        response = NegotiationResponse(
            response_id=str(uuid.uuid4()),
            request_id=request_id,
            responder_id=responder_id,
            responder_name=responder_name,
            accepted=True,
            status="accepted",
            agreed_capabilities=agreed_capabilities or request.required_capabilities,
        )
        
        # 更新协商状态
        for neg_id, negotiation in self._negotiations.items():
            if negotiation.request.request_id == request_id:
                negotiation.status = NegotiationStatus.ACCEPTED
                negotiation.participants.append(responder_id)
                negotiation.agreed_capabilities = response.agreed_capabilities
                negotiation.agreed_timeout = request.timeout_seconds
                negotiation.accepted_at = datetime.now()
                break
        
        return response
    
    def decline_request(
        self,
        request_id: str,
        responder_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        拒绝请求
        
        Args:
            request_id: 请求 ID
            responder_id: 拒绝者 ID
            reason: 拒绝原因
            
        Returns:
            bool: 是否成功
        """
        # 更新协商状态
        for neg_id, negotiation in self._negotiations.items():
            if negotiation.request.request_id == request_id:
                negotiation.declined_by.append(responder_id)
                if reason:
                    negotiation.error = reason
                return True
        
        return False
    
    def complete_negotiation(
        self,
        negotiation_id: str,
        result: Dict[str, Any]
    ) -> bool:
        """
        完成协商
        
        Args:
            negotiation_id: 协商 ID
            result: 最终结果
            
        Returns:
            bool: 是否成功
        """
        negotiation = self._negotiations.get(negotiation_id)
        if negotiation is None:
            return False
        
        negotiation.status = NegotiationStatus.COMPLETED
        negotiation.final_result = result
        negotiation.completed_at = datetime.now()
        
        # 清理待处理请求
        self._pending_requests.pop(negotiation.request.request_id, None)
        
        # 触发回调
        for callback in self._on_negotiation_complete:
            try:
                callback(negotiation)
            except Exception:
                pass
        
        return True
    
    def cancel_negotiation(self, negotiation_id: str, reason: Optional[str] = None) -> bool:
        """
        取消协商
        
        Args:
            negotiation_id: 协商 ID
            reason: 取消原因
            
        Returns:
            bool: 是否成功
        """
        negotiation = self._negotiations.get(negotiation_id)
        if negotiation is None:
            return False
        
        negotiation.status = NegotiationStatus.CANCELLED
        negotiation.error = reason
        
        # 清理待处理请求
        self._pending_requests.pop(negotiation.request.request_id, None)
        
        return True
    
    def check_timeouts(self) -> List[str]:
        """
        检查超时
        
        Returns:
            List[str]: 超时的协商 ID 列表
        """
        now = datetime.now()
        timed_out = []
        
        for neg_id, negotiation in self._negotiations.items():
            if negotiation.expires_at and now > negotiation.expires_at:
                if negotiation.status in [
                    NegotiationStatus.PENDING,
                    NegotiationStatus.NEGOTIATING,
                ]:
                    negotiation.status = NegotiationStatus.TIMEOUT
                    timed_out.append(neg_id)
        
        return timed_out
    
    def list_active_negotiations(self) -> List[NegotiationResult]:
        """列出活跃的协商"""
        return [
            n for n in self._negotiations.values()
            if n.status in [
                NegotiationStatus.PENDING,
                NegotiationStatus.NEGOTIATING,
            ]
        ]
    
    def list_negotiations_by_status(
        self,
        status: NegotiationStatus
    ) -> List[NegotiationResult]:
        """按状态列出协商"""
        return [n for n in self._negotiations.values() if n.status == status]
    
    def on_negotiation_start(
        self,
        callback: Callable[[NegotiationResult], None]
    ) -> None:
        """注册协商开始回调"""
        self._on_negotiation_start.append(callback)
    
    def on_negotiation_complete(
        self,
        callback: Callable[[NegotiationResult], None]
    ) -> None:
        """注册协商完成回调"""
        self._on_negotiation_complete.append(callback)
    
    def on_request_received(
        self,
        callback: Callable[[CollaborationRequest], None]
    ) -> None:
        """注册请求接收回调"""
        self._on_request_received.append(callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self._negotiations)
        by_status = {}
        for status in NegotiationStatus:
            by_status[status.value] = len(
                self.list_negotiations_by_status(status)
            )
        
        successful = len([
            n for n in self._negotiations.values()
            if n.is_successful
        ])
        
        return {
            "total_negotiations": total,
            "by_status": by_status,
            "successful_negotiations": successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "pending_requests": len(self._pending_requests),
        }


# 全局协商器实例
_default_negotiator: Optional[CollaborationNegotiator] = None


def get_negotiator() -> CollaborationNegotiator:
    """获取全局协商器"""
    global _default_negotiator
    if _default_negotiator is None:
        _default_negotiator = CollaborationNegotiator()
    return _default_negotiator
