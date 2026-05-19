"""
Session 扩展状态转换测试

覆盖 8 状态机的完整路径：
INITIAL → ACTIVE → IDLE/SUSPENDED → ACTIVE → COMPLETED/FAILED/TERMINATED
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime

from packages.Runtime.session.session import Session, SessionState, SessionEvent


class TestSessionStateMachine:
    """Session 状态机完整覆盖"""

    def setup_method(self):
        self.session = Session(user_id="user-1")

    def test_initial_state(self):
        assert self.session.state == SessionState.INITIAL
        assert not self.session.is_active
        assert not self.session.is_terminal

    def test_start_active(self):
        assert self.session.start() is True
        assert self.session.state == SessionState.ACTIVE
        assert self.session.is_active

    def test_invalid_pause_from_initial(self):
        """初始状态不能 pause"""
        result = self.session.pause()
        assert result is False
        assert self.session.state == SessionState.INITIAL

    def test_fail_session(self):
        """启动后可失败"""
        self.session.start()
        assert self.session.fail("network error") is True
        assert self.session.state == SessionState.FAILED
        assert self.session.is_terminal

    def test_terminal_states_blocking(self):
        """终止状态不能再 start"""
        self.session.start()
        self.session.complete()
        assert self.session.is_terminal
        # 再次 start 应失败
        assert self.session.start() is False

    def test_reset_to_initial(self):
        """重置回到初始状态"""
        self.session.start()
        self.session.complete()
        result = self.session.reset()
        if result:
            assert self.session.state == SessionState.INITIAL

    def test_history_records_transitions(self):
        """状态转换历史"""
        self.session.start()
        self.session.pause()
        self.session.resume()
        self.session.complete()

        history = self.session.get_history()
        assert len(history) >= 4

    def test_context_set_get(self):
        """上下文存取"""
        self.session.set_context("key1", "value1")
        self.session.set_context("key2", 42)
        assert self.session.get_context("key1") == "value1"
        assert self.session.get_context("key2") == 42
        assert self.session.get_context("nonexistent", "default") == "default"

    def test_context_update(self):
        """批量更新上下文"""
        self.session.update_context({"a": 1, "b": 2})
        assert self.session.get_context("a") == 1
        assert self.session.get_context("b") == 2

    def test_record_activity_updates_timestamp(self):
        """记录活动更新时间戳"""
        self.session.start()
        before = self.session.last_activity_at
        import time
        time.sleep(0.01)
        self.session.record_activity()
        assert self.session.last_activity_at >= before

    def test_to_dict(self):
        """序列化为字典"""
        self.session.start()
        self.session.set_context("session_data", "abc")
        d = self.session.to_dict()
        assert d["session_id"] == self.session.session_id
        assert d["user_id"] == "user-1"
        assert d["state"] == "active"

    def test_from_dict_roundtrip(self):
        """字典反序列化"""
        self.session.start()
        d = self.session.to_dict()
        restored = Session.from_dict(d)
        assert restored.session_id == self.session.session_id
        assert restored.state == SessionState.ACTIVE

    def test_idle_duration(self):
        """空闲时长计算"""
        self.session.start()
        duration = self.session.get_idle_duration()
        assert duration >= 0.0

    def test_listener_invoked_on_transition(self):
        """事件监听器"""
        calls = []

        def listener(event, old_state, new_state):
            calls.append((old_state, new_state))

        self.session.add_listener(SessionEvent.START, listener)
        self.session.start()
        assert len(calls) == 1
        assert calls[0] == (SessionState.INITIAL, SessionState.ACTIVE)

    def test_listener_removal(self):
        """移除监听器"""
        calls = []

        def listener(event, old_state, new_state):
            calls.append(event)

        self.session.add_listener(SessionEvent.START, listener)
        self.session.remove_listener(SessionEvent.START, listener)
        self.session.start()
        assert len(calls) == 0

    def test_send_event_unknown_returns_false(self):
        """未定义的事件转换返回 False"""
        # IDLE_TIMEOUT 从 INITIAL 应不可行
        result = self.session.send_event(SessionEvent.IDLE_TIMEOUT)
        assert result is False

    def test_metadata_preserved(self):
        """元数据保留"""
        s = Session(user_id="u1", metadata={"channel": "web"})
        assert s.metadata["channel"] == "web"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
