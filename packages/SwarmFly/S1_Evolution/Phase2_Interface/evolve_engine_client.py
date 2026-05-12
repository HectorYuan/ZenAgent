"""
EvolveEngine接口客户端

提供与EvolveEngine进化引擎的通信接口
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import logging
import asyncio
import json

logger = logging.getLogger(__name__)


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
    COGNITIVE = "cognitive"          # 认知能力
    EXECUTIVE = "executive"          # 执行能力
    COLLABORATIVE = "collaborative"  # 协作能力
    ADAPTIVE = "adaptive"            # 自适应能力
    REASONING = "reasoning"          # 推理能力


@dataclass
class Capability:
    """智能体能力"""
    capability_id: str
    name: str
    type: CapabilityType
    level: int = 1                    # 能力等级 1-10
    score: float = 0.0               # 能力评分 0.0-1.0
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


class EvolveEngineClient:
    """
    EvolveEngine客户端
    
    功能:
    - 能力双向同步
    - 执行结果上报
    - 能力进化请求
    - 进化事件订阅
    - 获取进化状态
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # 服务配置
        self.base_url = self.config.get("base_url", "http://localhost:8080/api/evolve")
        self.api_key = self.config.get("api_key", "")
        self.timeout = self.config.get("timeout", 30)
        
        # 本地缓存
        self._capability_cache: Dict[str, List[Capability]] = {}
        self._evolution_history: List[EvolutionResult] = []
        
        # 事件订阅
        self._event_subscribers: Dict[str, List[Callable]] = {}
        
        # 模拟模式(无实际服务时使用)
        self.mock_mode = self.config.get("mock_mode", True)
        
        logger.info(f"EvolveEngineClient initialized (mock_mode={self.mock_mode})")
    
    async def sync_capability_bidirectional(
        self,
        agent_id: str,
        local_capabilities: List[Capability],
        remote_capabilities: Optional[List[Capability]] = None
    ) -> Dict[str, List[Capability]]:
        """
        能力双向同步
        
        将本地能力与远程同步，返回合并后的能力列表
        
        Args:
            agent_id: 智能体ID
            local_capabilities: 本地能力列表
            remote_capabilities: 远程能力列表(可选)
            
        Returns:
            {
                "merged": [Capability],     # 合并后的能力
                "local_only": [Capability], # 仅本地有的能力
                "remote_only": [Capability], # 仅远程有的能力
                "conflicts": [(local, remote)], # 冲突的能力对
                "sync_timestamp": datetime
            }
        """
        if self.mock_mode:
            return await self._mock_sync_capability(agent_id, local_capabilities)
        
        # 实际API调用
        # TODO: 实现真实API调用
        raise NotImplementedError("Real API call not implemented")
    
    async def _mock_sync_capability(
        self,
        agent_id: str,
        local_capabilities: List[Capability]
    ) -> Dict[str, List[Capability]]:
        """模拟能力同步"""
        # 缓存本地能力
        self._capability_cache[agent_id] = local_capabilities
        
        # 模拟返回
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
        """
        上报执行结果
        
        将任务执行结果上报给进化引擎，用于能力评估
        
        Args:
            agent_id: 智能体ID
            task_id: 任务ID
            result: 执行结果
            execution_time: 执行时间(秒)
            success: 是否成功
            error_message: 错误信息
            
        Returns:
            是否上报成功
        """
        report_data = {
            "agent_id": agent_id,
            "task_id": task_id,
            "result": result,
            "execution_time": execution_time,
            "success": success,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.mock_mode:
            logger.info(f"MOCK: Reported execution result for task {task_id}")
            return True
        
        # 实际API调用
        # TODO: 实现真实API调用
        raise NotImplementedError("Real API call not implemented")
    
    async def request_capability_evolution(
        self,
        agent_id: str,
        target_capabilities: List[str],
        priority: int = 5,
        timeout_seconds: int = 300,
        callback: Optional[Callable] = None
    ) -> EvolutionRequest:
        """
        请求能力进化
        
        向进化引擎请求提升指定能力
        
        Args:
            agent_id: 智能体ID
            target_capabilities: 目标能力列表(能力ID或名称)
            priority: 优先级 1-10
            timeout_seconds: 超时时间
            callback: 进化完成回调
            
        Returns:
            EvolutionRequest: 进化请求对象
        """
        import uuid
        
        request = EvolutionRequest(
            request_id=f"evo_{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            target_capabilities=target_capabilities,
            priority=priority,
            timeout_seconds=timeout_seconds
        )
        
        if self.mock_mode:
            # 模拟进化过程
            logger.info(f"MOCK: Created evolution request {request.request_id}")
            
            # 触发回调
            if callback:
                await callback(request)
            
            return request
        
        # 实际API调用
        # TODO: 实现真实API调用
        raise NotImplementedError("Real API call not implemented")
    
    async def subscribe_evolution_events(
        self,
        agent_id: str,
        event_types: List[str],
        handler: Callable[[Dict], None]
    ) -> str:
        """
        订阅进化事件
        
        订阅指定类型的进化事件
        
        Args:
            agent_id: 智能体ID
            event_types: 事件类型列表
            handler: 事件处理函数
            
        Returns:
            subscription_id: 订阅ID
        """
        import uuid
        
        subscription_id = f"sub_{uuid.uuid4().hex[:12]}"
        
        for event_type in event_types:
            if event_type not in self._event_subscribers:
                self._event_subscribers[event_type] = []
            self._event_subscribers[event_type].append(handler)
        
        logger.info(f"Subscribed to events: {event_types} (subscription_id={subscription_id})")
        
        return subscription_id
    
    async def unsubscribe_evolution_events(self, subscription_id: str) -> bool:
        """
        取消订阅进化事件
        
        Args:
            subscription_id: 订阅ID
            
        Returns:
            是否取消成功
        """
        # 在mock模式下，简单记录
        logger.info(f"Unsubscribed from events (subscription_id={subscription_id})")
        return True
    
    async def get_agent_evolution_status(self, agent_id: str) -> Dict[str, Any]:
        """
        获取智能体进化状态
        
        获取指定智能体的当前进化状态和能力水平
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            {
                "agent_id": str,
                "current_state": EvolutionState,
                "capabilities": [Capability],
                "evolution_history": [EvolutionResult],
                "overall_score": float,
                "recommendations": [str]
            }
        """
        if self.mock_mode:
            return await self._mock_get_status(agent_id)
        
        # 实际API调用
        # TODO: 实现真实API调用
        raise NotImplementedError("Real API call not implemented")
    
    async def _mock_get_status(self, agent_id: str) -> Dict[str, Any]:
        """模拟获取进化状态"""
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
            "evolution_history": [
                {
                    "request_id": r.request_id,
                    "state": r.state.value,
                    "improvement_score": r.improvement_score,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None
                }
                for r in self._evolution_history[-10:]  # 最近10条
            ],
            "overall_score": sum(c.score for c in capabilities) / len(capabilities) if capabilities else 0.0,
            "recommendations": [
                "建议提升协作能力",
                "建议优化执行效率"
            ]
        }
    
    async def trigger_evolution_event(self, event_type: str, event_data: Dict):
        """
        触发进化事件
        
        内部方法，用于触发订阅的事件
        
        Args:
            event_type: 事件类型
            event_data: 事件数据
        """
        handlers = self._event_subscribers.get(event_type, [])
        
        for handler in handlers:
            try:
                await handler(event_data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    def get_cache(self, agent_id: str) -> List[Capability]:
        """获取缓存的能力列表"""
        return self._capability_cache.get(agent_id, [])
    
    def clear_cache(self, agent_id: Optional[str] = None):
        """清除缓存"""
        if agent_id:
            self._capability_cache.pop(agent_id, None)
        else:
            self._capability_cache.clear()
