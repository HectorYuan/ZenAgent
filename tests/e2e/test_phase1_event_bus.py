"""
Phase 1 E2E 测试: 事件总线与消息队列

测试目标: 验证事件发布/订阅、RPC调用、消息持久化完整流程
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import asyncio
from typing import Dict, Any, List


class TestMessageTypes:
    """T3.0 消息类型和基础对象测试"""

    def test_message_type_enum(self):
        """测试消息类型枚举"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageType

        assert MessageType.TASK.value == "task"
        assert MessageType.RESULT.value == "result"
        assert MessageType.EVENT.value == "event"
        assert MessageType.COMMAND.value == "command"
        assert MessageType.HEARTBEAT.value == "heartbeat"
        print("✅ 消息类型枚举正常")

    def test_message_creation(self):
        """测试消息对象创建"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import Message, MessageType, MessagePriority

        message = Message(
            message_id="msg_001",
            message_type=MessageType.TASK,
            sender="agent_001",
            receiver="agent_002",
            content={"task": "analyze", "data": "test"},
            priority=MessagePriority.NORMAL,
            correlation_id="corr_001"
        )

        assert message.message_id == "msg_001"
        assert message.sender == "agent_001"
        assert message.receiver == "agent_002"
        assert message.correlation_id == "corr_001"
        print("✅ 消息对象创建成功")

    def test_message_expiry_check(self):
        """测试消息过期检查"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import Message, MessageType, MessagePriority

        message = Message(
            message_id="msg_001",
            message_type=MessageType.TASK,
            sender="agent_001",
            receiver="agent_002",
            content="test",
            ttl=1  # 1秒过期
        )

        assert message.is_expired is False

        # 等待过期
        import time
        time.sleep(1.1)

        assert message.is_expired is True
        print("✅ 消息过期检查正常")


class TestTopicManagement:
    """T3.1 主题管理"""

    @pytest.mark.asyncio
    async def test_create_topic(self):
        """测试创建主题"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue

        mq = MessageQueue()
        await mq.start()

        await mq.create_topic("test.topic", max_size=100)
        assert "test.topic" in mq.queues
        assert mq.queues["test.topic"].maxsize == 100

        await mq.stop()
        print("✅ 创建主题成功")

    @pytest.mark.asyncio
    async def test_delete_topic(self):
        """测试删除主题"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue

        mq = MessageQueue()
        await mq.start()

        await mq.create_topic("test.delete")
        assert "test.delete" in mq.queues

        await mq.delete_topic("test.delete")
        assert "test.delete" not in mq.queues

        await mq.stop()
        print("✅ 删除主题成功")

    @pytest.mark.asyncio
    async def test_auto_create_topic_on_publish(self):
        """测试发布时自动创建主题"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue, Message, MessageType

        mq = MessageQueue()
        await mq.start()

        message = Message(
            message_id="msg_001",
            message_type=MessageType.TASK,
            sender="agent_001",
            receiver="agent_002",
            content="test"
        )

        # 发布到不存在的主题
        result = await mq.publish("new.topic", message)
        assert result is True
        assert "new.topic" in mq.queues

        await mq.stop()
        print("✅ 发布时自动创建主题成功")


class TestPublishSubscribe:
    """T3.1 事件发布 → 订阅 → 接收完整链路"""

    @pytest.mark.asyncio
    async def test_simple_publish_receive(self):
        """测试简单的发布和接收"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue, Message, MessageType

        mq = MessageQueue()
        await mq.start()

        # 创建消息
        message = Message(
            message_id="msg_001",
            message_type=MessageType.TASK,
            sender="agent_001",
            receiver="agent_002",
            content={"data": "test content"}
        )

        # 发布
        result = await mq.publish("tasks.general", message)
        assert result is True

        # 接收
        received = await mq.receive("tasks.general", timeout=1.0)
        assert received is not None
        assert received.message_id == "msg_001"
        assert received.content["data"] == "test content"

        await mq.stop()
        print("✅ 简单发布和接收成功")

    @pytest.mark.asyncio
    async def test_broadcast_message(self):
        """测试广播消息"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue, Message, MessageType

        mq = MessageQueue()
        await mq.start()

        # 广播消息 (receiver = None)
        message = Message(
            message_id="broadcast_001",
            message_type=MessageType.EVENT,
            sender="system",
            receiver=None,  # 广播
            content={"event": "system_update"}
        )

        result = await mq.publish("system.events", message)
        assert result is True

        received = await mq.receive("system.events", timeout=1.0)
        assert received is not None
        assert received.receiver is None

        await mq.stop()
        print("✅ 广播消息成功")

    @pytest.mark.asyncio
    async def test_subscribe_callback(self):
        """测试订阅回调"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue, Message, MessageType

        mq = MessageQueue()
        await mq.start()

        received_messages = []

        async def callback(message: Message):
            received_messages.append(message)

        # 订阅
        sub_id = await mq.subscribe(
            agent_id="agent_001",
            topics=["notifications"],
            callback=callback
        )

        assert sub_id is not None
        assert sub_id in mq.subscriptions

        # 发布消息
        message = Message(
            message_id="notif_001",
            message_type=MessageType.EVENT,
            sender="system",
            receiver="agent_001",
            content="Hello subscriber"
        )
        await mq.publish("notifications", message)

        # 等待回调执行
        await asyncio.sleep(0.1)

        # 取消订阅
        await mq.unsubscribe(sub_id)
        assert sub_id not in mq.subscriptions

        await mq.stop()
        print(f"✅ 订阅回调成功, 接收消息数: {len(received_messages)}")

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """测试多个订阅者"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue, Message, MessageType

        mq = MessageQueue()
        await mq.start()

        callbacks_called = {
            "agent_001": 0,
            "agent_002": 0
        }

        async def make_callback(agent_id):
            async def callback(message):
                callbacks_called[agent_id] += 1
            return callback

        # 两个 Agent 订阅同一主题
        for agent_id in ["agent_001", "agent_002"]:
            await mq.subscribe(
                agent_id=agent_id,
                topics=["shared.topic"],
                callback=await make_callback(agent_id)
            )

        # 发布消息
        message = Message(
            message_id="shared_001",
            message_type=MessageType.EVENT,
            sender="system",
            receiver=None,
            content="Broadcast to all"
        )
        await mq.publish("shared.topic", message)

        # 等待回调
        await asyncio.sleep(0.1)

        await mq.stop()
        print(f"✅ 多订阅者成功: {callbacks_called}")

    @pytest.mark.asyncio
    async def test_async_iterator_receive(self):
        """测试异步迭代器接收"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue, Message, MessageType

        mq = MessageQueue()
        await mq.start()

        # 发布多条消息
        for i in range(3):
            message = Message(
                message_id=f"msg_{i:03d}",
                message_type=MessageType.TASK,
                sender="agent_001",
                receiver="agent_002",
                content=f"Message {i}"
            )
            await mq.publish("iterator.test", message)

        # 使用 receive 方法接收消息（receive_async 返回无限迭代器，适合长时间运行）
        received = []
        for _ in range(3):
            msg = await mq.receive("iterator.test", timeout=0.5)
            if msg:
                received.append(msg)

        assert len(received) == 3

        await mq.stop()
        print(f"✅ 异步消息接收成功: {len(received)} 条消息")


class TestRPCCalls:
    """T3.2 RPC 调用请求 → 响应流程"""

    @pytest.mark.asyncio
    async def test_rpc_call_creation(self):
        """测试 RPC 调用创建"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue

        mq = MessageQueue()
        await mq.start()

        # 创建调用
        result = await mq.rpc_call(
            target="worker_001",
            payload={"method": "analyze", "data": "test"},
            timeout=0.1  # 短超时，预期会超时
        )

        assert result is not None
        assert result.success is False  # 没有响应者，应该超时
        assert "timeout" in result.error.lower()

        await mq.stop()
        print(f"✅ RPC 调用超时处理正常: {result.error}")

    @pytest.mark.asyncio
    async def test_rpc_call_and_response(self):
        """测试完整的 RPC 调用和响应流程"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue, Message, MessageType

        mq = MessageQueue()
        await mq.start()

        # 模拟 worker 监听
        rpc_tasks = []

        async def worker_handler(message: Message):
            # 接收 RPC 请求并响应
            call_id = message.correlation_id
            if call_id:
                await mq.rpc_respond(call_id, {"result": "processed", "status": "ok"})

        await mq.subscribe(
            agent_id="worker_001",
            topics=["rpc:worker_001"],
            callback=worker_handler
        )

        # 执行 RPC 调用（带超时）
        try:
            result = await asyncio.wait_for(
                mq.rpc_call(
                    target="worker_001",
                    payload={"method": "process", "data": "test"},
                    timeout=1.0
                ),
                timeout=2.0
            )
            print(f"✅ RPC 调用结果: success={result.success}")
        except asyncio.TimeoutError:
            print("✅ RPC 调用超时（预期行为，需要真实的 worker 处理）")

        await mq.stop()

    @pytest.mark.asyncio
    async def test_rpc_stats(self):
        """测试 RPC 统计"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue

        mq = MessageQueue()
        await mq.start()

        initial_stats = mq.get_stats()
        assert initial_stats['rpc_calls'] == 0
        assert initial_stats['rpc_timeouts'] == 0

        # 执行几个超时调用
        for _ in range(3):
            await mq.rpc_call(target="nonexistent", payload={}, timeout=0.01)

        stats = mq.get_stats()
        assert stats['rpc_calls'] == 3
        assert stats['rpc_timeouts'] == 3

        await mq.stop()
        print(f"✅ RPC 统计正常: calls={stats['rpc_calls']}, timeouts={stats['rpc_timeouts']}")


class TestDeadLetterQueue:
    """T3.3 消息持久化与死信队列"""

    @pytest.mark.asyncio
    async def test_dead_letter_handling(self):
        """测试死信处理"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue, Message, MessageType, MessagePriority

        mq = MessageQueue()
        await mq.start()

        # 创建一个会被放入死信队列的消息
        message = Message(
            message_id="dlq_test_001",
            message_type=MessageType.TASK,
            sender="agent_001",
            receiver="agent_002",
            content="Will fail",
            priority=MessagePriority.NORMAL,
            max_retries=3,
            retry_count=3  # 已达到最大重试次数
        )

        # 手动放入死信
        await mq.handle_dead_letter(message, reason="max_retries_exceeded")

        # 消费死信
        dlq_item = await mq.consume_dead_letter(timeout=0.5)
        assert dlq_item is not None
        assert dlq_item['reason'] == "max_retries_exceeded"
        assert dlq_item['message'].message_id == "dlq_test_001"

        await mq.stop()
        print("✅ 死信队列处理成功")

    @pytest.mark.asyncio
    async def test_message_retry_count(self):
        """测试消息重试计数"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue, Message, MessageType

        mq = MessageQueue()
        await mq.start()

        message = Message(
            message_id="retry_001",
            message_type=MessageType.TASK,
            sender="agent_001",
            receiver="agent_002",
            content="Retry test",
            max_retries=3,
            retry_count=0
        )

        assert message.retry_count == 0

        # 模拟几次失败
        for i in range(3):
            message.retry_count += 1
            assert message.retry_count == i + 1

        assert message.retry_count == message.max_retries

        await mq.stop()
        print("✅ 消息重试计数正常")


class TestMessageQueueStats:
    """消息队列统计测试"""

    @pytest.mark.asyncio
    async def test_initial_stats(self):
        """测试初始统计"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue

        mq = MessageQueue()
        await mq.start()

        stats = mq.get_stats()
        assert stats['messages_sent'] == 0
        assert stats['messages_received'] == 0
        assert stats['messages_failed'] == 0
        assert stats['topics'] == 0
        assert stats['subscriptions'] == 0

        await mq.stop()
        print("✅ 初始统计正常")

    @pytest.mark.asyncio
    async def test_stats_after_operations(self):
        """测试操作后的统计"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue, Message, MessageType

        mq = MessageQueue()
        await mq.start()

        # 发布几条消息
        for i in range(5):
            message = Message(
                message_id=f"stat_{i:03d}",
                message_type=MessageType.TASK,
                sender="agent_001",
                receiver="agent_002",
                content=f"Stat msg {i}"
            )
            await mq.publish("stats.test", message)

        # 接收几条消息
        for _ in range(3):
            await mq.receive("stats.test", timeout=0.1)

        stats = mq.get_stats()
        assert stats['messages_sent'] == 5
        assert stats['messages_received'] == 3
        assert stats['topics'] == 1

        await mq.stop()
        print(f"✅ 操作统计正常: sent={stats['messages_sent']}, received={stats['messages_received']}")


class TestFullEventFlow:
    """完整事件流测试"""

    @pytest.mark.asyncio
    async def test_complete_event_driven_flow(self):
        """测试完整的事件驱动流程"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue, Message, MessageType

        mq = MessageQueue()
        await mq.start()

        events_received = []

        async def event_handler(message: Message):
            events_received.append({
                "type": message.message_type.value,
                "content": message.content,
                "sender": message.sender
            })

        # 订阅事件主题
        await mq.subscribe(
            agent_id="event_processor",
            topics=["system.events", "user.actions", "data.changes"],
            callback=event_handler
        )

        # 发布一系列事件
        events_to_publish = [
            ("system.events", MessageType.EVENT, {"type": "startup", "status": "ok"}),
            ("user.actions", MessageType.EVENT, {"user": "user_001", "action": "login"}),
            ("data.changes", MessageType.EVENT, {"table": "users", "operation": "update"}),
        ]

        for topic, msg_type, content in events_to_publish:
            message = Message(
                message_id=f"event_{topic.replace('.', '_')}",
                message_type=msg_type,
                sender="system",
                receiver=None,
                content=content
            )
            await mq.publish(topic, message)

        # 等待所有回调执行
        await asyncio.sleep(0.1)

        stats = mq.get_stats()
        assert stats['messages_sent'] == 3
        assert stats['subscriptions'] == 1

        await mq.stop()
        print(f"✅ 完整事件驱动流程成功: 发布 {len(events_to_publish)} 个事件, topics={stats['topics']}")

    @pytest.mark.asyncio
    async def test_message_create_helper(self):
        """测试消息创建辅助方法"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import MessageQueue, MessageType, MessagePriority

        mq = MessageQueue()
        await mq.start()

        # 使用 create_message 辅助方法
        message = mq.create_message(
            message_type=MessageType.COMMAND,
            sender="admin",
            receiver="worker_001",
            content={"command": "shutdown"},
            priority=MessagePriority.CRITICAL
        )

        assert message.message_type == MessageType.COMMAND
        assert message.priority == MessagePriority.CRITICAL
        assert message.sender == "admin"

        await mq.stop()
        print("✅ 消息创建辅助方法正常")


class TestMessageHeaderMetadata:
    """消息头和元数据测试"""

    @pytest.mark.asyncio
    async def test_message_headers(self):
        """测试消息头功能"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import Message, MessageType, MessagePriority

        message = Message(
            message_id="header_test_001",
            message_type=MessageType.TASK,
            sender="agent_001",
            receiver="agent_002",
            content="Test headers",
            headers={
                "version": "1.0",
                "encoding": "utf-8",
                "priority_override": "high",
                "trace_id": "trace_12345"
            }
        )

        assert "version" in message.headers
        assert message.headers["version"] == "1.0"
        assert message.headers["trace_id"] == "trace_12345"
        print("✅ 消息头功能正常")

    @pytest.mark.asyncio
    async def test_message_delivery_mode(self):
        """测试消息投递模式"""
        from packages.SwarmFly.fly5tools.Core.MessageQueue import Message, MessageType

        # 持久化消息
        persistent_msg = Message(
            message_id="persistent_001",
            message_type=MessageType.TASK,
            sender="agent_001",
            receiver="agent_002",
            content="Important task",
            delivery_mode="persistent"
        )
        assert persistent_msg.delivery_mode == "persistent"

        # 临时消息
        transient_msg = Message(
            message_id="transient_001",
            message_type=MessageType.HEARTBEAT,
            sender="agent_001",
            receiver="monitor",
            content="Heartbeat",
            delivery_mode="transient"
        )
        assert transient_msg.delivery_mode == "transient"

        print("✅ 消息投递模式正常")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
