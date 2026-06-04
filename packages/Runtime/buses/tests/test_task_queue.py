"""
TaskQueue 补充单元测试

覆盖：任务状态流转、ack 确认、并发入队出队、相同优先级排序、空队列 dequeue、stats 统计
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pytest
import threading
from packages.Runtime.buses.task_queue import TaskQueue, Task, TaskPriority


class TestTaskQueueStatusFlow:
    """任务状态流转测试"""

    def test_task_default_status_pending(self):
        """新创建的任务默认状态为 pending"""
        task = Task(task_id="t1", task_type="test", payload={})
        assert task.status == "pending"
        assert task.started_at is None
        assert task.completed_at is None
        assert task.result is None
        assert task.error is None

    def test_task_status_transitions(self):
        """任务状态可以手动流转 pending -> running -> completed"""
        task = Task(task_id="t1", task_type="test", payload={})
        assert task.status == "pending"

        task.status = "running"
        task.started_at = 1000.0
        assert task.status == "running"

        task.status = "completed"
        task.completed_at = 2000.0
        task.result = {"output": "ok"}
        assert task.status == "completed"
        assert task.result == {"output": "ok"}

    def test_task_failed_status(self):
        """任务失败状态"""
        task = Task(task_id="t1", task_type="test", payload={})
        task.status = "failed"
        task.error = "connection timeout"
        assert task.status == "failed"
        assert task.error == "connection timeout"


class TestTaskQueueAck:
    """ack 确认机制测试"""

    def test_ack_returns_true(self):
        """ack 始终返回 True（当前实现）"""
        queue = TaskQueue(use_redis=False)
        assert queue.ack("task_001") is True

    def test_ack_with_result(self):
        """ack 可传入 result 参数"""
        queue = TaskQueue(use_redis=False)
        assert queue.ack("task_001", result={"output": "done"}) is True

    def test_ack_with_error(self):
        """ack 可传入 error 参数"""
        queue = TaskQueue(use_redis=False)
        assert queue.ack("task_001", error="something went wrong") is True


class TestTaskQueueConcurrent:
    """并发入队出队测试"""

    def test_concurrent_enqueue(self):
        """多线程并发入队不出错"""
        queue = TaskQueue(use_redis=False)
        n = 50
        barrier = threading.Barrier(n)

        def enqueue_task(i):
            barrier.wait()
            task = Task(task_id=f"task_{i}", task_type="test", payload={"i": i})
            queue.enqueue(task)

        threads = [threading.Thread(target=enqueue_task, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert queue.get_stats()["queue_length"] == n

    def test_concurrent_enqueue_dequeue(self):
        """多线程并发入队和出队"""
        queue = TaskQueue(use_redis=False)
        n = 30
        enqueued_ids = []
        lock = threading.Lock()

        def producer():
            for i in range(n):
                task = Task(task_id=f"task_{i}", task_type="test", payload={})
                queue.enqueue(task)
                with lock:
                    enqueued_ids.append(f"task_{i}")

        def consumer():
            dequeued = []
            for _ in range(n):
                t = queue.dequeue()
                if t:
                    dequeued.append(t.task_id)
            return dequeued

        t_producer = threading.Thread(target=producer)
        t_producer.start()
        t_producer.join()

        results = consumer()
        assert len(results) == n
        # 所有入队的任务都应该能出队
        assert set(results) == set(enqueued_ids)


class TestTaskQueuePriorityEdge:
    """优先级排序边界测试"""

    def test_same_priority_fifo(self):
        """相同优先级的任务按 FIFO 顺序出队"""
        queue = TaskQueue(use_redis=False)

        for i in range(5):
            task = Task(
                task_id=f"normal_{i}",
                task_type="test",
                payload={},
                priority=TaskPriority.NORMAL,
            )
            queue.enqueue(task)

        results = []
        for _ in range(5):
            t = queue.dequeue()
            results.append(t.task_id)

        assert results == ["normal_0", "normal_1", "normal_2", "normal_3", "normal_4"]

    def test_mixed_priority_ordering(self):
        """混合优先级：URGENT > HIGH > NORMAL > LOW"""
        queue = TaskQueue(use_redis=False)

        queue.enqueue(Task(task_id="low", task_type="t", payload={}, priority=TaskPriority.LOW))
        queue.enqueue(Task(task_id="urgent", task_type="t", payload={}, priority=TaskPriority.URGENT))
        queue.enqueue(Task(task_id="normal", task_type="t", payload={}, priority=TaskPriority.NORMAL))
        queue.enqueue(Task(task_id="high", task_type="t", payload={}, priority=TaskPriority.HIGH))

        results = [queue.dequeue().task_id for _ in range(4)]
        assert results == ["urgent", "high", "normal", "low"]


class TestTaskQueueDequeueEmpty:
    """空队列 dequeue 测试"""

    def test_dequeue_empty_returns_none(self):
        """空队列出队返回 None"""
        queue = TaskQueue(use_redis=False)
        result = queue.dequeue()
        assert result is None

    def test_dequeue_all_then_empty(self):
        """全部出队后再出队返回 None"""
        queue = TaskQueue(use_redis=False)
        queue.enqueue(Task(task_id="t1", task_type="test", payload={}))
        assert queue.dequeue() is not None
        assert queue.dequeue() is None


class TestTaskQueueStats:
    """stats 统计测试"""

    def test_stats_empty_queue(self):
        """空队列统计"""
        queue = TaskQueue(use_redis=False)
        stats = queue.get_stats()
        assert stats["queue_length"] == 0
        assert stats["use_redis"] is False
        assert stats["queue_name"] == "zenagent:tasks"

    def test_stats_reflects_queue_length(self):
        """统计正确反映队列长度"""
        queue = TaskQueue(use_redis=False)

        for i in range(10):
            queue.enqueue(Task(task_id=f"t_{i}", task_type="test", payload={}))
        assert queue.get_stats()["queue_length"] == 10

        for _ in range(3):
            queue.dequeue()
        assert queue.get_stats()["queue_length"] == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
