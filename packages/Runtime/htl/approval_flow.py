"""
审批流程 - Approval Flow

管理审批请求的创建、流转和结果处理
"""


from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import uuid


class ApprovalStatus(Enum):
    """审批状态"""
    PENDING = "pending"           # 待审批
    APPROVED = "approved"         # 已批准
    REJECTED = "rejected"         # 已拒绝
    EXPIRED = "expired"           # 已过期
    CANCELLED = "cancelled"       # 已取消
    TIMEOUT = "timeout"           # 超时


class ApprovalPriority(Enum):
    """审批优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ApprovalRequest:
    """审批请求"""
    request_id: str
    operation_type: str
    operation_data: Dict[str, Any]
    risk_level: str
    priority: ApprovalPriority
    created_at: datetime
    created_by: str
    approvers: List[str]
    status: ApprovalStatus = ApprovalStatus.PENDING
    reason: Optional[str] = None
    notes: str = ""
    deadline: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "operation_type": self.operation_type,
            "operation_data": self.operation_data,
            "risk_level": self.risk_level,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "approvers": self.approvers,
            "status": self.status.value,
            "reason": self.reason,
            "notes": self.notes,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalRequest":
        """从字典创建"""
        data = data.copy()
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["status"] = ApprovalStatus(data["status"])
        data["priority"] = ApprovalPriority(data["priority"])
        if data.get("deadline"):
            data["deadline"] = datetime.fromisoformat(data["deadline"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        return cls(**data)
    
    def is_pending(self) -> bool:
        """是否待审批"""
        return self.status == ApprovalStatus.PENDING
    
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]
    
    def is_expired(self) -> bool:
        """是否已过期"""
        if self.deadline and datetime.now() > self.deadline:
            return True
        return False


@dataclass
class ApprovalResult:
    """审批结果"""
    request_id: str
    status: ApprovalStatus
    approved_by: Optional[str]
    decided_at: datetime
    reason: Optional[str] = None
    comments: str = ""
    execution_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "approved_by": self.approved_by,
            "decided_at": self.decided_at.isoformat(),
            "reason": self.reason,
            "comments": self.comments,
            "execution_data": self.execution_data
        }


class ApprovalFlow:
    """
    审批流程管理器
    
    负责审批请求的创建、跟踪和结果处理。
    """
    
    def __init__(
        self,
        default_timeout: int = 3600,
        max_retries: int = 3,
        enable_notifications: bool = True
    ):
        """
        初始化审批流程
        
        Args:
            default_timeout: 默认超时时间（秒）
            max_retries: 最大重试次数
            enable_notifications: 是否启用通知
        """
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.enable_notifications = enable_notifications
        
        self._requests: Dict[str, ApprovalRequest] = {}
        self._results: Dict[str, ApprovalResult] = {}
        self._request_history: List[ApprovalRequest] = []
        self._callbacks: Dict[str, List[Callable]] = {
            "on_request_created": [],
            "on_request_approved": [],
            "on_request_rejected": [],
            "on_request_expired": [],
            "on_request_cancelled": []
        }
        self._approver_assignments: Dict[str, str] = {}
    
    def create_request(
        self,
        operation_type: str,
        operation_data: Dict[str, Any],
        risk_level: str,
        created_by: str,
        approvers: Optional[List[str]] = None,
        priority: ApprovalPriority = ApprovalPriority.NORMAL,
        reason: Optional[str] = None,
        deadline: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ApprovalRequest:
        """
        创建审批请求
        
        Args:
            operation_type: 操作类型
            operation_data: 操作数据
            risk_level: 风险等级
            created_by: 创建者
            approvers: 审批者列表
            priority: 优先级
            reason: 申请理由
            deadline: 截止时间
            metadata: 附加元数据
            
        Returns:
            ApprovalRequest: 审批请求
        """
        # 生成请求 ID
        request_id = str(uuid.uuid4())
        
        # 设置默认截止时间
        if deadline is None:
            deadline = datetime.now() + timedelta(seconds=self.default_timeout)
        
        # 自动分配审批者
        if not approvers:
            approvers = self._auto_assign_approvers(risk_level, operation_type)
        
        request = ApprovalRequest(
            request_id=request_id,
            operation_type=operation_type,
            operation_data=operation_data,
            risk_level=risk_level,
            priority=priority,
            created_at=datetime.now(),
            created_by=created_by,
            approvers=approvers,
            reason=reason,
            deadline=deadline,
            metadata=metadata or {}
        )
        
        self._requests[request_id] = request
        self._request_history.append(request)
        
        # 触发回调
        for callback in self._callbacks["on_request_created"]:
            callback(request)
        
        # 发送通知
        if self.enable_notifications:
            self._send_notifications(request)
        
        return request
    
    def approve(
        self,
        request_id: str,
        approver: str,
        comments: str = "",
        execution_data: Optional[Dict[str, Any]] = None
    ) -> ApprovalResult:
        """
        批准请求
        
        Args:
            request_id: 请求 ID
            approver: 审批者
            comments: 审批意见
            execution_data: 执行数据
            
        Returns:
            ApprovalResult: 审批结果
        """
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        if not request.is_pending():
            raise ValueError(f"Request {request_id} is not pending")
        
        if approver not in request.approvers:
            raise ValueError(f"Approver {approver} is not authorized")
        
        # 更新请求状态
        request.status = ApprovalStatus.APPROVED
        request.completed_at = datetime.now()
        request.notes = comments
        
        # 创建结果
        result = ApprovalResult(
            request_id=request_id,
            status=ApprovalStatus.APPROVED,
            approved_by=approver,
            decided_at=datetime.now(),
            reason=request.reason,
            comments=comments,
            execution_data=execution_data
        )
        
        self._results[request_id] = result
        
        # 触发回调
        for callback in self._callbacks["on_request_approved"]:
            callback(request, result)
        
        return result
    
    def reject(
        self,
        request_id: str,
        approver: str,
        reason: str,
        comments: str = ""
    ) -> ApprovalResult:
        """
        拒绝请求
        
        Args:
            request_id: 请求 ID
            approver: 审批者
            reason: 拒绝原因
            comments: 审批意见
            
        Returns:
            ApprovalResult: 审批结果
        """
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        if not request.is_pending():
            raise ValueError(f"Request {request_id} is not pending")
        
        # 更新请求状态
        request.status = ApprovalStatus.REJECTED
        request.completed_at = datetime.now()
        request.notes = comments
        
        # 创建结果
        result = ApprovalResult(
            request_id=request_id,
            status=ApprovalStatus.REJECTED,
            approved_by=approver,
            decided_at=datetime.now(),
            reason=reason,
            comments=comments
        )
        
        self._results[request_id] = result
        
        # 触发回调
        for callback in self._callbacks["on_request_rejected"]:
            callback(request, result)
        
        return result
    
    def cancel(self, request_id: str, cancelled_by: str) -> bool:
        """
        取消请求
        
        Args:
            request_id: 请求 ID
            cancelled_by: 取消者
            
        Returns:
            bool: 是否成功
        """
        request = self._requests.get(request_id)
        if not request:
            return False
        
        if not request.is_pending():
            return False
        
        # 更新状态
        request.status = ApprovalStatus.CANCELLED
        request.completed_at = datetime.now()
        
        # 触发回调
        for callback in self._callbacks["on_request_cancelled"]:
            callback(request)
        
        return True
    
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """获取请求"""
        return self._requests.get(request_id)
    
    def get_pending_requests(
        self,
        approver: Optional[str] = None,
        risk_level: Optional[str] = None
    ) -> List[ApprovalRequest]:
        """
        获取待审批请求
        
        Args:
            approver: 审批者过滤
            risk_level: 风险等级过滤
            
        Returns:
            List[ApprovalRequest]: 请求列表
        """
        pending = [
            r for r in self._requests.values()
            if r.is_pending() and not r.is_expired()
        ]
        
        if approver:
            pending = [r for r in pending if approver in r.approvers]
        
        if risk_level:
            pending = [r for r in pending if r.risk_level == risk_level]
        
        # 按优先级和创建时间排序
        priority_order = {
            ApprovalPriority.CRITICAL: 0,
            ApprovalPriority.HIGH: 1,
            ApprovalPriority.NORMAL: 2,
            ApprovalPriority.LOW: 3
        }
        
        pending.sort(key=lambda r: (
            priority_order.get(r.priority, 99),
            r.created_at
        ))
        
        return pending
    
    def get_result(self, request_id: str) -> Optional[ApprovalResult]:
        """获取审批结果"""
        return self._results.get(request_id)
    
    def get_request_history(
        self,
        created_by: Optional[str] = None,
        status: Optional[ApprovalStatus] = None,
        limit: int = 100
    ) -> List[ApprovalRequest]:
        """
        获取请求历史
        
        Args:
            created_by: 创建者过滤
            status: 状态过滤
            limit: 限制数量
            
        Returns:
            List[ApprovalRequest]: 历史请求
        """
        history = self._request_history
        
        if created_by:
            history = [r for r in history if r.created_by == created_by]
        
        if status:
            history = [r for r in history if r.status == status]
        
        return history[-limit:]
    
    def check_expired_requests(self) -> List[ApprovalRequest]:
        """检查并更新过期请求"""
        expired = []
        
        for request in self._requests.values():
            if request.is_pending() and request.is_expired():
                request.status = ApprovalStatus.EXPIRED
                request.completed_at = datetime.now()
                expired.append(request)
                
                for callback in self._callbacks["on_request_expired"]:
                    callback(request)
        
        return expired
    
    def register_callback(self, event: str, callback: Callable) -> None:
        """注册回调"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def set_approver_assignment(self, approver: str, role: str) -> None:
        """设置审批者角色"""
        self._approver_assignments[approver] = role
    
    def _auto_assign_approvers(
        self,
        risk_level: str,
        operation_type: str
    ) -> List[str]:
        """自动分配审批者"""
        # 根据风险等级确定审批者数量
        approver_counts = {
            "low": 0,
            "medium": 1,
            "high": 2,
            "critical": 3
        }
        
        count = approver_counts.get(risk_level, 1)
        
        # 根据角色分配审批者
        role_approvers = [
            approver
            for approver, role in self._approver_assignments.items()
            if role == "approver" or (risk_level == "critical" and role == "admin")
        ]
        
        return role_approvers[:count] if role_approvers else []
    
    def _send_notifications(self, request: ApprovalRequest) -> None:
        """发送通知"""
        # 通知审批者
        for approver in request.approvers:
            # 实际实现应调用通知服务
            pass
    
    def export_requests(self) -> List[Dict[str, Any]]:
        """导出请求"""
        return [r.to_dict() for r in self._requests.values()]
    
    def import_requests(self, requests: List[Dict[str, Any]]) -> None:
        """导入请求"""
        for req_dict in requests:
            request = ApprovalRequest.from_dict(req_dict)
            self._requests[request.request_id] = request
