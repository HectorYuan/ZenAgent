"""
HandoffBridge - 智能体交接桥接模块

负责智能体之间的任务交接和状态传递
修复版本: v1.1 (S1进化)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import logging
import uuid

logger = logging.getLogger(__name__)


class HandoffState(Enum):
    """交接状态枚举"""
    IDLE = "idle"                      # 空闲
    INITIATING = "initiating"         # 初始化中
    TRANSFERRING = "transferring"     # 传输中
    WAITING_CONFIRMATION = "waiting"   # 等待确认
    CONFIRMED = "confirmed"            # 已确认
    COMPLETED = "completed"            # 已完成
    FAILED = "failed"                  # 失败
    TIMEOUT = "timeout"                # 超时
    CANCELLED = "cancelled"            # 已取消


class HandoffPriority(Enum):
    """交接优先级"""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class HandoffContext:
    """交接上下文"""
    task_id: str
    source_agent_id: str
    target_agent_id: str
    task_data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    priority: HandoffPriority = HandoffPriority.NORMAL
    timeout_seconds: int = 300  # 默认5分钟超时
    
    def is_expired(self) -> bool:
        """检查是否超时"""
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.timeout_seconds
    
    def time_remaining(self) -> float:
        """剩余时间(秒)"""
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return max(0, self.timeout_seconds - elapsed)


@dataclass
class HandoffResult:
    """交接结果"""
    handoff_id: str
    state: HandoffState
    context: HandoffContext
    result_data: Optional[Dict] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None
    
    def is_successful(self) -> bool:
        """是否成功"""
        return self.state in (HandoffState.COMPLETED, HandoffState.CONFIRMED)


class HandoffBridge:
    """
    HandoffBridge - 智能体交接桥接模块
    
    核心功能:
    - 智能体间任务交接
    - 交接状态管理
    - 超时和重试机制
    - 交接上下文传递
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # 状态管理
        self._active_handoffs: Dict[str, HandoffContext] = {}
        self._handoff_history: List[HandoffResult] = []
        
        # 超时配置
        self.default_timeout = self.config.get("default_timeout", 300)
        self.max_retry_attempts = self.config.get("max_retry_attempts", 3)
        
        # 回调函数
        self.on_handoff_initiated: Optional[Callable] = None
        self.on_handoff_completed: Optional[Callable] = None
        self.on_handoff_failed: Optional[Callable] = None
        self.on_handoff_timeout: Optional[Callable] = None
        
        # 统计信息
        self.stats = {
            "total_handoffs": 0,
            "successful_handoffs": 0,
            "failed_handoffs": 0,
            "timeout_handoffs": 0,
            "avg_handoff_time": 0.0
        }
        
        logger.info("HandoffBridge initialized")
    
    def initiate_handoff(
        self,
        source_agent_id: str,
        target_agent_id: str,
        task_data: Dict[str, Any],
        priority: HandoffPriority = HandoffPriority.NORMAL,
        timeout_seconds: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        发起交接
        
        Args:
            source_agent_id: 源智能体ID
            target_agent_id: 目标智能体ID
            task_data: 任务数据
            priority: 优先级
            timeout_seconds: 超时时间(秒)
            metadata: 元数据
            
        Returns:
            handoff_id: 交接ID
        """
        # 边界条件检查
        if not source_agent_id:
            raise ValueError("source_agent_id cannot be empty")
        if not target_agent_id:
            raise ValueError("target_agent_id cannot be empty")
        if source_agent_id == target_agent_id:
            raise ValueError("source and target agents cannot be the same")
        if not task_data:
            raise ValueError("task_data cannot be empty")
        
        # 生成交接ID
        handoff_id = f"handoff_{uuid.uuid4().hex[:12]}"
        
        # 创建交接上下文
        context = HandoffContext(
            task_id=task_data.get("task_id", handoff_id),
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            task_data=task_data,
            metadata=metadata or {},
            priority=priority,
            timeout_seconds=timeout_seconds or self.default_timeout
        )
        
        # 存储交接上下文
        self._active_handoffs[handoff_id] = context
        
        # 更新统计
        self.stats["total_handoffs"] += 1
        
        # 触发回调
        if self.on_handoff_initiated:
            self.on_handoff_initiated(handoff_id, context)
        
        logger.info(f"Handoff {handoff_id} initiated: {source_agent_id} -> {target_agent_id}")
        
        return handoff_id
    
    def confirm_handoff(self, handoff_id: str, result_data: Optional[Dict] = None) -> HandoffResult:
        """
        确认交接
        
        Args:
            handoff_id: 交接ID
            result_data: 结果数据
            
        Returns:
            HandoffResult: 交接结果
        """
        # 边界条件检查
        if handoff_id not in self._active_handoffs:
            raise ValueError(f"Handoff {handoff_id} not found")
        
        context = self._active_handoffs[handoff_id]
        
        # 检查超时
        if context.is_expired():
            return self._handle_timeout(handoff_id)
        
        # 创建结果
        result = HandoffResult(
            handoff_id=handoff_id,
            state=HandoffState.CONFIRMED,
            context=context,
            result_data=result_data,
            completed_at=datetime.now()
        )
        
        # 移动到历史
        self._complete_handoff(handoff_id, result)
        
        # 触发回调
        if self.on_handoff_completed:
            self.on_handoff_completed(result)
        
        logger.info(f"Handoff {handoff_id} confirmed")
        
        return result
    
    def complete_handoff(self, handoff_id: str, result_data: Optional[Dict] = None) -> HandoffResult:
        """
        完成交接
        
        Args:
            handoff_id: 交接ID
            result_data: 结果数据
            
        Returns:
            HandoffResult: 交接结果
        """
        # 边界条件检查
        if handoff_id not in self._active_handoffs:
            raise ValueError(f"Handoff {handoff_id} not found")
        
        context = self._active_handoffs[handoff_id]
        
        # 检查超时
        if context.is_expired():
            return self._handle_timeout(handoff_id)
        
        # 创建结果
        result = HandoffResult(
            handoff_id=handoff_id,
            state=HandoffState.COMPLETED,
            context=context,
            result_data=result_data,
            completed_at=datetime.now()
        )
        
        # 移动到历史
        self._complete_handoff(handoff_id, result)
        
        # 更新统计
        self.stats["successful_handoffs"] += 1
        self._update_avg_time(result)
        
        # 触发回调
        if self.on_handoff_completed:
            self.on_handoff_completed(result)
        
        logger.info(f"Handoff {handoff_id} completed")
        
        return result
    
    def fail_handoff(self, handoff_id: str, error_message: str) -> HandoffResult:
        """
        交接失败
        
        Args:
            handoff_id: 交接ID
            error_message: 错误信息
            
        Returns:
            HandoffResult: 交接结果
        """
        # 边界条件检查
        if handoff_id not in self._active_handoffs:
            raise ValueError(f"Handoff {handoff_id} not found")
        
        context = self._active_handoffs[handoff_id]
        
        # 创建结果
        result = HandoffResult(
            handoff_id=handoff_id,
            state=HandoffState.FAILED,
            context=context,
            error_message=error_message,
            completed_at=datetime.now()
        )
        
        # 移动到历史
        self._complete_handoff(handoff_id, result)
        
        # 更新统计
        self.stats["failed_handoffs"] += 1
        
        # 触发回调
        if self.on_handoff_failed:
            self.on_handoff_failed(result)
        
        logger.error(f"Handoff {handoff_id} failed: {error_message}")
        
        return result
    
    def cancel_handoff(self, handoff_id: str, reason: str = "") -> HandoffResult:
        """
        取消交接
        
        Args:
            handoff_id: 交接ID
            reason: 取消原因
            
        Returns:
            HandoffResult: 交接结果
        """
        if handoff_id not in self._active_handoffs:
            raise ValueError(f"Handoff {handoff_id} not found")
        
        context = self._active_handoffs[handoff_id]
        
        # 创建结果
        result = HandoffResult(
            handoff_id=handoff_id,
            state=HandoffState.CANCELLED,
            context=context,
            error_message=reason,
            completed_at=datetime.now()
        )
        
        # 移动到历史
        self._complete_handoff(handoff_id, result)
        
        logger.info(f"Handoff {handoff_id} cancelled: {reason}")
        
        return result
    
    def _handle_timeout(self, handoff_id: str) -> HandoffResult:
        """处理超时"""
        context = self._active_handoffs[handoff_id]
        
        result = HandoffResult(
            handoff_id=handoff_id,
            state=HandoffState.TIMEOUT,
            context=context,
            error_message="Handoff timeout",
            completed_at=datetime.now()
        )
        
        # 移动到历史
        self._complete_handoff(handoff_id, result)
        
        # 更新统计
        self.stats["timeout_handoffs"] += 1
        
        # 触发回调
        if self.on_handoff_timeout:
            self.on_handoff_timeout(result)
        
        logger.warning(f"Handoff {handoff_id} timeout")
        
        return result
    
    def _complete_handoff(self, handoff_id: str, result: HandoffResult):
        """完成交接处理"""
        # 从活跃列表移除
        if handoff_id in self._active_handoffs:
            del self._active_handoffs[handoff_id]
        
        # 添加到历史
        self._handoff_history.append(result)
        
        # 限制历史长度
        max_history = self.config.get("max_history_size", 1000)
        if len(self._handoff_history) > max_history:
            self._handoff_history = self._handoff_history[-max_history:]
    
    def _update_avg_time(self, result: HandoffResult):
        """更新平均交接时间"""
        if result.completed_at and result.context.created_at:
            handoff_time = (result.completed_at - result.context.created_at).total_seconds()
            total = self.stats["successful_handoffs"]
            current_avg = self.stats["avg_handoff_time"]
            self.stats["avg_handoff_time"] = (current_avg * (total - 1) + handoff_time) / total
    
    def get_handoff_status(self, handoff_id: str) -> Optional[Dict]:
        """
        获取交接状态
        
        Args:
            handoff_id: 交接ID
            
        Returns:
            交接状态字典
        """
        # 检查活跃交接
        if handoff_id in self._active_handoffs:
            context = self._active_handoffs[handoff_id]
            return {
                "handoff_id": handoff_id,
                "state": HandoffState.TRANSFERRING.value,
                "context": {
                    "task_id": context.task_id,
                    "source_agent_id": context.source_agent_id,
                    "target_agent_id": context.target_agent_id,
                    "time_remaining": context.time_remaining(),
                    "is_expired": context.is_expired()
                }
            }
        
        # 检查历史
        for result in reversed(self._handoff_history):
            if result.handoff_id == handoff_id:
                return {
                    "handoff_id": handoff_id,
                    "state": result.state.value,
                    "result": result.result_data,
                    "error": result.error_message,
                    "completed_at": result.completed_at.isoformat() if result.completed_at else None
                }
        
        return None
    
    def get_active_handoffs(
        self,
        agent_id: Optional[str] = None,
        state: Optional[HandoffState] = None
    ) -> List[Dict]:
        """
        获取活跃交接列表
        
        Args:
            agent_id: 智能体ID(可选)
            state: 状态(可选)
            
        Returns:
            交接列表
        """
        handoffs = []
        
        for handoff_id, context in self._active_handoffs.items():
            # 按智能体过滤
            if agent_id:
                if agent_id != context.source_agent_id and agent_id != context.target_agent_id:
                    continue
            
            # 按状态过滤
            if state:
                if state == HandoffState.TRANSFERRING or state == HandoffState.WAITING_CONFIRMATION:
                    handoffs.append({
                        "handoff_id": handoff_id,
                        "state": state.value,
                        "context": {
                            "task_id": context.task_id,
                            "source_agent_id": context.source_agent_id,
                            "target_agent_id": context.target_agent_id,
                            "time_remaining": context.time_remaining()
                        }
                    })
        
        return handoffs
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "active_handoffs": len(self._active_handoffs),
            "history_size": len(self._handoff_history),
            "success_rate": (
                self.stats["successful_handoffs"] / self.stats["total_handoffs"]
                if self.stats["total_handoffs"] > 0 else 0
            )
        }
    
    def cleanup_expired(self) -> int:
        """
        清理超时交接
        
        Returns:
            清理数量
        """
        expired_ids = [
            handoff_id for handoff_id, context in self._active_handoffs.items()
            if context.is_expired()
        ]
        
        for handoff_id in expired_ids:
            self._handle_timeout(handoff_id)
        
        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired handoffs")
        
        return len(expired_ids)
