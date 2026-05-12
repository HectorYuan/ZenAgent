"""
消息队列 (Message Queue)

提供智能体间消息传递功能:
- 消息发布/订阅
- RPC调用
- 消息持久化
- 死信处理
"""

from typing import Dict, List, Any, Optional, Callable, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import asyncio
import uuid
import json

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型"""
    TASK = "task"              # 任务消息
    RESULT = "result"          # 结果消息
    EVENT = "event"           # 事件消息
    COMMAND = "command"       # 命令消息
    HEARTBEAT = "heartbeat"   # 心跳消息


class MessagePriority(Enum):
    """消息优先级"""
    CRITICAL = 0
    URGENT = 1
    NORMAL = 2
    LOW = 3


@dataclass
class Message:
    """消息对象"""
    message_id: str
    message_type: MessageType
    sender: str
    receiver: Optional[str]  # None表示广播
    content: Any
    timestamp: datetime = field(default_factory=datetime.now)
    priority: MessagePriority = MessagePriority.NORMAL
    correlation_id: Optional[str] = None  # 用于关联请求和响应
    headers: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    ttl: int = 3600  # 生存时间(秒)
    delivery_mode: str = "persistent"  # persistent, transient
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > self.ttl


@dataclass
class Subscription:
    """订阅"""
    subscription_id: str
    agent_id: str
    topics: List[str]
    callback: Callable
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CallResult:
    """RPC调用结果"""
    call_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class MessageQueue:
    """
    消息队列
    
    功能:
    - 消息发布/订阅
    - 主题管理
    - RPC调用
    - 消息持久化
    - 死信处理
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 消息存储
        self.queues: Dict[str, asyncio.Queue] = {}  # topic -> queue
        self.dead_letter_queue: asyncio.Queue = asyncio.Queue()
        
        # 订阅者
        self.subscriptions: Dict[str, Subscription] = {}  # subscription_id -> Subscription
        self.agent_subscriptions: Dict[str, List[str]] = {}  # agent_id -> [subscription_ids]
        self.topic_subscribers: Dict[str, List[str]] = {}  # topic -> [agent_ids]
        
        # RPC调用
        self.pending_calls: Dict[str, asyncio.Future] = {}
        self.call_timeout = self.config.get('call_timeout', 30)
        
        # 统计
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'messages_failed': 0,
            'rpc_calls': 0,
            'rpc_timeouts': 0
        }
        
        # 运行状态
        self._running = False
        self._receive_tasks: Dict[str, asyncio.Task] = {}
    
    async def start(self):
        """启动消息队列"""
        self._running = True
        logger.info("Message queue started")
    
    async def stop(self):
        """停止消息队列"""
        self._running = False
        
        # 取消所有接收任务
        for task in self._receive_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # 清空队列
        self.queues.clear()
        
        logger.info("Message queue stopped")
    
    # ==================== 主题管理 ====================
    
    async def create_topic(self, topic: str, max_size: int = 1000):
        """创建主题"""
        if topic not in self.queues:
            self.queues[topic] = asyncio.Queue(maxsize=max_size)
            self.topic_subscribers[topic] = []
            logger.info(f"Topic created: {topic}")
    
    async def delete_topic(self, topic: str):
        """删除主题"""
        if topic in self.queues:
            del self.queues[topic]
        if topic in self.topic_subscribers:
            del self.topic_subscribers[topic]
    
    # ==================== 发布/订阅 ====================
    
    async def publish(self, topic: str, message: Message) -> bool:
        """
        发布消息
        
        Args:
            topic: 主题
            message: 消息
            
        Returns:
            bool: 是否成功
        """
        # 确保主题存在
        if topic not in self.queues:
            await self.create_topic(topic)
        
        try:
            # 放入队列
            await asyncio.wait_for(
                self.queues[topic].put(message),
                timeout=5
            )
            
            self.stats['messages_sent'] += 1
            
            # 分发给订阅者
            await self._dispatch_to_subscribers(topic, message)
            
            return True
            
        except asyncio.TimeoutError:
            logger.warning(f"Queue full, message dropped: {message.message_id}")
            self.stats['messages_failed'] += 1
            return False
        except Exception as e:
            logger.error(f"Publish error: {e}")
            self.stats['messages_failed'] += 1
            return False
    
    async def _dispatch_to_subscribers(self, topic: str, message: Message):
        """分发给订阅者"""
        for agent_id in self.topic_subscribers.get(topic, []):
            # 异步触发回调(不等待)
            asyncio.create_task(self._notify_subscriber(agent_id, topic, message))
    
    async def _notify_subscriber(self, agent_id: str, topic: str, message: Message):
        """通知订阅者"""
        subs = self.agent_subscriptions.get(agent_id, [])
        for sub_id in subs:
            sub = self.subscriptions.get(sub_id)
            if sub and topic in sub.topics:
                try:
                    await asyncio.wait_for(
                        sub.callback(message),
                        timeout=5
                    )
                except Exception as e:
                    logger.error(f"Subscriber callback error: {e}")
    
    async def subscribe(
        self,
        agent_id: str,
        topics: List[str],
        callback: Callable[[Message], Any]
    ) -> str:
        """
        订阅主题
        
        Args:
            agent_id: 订阅者ID
            topics: 主题列表
            callback: 回调函数
            
        Returns:
            str: 订阅ID
        """
        subscription_id = str(uuid.uuid4())[:8]
        
        subscription = Subscription(
            subscription_id=subscription_id,
            agent_id=agent_id,
            topics=topics,
            callback=callback
        )
        
        self.subscriptions[subscription_id] = subscription
        
        if agent_id not in self.agent_subscriptions:
            self.agent_subscriptions[agent_id] = []
        self.agent_subscriptions[agent_id].append(subscription_id)
        
        for topic in topics:
            if topic not in self.topic_subscribers:
                self.topic_subscribers[topic] = []
            if agent_id not in self.topic_subscribers[topic]:
                self.topic_subscribers[topic].append(agent_id)
        
        logger.info(f"Subscription created: {subscription_id} for {agent_id}")
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str):
        """取消订阅"""
        sub = self.subscriptions.get(subscription_id)
        if not sub:
            return
        
        # 从所有索引中移除
        for topic in sub.topics:
            if topic in self.topic_subscribers:
                self.topic_subscribers[topic] = [
                    aid for aid in self.topic_subscribers[topic]
                    if aid != sub.agent_id
                ]
        
        if sub.agent_id in self.agent_subscriptions:
            self.agent_subscriptions[sub.agent_id] = [
                sid for sid in self.agent_subscriptions[sub.agent_id]
                if sid != subscription_id
            ]
        
        del self.subscriptions[subscription_id]
        logger.info(f"Subscription removed: {subscription_id}")
    
    # ==================== 消息接收 ====================
    
    async def receive(self, topic: str, timeout: Optional[float] = None) -> Optional[Message]:
        """
        接收消息
        
        Args:
            topic: 主题
            timeout: 超时时间
            
        Returns:
            Optional[Message]: 消息，超时返回None
        """
        if topic not in self.queues:
            return None
        
        try:
            if timeout:
                message = await asyncio.wait_for(
                    self.queues[topic].get(),
                    timeout=timeout
                )
            else:
                message = await self.queues[topic].get()
            
            self.stats['messages_received'] += 1
            return message
            
        except asyncio.TimeoutError:
            return None
    
    def receive_async(self, topic: str) -> AsyncIterator[Message]:
        """
        异步消息流
        
        Args:
            topic: 主题
            
        Yields:
            Message: 消息
        """
        async def _iter():
            while self._running:
                message = await self.receive(topic, timeout=1)
                if message:
                    yield message
        
        return _iter()
    
    # ==================== RPC调用 ====================
    
    async def rpc_call(
        self,
        target: str,
        payload: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> CallResult:
        """
        RPC调用
        
        Args:
            target: 目标智能体
            payload: 调用参数
            timeout: 超时时间
            
        Returns:
            CallResult: 调用结果
        """
        call_id = str(uuid.uuid4())[:12]
        timeout = timeout or self.call_timeout
        
        # 创建future用于接收响应
        future = asyncio.get_event_loop().create_future()
        self.pending_calls[call_id] = future
        self.stats['rpc_calls'] += 1
        
        # 发送调用请求
        request = Message(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.TASK,
            sender="caller",
            receiver=target,
            content=payload,
            correlation_id=call_id,
            priority=MessagePriority.URGENT
        )
        
        # 发布到目标队列
        await self.publish(f"rpc:{target}", request)
        
        try:
            # 等待响应
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
            
        except asyncio.TimeoutError:
            self.stats['rpc_timeouts'] += 1
            return CallResult(
                call_id=call_id,
                success=False,
                error="RPC timeout"
            )
        finally:
            self.pending_calls.pop(call_id, None)
    
    async def rpc_respond(self, call_id: str, result: Any):
        """RPC响应"""
        if call_id in self.pending_calls:
            response = CallResult(
                call_id=call_id,
                success=True,
                result=result,
                execution_time_ms=0  # TODO: 计算执行时间
            )
            self.pending_calls[call_id].set_result(response)
    
    # ==================== 死信处理 ====================
    
    async def handle_dead_letter(self, message: Message, reason: str):
        """处理死信"""
        message.retry_count += 1
        
        if message.retry_count < message.max_retries:
            # 重新入队(带延迟)
            await asyncio.sleep(message.retry_count * 60)  # 递增延迟
            await self.publish(f"dlq.retry", message)
        else:
            # 放入死信队列
            await self.dead_letter_queue.put({
                'message': message,
                'reason': reason,
                'failed_at': datetime.now()
            })
            
            logger.warning(
                f"Message moved to DLQ: {message.message_id}, "
                f"reason: {reason}"
            )
    
    async def consume_dead_letter(self, timeout: float = 1.0) -> Optional[Dict]:
        """消费死信"""
        try:
            return await asyncio.wait_for(
                self.dead_letter_queue.get(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None
    
    # ==================== 工具方法 ====================
    
    def create_message(
        self,
        message_type: MessageType,
        sender: str,
        receiver: Optional[str],
        content: Any,
        priority: MessagePriority = MessagePriority.NORMAL,
        **kwargs
    ) -> Message:
        """创建消息"""
        return Message(
            message_id=str(uuid.uuid4())[:12],
            message_type=message_type,
            sender=sender,
            receiver=receiver,
            content=content,
            priority=priority,
            **kwargs
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            **self.stats,
            'topics': len(self.queues),
            'subscriptions': len(self.subscriptions),
            'pending_calls': len(self.pending_calls),
            'dlq_size': self.dead_letter_queue.qsize()
        }
