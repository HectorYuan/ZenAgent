"""
Runtime Buses 单元测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pytest
import time
from packages.Runtime.buses.event_bus import EventBus, Event, EventType
from packages.Runtime.buses.task_queue import TaskQueue, Task, TaskPriority


class TestEventBus:
    """事件总线测试"""
    
    def test_creation(self):
        """测试创建"""
        bus = EventBus(use_redis=False)
        assert bus is not None
        print("✓ EventBus 创建成功")
    
    def test_publish_subscribe(self):
        """测试发布订阅"""
        bus = EventBus(use_redis=False)
        received = []
        
        def callback(event):
            received.append(event)
        
        bus.subscribe("agent.created", callback)
        
        event = Event(
            event_type=EventType.AGENT_CREATED,
            source="test",
            data={"agent_id": "agent_001"}
        )
        
        bus.publish(event)
        assert len(received) == 1
        assert received[0].event_type == EventType.AGENT_CREATED
        print("✓ 发布订阅测试通过")
    
    def test_stats(self):
        """测试统计"""
        bus = EventBus(use_redis=False)
        stats = bus.get_stats()
        assert 'local_subscribers' in stats
        assert 'use_redis' in stats
        print(f"✓ 统计信息: {stats}")


class TestTaskQueue:
    """任务队列测试"""
    
    def test_creation(self):
        """测试创建"""
        queue = TaskQueue(use_redis=False)
        assert queue is not None
        print("✓ TaskQueue 创建成功")
    
    def test_enqueue_dequeue(self):
        """测试入队出队"""
        queue = TaskQueue(use_redis=False)
        
        task = Task(
            task_id="task_001",
            task_type="test",
            payload={"data": "test"}
        )
        
        queue.enqueue(task)
        assert queue.get_stats()['queue_length'] == 1
        
        dequeued = queue.dequeue()
        assert dequeued is not None
        assert dequeued.task_id == "task_001"
        print("✓ 入队出队测试通过")
    
    def test_priority(self):
        """测试优先级"""
        queue = TaskQueue(use_redis=False)
        
        for i in range(3):
            task = Task(
                task_id=f"low_{i}",
                task_type="test",
                payload={},
                priority=TaskPriority.LOW
            )
            queue.enqueue(task)
        
        task = Task(
            task_id="high",
            task_type="test",
            payload={},
            priority=TaskPriority.HIGH
        )
        queue.enqueue(task)
        
        dequeued = queue.dequeue()
        assert dequeued.priority == TaskPriority.HIGH
        print("✓ 优先级测试通过")
    
    def test_stats(self):
        """测试统计"""
        queue = TaskQueue(use_redis=False)
        stats = queue.get_stats()
        assert 'queue_length' in stats
        assert 'use_redis' in stats
        print(f"✓ 统计信息: {stats}")


class TestEventBusWithRedis:
    """带 Redis 的事件总线测试"""
    
    def test_with_redis(self):
        """测试 Redis 模式"""
        bus = EventBus(use_redis=True)
        print(f"✓ Redis 模式: use_redis={bus.use_redis}")


class TestTaskQueueWithRedis:
    """带 Redis 的任务队列测试"""
    
    def test_with_redis(self):
        """测试 Redis 模式"""
        queue = TaskQueue(use_redis=True)
        print(f"✓ Redis 模式: use_redis={queue.use_redis}, length={queue.get_stats()['queue_length']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
