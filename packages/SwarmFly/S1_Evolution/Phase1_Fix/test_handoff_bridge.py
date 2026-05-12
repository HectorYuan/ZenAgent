"""
HandoffBridge边界测试用例

测试各种边界条件和异常场景
修复版本: v1.1 (S1进化)
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handoff_bridge import (
    HandoffBridge, 
    HandoffState, 
    HandoffPriority,
    HandoffContext,
    HandoffResult
)
from datetime import datetime, timedelta


class TestHandoffBridgeBasic:
    """基础功能测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.bridge = HandoffBridge()
    
    def test_initiate_basic_handoff(self):
        """测试基本交接"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            task_data={"task": "test_task"}
        )
        
        assert handoff_id is not None
        assert handoff_id in self.bridge._active_handoffs
    
    def test_confirm_handoff(self):
        """测试确认交接"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            task_data={"task": "test_task"}
        )
        
        result = self.bridge.confirm_handoff(handoff_id, {"status": "confirmed"})
        
        assert result.is_successful()
        assert result.state == HandoffState.CONFIRMED
        assert handoff_id not in self.bridge._active_handoffs
    
    def test_complete_handoff(self):
        """测试完成交接"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            task_data={"task": "test_task"}
        )
        
        result = self.bridge.complete_handoff(handoff_id, {"result": "success"})
        
        assert result.is_successful()
        assert result.state == HandoffState.COMPLETED
        assert result.result_data == {"result": "success"}


class TestHandoffBridgeBoundary:
    """边界条件测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.bridge = HandoffBridge()
    
    def test_empty_source_agent_id(self):
        """边界: 空源智能体ID"""
        with pytest.raises(ValueError, match="source_agent_id cannot be empty"):
            self.bridge.initiate_handoff(
                source_agent_id="",
                target_agent_id="agent_2",
                task_data={"task": "test"}
            )
    
    def test_empty_target_agent_id(self):
        """边界: 空目标智能体ID"""
        with pytest.raises(ValueError, match="target_agent_id cannot be empty"):
            self.bridge.initiate_handoff(
                source_agent_id="agent_1",
                target_agent_id="",
                task_data={"task": "test"}
            )
    
    def test_same_source_and_target(self):
        """边界: 源和目标相同"""
        with pytest.raises(ValueError, match="source and target agents cannot be the same"):
            self.bridge.initiate_handoff(
                source_agent_id="agent_1",
                target_agent_id="agent_1",
                task_data={"task": "test"}
            )
    
    def test_empty_task_data(self):
        """边界: 空任务数据"""
        with pytest.raises(ValueError, match="task_data cannot be empty"):
            self.bridge.initiate_handoff(
                source_agent_id="agent_1",
                target_agent_id="agent_2",
                task_data={}
            )
    
    def test_none_task_data(self):
        """边界: None任务数据"""
        with pytest.raises(ValueError, match="task_data cannot be empty"):
            self.bridge.initiate_handoff(
                source_agent_id="agent_1",
                target_agent_id="agent_2",
                task_data=None
            )
    
    def test_handoff_not_found(self):
        """边界: 交接不存在"""
        with pytest.raises(ValueError, match="Handoff .* not found"):
            self.bridge.confirm_handoff("nonexistent_handoff")
    
    def test_confirm_completed_handoff(self):
        """边界: 重复确认已完成交接"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            task_data={"task": "test"}
        )
        
        self.bridge.complete_handoff(handoff_id)
        
        # 尝试再次确认
        with pytest.raises(ValueError, match="Handoff .* not found"):
            self.bridge.confirm_handoff(handoff_id)


class TestHandoffBridgeTimeout:
    """超时测试"""
    
    def test_default_timeout(self):
        """测试默认超时"""
        bridge = HandoffBridge({"default_timeout": 1})
        
        handoff_id = bridge.initiate_handoff(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            task_data={"task": "test"}
        )
        
        context = bridge._active_handoffs[handoff_id]
        assert context.timeout_seconds == 1
        assert not context.is_expired()
    
    def test_custom_timeout(self):
        """测试自定义超时"""
        bridge = HandoffBridge()
        
        handoff_id = bridge.initiate_handoff(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            task_data={"task": "test"},
            timeout_seconds=60
        )
        
        context = bridge._active_handoffs[handoff_id]
        assert context.timeout_seconds == 60
    
    def test_timeout_detection(self):
        """测试超时检测"""
        bridge = HandoffBridge({"default_timeout": 1})
        
        handoff_id = bridge.initiate_handoff(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            task_data={"task": "test"}
        )
        
        # 手动修改创建时间模拟超时
        context = bridge._active_handoffs[handoff_id]
        context.created_at = datetime.now() - timedelta(seconds=2)
        
        assert context.is_expired()
        assert context.time_remaining() == 0
    
    def test_timeout_handling(self):
        """测试超时处理"""
        bridge = HandoffBridge({"default_timeout": 1})
        
        handoff_id = bridge.initiate_handoff(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            task_data={"task": "test"}
        )
        
        # 手动修改创建时间模拟超时
        context = bridge._active_handoffs[handoff_id]
        context.created_at = datetime.now() - timedelta(seconds=2)
        
        # 尝试确认应该触发超时
        result = bridge.confirm_handoff(handoff_id)
        
        assert result.state == HandoffState.TIMEOUT
        assert result.error_message == "Handoff timeout"


class TestHandoffBridgeConcurrency:
    """并发测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.bridge = HandoffBridge()
    
    def test_multiple_handoffs(self):
        """测试多个并发交接"""
        handoff_ids = []
        
        for i in range(10):
            handoff_id = self.bridge.initiate_handoff(
                source_agent_id=f"agent_{i}",
                target_agent_id=f"agent_{i+1}",
                task_data={"task": f"test_{i}"}
            )
            handoff_ids.append(handoff_id)
        
        assert len(self.bridge._active_handoffs) == 10
        
        # 完成所有交接
        for handoff_id in handoff_ids:
            self.bridge.complete_handoff(handoff_id)
        
        assert len(self.bridge._active_handoffs) == 0
        assert len(self.bridge._handoff_history) == 10
    
    def test_parallel_handshake(self):
        """测试并行握手"""
        handoff_id_1 = self.bridge.initiate_handoff(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            task_data={"task": "test_1"}
        )
        
        handoff_id_2 = self.bridge.initiate_handoff(
            source_agent_id="agent_2",
            target_agent_id="agent_3",
            task_data={"task": "test_2"}
        )
        
        # 并行确认
        result_1 = self.bridge.confirm_handoff(handoff_id_1)
        result_2 = self.bridge.confirm_handoff(handoff_id_2)
        
        assert result_1.is_successful()
        assert result_2.is_successful()


class TestHandoffBridgePriority:
    """优先级测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.bridge = HandoffBridge()
    
    def test_priority_levels(self):
        """测试优先级级别"""
        priorities = [
            HandoffPriority.LOW,
            HandoffPriority.NORMAL,
            HandoffPriority.HIGH,
            HandoffPriority.CRITICAL
        ]
        
        for priority in priorities:
            handoff_id = self.bridge.initiate_handoff(
                source_agent_id="agent_1",
                target_agent_id="agent_2",
                task_data={"task": "test"},
                priority=priority
            )
            
            context = self.bridge._active_handoffs[handoff_id]
            assert context.priority == priority


class TestHandoffBridgeMetadata:
    """元数据测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.bridge = HandoffBridge()
    
    def test_metadata_persistence(self):
        """测试元数据持久化"""
        metadata = {
            "key1": "value1",
            "key2": 123,
            "nested": {"a": 1, "b": 2}
        }
        
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            task_data={"task": "test"},
            metadata=metadata
        )
        
        context = self.bridge._active_handoffs[handoff_id]
        assert context.metadata == metadata
        
        # 确认后元数据应该保留
        result = self.bridge.complete_handoff(handoff_id)
        assert result.context.metadata == metadata


class TestHandoffBridgeStats:
    """统计测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.bridge = HandoffBridge()
    
    def test_stats_initialization(self):
        """测试统计初始化"""
        stats = self.bridge.get_stats()
        
        assert stats["total_handoffs"] == 0
        assert stats["successful_handoffs"] == 0
        assert stats["failed_handoffs"] == 0
        assert stats["timeout_handoffs"] == 0
    
    def test_stats_update_on_success(self):
        """测试成功时统计更新"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            task_data={"task": "test"}
        )
        
        self.bridge.complete_handoff(handoff_id)
        
        stats = self.bridge.get_stats()
        assert stats["total_handoffs"] == 1
        assert stats["successful_handoffs"] == 1
    
    def test_stats_update_on_failure(self):
        """测试失败时统计更新"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            task_data={"task": "test"}
        )
        
        self.bridge.fail_handoff(handoff_id, "Test error")
        
        stats = self.bridge.get_stats()
        assert stats["total_handoffs"] == 1
        assert stats["failed_handoffs"] == 1


class TestHandoffBridgeHistory:
    """历史记录测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.bridge = HandoffBridge({"max_history_size": 5})
    
    def test_history_recording(self):
        """测试历史记录"""
        for i in range(3):
            handoff_id = self.bridge.initiate_handoff(
                source_agent_id="agent_1",
                target_agent_id="agent_2",
                task_data={"task": f"test_{i}"}
            )
            self.bridge.complete_handoff(handoff_id)
        
        assert len(self.bridge._handoff_history) == 3
    
    def test_history_limit(self):
        """测试历史限制"""
        for i in range(10):
            handoff_id = self.bridge.initiate_handoff(
                source_agent_id="agent_1",
                target_agent_id="agent_2",
                task_data={"task": f"test_{i}"}
            )
            self.bridge.complete_handoff(handoff_id)
        
        assert len(self.bridge._handoff_history) == 5


class TestHandoffBridgeQuery:
    """查询测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.bridge = HandoffBridge()
    
    def test_get_status_active(self):
        """测试获取活跃交接状态"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            task_data={"task": "test"}
        )
        
        status = self.bridge.get_handoff_status(handoff_id)
        
        assert status is not None
        assert status["handoff_id"] == handoff_id
        assert status["state"] == HandoffState.TRANSFERRING.value
    
    def test_get_status_completed(self):
        """测试获取已完成交接状态"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            task_data={"task": "test"}
        )
        
        self.bridge.complete_handoff(handoff_id)
        
        status = self.bridge.get_handoff_status(handoff_id)
        
        assert status is not None
        assert status["state"] == HandoffState.COMPLETED.value
    
    def test_get_status_not_found(self):
        """测试获取不存在的交接状态"""
        status = self.bridge.get_handoff_status("nonexistent")
        assert status is None
    
    def test_get_active_handoffs_by_agent(self):
        """测试按智能体获取活跃交接"""
        handoff_id = self.bridge.initiate_handoff(
            source_agent_id="agent_1",
            target_agent_id="agent_2",
            task_data={"task": "test"}
        )
        
        handoffs = self.bridge.get_active_handoffs(agent_id="agent_1")
        
        assert len(handoffs) == 1
        assert handoffs[0]["handoff_id"] == handoff_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
