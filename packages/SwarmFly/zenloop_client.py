"""
ZenLoop工具循环引擎接口客户端

提供与ZenLoop工具中心的通信接口
"""

# HACK: 确保项目根在 PYTHONPATH (TODO: 改为 PYTHONPATH=. 或 namespace package)

from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import logging
import asyncio
import uuid

logger = logging.getLogger(__name__)


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
        """成功率"""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions


class ZenLoopClient:
    """
    ZenLoop工具循环引擎客户端
    
    功能:
    - 工具注册
    - 工具发现
    - 工具调度
    - 使用监控
    - 工具释放
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # 服务配置
        self.base_url = self.config.get("base_url", "http://localhost:8081/api/zenloop")
        self.api_key = self.config.get("api_key", "")
        self.timeout = self.config.get("timeout", 30)
        
        # 本地缓存
        self._tool_registry: Dict[str, Tool] = {}
        self._execution_history: List[ToolExecution] = []
        self._usage_metrics: Dict[str, UsageMetrics] = {}
        
        # 模拟模式
        self.mock_mode = self.config.get("mock_mode", True)
        
        logger.info(f"ZenLoopClient initialized (mock_mode={self.mock_mode})")
    
    async def register_tool(
        self,
        name: str,
        description: str,
        category: str,
        parameters: Dict[str, Any],
        output_schema: Optional[Dict[str, Any]] = None,
        version: str = "1.0.0",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tool:
        """
        注册工具
        
        向工具中心注册一个新工具
        
        Args:
            name: 工具名称
            description: 工具描述
            category: 工具类别
            parameters: 参数定义
            output_schema: 输出schema
            version: 版本号
            metadata: 元数据
            
        Returns:
            Tool: 注册成功的工具对象
        """
        tool_id = f"tool_{uuid.uuid4().hex[:12]}"
        
        tool = Tool(
            tool_id=tool_id,
            name=name,
            description=description,
            category=category,
            version=version,
            status=ToolStatus.AVAILABLE,
            parameters=parameters,
            output_schema=output_schema or {},
            metadata=metadata or {}
        )
        
        if self.mock_mode:
            self._tool_registry[tool_id] = tool
            self._usage_metrics[tool_id] = UsageMetrics(tool_id=tool_id)
            logger.info(f"MOCK: Registered tool {name} ({tool_id})")
            return tool
        
        # 实际API调用
        # TODO: 实现真实API调用
        raise NotImplementedError(
            "ZenLoop real API not implemented. Set mock_mode=True (default) or implement the API client."
        )
    
    async def discover_tools(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: ToolStatus = ToolStatus.AVAILABLE,
        limit: int = 50
    ) -> List[Tool]:
        """
        发现工具
        
        根据条件发现可用的工具
        
        Args:
            query: 搜索关键词
            category: 工具类别
            tags: 标签列表
            status: 工具状态
            limit: 返回数量限制
            
        Returns:
            List[Tool]: 匹配的工具列表
        """
        if self.mock_mode:
            return await self._mock_discover_tools(query, category, tags, status, limit)
        
        # 实际API调用
        # TODO: 实现真实API调用
        raise NotImplementedError(
            "ZenLoop real API not implemented. Set mock_mode=True (default) or implement the API client."
        )
    
    async def _mock_discover_tools(
        self,
        query: Optional[str],
        category: Optional[str],
        tags: Optional[List[str]],
        status: ToolStatus,
        limit: int
    ) -> List[Tool]:
        """模拟工具发现"""
        results = []
        
        for tool in self._tool_registry.values():
            # 状态过滤
            if tool.status != status:
                continue
            
            # 类别过滤
            if category and tool.category != category:
                continue
            
            # 关键词过滤
            if query:
                query_lower = query.lower()
                if query_lower not in tool.name.lower() and query_lower not in tool.description.lower():
                    continue
            
            results.append(tool)
            
            if len(results) >= limit:
                break
        
        return results
    
    async def schedule_tool_execution(
        self,
        tool_id: str,
        agent_id: str,
        parameters: Dict[str, Any],
        priority: int = 5,
        timeout_seconds: int = 60,
        callback: Optional[Callable] = None
    ) -> ToolExecution:
        """
        调度工具执行
        
        调度一个工具的执行
        
        Args:
            tool_id: 工具ID
            agent_id: 调用智能体ID
            parameters: 执行参数
            priority: 优先级
            timeout_seconds: 超时时间
            callback: 完成回调
            
        Returns:
            ToolExecution: 执行记录
        """
        if tool_id not in self._tool_registry:
            raise ValueError(f"Tool {tool_id} not found")
        
        execution = ToolExecution(
            execution_id=f"exec_{uuid.uuid4().hex[:12]}",
            tool_id=tool_id,
            agent_id=agent_id,
            parameters=parameters,
            status=ExecutionStatus.RUNNING
        )
        
        if self.mock_mode:
            # 更新工具状态
            tool = self._tool_registry[tool_id]
            tool.status = ToolStatus.BUSY
            
            # 更新指标
            metrics = self._usage_metrics.get(tool_id)
            if metrics:
                metrics.total_executions += 1
            
            logger.info(f"MOCK: Scheduled tool execution {execution.execution_id}")
            
            # 模拟执行完成
            execution.status = ExecutionStatus.COMPLETED
            execution.result = {"status": "success", "output": "Mock result"}
            execution.end_time = datetime.now()
            execution.execution_time = 0.5
            
            # 更新指标
            if metrics:
                metrics.successful_executions += 1
                metrics.last_used = datetime.now()
            
            # 恢复工具状态
            tool.status = ToolStatus.AVAILABLE
            
            # 触发回调
            if callback:
                await callback(execution)
            
            return execution
        
        # 实际API调用
        # TODO: 实现真实API调用
        raise NotImplementedError(
            "ZenLoop real API not implemented. Set mock_mode=True (default) or implement the API client."
        )
    
    async def monitor_tool_usage(self, tool_id: Optional[str] = None) -> Dict[str, UsageMetrics]:
        """
        监控工具使用
        
        获取工具的使用指标
        
        Args:
            tool_id: 工具ID (可选，为None则返回所有)
            
        Returns:
            Dict[str, UsageMetrics]: 工具使用指标
        """
        if tool_id:
            return {tool_id: self._usage_metrics.get(tool_id, UsageMetrics(tool_id=tool_id))}
        
        return self._usage_metrics
    
    async def release_tool(self, tool_id: str, force: bool = False) -> bool:
        """
        释放工具
        
        从工具中心注销一个工具
        
        Args:
            tool_id: 工具ID
            force: 是否强制释放
            
        Returns:
            bool: 是否释放成功
        """
        if tool_id not in self._tool_registry:
            logger.warning(f"Tool {tool_id} not found")
            return False
        
        tool = self._tool_registry[tool_id]
        
        # 检查是否有正在执行的任务
        if not force:
            active_executions = [
                e for e in self._execution_history
                if e.tool_id == tool_id and e.status == ExecutionStatus.RUNNING
            ]
            if active_executions:
                logger.warning(f"Tool {tool_id} has active executions")
                return False
        
        # 标记为废弃
        tool.status = ToolStatus.DEPRECATED
        
        # 从注册表移除
        del self._tool_registry[tool_id]
        
        logger.info(f"Released tool {tool_id}")
        
        return True
    
    async def get_tool_info(self, tool_id: str) -> Optional[Tool]:
        """
        获取工具信息
        
        Args:
            tool_id: 工具ID
            
        Returns:
            Tool: 工具对象
        """
        return self._tool_registry.get(tool_id)
    
    async def get_execution_history(
        self,
        agent_id: Optional[str] = None,
        tool_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        limit: int = 100
    ) -> List[ToolExecution]:
        """
        获取执行历史
        
        Args:
            agent_id: 智能体ID
            tool_id: 工具ID
            status: 执行状态
            limit: 返回数量
            
        Returns:
            List[ToolExecution]: 执行记录列表
        """
        results = self._execution_history
        
        if agent_id:
            results = [e for e in results if e.agent_id == agent_id]
        
        if tool_id:
            results = [e for e in results if e.tool_id == tool_id]
        
        if status:
            results = [e for e in results if e.status == status]
        
        return results[-limit:]
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """
        取消执行
        
        Args:
            execution_id: 执行ID
            
        Returns:
            bool: 是否取消成功
        """
        for execution in self._execution_history:
            if execution.execution_id == execution_id:
                if execution.status in (ExecutionStatus.PENDING, ExecutionStatus.RUNNING):
                    execution.status = ExecutionStatus.CANCELLED
                    execution.end_time = datetime.now()
                    
                    # 恢复工具状态
                    tool = self._tool_registry.get(execution.tool_id)
                    if tool:
                        tool.status = ToolStatus.AVAILABLE
                    
                    logger.info(f"Cancelled execution {execution_id}")
                    return True
                else:
                    logger.warning(f"Cannot cancel execution {execution_id} with status {execution.status}")
                    return False
        
        return False
