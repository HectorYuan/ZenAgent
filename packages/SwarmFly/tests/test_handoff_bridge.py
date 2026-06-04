"""
HandoffBridge 交接桥接模块单元测试
"""

import pytest
import sys
import os
from unittest.mock import MagicMock
from datetime import datetime, timedelta

PACKAGES_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PACKAGES_DIR)

from SwarmFly.handoff_bridge import (
    HandoffState,
    HandoffPriority,
    HandoffContext,
    HandoffResult,
    HandoffBridge,
)


class TestHandoffState:
    """HandoffState 枚举测试"""

    def test_state_values(self):
        """测试状态枚举值"""
        assert HandoffState.IDLE.value == "idle"
        assert HandoffState.INITIATING.value == "initiating"
        assert HandoffState.TRANSFERRING.value == "transferring"
        assert HandoffState.CONFIRMED.value == "confirmed"
        assert HandoffState.COMPLETED.value == "completed"
        assert HandoffState.FAILED.value == "failed"
        assert HandoffState.TIMEOUT.value == "timeout"
        assert HandoffState.CANCELLED.value == "cancelled"


class TestHandoffPriority:
    """HandoffPriority 枚举测试"""

    def test_priority_ordering(self):
        """测试优先级排序"""
        assert HandoffPriority.LOW.value < HandoffPriority.NORMAL.value
        assert HandoffPriority.NORMAL.value < HandoffPriority.HIGH.value
        assert HandoffPriority.HIGH.value < HandoffPriority.CRITICAL.value

    def test_priority_values(self):
        """测试优先级具体值"""
        assert HandoffPriority.LOW.value == 1
        assert HandoffPriority.NORMAL.value == 5
        assert HandoffPriority.HIGH.value == 10
        assert HandoffPriority.CRITICAL.value == 20


class TestHandoffContext:
    """HandoffContext 数据类测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.context = HandoffContext(
            task_id="task_001",
            source_agent_id="agent_a",
            target_agent_id="agent_b",
            task_data={"action": "delegate", "payload": "hello"},
            priority=HandoffPriority.HIGH,
            timeout_seconds=300,
        )

    def test_context_creation(self):
        """测试上下文创建"""
        assert self.context.task_id == "task_001"
        assert self.context.source_agent_id == "agent_a"
        assert self.context.target_agent_id == "agent_b"
        assert self.context.priority == HandoffPriority.HIGH
        assert self.context.timeout_seconds == 300

    def test_context_default_metadata(self):
        """测试默认元数据为空字典"""
        assert self.context.metadata == {}

    def test_is_expired_not_expired(self):
        """测试未超时"""
        assert self.context.is_expired() is False

    def test_is_expired_when_expired(self):
        """测试已超时"""
        context = HandoffContext(
            task_id="task_expired",
            source_agent_id="a",
            target_agent_id="b",
            task_data={"k": "v"},
            timeout_seconds=0,
            created_at=datetime.now() - timedelta(seconds=10),
        )
        assert context.is_expired() is True

    def test_time_remaining_positive(self):
        """测试剩余时间为正"""
        remaining = self.context.time_remaining()
        assert remaining > 0
        assert remaining <= 300

    def test_time_remaining_zero_after_timeout(self):
        """测试超时后剩余时间为零"""
        context = HandoffContext(
            task_id="task_zero",
            source_agent_id="a",
            target_agent_id="b",
            task_data={"k": "v"},
            timeout_seconds=0,
            created_at=datetime.now() - timedelta(seconds=5),
        )
        assert context.time_remaining() == 0


class TestHandoffResult:
    """HandoffResult 数据类测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.context = HandoffContext(
            task_id="task_r",
            source_agent_id="a",
            target_agent_id="b",
            task_data={"k": "v"},
        )

    def test_result_successful_confirmed(self):
        """测试确认状态为成功"""
        result = HandoffResult(
            handoff_id="h1",
            state=HandoffState.CONFIRMED,
            context=self.context,
        )
        assert result.is_successful() is True

    def test_result_successful_completed(self):
        """测试完成状态为成功"""
        result = HandoffResult(
            handoff_id="h2",
            state=HandoffState.COMPLETED,
            context=self.context,
        )
        assert result.is_successful() is True

    def test_result_not_successful_failed(self):
        """测试失败状态不是成功"""
        result = HandoffResult(
            handoff_id="h3",
            state=HandoffState.FAILED,
            context=self.context,
        )
        assert result.is_successful() is False


class TestHandoffBridge:
    """HandoffBridge 核心功能测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.bridge = HandoffBridge()
        self.source = "agent_alpha"
        self.target = "agent_beta"
        self.task_data = {"task_id": "t1", "action": "process", "data": [1, 2, 3]}

    def test_bridge_creation_default(self):
        """测试默认创建 HandoffBridge"""
        bridge = HandoffBridge()
        assert bridge.default_timeout == 300
        assert bridge.max_retry_attempts == 3
        assert bridge.stats["total_handoffs"] == 0

    def test_bridge_creation_with_config(self):
        """测试带配置创建 HandoffBridge"""
        bridge = HandoffBridge(config={"default_timeout": 60, "max_retry_attempts": 5})
        assert bridge.default_timeout == 60
        assert bridge.max_retry_attempts == 5

    def test_initiate_handoff_success(self):
        """测试成功发起交接"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
            priority=HandoffPriority.HIGH,
        )
        assert handoff_id.startswith("handoff_")
        assert self.bridge.stats["total_handoffs"] == 1
        assert handoff_id in self.bridge._active_handoffs

    def test_initiate_handoff_empty_source_raises(self):
        """测试空源智能体ID抛出异常"""
        with pytest.raises(ValueError, match="source_agent_id cannot be empty"):
            self.bridge.initiate_handoff(
                source_agent_id="",
                target_agent_id=self.target,
                task_data=self.task_data,
            )

    def test_initiate_handoff_same_agent_raises(self):
        """测试源和目标相同抛出异常"""
        with pytest.raises(ValueError, match="source and target agents cannot be the same"):
            self.bridge.initiate_handoff(
                source_agent_id="agent_same",
                target_agent_id="agent_same",
                task_data=self.task_data,
            )

    def test_initiate_handoff_empty_task_raises(self):
        """测试空任务数据抛出异常"""
        with pytest.raises(ValueError, match="task_data cannot be empty"):
            self.bridge.initiate_handoff(
                source_agent_id=self.source,
                target_agent_id=self.target,
                task_data={},
            )

    def test_confirm_handoff_success(self):
        """测试确认交接成功"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
        )
        result = self.bridge.confirm_handoff(handoff_id, result_data={"status": "ok"})
        assert result.state == HandoffState.CONFIRMED
        assert result.is_successful() is True
        assert result.result_data == {"status": "ok"}
        assert handoff_id not in self.bridge._active_handoffs

    def test_confirm_handoff_not_found_raises(self):
        """测试确认不存在的交接抛出异常"""
        with pytest.raises(ValueError, match="not found"):
            self.bridge.confirm_handoff("nonexistent_id")

    def test_complete_handoff_success(self):
        """测试完成交接并更新统计"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
        )
        result = self.bridge.complete_handoff(handoff_id, result_data={"output": "done"})
        assert result.state == HandoffState.COMPLETED
        assert result.is_successful() is True
        assert self.bridge.stats["successful_handoffs"] == 1
        assert handoff_id not in self.bridge._active_handoffs
        # 平均时间应已更新
        assert self.bridge.stats["avg_handoff_time"] >= 0

    def test_fail_handoff_updates_stats(self):
        """测试交接失败更新统计"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
        )
        result = self.bridge.fail_handoff(handoff_id, error_message="connection lost")
        assert result.state == HandoffState.FAILED
        assert result.error_message == "connection lost"
        assert result.is_successful() is False
        assert self.bridge.stats["failed_handoffs"] == 1

    def test_cancel_handoff(self):
        """测试取消交接"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
        )
        result = self.bridge.cancel_handoff(handoff_id, reason="user cancelled")
        assert result.state == HandoffState.CANCELLED
        assert result.error_message == "user cancelled"
        assert handoff_id not in self.bridge._active_handoffs

    def test_full_handoff_lifecycle(self):
        """测试完整交接生命周期: 发起 -> 确认 -> 完成"""
        # 发起
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
            priority=HandoffPriority.CRITICAL,
            timeout_seconds=60,
        )
        assert handoff_id in self.bridge._active_handoffs
        assert self.bridge.stats["total_handoffs"] == 1

        # 确认
        confirm_result = self.bridge.confirm_handoff(handoff_id)
        assert confirm_result.state == HandoffState.CONFIRMED
        # 确认后已从活跃列表移除
        assert handoff_id not in self.bridge._active_handoffs

        # 重新发起以测试 complete（因为 confirm 已经移除了）
        handoff_id2 = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
        )
        complete_result = self.bridge.complete_handoff(handoff_id2, result_data={"final": True})
        assert complete_result.state == HandoffState.COMPLETED
        assert complete_result.result_data == {"final": True}

    def test_timeout_on_confirm(self):
        """测试确认时超时处理"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
            timeout_seconds=1,  # 使用最小正值（0 会被 or 替换为默认值）
        )
        # 手动将创建时间回退以确保超时
        self.bridge._active_handoffs[handoff_id].created_at = datetime.now() - timedelta(seconds=5)
        result = self.bridge.confirm_handoff(handoff_id)
        assert result.state == HandoffState.TIMEOUT
        assert self.bridge.stats["timeout_handoffs"] == 1

    def test_timeout_on_complete(self):
        """测试完成时超时处理"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
            timeout_seconds=1,
        )
        self.bridge._active_handoffs[handoff_id].created_at = datetime.now() - timedelta(seconds=5)
        result = self.bridge.complete_handoff(handoff_id)
        assert result.state == HandoffState.TIMEOUT
        assert self.bridge.stats["timeout_handoffs"] == 1

    def test_cleanup_expired(self):
        """测试清理超时交接"""
        # 创建两个交接，一个超时一个正常
        h1 = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
            timeout_seconds=1,
        )
        self.bridge._active_handoffs[h1].created_at = datetime.now() - timedelta(seconds=10)

        h2 = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data={"task_id": "t2", "action": "other"},
            timeout_seconds=300,
        )

        cleaned = self.bridge.cleanup_expired()
        assert cleaned == 1
        assert h1 not in self.bridge._active_handoffs
        assert h2 in self.bridge._active_handoffs

    def test_get_handoff_status_active(self):
        """测试获取活跃交接状态"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
        )
        status = self.bridge.get_handoff_status(handoff_id)
        assert status is not None
        assert status["handoff_id"] == handoff_id
        assert status["state"] == HandoffState.TRANSFERRING.value
        assert status["context"]["source_agent_id"] == self.source
        assert status["context"]["target_agent_id"] == self.target

    def test_get_handoff_status_history(self):
        """测试从历史获取交接状态"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
        )
        self.bridge.complete_handoff(handoff_id, result_data={"done": True})
        status = self.bridge.get_handoff_status(handoff_id)
        assert status is not None
        assert status["state"] == HandoffState.COMPLETED.value
        assert status["result"] == {"done": True}

    def test_get_handoff_status_not_found(self):
        """测试获取不存在的交接状态返回 None"""
        status = self.bridge.get_handoff_status("nonexistent")
        assert status is None

    def test_get_stats(self):
        """测试统计信息"""
        # 完成一次成功交接
        h1 = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
        )
        self.bridge.complete_handoff(h1)

        # 完成一次失败交接
        h2 = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data={"task_id": "t2", "action": "fail"},
        )
        self.bridge.fail_handoff(h2, error_message="oops")

        stats = self.bridge.get_stats()
        assert stats["total_handoffs"] == 2
        assert stats["successful_handoffs"] == 1
        assert stats["failed_handoffs"] == 1
        assert stats["success_rate"] == 0.5
        assert stats["active_handoffs"] == 0
        assert stats["history_size"] == 2

    def test_get_stats_empty(self):
        """测试空统计信息"""
        stats = self.bridge.get_stats()
        assert stats["total_handoffs"] == 0
        assert stats["success_rate"] == 0
        assert stats["active_handoffs"] == 0

    def test_callback_on_initiated(self):
        """测试发起回调"""
        callback = MagicMock()
        self.bridge.on_handoff_initiated = callback
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
        )
        callback.assert_called_once()
        assert callback.call_args[0][0] == handoff_id

    def test_callback_on_completed(self):
        """测试完成回调"""
        callback = MagicMock()
        self.bridge.on_handoff_completed = callback
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
        )
        self.bridge.complete_handoff(handoff_id)
        callback.assert_called_once()
        result = callback.call_args[0][0]
        assert isinstance(result, HandoffResult)
        assert result.state == HandoffState.COMPLETED

    def test_callback_on_failed(self):
        """测试失败回调"""
        callback = MagicMock()
        self.bridge.on_handoff_failed = callback
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
        )
        self.bridge.fail_handoff(handoff_id, "error")
        callback.assert_called_once()

    def test_callback_on_timeout(self):
        """测试超时回调"""
        callback = MagicMock()
        self.bridge.on_handoff_timeout = callback
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
            timeout_seconds=1,
        )
        self.bridge._active_handoffs[handoff_id].created_at = datetime.now() - timedelta(seconds=5)
        self.bridge.confirm_handoff(handoff_id)
        callback.assert_called_once()

    def test_history_trimming(self):
        """测试历史记录裁剪"""
        bridge = HandoffBridge(config={"max_history_size": 3})
        for i in range(5):
            hid = bridge.initiate_handoff(
                source_agent_id="a",
                target_agent_id="b",
                task_data={"task_id": f"t{i}"},
            )
            bridge.complete_handoff(hid)
        assert len(bridge._handoff_history) == 3

    def test_priority_custom_timeout(self):
        """测试自定义超时时间"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
            timeout_seconds=60,
        )
        context = self.bridge._active_handoffs[handoff_id]
        assert context.timeout_seconds == 60

    def test_metadata_passthrough(self):
        """测试元数据透传"""
        meta = {"trace_id": "abc123", "session": "s1"}
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id=self.source,
            target_agent_id=self.target,
            task_data=self.task_data,
            metadata=meta,
        )
        context = self.bridge._active_handoffs[handoff_id]
        assert context.metadata == meta
