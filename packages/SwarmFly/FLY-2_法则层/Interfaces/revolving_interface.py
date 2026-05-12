"""
Revolving引擎接口

提供与Revolving引擎的双向通信:
- 规则同步
- 任务路由
- 状态同步
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import asyncio

logger = logging.getLogger(__name__)


class SyncDirection(Enum):
    """同步方向"""
    PUSH = "push"      # 推送到Revolving
    PULL = "pull"      # 从Revolving拉取
    BIDIRECTIONAL = "bidirectional"


class RuleSyncStatus(Enum):
    """规则同步状态"""
    PENDING = "pending"
    SYNCING = "syncing"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class RuleSyncEvent:
    """规则同步事件"""
    event_id: str
    rule_id: str
    direction: SyncDirection
    status: RuleSyncStatus
    timestamp: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskRouteEvent:
    """任务路由事件"""
    event_id: str
    task_id: str
    source: str  # 任务来源
    target: Optional[str] = None  # 路由目标
    route_type: str = "direct"  # direct, balanced, priority
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskRouteRequest:
    """任务路由请求"""
    task_id: str
    task_type: str
    requirements: Dict[str, Any] = field(default_factory=dict)
    source_agent: Optional[str] = None
    priority: int = 50
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskRouteResult:
    """任务路由结果"""
    task_id: str
    target_agent: Optional[str]
    route_strategy: str
    estimated_completion: Optional[datetime] = None
    success: bool = True
    reason: str = ""
    alternatives: List[str] = field(default_factory=list)


class RevolvingInterface:
    """
    Revolving引擎接口
    
    负责与Revolving引擎的通信和协调:
    - 规则同步
    - 任务路由
    - 状态同步
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Revolving引擎连接配置
        self.revolving_url = self.config.get('revolving_url', 'http://localhost:8081')
        self.connection_timeout = self.config.get('connection_timeout', 30)
        
        # 同步配置
        self.sync_direction = SyncDirection(
            self.config.get('sync_direction', 'bidirectional')
        )
        self.auto_sync = self.config.get('auto_sync', True)
        self.sync_interval = self.config.get('sync_interval', 60)  # 秒
        
        # 回调
        self.on_rule_update: List[Callable] = []
        self.on_task_routed: List[Callable] = []
        
        # 同步状态
        self.is_connected = False
        self.last_sync_time: Optional[datetime] = None
        self.synced_rules: Dict[str, RuleSyncStatus] = {}
        
        # 任务路由缓存
        self.route_cache: Dict[str, TaskRouteResult] = {}
        
        # 统计
        self.stats = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'total_routes': 0,
            'successful_routes': 0
        }
    
    async def connect(self) -> bool:
        """连接到Revolving引擎"""
        try:
            # 模拟连接
            # 实际实现应该使用HTTP客户端连接
            logger.info(f"Connecting to Revolving engine at {self.revolving_url}")
            
            # 模拟延迟
            await asyncio.sleep(0.1)
            
            self.is_connected = True
            logger.info("Connected to Revolving engine")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Revolving: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """断开连接"""
        self.is_connected = False
        logger.info("Disconnected from Revolving engine")
    
    # ==================== 规则同步 ====================
    
    async def sync_rules_to_revolving(
        self,
        rules: List[Dict[str, Any]]
    ) -> List[RuleSyncEvent]:
        """
        同步规则到Revolving引擎
        
        Args:
            rules: 规则列表
            
        Returns:
            List[RuleSyncEvent]: 同步结果
        """
        if not self.is_connected:
            if not await self.connect():
                return []
        
        events = []
        
        for rule in rules:
            event = RuleSyncEvent(
                event_id=self._generate_event_id(),
                rule_id=rule.get('id', ''),
                direction=SyncDirection.PUSH,
                status=RuleSyncStatus.SYNCING
            )
            
            try:
                # 模拟同步
                await asyncio.sleep(0.05)
                
                event.status = RuleSyncStatus.SUCCESS
                self.synced_rules[event.rule_id] = RuleSyncStatus.SUCCESS
                self.stats['successful_syncs'] += 1
                
            except Exception as e:
                event.status = RuleSyncStatus.FAILED
                event.error_message = str(e)
                self.synced_rules[event.rule_id] = RuleSyncStatus.FAILED
                self.stats['failed_syncs'] += 1
                logger.error(f"Rule sync failed: {event.rule_id} - {e}")
            
            events.append(event)
            self.stats['total_syncs'] += 1
        
        self.last_sync_time = datetime.now()
        
        # 触发回调
        for callback in self.on_rule_update:
            try:
                callback('sync_complete', events)
            except Exception as e:
                logger.error(f"Rule update callback error: {e}")
        
        return events
    
    async def subscribe_rule_updates(
        self,
        callback: Callable[[str, Any], None]
    ) -> str:
        """
        订阅规则更新
        
        Args:
            callback: 回调函数
            
        Returns:
            str: 订阅ID
        """
        subscription_id = self._generate_event_id()
        self.on_rule_update.append(callback)
        logger.info(f"Subscribed to rule updates: {subscription_id}")
        return subscription_id
    
    async def pull_rules_from_revolving(self) -> List[Dict[str, Any]]:
        """
        从Revolving拉取规则
        
        Returns:
            List[Dict[str, Any]]: 规则列表
        """
        if not self.is_connected:
            if not await self.connect():
                return []
        
        try:
            # 模拟拉取
            await asyncio.sleep(0.1)
            
            # 返回空列表表示成功连接但无新规则
            return []
            
        except Exception as e:
            logger.error(f"Failed to pull rules: {e}")
            return []
    
    # ==================== 任务路由 ====================
    
    async def route_task(self, request: TaskRouteRequest) -> TaskRouteResult:
        """
        通过Revolving路由任务
        
        Args:
            request: 路由请求
            
        Returns:
            TaskRouteResult: 路由结果
        """
        if not self.is_connected:
            if not await self.connect():
                return TaskRouteResult(
                    task_id=request.task_id,
                    target_agent=None,
                    route_strategy="none",
                    success=False,
                    reason="Not connected to Revolving"
                )
        
        try:
            # 模拟路由决策
            await asyncio.sleep(0.05)
            
            # 生成路由结果
            result = TaskRouteResult(
                task_id=request.task_id,
                target_agent=self._select_target_agent(request),
                route_strategy="priority",
                estimated_completion=datetime.now()
            )
            
            self.stats['successful_routes'] += 1
            
            # 触发回调
            for callback in self.on_task_routed:
                try:
                    callback(request, result)
                except Exception as e:
                    logger.error(f"Task routed callback error: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Task routing failed: {e}")
            self.stats['successful_routes'] -= 1
            return TaskRouteResult(
                task_id=request.task_id,
                target_agent=None,
                route_strategy="failed",
                success=False,
                reason=str(e)
            )
    
    async def batch_route_tasks(
        self,
        requests: List[TaskRouteRequest]
    ) -> List[TaskRouteResult]:
        """批量路由任务"""
        results = []
        
        for request in requests:
            result = await self.route_task(request)
            results.append(result)
            self.stats['total_routes'] += 1
        
        return results
    
    def _select_target_agent(self, request: TaskRouteRequest) -> Optional[str]:
        """选择目标智能体"""
        # 简化实现：基于任务类型选择
        task_type_agents = {
            'analysis': 'agent_analysis_01',
            'execution': 'agent_exec_01',
            'communication': 'agent_comm_01'
        }
        
        return task_type_agents.get(request.task_type, 'agent_default')
    
    # ==================== 状态同步 ====================
    
    async def report_status(self, status: Dict[str, Any]) -> bool:
        """向Revolving报告状态"""
        if not self.is_connected:
            return False
        
        try:
            # 模拟状态报告
            await asyncio.sleep(0.02)
            logger.debug(f"Status reported: {status.get('state', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Status report failed: {e}")
            return False
    
    async def get_revolving_status(self) -> Dict[str, Any]:
        """获取Revolving引擎状态"""
        return {
            'is_connected': self.is_connected,
            'last_sync': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'synced_rules': len(self.synced_rules),
            'stats': self.stats
        }
    
    # ==================== 工具方法 ====================
    
    def _generate_event_id(self) -> str:
        """生成事件ID"""
        import hashlib
        import time
        content = f"{time.time()}:{datetime.now().microsecond}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
