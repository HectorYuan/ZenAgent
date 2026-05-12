"""
ZenLoop接口测试用例
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zenloop_client import (
    ZenLoopClient,
    Tool,
    ToolStatus,
    ToolExecution,
    ExecutionStatus,
    UsageMetrics
)
import asyncio


class TestZenLoopBasic:
    """ZenLoop基础功能测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.client = ZenLoopClient({"mock_mode": True})
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        assert self.client is not None
        assert self.client.mock_mode is True


class TestToolRegistration:
    """工具注册测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.client = ZenLoopClient({"mock_mode": True})
    
    def test_register_tool_basic(self):
        """测试基本工具注册"""
        async def run():
            tool = await self.client.register_tool(
                name="test_tool",
                description="A test tool",
                category="testing",
                parameters={"input": {"type": "string"}}
            )
            
            assert tool.tool_id.startswith("tool_")
            assert tool.name == "test_tool"
            assert tool.category == "testing"
            assert tool.status == ToolStatus.AVAILABLE
            return True
        
        assert asyncio.run(run())
    
    def test_register_tool_with_full_params(self):
        """测试完整参数的工具注册"""
        async def run():
            tool = await self.client.register_tool(
                name="full_tool",
                description="Tool with full parameters",
                category="testing",
                parameters={"param1": "value1"},
                output_schema={"type": "object"},
                version="2.0.0",
                metadata={"author": "test"}
            )
            
            assert tool.version == "2.0.0"
            assert tool.output_schema == {"type": "object"}
            assert tool.metadata["author"] == "test"
            return True
        
        assert asyncio.run(run())
    
    def test_register_multiple_tools(self):
        """测试注册多个工具"""
        async def run():
            for i in range(5):
                tool = await self.client.register_tool(
                    name=f"tool_{i}",
                    description=f"Test tool {i}",
                    category="testing",
                    parameters={}
                )
                assert tool.tool_id in self.client._tool_registry
            
            assert len(self.client._tool_registry) >= 5
            return True
        
        assert asyncio.run(run())


class TestToolDiscovery:
    """工具发现测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.client = ZenLoopClient({"mock_mode": True})
    
    @pytest.fixture
    async def register_test_tools(self):
        """注册测试工具"""
        await self.client.register_tool(
            name="search_tool",
            description="Search for items",
            category="search",
            parameters={}
        )
        await self.client.register_tool(
            name="analyze_tool",
            description="Analyze data",
            category="analysis",
            parameters={}
        )
        await self.client.register_tool(
            name="report_tool",
            description="Generate reports",
            category="reporting",
            parameters={}
        )
    
    def test_discover_all_tools(self, register_test_tools):
        """测试发现所有工具"""
        async def run():
            tools = await self.client.discover_tools()
            assert len(tools) >= 3
            return True
        
        assert asyncio.run(run())
    
    def test_discover_by_category(self, register_test_tools):
        """测试按类别发现"""
        async def run():
            search_tools = await self.client.discover_tools(category="search")
            assert len(search_tools) >= 1
            assert all(t.category == "search" for t in search_tools)
            return True
        
        assert asyncio.run(run())
    
    def test_discover_by_query(self, register_test_tools):
        """测试关键词搜索"""
        async def run():
            tools = await self.client.discover_tools(query="analyze")
            assert len(tools) >= 1
            assert any("analyze" in t.name.lower() or "analyze" in t.description.lower() 
                      for t in tools)
            return True
        
        assert asyncio.run(run())


class TestToolExecution:
    """工具执行测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.client = ZenLoopClient({"mock_mode": True})
    
    @pytest.fixture
    async def register_execution_tool(self):
        """注册可执行工具"""
        return await self.client.register_tool(
            name="exec_tool",
            description="Executable tool",
            category="testing",
            parameters={"data": {"type": "string"}}
        )
    
    def test_schedule_execution(self, register_execution_tool):
        """测试调度执行"""
        async def run():
            execution = await self.client.schedule_tool_execution(
                tool_id=register_execution_tool.tool_id,
                agent_id="agent_1",
                parameters={"data": "test"}
            )
            
            assert execution.execution_id.startswith("exec_")
            assert execution.agent_id == "agent_1"
            assert execution.tool_id == register_execution_tool.tool_id
            return True
        
        assert asyncio.run(run())
    
    def test_execution_with_callback(self, register_execution_tool):
        """测试带回调的执行"""
        async def run():
            callback_result = None
            
            async def callback(execution):
                nonlocal callback_result
                callback_result = execution
            
            execution = await self.client.schedule_tool_execution(
                tool_id=register_execution_tool.tool_id,
                agent_id="agent_1",
                parameters={},
                callback=callback
            )
            
            assert callback_result is not None
            assert callback_result.execution_id == execution.execution_id
            return True
        
        assert asyncio.run(run())
    
    def test_schedule_execution_with_priority(self, register_execution_tool):
        """测试优先级执行"""
        async def run():
            execution = await self.client.schedule_tool_execution(
                tool_id=register_execution_tool.tool_id,
                agent_id="agent_1",
                parameters={},
                priority=10
            )
            
            assert execution.execution_id.startswith("exec_")
            return True
        
        assert asyncio.run(run())


class TestToolMonitoring:
    """工具监控测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.client = ZenLoopClient({"mock_mode": True})
    
    @pytest.fixture
    async def tool_with_executions(self):
        """创建有执行记录的工具"""
        tool = await self.client.register_tool(
            name="monitor_tool",
            description="Tool for monitoring",
            category="testing",
            parameters={}
        )
        
        # 执行几次
        for _ in range(3):
            await self.client.schedule_tool_execution(
                tool_id=tool.tool_id,
                agent_id="agent_1",
                parameters={}
            )
        
        return tool
    
    def test_monitor_tool_usage(self, tool_with_executions):
        """测试监控工具使用"""
        async def run():
            metrics = await self.client.monitor_tool_usage(tool_with_executions.tool_id)
            
            assert tool_with_executions.tool_id in metrics
            assert metrics[tool_with_executions.tool_id].total_executions >= 3
            return True
        
        assert asyncio.run(run())
    
    def test_monitor_all_tools(self, tool_with_executions):
        """测试监控所有工具"""
        async def run():
            all_metrics = await self.client.monitor_tool_usage()
            
            assert tool_with_executions.tool_id in all_metrics
            assert isinstance(all_metrics[tool_with_executions.tool_id], UsageMetrics)
            return True
        
        assert asyncio.run(run())


class TestToolRelease:
    """工具释放测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.client = ZenLoopClient({"mock_mode": True})
    
    def test_release_tool(self):
        """测试释放工具"""
        async def run():
            tool = await self.client.register_tool(
                name="release_tool",
                description="Tool to release",
                category="testing",
                parameters={}
            )
            
            result = await self.client.release_tool(tool.tool_id)
            assert result is True
            assert tool.tool_id not in self.client._tool_registry
            return True
        
        assert asyncio.run(run())
    
    def test_release_nonexistent_tool(self):
        """测试释放不存在的工具"""
        async def run():
            result = await self.client.release_tool("nonexistent_tool")
            assert result is False
            return True
        
        assert asyncio.run(run())


class TestTool:
    """工具模型测试"""
    
    def test_tool_creation(self):
        """测试工具创建"""
        tool = Tool(
            tool_id="test_123",
            name="Test Tool",
            description="A test tool",
            category="testing",
            version="1.0.0"
        )
        
        assert tool.tool_id == "test_123"
        assert tool.name == "Test Tool"
        assert tool.status == ToolStatus.AVAILABLE
    
    def test_tool_default_status(self):
        """测试默认状态"""
        tool = Tool(
            tool_id="test",
            name="Test",
            description="Test",
            category="test"
        )
        
        assert tool.status == ToolStatus.AVAILABLE


class TestToolExecutionModel:
    """工具执行模型测试"""
    
    def test_execution_creation(self):
        """测试执行创建"""
        execution = ToolExecution(
            execution_id="exec_123",
            tool_id="tool_1",
            agent_id="agent_1",
            parameters={"key": "value"}
        )
        
        assert execution.execution_id == "exec_123"
        assert execution.status == ExecutionStatus.PENDING
    
    def test_execution_completion(self):
        """测试执行完成"""
        execution = ToolExecution(
            execution_id="exec_123",
            tool_id="tool_1",
            agent_id="agent_1",
            parameters={},
            status=ExecutionStatus.COMPLETED,
            result={"output": "success"}
        )
        
        assert execution.status == ExecutionStatus.COMPLETED
        assert execution.result == {"output": "success"}


class TestUsageMetrics:
    """使用指标测试"""
    
    def test_usage_metrics_creation(self):
        """测试指标创建"""
        metrics = UsageMetrics(
            tool_id="tool_1",
            total_executions=100,
            successful_executions=95
        )
        
        assert metrics.tool_id == "tool_1"
        assert metrics.total_executions == 100
        assert metrics.success_rate == 0.95
    
    def test_success_rate_zero_executions(self):
        """测试零执行时的成功率"""
        metrics = UsageMetrics(tool_id="tool_1")
        assert metrics.success_rate == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
