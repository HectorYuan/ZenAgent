"""
Runtime 层统一入口 - Runtime Core

整合 Context Manager、Checkpoint Manager、HTL Manager 和 Session Manager
提供完整的 Runtime 功能支持
"""

import sys
import os

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass, field
import logging

from context_compaction import ContextManager, ContextConfig, ContextStats, ContextState
from checkpoint import EventStore, Event, EventType, SnapshotManager, RecoveryManager, RecoveryStrategy
from htl import HTLHandler, HTLConfig, HTLOperationMode, ApprovalFlow
from session import SessionManager, Session, SessionState, SessionEvent

logger = logging.getLogger(__name__)


@dataclass
class RuntimeConfig:
    """Runtime 配置"""
    # Context Compaction 配置
    max_tokens: int = 8000
    auto_compress: bool = True
    compression_threshold: float = 0.9
    
    # Checkpoint 配置
    checkpoint_enabled: bool = True
    snapshot_interval: int = 100
    max_snapshots: int = 10
    
    # HTL 配置
    htl_enabled: bool = True
    htl_timeout: int = 3600
    allow_bypass: bool = False
    
    # Session 配置
    session_idle_timeout: int = 300
    max_sessions: int = 1000
    auto_cleanup: bool = True
    
    # 通用配置
    enable_audit_log: bool = True
    log_level: str = "INFO"


class Runtime:
    """
    Runtime 层核心
    
    统一管理 Context、Checkpoint、HTL 和 Session 四大模块，
    提供一致的 API 接口。
    """
    
    def __init__(self, config: Optional[RuntimeConfig] = None):
        """
        初始化 Runtime
        
        Args:
            config: Runtime 配置
        """
        self.config = config or RuntimeConfig()
        
        # 初始化各模块
        self._init_context_manager()
        self._init_checkpoint_manager()
        self._init_htl_manager()
        self._init_session_manager()
        
        # 运行时状态
        self._start_time = datetime.now()
        self._stats: Dict[str, Any] = {
            "total_operations": 0,
            "total_compressions": 0,
            "total_checkpoints": 0,
            "total_approvals": 0
        }
        
        # 钩子函数
        self._hooks: Dict[str, List[Callable]] = {
            "on_start": [],
            "on_stop": [],
            "on_error": []
        }
        
        logger.info("Runtime initialized")
    
    def _init_context_manager(self) -> None:
        """初始化上下文管理器"""
        context_config = ContextConfig(
            max_tokens=self.config.max_tokens,
            auto_compress=self.config.auto_compress,
            compression_threshold=self.config.compression_threshold
        )
        self.context_manager = ContextManager(context_config)
        
        # 注册压缩回调
        self.context_manager.register_hook(
            "after_compress",
            lambda result: self._on_context_compressed(result)
        )
    
    def _init_checkpoint_manager(self) -> None:
        """初始化检查点管理器"""
        # 创建事件存储
        self.event_store = EventStore()
        
        # 创建快照管理器
        self.snapshot_manager = SnapshotManager(
            auto_snapshot=self.config.checkpoint_enabled,
            snapshot_interval=self.config.snapshot_interval,
            max_snapshots=self.config.max_snapshots
        )
        
        # 创建恢复管理器
        self.recovery_manager = RecoveryManager(
            event_store=self.event_store,
            snapshot_manager=self.snapshot_manager
        )
    
    def _init_htl_manager(self) -> None:
        """初始化 HTL 管理器"""
        htl_config = HTLConfig(
            enabled=self.config.htl_enabled,
            default_timeout=self.config.htl_timeout,
            allow_bypass=self.config.allow_bypass,
            enable_audit_log=self.config.enable_audit_log
        )
        self.htl_handler = HTLHandler(htl_config)
        self.approval_flow = self.htl_handler.approval_flow
    
    def _init_session_manager(self) -> None:
        """初始化会话管理器"""
        self.session_manager = SessionManager(
            idle_timeout=self.config.session_idle_timeout,
            max_sessions=self.config.max_sessions,
            auto_cleanup=self.config.auto_cleanup
        )
    
    # ==================== Context Management ====================
    
    def add_message(self, message: Dict[str, Any]) -> ContextStats:
        """添加消息到上下文"""
        self._stats["total_operations"] += 1
        return self.context_manager.add_message(message)
    
    def get_context(self) -> List[Dict[str, Any]]:
        """获取当前上下文"""
        return self.context_manager.get_messages()
    
    def compress_context(
        self,
        task_context: Optional[str] = None,
        force: bool = False
    ) -> Any:
        """压缩上下文"""
        result = self.context_manager.compress(force=force, task_context=task_context)
        self._stats["total_compressions"] += 1
        return result
    
    def get_context_stats(self) -> ContextStats:
        """获取上下文统计"""
        return self.context_manager.get_stats()
    
    # ==================== Checkpoint Management ====================
    
    def save_checkpoint(
        self,
        aggregate_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """保存检查点"""
        # 保存事件
        self.event_store.append(
            event_type=EventType.CHECKPOINT_SAVE,
            data={"state": state},
            aggregate_id=aggregate_id,
            metadata=metadata
        )
        
        # 保存快照
        snapshot = self.snapshot_manager.create_snapshot(
            aggregate_id=aggregate_id,
            state=state,
            metadata=metadata
        )
        
        self._stats["total_checkpoints"] += 1
        return snapshot.snapshot_id
    
    def restore_checkpoint(
        self,
        aggregate_id: str,
        strategy: RecoveryStrategy = RecoveryStrategy.SNAPSHOT_THEN_EVENTS
    ) -> Optional[Dict[str, Any]]:
        """恢复检查点"""
        result = self.recovery_manager.recover(aggregate_id, strategy=strategy)
        return result.recovered_state if result.success else None
    
    def create_event(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        aggregate_id: Optional[str] = None
    ) -> Event:
        """创建事件"""
        return self.event_store.append(
            event_type=event_type,
            data=data,
            aggregate_id=aggregate_id
        )
    
    def get_events(
        self,
        aggregate_id: Optional[str] = None,
        event_types: Optional[List[EventType]] = None
    ) -> List[Event]:
        """获取事件"""
        return self.event_store.get_events(
            aggregate_id=aggregate_id,
            event_types=event_types
        )
    
    # ==================== HTL (Human-in-the-Loop) ====================
    
    def process_with_approval(
        self,
        operation_type: str,
        operation_data: Dict[str, Any],
        created_by: str,
        context: Optional[Dict[str, Any]] = None,
        mode: Optional[HTLOperationMode] = None
    ) -> Any:
        """需要审批的操作"""
        if not self.config.htl_enabled:
            # 直接执行
            handler = self.htl_handler._operation_handlers.get(operation_type)
            if handler:
                return handler(operation_data)
            return {"status": "no_handler"}
        
        self._stats["total_operations"] += 1
        operation = self.htl_handler.process(
            operation_type=operation_type,
            operation_data=operation_data,
            created_by=created_by,
            context=context,
            mode=mode
        )
        
        if operation.status == "approved" or operation.status == "bypassed":
            self._stats["total_approvals"] += 1
            return operation.result
        
        return {
            "status": "awaiting_approval",
            "operation_id": operation.operation_id,
            "approval_request_id": operation.approval_request.request_id if operation.approval_request else None
        }
    
    def approve_operation(
        self,
        request_id: str,
        approver: str,
        comments: str = ""
    ) -> bool:
        """批准操作"""
        result = self.htl_handler.handle_approval_result(
            request_id=request_id,
            approved=True,
            approver=approver,
            comments=comments
        )
        return result is not None
    
    def reject_operation(
        self,
        request_id: str,
        approver: str,
        reason: str
    ) -> bool:
        """拒绝操作"""
        result = self.htl_handler.handle_approval_result(
            request_id=request_id,
            approved=False,
            approver=approver,
            comments=reason
        )
        return result is not None
    
    def get_pending_approvals(self) -> List[Any]:
        """获取待审批列表"""
        return self.htl_handler.get_pending_operations()
    
    # ==================== Session Management ====================
    
    def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """创建会话"""
        session = self.session_manager.create_session(user_id, metadata)
        
        # 自动开始会话
        session.start()
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self.session_manager.get_session(session_id)
    
    def end_session(self, session_id: str, reason: str = "completed") -> bool:
        """结束会话"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        if reason == "completed":
            return session.complete()
        elif reason == "failed":
            return session.fail(reason)
        else:
            return session.terminate()
    
    def list_active_sessions(self) -> List[Session]:
        """列出活跃会话"""
        return self.session_manager.list_sessions(state=SessionState.ACTIVE)
    
    # ==================== Lifecycle ====================
    
    def register_hook(self, event: str, callback: Callable) -> None:
        """注册钩子"""
        if event in self._hooks:
            self._hooks[event].append(callback)
    
    def start(self) -> None:
        """启动 Runtime"""
        logger.info("Runtime starting...")
        
        for callback in self._hooks["on_start"]:
            try:
                callback(self)
            except Exception as e:
                logger.error(f"Error in on_start hook: {e}")
        
        logger.info("Runtime started")
    
    def stop(self) -> None:
        """停止 Runtime"""
        logger.info("Runtime stopping...")
        
        # 清理会话
        self.session_manager.cleanup_idle_sessions()
        
        for callback in self._hooks["on_stop"]:
            try:
                callback(self)
            except Exception as e:
                logger.error(f"Error in on_stop hook: {e}")
        
        logger.info("Runtime stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取运行时统计"""
        return {
            "uptime": (datetime.now() - self._start_time).total_seconds(),
            "context_stats": self.context_manager.get_stats().to_dict(),
            "checkpoint_stats": {
                "total_events": self.event_store.get_event_count(),
                "total_snapshots": self.snapshot_manager.get_snapshot_count(),
                "total_checkpoints": self._stats["total_checkpoints"]
            },
            "htl_stats": {
                "pending_approvals": len(self.htl_handler.get_pending_operations()),
                "total_operations": self._stats["total_operations"],
                "total_approvals": self._stats["total_approvals"]
            },
            "session_stats": self.session_manager.get_stats(),
            "runtime_stats": self._stats
        }
    
    def export_state(self) -> Dict[str, Any]:
        """导出完整状态"""
        return {
            "config": {
                "max_tokens": self.config.max_tokens,
                "auto_compress": self.config.auto_compress,
                "checkpoint_enabled": self.config.checkpoint_enabled,
                "htl_enabled": self.config.htl_enabled,
                "session_idle_timeout": self.config.session_idle_timeout
            },
            "context": self.context_manager.export_state(),
            "sessions": {
                sid: session.to_dict()
                for sid, session in self.session_manager._sessions.items()
            },
            "stats": self.get_stats()
        }
    
    def _on_context_compressed(self, result: Any) -> None:
        """上下文压缩回调"""
        logger.info(f"Context compressed: {result.removed_count} messages removed")
        
        # 可选的自动检查点
        if self.config.checkpoint_enabled:
            self.create_event(
                event_type=EventType.ACTION_RESULT,
                data={
                    "action": "context_compressed",
                    "removed_count": result.removed_count,
                    "compression_ratio": result.compression_ratio
                }
            )


# 导出主要类
__all__ = [
    "Runtime",
    "RuntimeConfig",
    "ContextManager",
    "ContextConfig",
    "ContextStats",
    "EventStore",
    "Event",
    "EventType",
    "SnapshotManager",
    "Snapshot",
    "RecoveryManager",
    "RecoveryStrategy",
    "HTLHandler",
    "HTLConfig",
    "HTLOperationMode",
    "ApprovalFlow",
    "SessionManager",
    "Session",
    "SessionState",
    "SessionEvent",
]
