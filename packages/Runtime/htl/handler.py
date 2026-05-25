"""
HiTL 处理器 - HTL Handler

整合审批流程和策略，提供完整的人工审批功能
"""

import sys
import os
# HACK: 确保项目根在 PYTHONPATH (TODO: 改为 PYTHONPATH=. 或 namespace package)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import logging

from .approval_flow import ApprovalFlow, ApprovalRequest, ApprovalResult, ApprovalStatus, ApprovalPriority
from .policy import ApprovalPolicy, PolicyEngine, RiskLevel, RiskAssessment

logger = logging.getLogger(__name__)


class HTLOperationMode(Enum):
    """HTL 操作模式"""
    SYNC = "sync"           # 同步模式：阻塞等待审批
    ASYNC = "async"         # 异步模式：立即返回，请求后续处理
    BYPASS = "bypass"       # 绕过模式：跳过审批（仅用于测试）


@dataclass
class HTLConfig:
    """HTL 配置"""
    enabled: bool = True
    default_mode: HTLOperationMode = HTLOperationMode.SYNC
    default_timeout: int = 3600
    allow_bypass: bool = False
    bypass_roles: List[str] = field(default_factory=list)
    enable_notifications: bool = True
    enable_audit_log: bool = True
    policy: Optional[ApprovalPolicy] = None


@dataclass
class HTLOperation:
    """HTL 操作"""
    operation_id: str
    operation_type: str
    operation_data: Dict[str, Any]
    context: Dict[str, Any]
    mode: HTLOperationMode
    created_at: datetime
    created_by: str
    risk_assessment: Optional[RiskAssessment] = None
    approval_request: Optional[ApprovalRequest] = None
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None


class HTLHandler:
    """
    HiTL 处理器
    
    整合策略评估和审批流程，提供统一的人工审批接口。
    """
    
    def __init__(self, config: Optional[HTLConfig] = None):
        """
        初始化 HTL 处理器
        
        Args:
            config: HTL 配置
        """
        self.config = config or HTLConfig()
        self.approval_flow = ApprovalFlow(
            default_timeout=self.config.default_timeout,
            enable_notifications=self.config.enable_notifications
        )
        self.policy = self.config.policy or ApprovalPolicy()
        self.policy_engine = PolicyEngine(self.policy)
        
        self._operations: Dict[str, HTLOperation] = {}
        self._operation_handlers: Dict[str, Callable] = {}
        self._callbacks: Dict[str, List[Callable]] = {
            "on_operation_start": [],
            "on_operation_approved": [],
            "on_operation_rejected": [],
            "on_operation_timeout": [],
            "on_operation_complete": []
        }
        self._audit_log: List[Dict[str, Any]] = []
    
    def register_operation_handler(
        self,
        operation_type: str,
        handler: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """
        注册操作处理器
        
        Args:
            operation_type: 操作类型
            handler: 处理函数
        """
        self._operation_handlers[operation_type] = handler
    
    def register_callback(self, event: str, callback: Callable) -> None:
        """注册回调"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def process(
        self,
        operation_type: str,
        operation_data: Dict[str, Any],
        created_by: str,
        context: Optional[Dict[str, Any]] = None,
        mode: Optional[HTLOperationMode] = None,
        force_approval: bool = False
    ) -> HTLOperation:
        """
        处理操作
        
        Args:
            operation_type: 操作类型
            operation_data: 操作数据
            created_by: 创建者
            context: 上下文
            mode: 操作模式
            force_approval: 强制审批
            
        Returns:
            HTLOperation: HTL 操作
        """
        operation_id = f"htl_{datetime.now().timestamp()}"
        mode = mode or self.config.default_mode
        
        # 构建上下文
        full_context = context or {}
        full_context.setdefault("hour", datetime.now().hour)
        
        # 创建操作
        operation = HTLOperation(
            operation_id=operation_id,
            operation_type=operation_type,
            operation_data=operation_data,
            context=full_context,
            mode=mode,
            created_at=datetime.now(),
            created_by=created_by
        )
        
        self._operations[operation_id] = operation
        
        # 触发回调
        for callback in self._callbacks["on_operation_start"]:
            callback(operation)
        
        # 记录审计日志
        self._log_audit("operation_start", operation)
        
        try:
            # 风险评估
            assessment = self.policy_engine.evaluate(
                operation_type,
                operation_data,
                full_context
            )
            operation.risk_assessment = assessment
            
            # 检查是否需要审批
            requires_approval = force_approval or assessment.requires_approval
            
            # 检查是否绕过
            if (mode == HTLOperationMode.BYPASS or 
                (self.config.allow_bypass and created_by in self.config.bypass_roles)):
                operation.status = "bypassed"
                operation.result = self._execute_operation(operation)
                self._complete_operation(operation)
                return operation
            
            if not requires_approval:
                # 不需要审批，直接执行
                operation.status = "approved"
                operation.result = self._execute_operation(operation)
                self._complete_operation(operation)
                return operation
            
            # 需要审批
            if mode == HTLOperationMode.SYNC:
                return self._process_sync(operation, assessment)
            else:
                return self._process_async(operation, assessment)
                
        except Exception as e:
            operation.status = "error"
            operation.error = str(e)
            logger.error(f"HTL operation failed: {e}")
            self._log_audit("operation_error", operation)
            raise
    
    def _process_sync(
        self,
        operation: HTLOperation,
        assessment: RiskAssessment
    ) -> HTLOperation:
        """同步处理"""
        # 创建审批请求
        approval_request = self.approval_flow.create_request(
            operation_type=operation.operation_type,
            operation_data=operation.operation_data,
            risk_level=assessment.risk_level.value,
            created_by=operation.created_by,
            approvers=assessment.suggested_approvers or None,
            priority=ApprovalPriority.HIGH if assessment.risk_level == RiskLevel.CRITICAL else ApprovalPriority.NORMAL,
            reason=f"Risk score: {assessment.score}. Factors: {', '.join(assessment.factors[:3])}"
        )
        
        operation.approval_request = approval_request
        
        # 注意：同步模式下需要外部调用 approve/reject
        # 这里标记为等待审批
        operation.status = "awaiting_approval"
        
        return operation
    
    def _process_async(
        self,
        operation: HTLOperation,
        assessment: RiskAssessment
    ) -> HTLOperation:
        """异步处理"""
        # 创建审批请求
        approval_request = self.approval_flow.create_request(
            operation_type=operation.operation_type,
            operation_data=operation.operation_data,
            risk_level=assessment.risk_level.value,
            created_by=operation.created_by,
            approvers=assessment.suggested_approvers or None,
            priority=ApprovalPriority.HIGH if assessment.risk_level == RiskLevel.CRITICAL else ApprovalPriority.NORMAL
        )
        
        operation.approval_request = approval_request
        operation.status = "awaiting_approval"
        
        return operation
    
    def handle_approval_result(
        self,
        request_id: str,
        approved: bool,
        approver: str,
        comments: str = ""
    ) -> Optional[HTLOperation]:
        """
        处理审批结果
        
        Args:
            request_id: 审批请求 ID
            approved: 是否批准
            approver: 审批者
            comments: 审批意见
            
        Returns:
            Optional[HTLOperation]: 相关的操作
        """
        # 查找相关操作
        operation = None
        for op in self._operations.values():
            if (op.approval_request and 
                op.approval_request.request_id == request_id):
                operation = op
                break
        
        if not operation:
            return None
        
        try:
            if approved:
                # 批准
                self.approval_flow.approve(request_id, approver, comments)
                operation.status = "approved"
                
                # 执行操作
                operation.result = self._execute_operation(operation)
                
                # 触发回调
                for callback in self._callbacks["on_operation_approved"]:
                    callback(operation)
                
                self._log_audit("operation_approved", operation)
            else:
                # 拒绝
                self.approval_flow.reject(request_id, approver, comments)
                operation.status = "rejected"
                operation.result = None
                
                # 触发回调
                self._log_audit("operation_rejected", operation)
            
            self._complete_operation(operation)
            
        except Exception as e:
            operation.status = "error"
            operation.error = str(e)
            logger.error(f"Handle approval result failed: {e}")
        
        return operation
    
    def _execute_operation(self, operation: HTLOperation) -> Any:
        """执行操作"""
        handler = self._operation_handlers.get(operation.operation_type)
        
        if not handler:
            logger.warning(f"No handler for operation type: {operation.operation_type}")
            return {"status": "no_handler", "message": "Operation executed without handler"}
        
        return handler(operation.operation_data)
    
    def _complete_operation(self, operation: HTLOperation) -> None:
        """完成操作"""
        operation.status = "completed"
        
        for callback in self._callbacks["on_operation_complete"]:
            callback(operation)
        
        self._log_audit("operation_complete", operation)
    
    def check_pending_operations(self) -> List[HTLOperation]:
        """检查待处理的审批"""
        # 检查过期请求
        self.approval_flow.check_expired_requests()
        
        # 获取所有待审批操作
        pending = []
        for operation in self._operations.values():
            if operation.status == "awaiting_approval":
                if operation.approval_request:
                    if operation.approval_request.is_expired():
                        operation.status = "timeout"
                        for callback in self._callbacks["on_operation_timeout"]:
                            callback(operation)
                    elif operation.approval_request.is_completed():
                        result = self.approval_flow.get_result(
                            operation.approval_request.request_id
                        )
                        if result:
                            if result.status == ApprovalStatus.APPROVED:
                                operation.status = "approved"
                                operation.result = self._execute_operation(operation)
                            else:
                                operation.status = "rejected"
                            
                            self._complete_operation(operation)
                
                pending.append(operation)
        
        return pending
    
    def get_operation(self, operation_id: str) -> Optional[HTLOperation]:
        """获取操作"""
        return self._operations.get(operation_id)
    
    def get_pending_operations(self) -> List[HTLOperation]:
        """获取所有待处理操作"""
        return [
            op for op in self._operations.values()
            if op.status in ["pending", "awaiting_approval"]
        ]
    
    def get_operation_history(
        self,
        created_by: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[HTLOperation]:
        """获取操作历史"""
        history = list(self._operations.values())
        
        if created_by:
            history = [op for op in history if op.created_by == created_by]
        
        if status:
            history = [op for op in history if op.status == status]
        
        history.sort(key=lambda op: op.created_at, reverse=True)
        return history[:limit]
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """获取审计日志"""
        return self._audit_log.copy()
    
    def _log_audit(self, event: str, operation: HTLOperation) -> None:
        """记录审计日志"""
        if not self.config.enable_audit_log:
            return
        
        log_entry = {
            "event": event,
            "operation_id": operation.operation_id,
            "operation_type": operation.operation_type,
            "created_by": operation.created_by,
            "status": operation.status,
            "timestamp": datetime.now().isoformat()
        }
        
        self._audit_log.append(log_entry)
        
        # 限制日志大小
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-5000:]
    
    def export_state(self) -> Dict[str, Any]:
        """导出状态"""
        return {
            "operations": {
                op_id: {
                    "operation_type": op.operation_type,
                    "operation_data": op.operation_data,
                    "context": op.context,
                    "mode": op.mode.value,
                    "created_at": op.created_at.isoformat(),
                    "created_by": op.created_by,
                    "status": op.status,
                    "risk_assessment": op.risk_assessment.to_dict() if op.risk_assessment else None,
                    "approval_request": op.approval_request.to_dict() if op.approval_request else None,
                    "result": op.result,
                    "error": op.error
                }
                for op_id, op in self._operations.items()
            },
            "audit_log": self._audit_log
        }
