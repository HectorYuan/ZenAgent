"""
EvolveEngine接口测试用例
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evolve_engine_client import (
    EvolveEngineClient,
    Capability,
    CapabilityType,
    EvolutionState,
    EvolutionRequest,
    EvolutionResult
)
from datetime import datetime
import asyncio


class TestEvolveEngineBasic:
    """EvolveEngine基础功能测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.client = EvolveEngineClient({"mock_mode": True})
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        assert self.client is not None
        assert self.client.mock_mode is True
    
    def test_get_agent_evolution_status(self):
        """测试获取进化状态"""
        async def run():
            status = await self.client.get_agent_evolution_status("agent_1")
            assert status["agent_id"] == "agent_1"
            assert "current_state" in status
            assert "capabilities" in status
            return True
        
        assert asyncio.run(run())


class TestCapabilitySync:
    """能力同步测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.client = EvolveEngineClient({"mock_mode": True})
    
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
            
            assert "merged" in result
            assert "local_only" in result
            assert "remote_only" in result
            assert "sync_timestamp" in result
            return True
        
        assert asyncio.run(run())
    
    def test_capability_cache(self):
        """测试能力缓存"""
        async def run():
            capabilities = [
                Capability(
                    capability_id="cap_1",
                    name="test",
                    type=CapabilityType.COGNITIVE,
                    level=3
                )
            ]
            
            await self.client.sync_capability_bidirectional(
                agent_id="agent_cache_test",
                local_capabilities=capabilities
            )
            
            cached = self.client.get_cache("agent_cache_test")
            assert len(cached) == 1
            assert cached[0].capability_id == "cap_1"
            return True
        
        assert asyncio.run(run())


class TestEvolutionRequest:
    """进化请求测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.client = EvolveEngineClient({"mock_mode": True})
    
    def test_request_capability_evolution(self):
        """测试能力进化请求"""
        async def run():
            request = await self.client.request_capability_evolution(
                agent_id="agent_1",
                target_capabilities=["reasoning", "collaborative"],
                priority=8
            )
            
            assert request.agent_id == "agent_1"
            assert request.target_capabilities == ["reasoning", "collaborative"]
            assert request.priority == 8
            assert request.request_id.startswith("evo_")
            return True
        
        assert asyncio.run(run())
    
    def test_evolution_request_with_callback(self):
        """测试带回调的进化请求"""
        async def run():
            callback_invoked = False
            
            async def callback(request):
                nonlocal callback_invoked
                callback_invoked = True
            
            await self.client.request_capability_evolution(
                agent_id="agent_1",
                target_capabilities=["reasoning"],
                callback=callback
            )
            
            assert callback_invoked
            return True
        
        assert asyncio.run(run())


class TestExecutionResult:
    """执行结果上报测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.client = EvolveEngineClient({"mock_mode": True})
    
    def test_report_execution_result_success(self):
        """测试上报成功结果"""
        async def run():
            result = await self.client.report_execution_result(
                agent_id="agent_1",
                task_id="task_1",
                result={"output": "success"},
                execution_time=1.5,
                success=True
            )
            
            assert result is True
            return True
        
        assert asyncio.run(run())
    
    def test_report_execution_result_failure(self):
        """测试上报失败结果"""
        async def run():
            result = await self.client.report_execution_result(
                agent_id="agent_1",
                task_id="task_1",
                result={},
                execution_time=1.0,
                success=False,
                error_message="Task failed"
            )
            
            assert result is True  # mock模式下总是返回True
            return True
        
        assert asyncio.run(run())


class TestEventSubscription:
    """事件订阅测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.client = EvolveEngineClient({"mock_mode": True})
    
    def test_subscribe_evolution_events(self):
        """测试订阅进化事件"""
        async def run():
            async def handler(event_data):
                pass
            
            subscription_id = await self.client.subscribe_evolution_events(
                agent_id="agent_1",
                event_types=["evolution_started", "evolution_completed"],
                handler=handler
            )
            
            assert subscription_id.startswith("sub_")
            return True
        
        assert asyncio.run(run())
    
    def test_unsubscribe_evolution_events(self):
        """测试取消订阅"""
        async def run():
            async def handler(event_data):
                pass
            
            subscription_id = await self.client.subscribe_evolution_events(
                agent_id="agent_1",
                event_types=["evolution_started"],
                handler=handler
            )
            
            result = await self.client.unsubscribe_evolution_events(subscription_id)
            assert result is True
            return True
        
        assert asyncio.run(run())


class TestCapability:
    """能力模型测试"""
    
    def test_capability_creation(self):
        """测试能力创建"""
        cap = Capability(
            capability_id="test_cap",
            name="Test Capability",
            type=CapabilityType.COGNITIVE,
            level=5,
            score=0.75
        )
        
        assert cap.capability_id == "test_cap"
        assert cap.name == "Test Capability"
        assert cap.type == CapabilityType.COGNITIVE
        assert cap.level == 5
        assert cap.score == 0.75
    
    def test_capability_default_values(self):
        """测试能力默认值"""
        cap = Capability(
            capability_id="test_cap",
            name="Test",
            type=CapabilityType.EXECUTIVE
        )
        
        assert cap.level == 1
        assert cap.score == 0.0
        assert isinstance(cap.metadata, dict)


class TestEvolutionRequestModel:
    """进化请求模型测试"""
    
    def test_evolution_request_creation(self):
        """测试进化请求创建"""
        req = EvolutionRequest(
            request_id="evo_123",
            agent_id="agent_1",
            target_capabilities=["reasoning", "adaptive"]
        )
        
        assert req.request_id == "evo_123"
        assert req.agent_id == "agent_1"
        assert len(req.target_capabilities) == 2
        assert req.priority == 5  # 默认值
        assert req.timeout_seconds == 300  # 默认值


class TestEvolutionResultModel:
    """进化结果模型测试"""
    
    def test_evolution_result_success(self):
        """测试成功进化结果"""
        result = EvolutionResult(
            request_id="evo_123",
            agent_id="agent_1",
            state=EvolutionState.COMPLETED,
            evolved_capabilities=[],
            improvement_score=0.15,
            completed_at=datetime.now()
        )
        
        assert result.state == EvolutionState.COMPLETED
        assert result.improvement_score == 0.15
    
    def test_evolution_result_failure(self):
        """测试失败进化结果"""
        result = EvolutionResult(
            request_id="evo_123",
            agent_id="agent_1",
            state=EvolutionState.FAILED,
            evolved_capabilities=[],
            error_message="Evolution failed"
        )
        
        assert result.state == EvolutionState.FAILED
        assert result.error_message == "Evolution failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
