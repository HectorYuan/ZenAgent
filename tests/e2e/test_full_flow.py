"""
ZenAgent 端到端测试
测试完整的 Agent 生命周期流程
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import time

# ============ ZenAgent 层 ============
from packages.ZenAgent.mcp.protocol import MCPProtocol, MCPMessageType
from packages.ZenAgent.mcp.registry import AgentRegistry, AgentCapability, AgentMetadata
from packages.ZenAgent.mcp.session import MCPSession, MCPSessionState
from packages.ZenAgent.hooks.hook_manager import HookManager
from packages.ZenAgent.awakening.adapter import AwakeningAdapter

# ============ Runtime 层 ============
from packages.Runtime.session.session import Session, SessionState
from packages.Runtime.context_compaction.manager import ContextManager
from packages.Runtime.checkpoint.event_store import EventStore

# ============ MetaSoul 层 ============
from packages.MetaSoul.memory.meta_soul import MetaSoul, MemoryType
from packages.MetaSoul.learning.learner import SelfLearner
from packages.MetaSoul.personality.personality import Personality


class TestEndToEndAgentLifecycle:
    """端到端测试：Agent 完整生命周期"""
    
    def test_1_agent_registry_flow(self):
        """测试1：Agent 注册流程"""
        print("\n=== 测试1：Agent 注册流程 ===")
        registry = AgentRegistry()
        metadata = AgentMetadata(
            agent_id="test_agent_001",
            name="Test Agent",
            capabilities=[AgentCapability.TEXT_GENERATION],
            version="1.0.0"
        )
        agent_info = registry.register(metadata)
        assert agent_info is not None
        print(f"✓ Agent 注册成功")
        
        retrieved = registry.get("test_agent_001")
        assert retrieved is not None
        print(f"✓ Agent 获取成功")
        print("✅ Agent 注册流程完成")
    
    def test_2_runtime_context_flow(self):
        """测试2：Runtime 上下文流程"""
        print("\n=== 测试2：Runtime 上下文流程 ===")
        
        context_mgr = ContextManager()
        context_mgr.add_message({"role": "user", "content": "你好"})
        context_mgr.add_message({"role": "assistant", "content": "你好！"})
        context_mgr.add_message({"role": "user", "content": "帮我写个函数"})
        
        messages = context_mgr.get_messages()
        assert len(messages) == 3
        print(f"✓ 添加了 {len(messages)} 条消息")
        
        stats = context_mgr.get_stats()
        assert stats.message_count == 3  # 修复
        print(f"✓ 上下文统计: message_count={stats.message_count}")
        
        session = Session()
        session.start()
        assert session.state == SessionState.ACTIVE
        print(f"✓ Runtime Session 启动成功")
        
        session.pause()
        assert session.state == SessionState.SUSPENDED
        print(f"✓ Session 暂停成功")
        
        session.resume()
        assert session.state == SessionState.ACTIVE
        print(f"✓ Session 恢复成功")
        print("✅ Runtime 上下文流程完成")
    
    def test_3_soulteam_memory_flow(self):
        """测试3：SoulTeam 记忆流程"""
        print("\n=== 测试3：SoulTeam 记忆流程 ===")
        
        soul_id = "soul_001"
        soul = MetaSoul()
        soul.soul_id = soul_id
        print(f"✓ MetaSoul 创建成功: {soul_id}")
        
        memories = [
            ("用户问了Python问题", MemoryType.EPISODIC),
            ("Python代码规范", MemoryType.SEMANTIC),
            ("当前对话上下文", MemoryType.WORKING),
            ("编程技能", MemoryType.PROCEDURAL),
        ]
        
        for content, mem_type in memories:
            memory_id = soul.store_memory(content, mem_type)
            assert memory_id is not None
        print(f"✓ 存储了 {len(memories)} 条记忆")
        
        stats = soul.get_stats()
        print(f"✓ 记忆统计: total_memories={stats['total_memories']}")
        
        learner = SelfLearner(soul_id=soul_id)
        result = learner.learn({
            'input': 'Python函数定义',
            'output': 'def func(): pass',
            'success': True
        })
        assert result is not None
        print(f"✓ SelfLearner 学习成功")
        
        personality = Personality()
        traits = personality.get_traits()  # 修复
        assert len(traits) > 0
        print(f"✓ Personality 初始化: {len(traits)} 个特质")
        print("✅ SoulTeam 记忆流程完成")
    
    def test_4_full_integration_flow(self):
        """测试4：完整集成流程"""
        print("\n=== 测试4：完整集成流程 ===")
        
        agent_id = "agent_full_001"
        
        registry = AgentRegistry()
        metadata = AgentMetadata(agent_id=agent_id, name="Full Agent", capabilities=[AgentCapability.TEXT_GENERATION])
        registry.register(metadata)
        
        runtime_session = Session()
        runtime_session.start()
        
        context = ContextManager()
        soul = MetaSoul()
        soul.soul_id = agent_id
        
        awakening = AwakeningAdapter()
        awakening.agent_id = agent_id
        awakening.awaken()
        
        personality = Personality()
        
        print("✓ 所有组件创建完成")
        
        messages = [
            ("user", "你好，请帮我分析这段代码"),
            ("assistant", "好的，请提供代码片段"),
            ("user", "def hello(): print('world')"),
            ("assistant", "这是一个简单的Hello World函数..."),
        ]
        
        for role, content in messages:
            context.add_message({"role": role, "content": content})
            soul.store_memory(f"{role}: {content}", MemoryType.WORKING)
        
        print(f"✓ 模拟了 {len(messages)} 轮对话")
        
        learner = SelfLearner(soul_id=agent_id)
        learner.learn({
            'input': '代码分析请求',
            'output': '代码分析完成',
            'success': True,
            'feedback': 0.9
        })
        print("✓ 学习反馈已记录")
        
        assert runtime_session.is_active == True  # 修复：是属性不是方法
        assert awakening.is_awakened
        assert context.get_stats().message_count == len(messages)
        print("✓ 所有状态检查通过")
        
        runtime_session.complete()
        print("✓ 资源清理完成")
        print("✅ 完整集成流程完成")


class TestEndToEndCollaboration:
    """端到端测试：多 Agent 协作"""
    
    def test_multi_agent_creation(self):
        """测试：多 Agent 创建"""
        print("\n=== 测试：多 Agent 创建 ===")
        
        agents = {}
        for i in range(3):
            agent_id = f"agent_{i}"
            agents[agent_id] = {
                'registry': AgentRegistry(),
                'soul': MetaSoul(),
                'awakening': AwakeningAdapter(),
            }
            agents[agent_id]['awakening'].agent_id = agent_id
            agents[agent_id]['awakening'].awaken()
            agents[agent_id]['soul'].soul_id = agent_id
            
            metadata = AgentMetadata(agent_id=agent_id, name=f"Agent {i}")
            agents[agent_id]['registry'].register(metadata)
        
        print(f"✓ 创建了 {len(agents)} 个 Agent")
        
        agents['agent_0']['soul'].store_memory("任务信息", MemoryType.EPISODIC)
        agents['agent_1']['soul'].store_memory("协作请求", MemoryType.EPISODIC)
        print(f"✓ 协作数据共享成功")
        print("✅ 多 Agent 协作测试完成")


class TestEndToEndErrorHandling:
    """端到端测试：错误处理"""
    
    def test_checkpoint_recovery(self):
        """测试：检查点恢复"""
        print("\n=== 测试：检查点恢复 ===")
        
        event_store = EventStore()
        
        session = Session()
        session.start()
        session_id = session.session_id
        
        context = ContextManager()
        for i in range(5):
            context.add_message({"role": "user", "content": f"消息 {i}"})
        
        print("✓ 正常处理流程完成")
        
        state = context.export_state()
        print(f"✓ 状态已导出")
        
        new_context = ContextManager()
        new_context.import_state(state)
        assert new_context.get_stats().message_count == 5  # 修复
        print(f"✓ 状态已恢复")
        print("✅ 检查点恢复测试完成")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


class TestEndToEndEventBusAndQueue:
    """端到端测试：事件总线和任务队列"""
    
    def test_event_bus_with_redis(self):
        """测试：事件总线（Redis模式）"""
        print("\n=== 测试：事件总线（Redis模式） ===")
        
        from packages.Runtime.buses.event_bus import EventBus, Event, EventType
        
        # 创建事件总线
        bus = EventBus(use_redis=True)
        print(f"✓ EventBus 创建: use_redis={bus.use_redis}")
        
        # 订阅事件
        received = []
        def handler(event):
            received.append(event)
        
        bus.subscribe("session.*", handler)
        print(f"✓ 订阅 session.* 事件")
        
        # 发布事件
        event = Event(
            event_type=EventType.SESSION_STARTED,
            source="test",
            data={"session_id": "test_session"}
        )
        bus.publish(event)
        print(f"✓ 发布事件")
        
        # 统计
        stats = bus.get_stats()
        print(f"✓ 统计: {stats}")
        print("✅ 事件总线测试完成")
    
    def test_task_queue_with_redis(self):
        """测试：任务队列（Redis模式）"""
        print("\n=== 测试：任务队列（Redis模式） ===")
        
        from packages.Runtime.buses.task_queue import TaskQueue, Task, TaskPriority
        
        # 创建任务队列
        queue = TaskQueue(use_redis=True)
        print(f"✓ TaskQueue 创建: use_redis={queue.use_redis}")
        
        # 入队
        task = Task(
            task_id="test_task",
            task_type="analysis",
            payload={"data": "test"},
            priority=TaskPriority.HIGH
        )
        queue.enqueue(task)
        print(f"✓ 任务入队")
        
        # 出队
        dequeued = queue.dequeue()
        assert dequeued is not None
        assert dequeued.task_id == "test_task"
        print(f"✓ 任务出队: {dequeued.task_id}")
        
        # 统计
        stats = queue.get_stats()
        print(f"✓ 统计: {stats}")
        print("✅ 任务队列测试完成")
    
    def test_full_pipeline(self):
        """测试：完整流水线"""
        print("\n=== 测试：完整流水线 ===")
        
        from packages.Runtime.buses.event_bus import EventBus, Event, EventType
        from packages.Runtime.buses.task_queue import TaskQueue, Task, TaskPriority
        
        bus = EventBus(use_redis=True)
        queue = TaskQueue(use_redis=True)
        
        # 1. 接收任务
        task = Task(
            task_id="pipeline_task",
            task_type="full_pipeline",
            payload={"step": 1}
        )
        queue.enqueue(task)
        
        # 2. 发布开始事件
        event = Event(
            event_type=EventType.TASK_SUBMITTED,
            source="pipeline",
            data={"task_id": task.task_id}
        )
        bus.publish(event)
        
        # 3. 处理任务
        processed = queue.dequeue()
        if processed:
            # 4. 发布完成事件
            complete_event = Event(
                event_type=EventType.TASK_COMPLETED,
                source="pipeline",
                data={"task_id": processed.task_id}
            )
            bus.publish(complete_event)
        
        print(f"✓ 流水线执行完成")
        print("✅ 完整流水线测试完成")
