"""
EventBus 补充单元测试

覆盖：多订阅者、取消订阅、事件过滤、异常回调、事件历史、统计准确性
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pytest
from packages.Runtime.buses.event_bus import EventBus, Event, EventType


class TestEventBusMultiSubscriber:
    """多订阅者测试"""

    def test_multiple_subscribers_receive_same_event(self):
        """多个订阅者收到同一事件"""
        bus = EventBus(use_redis=False)
        received_a, received_b, received_c = [], [], []

        bus.subscribe("agent.created", lambda e: received_a.append(e))
        bus.subscribe("agent.created", lambda e: received_b.append(e))
        bus.subscribe("agent.created", lambda e: received_c.append(e))

        event = Event(event_type=EventType.AGENT_CREATED, source="test", data={})
        count = bus.publish(event)

        assert len(received_a) == 1
        assert len(received_b) == 1
        assert len(received_c) == 1
        assert count == 3

    def test_unsubscribe_no_longer_receives(self):
        """取消订阅后不再收到事件"""
        bus = EventBus(use_redis=False)
        received = []

        def callback(event):
            received.append(event)

        bus.subscribe("agent.created", callback)
        # 发布一次确认能收到
        event1 = Event(event_type=EventType.AGENT_CREATED, source="test", data={})
        bus.publish(event1)
        assert len(received) == 1

        # 手动移除回调（EventBus 没有 unsubscribe API，直接操作内部列表）
        bus._local_subscribers["agent.created"].remove(callback)

        # 再发布一次，不应收到
        event2 = Event(event_type=EventType.AGENT_CREATED, source="test", data={})
        bus.publish(event2)
        assert len(received) == 1  # 仍然是 1

    def test_different_event_type_filtering(self):
        """不同事件类型过滤——订阅者只收到订阅类型的事件"""
        bus = EventBus(use_redis=False)
        agent_events, session_events = [], []

        bus.subscribe("agent.created", lambda e: agent_events.append(e))
        bus.subscribe("session.started", lambda e: session_events.append(e))

        bus.publish(Event(event_type=EventType.AGENT_CREATED, source="test", data={}))
        bus.publish(Event(event_type=EventType.SESSION_STARTED, source="test", data={}))
        bus.publish(Event(event_type=EventType.AGENT_CREATED, source="test", data={}))

        assert len(agent_events) == 2
        assert len(session_events) == 1

    def test_exception_in_callback_does_not_break_others(self):
        """异常回调不影响其他订阅者"""
        bus = EventBus(use_redis=False)
        good_received = []

        def bad_callback(event):
            raise ValueError("故意抛出异常")

        def good_callback(event):
            good_received.append(event)

        bus.subscribe("agent.created", bad_callback)
        bus.subscribe("agent.created", good_callback)

        event = Event(event_type=EventType.AGENT_CREATED, source="test", data={})
        count = bus.publish(event)

        # good_callback 应该被调用，bad_callback 异常被吞掉
        assert len(good_received) == 1
        assert count == 1  # 只有 good_callback 成功

    def test_event_history_via_subscriber(self):
        """事件历史可通过订阅者回调收集验证"""
        bus = EventBus(use_redis=False)
        history = []

        bus.subscribe("agent.created", lambda e: history.append(e))
        bus.subscribe("session.started", lambda e: history.append(e))

        for i in range(5):
            bus.publish(Event(event_type=EventType.AGENT_CREATED, source=f"src_{i}", data={"i": i}))

        bus.publish(Event(event_type=EventType.SESSION_STARTED, source="sess", data={}))

        assert len(history) == 6
        assert history[0].data["i"] == 0
        assert history[-1].event_type == EventType.SESSION_STARTED

    def test_stats_accuracy(self):
        """统计信息准确性"""
        bus = EventBus(use_redis=False)

        # 初始状态
        stats = bus.get_stats()
        assert stats["local_subscribers"] == 0
        assert stats["event_types"] == []

        # 添加订阅者
        bus.subscribe("agent.created", lambda e: None)
        bus.subscribe("agent.created", lambda e: None)
        bus.subscribe("session.started", lambda e: None)

        stats = bus.get_stats()
        assert stats["local_subscribers"] == 3
        assert set(stats["event_types"]) == {"agent.created", "session.started"}
        assert stats["use_redis"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
