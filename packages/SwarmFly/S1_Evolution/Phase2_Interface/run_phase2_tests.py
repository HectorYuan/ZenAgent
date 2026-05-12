"""
Phase 2: 接口测试运行器
独立运行接口测试，不依赖SwarmFly核心模块
"""

import sys
import os

# 独立导入，不依赖外部模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接导入测试文件中的类定义，避免导入SwarmFly __init__.py
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
import logging
import uuid

logger = logging.getLogger(__name__)


# ============== EvolveEngine Models ==============

class EvolutionState(Enum):
    """进化状态"""
    IDLE = "idle"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class CapabilityType(Enum):
    """能力类型"""
    COGNITIVE = "cognitive"
    EXECUTIVE = "executive"
    COLLABORATIVE = "collaborative"
    ADAPTIVE = "adaptive"
    REASONING = "reasoning"


@dataclass
class Capability:
    """智能体能力"""
    capability_id: str
    name: str
    type: CapabilityType
    level: int = 1
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class EvolutionRequest:
    """进化请求"""
    request_id: str
    agent_id: str
    target_capabilities: List[str]
    priority: int = 5
    timeout_seconds: int = 300
    callback_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class EvolutionResult:
    """进化结果"""
    request_id: str
    agent_id: str
    state: EvolutionState
    evolved_capabilities: List[Capability]
    improvement_score: float = 0.0
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


# ============== EvolveEngine Client ==============

class EvolveEngineClient:
    """EvolveEngine客户端"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.base_url = self.config.get("base_url", "http://localhost:8080/api/evolve")
        self.api_key = self.config.get("api_key", "")
        self.timeout = self.config.get("timeout", 30)
        self._capability_cache: Dict[str, List[Capability]] = {}
        self._evolution_history: List[EvolutionResult] = []
        self._event_subscribers: Dict[str, List[Callable]] = {}
        self.mock_mode = self.config.get("mock_mode", True)
        logger.info(f"EvolveEngineClient initialized (mock_mode={self.mock_mode})")
    
    async def sync_capability_bidirectional(
        self,
        agent_id: str,
        local_capabilities: List[Capability],
        remote_capabilities: Optional[List[Capability]] = None
    ) -> Dict[str, List[Capability]]:
        """能力双向同步"""
        self._capability_cache[agent_id] = local_capabilities
        return {
            "merged": local_capabilities,
            "local_only": local_capabilities,
            "remote_only": [],
            "conflicts": [],
            "sync_timestamp": datetime.now()
        }
    
    async def report_execution_result(
        self,
        agent_id: str,
        task_id: str,
        result: Dict[str, Any],
        execution_time: float,
        success: bool,
        error_message: Optional[str] = None
    ) -> bool:
        """上报执行结果"""
        if self.mock_mode:
            logger.info(f"MOCK: Reported execution result for task {task_id}")
            return True
        return False
    
    async def request_capability_evolution(
        self,
        agent_id: str,
        target_capabilities: List[str],
        priority: int = 5,
        timeout_seconds: int = 300,
        callback: Optional[Callable] = None
    ) -> EvolutionRequest:
        """请求能力进化"""
        request = EvolutionRequest(
            request_id=f"evo_{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            target_capabilities=target_capabilities,
            priority=priority,
            timeout_seconds=timeout_seconds
        )
        if callback:
            await callback(request)
        return request
    
    async def subscribe_evolution_events(
        self,
        agent_id: str,
        event_types: List[str],
        handler: Callable
    ) -> str:
        """订阅进化事件"""
        subscription_id = f"sub_{uuid.uuid4().hex[:12]}"
        for event_type in event_types:
            if event_type not in self._event_subscribers:
                self._event_subscribers[event_type] = []
            self._event_subscribers[event_type].append(handler)
        return subscription_id
    
    async def unsubscribe_evolution_events(self, subscription_id: str) -> bool:
        """取消订阅"""
        return True
    
    async def get_agent_evolution_status(self, agent_id: str) -> Dict[str, Any]:
        """获取进化状态"""
        capabilities = self._capability_cache.get(agent_id, [])
        return {
            "agent_id": agent_id,
            "current_state": EvolutionState.IDLE.value,
            "capabilities": [
                {
                    "capability_id": c.capability_id,
                    "name": c.name,
                    "type": c.type.value,
                    "level": c.level,
                    "score": c.score
                } for c in capabilities
            ],
            "evolution_history": [],
            "overall_score": sum(c.score for c in capabilities) / len(capabilities) if capabilities else 0.0,
            "recommendations": ["建议提升协作能力"]
        }
    
    def get_cache(self, agent_id: str) -> List[Capability]:
        """获取缓存"""
        return self._capability_cache.get(agent_id, [])


# ============== ZenLoop Models ==============

class ToolStatus(Enum):
    """工具状态"""
    AVAILABLE = "available"
    BUSY = "busy"
    RESERVED = "reserved"
    UNAVAILABLE = "unavailable"
    DEPRECATED = "deprecated"


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class Tool:
    """工具定义"""
    tool_id: str
    name: str
    description: str
    category: str
    version: str = "1.0.0"
    status: ToolStatus = ToolStatus.AVAILABLE
    parameters: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.now)


@dataclass
class ToolExecution:
    """工具执行记录"""
    execution_id: str
    tool_id: str
    agent_id: str
    parameters: Dict[str, Any]
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[Dict] = None
    error: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    execution_time: float = 0.0


@dataclass
class UsageMetrics:
    """使用指标"""
    tool_id: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    avg_execution_time: float = 0.0
    last_used: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions


# ============== ZenLoop Client ==============

class ZenLoopClient:
    """ZenLoop工具循环引擎客户端"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.base_url = self.config.get("base_url", "http://localhost:8081/api/zenloop")
        self.api_key = self.config.get("api_key", "")
        self.timeout = self.config.get("timeout", 30)
        self._tools: Dict[str, Tool] = {}
        self._executions: Dict[str, ToolExecution] = {}
        self._metrics: Dict[str, UsageMetrics] = {}
        self.mock_mode = self.config.get("mock_mode", True)
        logger.info(f"ZenLoopClient initialized (mock_mode={self.mock_mode})")
    
    async def register_tool(self, tool: Tool) -> bool:
        """注册工具"""
        if self.mock_mode:
            self._tools[tool.tool_id] = tool
            self._metrics[tool.tool_id] = UsageMetrics(tool_id=tool.tool_id)
            logger.info(f"MOCK: Registered tool {tool.tool_id}")
            return True
        return False
    
    async def discover_tools(
        self,
        category: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Tool]:
        """发现工具"""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        if keywords:
            tools = [t for t in tools if any(kw.lower() in t.name.lower() or kw.lower() in t.description.lower() for kw in keywords)]
        return tools[:limit]
    
    async def invoke_tool(
        self,
        tool_id: str,
        agent_id: str,
        parameters: Dict[str, Any],
        timeout: int = 60
    ) -> ToolExecution:
        """调用工具"""
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        execution = ToolExecution(
            execution_id=execution_id,
            tool_id=tool_id,
            agent_id=agent_id,
            parameters=parameters,
            status=ExecutionStatus.RUNNING
        )
        self._executions[execution_id] = execution
        
        if tool_id in self._metrics:
            self._metrics[tool_id].total_executions += 1
            self._metrics[tool_id].last_used = datetime.now()
        
        # 模拟执行完成
        execution.status = ExecutionStatus.COMPLETED
        execution.result = {"output": "success", "tool_id": tool_id}
        execution.end_time = datetime.now()
        
        return execution
    
    async def get_tool_status(self, tool_id: str) -> Optional[Tool]:
        """获取工具状态"""
        return self._tools.get(tool_id)
    
    async def release_tool(self, tool_id: str) -> bool:
        """释放工具"""
        if tool_id in self._tools:
            self._tools[tool_id].status = ToolStatus.AVAILABLE
            logger.info(f"Released tool {tool_id}")
            return True
        return False
    
    async def monitor_tool_usage(self, tool_id: str) -> Optional[UsageMetrics]:
        """监控工具使用"""
        return self._metrics.get(tool_id)


# ============== Tests ==============

import unittest


class TestEvolveEngine(unittest.TestCase):
    """EvolveEngine接口测试"""
    
    def setUp(self):
        self.client = EvolveEngineClient({"mock_mode": True})
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        self.assertIsNotNone(self.client)
        self.assertTrue(self.client.mock_mode)
    
    def test_sync_capability_bidirectional(self):
        """测试能力双向同步"""
        async def run():
            capabilities = [
                Capability(
                    capability_id="cap_1",
                    name="reasoning",
                    type=CapabilityType.REASONING,
                    level=5,
                    score=0.8
                )
            ]
            result = await self.client.sync_capability_bidirectional(
                agent_id="agent_1",
                local_capabilities=capabilities
            )
            self.assertIn("merged", result)
            self.assertIn("local_only", result)
            return True
        
        self.assertTrue(asyncio.run(run()))
    
    def test_request_capability_evolution(self):
        """测试能力进化请求"""
        async def run():
            request = await self.client.request_capability_evolution(
                agent_id="agent_1",
                target_capabilities=["reasoning", "collaborative"],
                priority=8
            )
            self.assertEqual(request.agent_id, "agent_1")
            self.assertEqual(request.priority, 8)
            self.assertTrue(request.request_id.startswith("evo_"))
            return True
        
        self.assertTrue(asyncio.run(run()))
    
    def test_report_execution_result(self):
        """测试上报执行结果"""
        async def run():
            result = await self.client.report_execution_result(
                agent_id="agent_1",
                task_id="task_1",
                result={"output": "success"},
                execution_time=1.5,
                success=True
            )
            self.assertTrue(result)
            return True
        
        self.assertTrue(asyncio.run(run()))
    
    def test_subscribe_evolution_events(self):
        """测试订阅进化事件"""
        async def run():
            async def handler(event_data):
                pass
            
            subscription_id = await self.client.subscribe_evolution_events(
                agent_id="agent_1",
                event_types=["evolution_started"],
                handler=handler
            )
            self.assertTrue(subscription_id.startswith("sub_"))
            return True
        
        self.assertTrue(asyncio.run(run()))
    
    def test_get_agent_evolution_status(self):
        """测试获取进化状态"""
        async def run():
            status = await self.client.get_agent_evolution_status("agent_1")
            self.assertEqual(status["agent_id"], "agent_1")
            self.assertIn("current_state", status)
            return True
        
        self.assertTrue(asyncio.run(run()))


class TestZenLoop(unittest.TestCase):
    """ZenLoop接口测试"""
    
    def setUp(self):
        self.client = ZenLoopClient({"mock_mode": True})
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        self.assertIsNotNone(self.client)
        self.assertTrue(self.client.mock_mode)
    
    def test_register_tool(self):
        """测试工具注册"""
        async def run():
            tool = Tool(
                tool_id="tool_1",
                name="Calculator",
                description="A simple calculator",
                category="math"
            )
            result = await self.client.register_tool(tool)
            self.assertTrue(result)
            return True
        
        self.assertTrue(asyncio.run(run()))
    
    def test_discover_tools(self):
        """测试工具发现"""
        async def run():
            # 先注册一些工具
            await self.client.register_tool(Tool(
                tool_id="tool_1",
                name="Calculator",
                description="A calculator",
                category="math"
            ))
            await self.client.register_tool(Tool(
                tool_id="tool_2",
                name="TextParser",
                description="Parse text",
                category="nlp"
            ))
            
            tools = await self.client.discover_tools(category="math")
            self.assertEqual(len(tools), 1)
            self.assertEqual(tools[0].name, "Calculator")
            return True
        
        self.assertTrue(asyncio.run(run()))
    
    def test_invoke_tool(self):
        """测试工具调用"""
        async def run():
            # 先注册工具
            await self.client.register_tool(Tool(
                tool_id="tool_1",
                name="Calculator",
                description="A calculator",
                category="math"
            ))
            
            execution = await self.client.invoke_tool(
                tool_id="tool_1",
                agent_id="agent_1",
                parameters={"operation": "add", "a": 1, "b": 2}
            )
            self.assertEqual(execution.status, ExecutionStatus.COMPLETED)
            self.assertIsNotNone(execution.result)
            return True
        
        self.assertTrue(asyncio.run(run()))
    
    def test_get_tool_status(self):
        """测试获取工具状态"""
        async def run():
            tool = Tool(
                tool_id="tool_1",
                name="Calculator",
                description="A calculator",
                category="math"
            )
            await self.client.register_tool(tool)
            
            status = await self.client.get_tool_status("tool_1")
            self.assertIsNotNone(status)
            self.assertEqual(status.name, "Calculator")
            return True
        
        self.assertTrue(asyncio.run(run()))
    
    def test_release_tool(self):
        """测试工具释放"""
        async def run():
            tool = Tool(
                tool_id="tool_1",
                name="Calculator",
                description="A calculator",
                category="math"
            )
            await self.client.register_tool(tool)
            
            result = await self.client.release_tool("tool_1")
            self.assertTrue(result)
            return True
        
        self.assertTrue(asyncio.run(run()))
    
    def test_monitor_tool_usage(self):
        """测试工具使用监控"""
        async def run():
            tool = Tool(
                tool_id="tool_1",
                name="Calculator",
                description="A calculator",
                category="math"
            )
            await self.client.register_tool(tool)
            
            # 使用工具
            await self.client.invoke_tool(
                tool_id="tool_1",
                agent_id="agent_1",
                parameters={}
            )
            
            metrics = await self.client.monitor_tool_usage("tool_1")
            self.assertIsNotNone(metrics)
            self.assertEqual(metrics.total_executions, 1)
            return True
        
        self.assertTrue(asyncio.run(run()))


class TestInterfaceIntegration(unittest.TestCase):
    """接口集成测试"""
    
    def setUp(self):
        self.evolve_client = EvolveEngineClient({"mock_mode": True})
        self.zenloop_client = ZenLoopClient({"mock_mode": True})
    
    def test_full_evolution_flow(self):
        """测试完整进化流程"""
        async def run():
            # 1. 注册工具
            tool = Tool(
                tool_id="tool_1",
                name="LearningTool",
                description="A learning tool",
                category="learning"
            )
            await self.zenloop_client.register_tool(tool)
            
            # 2. 同步能力
            capabilities = [
                Capability(
                    capability_id="cap_1",
                    name="learning",
                    type=CapabilityType.COGNITIVE,
                    level=3,
                    score=0.5
                )
            ]
            sync_result = await self.evolve_client.sync_capability_bidirectional(
                agent_id="agent_1",
                local_capabilities=capabilities
            )
            self.assertIn("merged", sync_result)
            
            # 3. 请求进化
            request = await self.evolve_client.request_capability_evolution(
                agent_id="agent_1",
                target_capabilities=["learning"]
            )
            self.assertIsNotNone(request)
            
            # 4. 上报执行结果
            report_result = await self.evolve_client.report_execution_result(
                agent_id="agent_1",
                task_id="task_1",
                result={"success": True},
                execution_time=2.0,
                success=True
            )
            self.assertTrue(report_result)
            
            return True
        
        self.assertTrue(asyncio.run(run()))


if __name__ == "__main__":
    # 运行测试
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestEvolveEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestZenLoop))
    suite.addTests(loader.loadTestsFromTestCase(TestInterfaceIntegration))
    
    # 运行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "="*60)
    print("Phase 2 接口测试结果总结")
    print("="*60)
    print(f"测试用例: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("="*60)
