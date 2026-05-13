"""
ZenAgent 核心入口

整合 MCP、Hooks、Awakening 和 Collaboration 模块的统一入口
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import uuid

# MCP 模块
from .mcp import (
    MCPProtocol,
    MCPMessage,
    MCPRequest,
    MCPResponse,
    MCPSession,
    MCPSessionState,
    MCPSessionManager,
    MCPHandler,
    MCPHandlerRegistry,
    AgentRegistry,
    RegisteredAgent,
    AgentMetadata,
    AgentStatus,
    AgentCapability,
)

# Hooks 模块
from .hooks import (
    HookManager,
    HookPriority,
    HookEvent,
    LifecycleHook,
    LifecycleEvent,
    LifecycleManager,
    LoggingHook,
    MetricsHook,
    RateLimitHook,
    MonitoringHook,
    # 装饰器
    on_create,
    on_start,
    on_message,
    on_response,
    on_error,
    on_shutdown,
)

# Awakening 模块
from .awakening import (
    AwakeningAdapter,
    AwakeningState,
    AwakeningCapability,
    CapabilityRegistry,
    EvolutionEngine,
    EvolutionStage,
    EvolutionEvent,
)

# Collaboration 模块
from .collaboration import (
    CollaborationProtocol,
    CollaborationMessage,
    CollaborationRequest,
    CollaborationResponse,
    ProtocolType,
    MessagePriority,
    CollaborationNegotiator,
    NegotiationResult,
    NegotiationStatus,
    TaskRouter,
    TaskRoute,
    RouteStrategy,
)


@dataclass
class ZenAgentConfig:
    """ZenAgent 配置"""
    # Agent 基本信息
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = "ZenAgent"
    agent_type: str = "general"
    
    # MCP 配置
    mcp_protocol_version: str = "1.0.0"
    session_idle_timeout: int = 300
    session_max_lifetime: int = 3600
    
    # Hooks 配置
    enable_logging: bool = True
    enable_metrics: bool = True
    enable_rate_limit: bool = True
    rate_limit_max_per_window: int = 100
    rate_limit_window_seconds: int = 60
    
    # Awakening 配置
    awakening_threshold: float = 0.8
    enable_evolution: bool = True
    
    # Collaboration 配置
    collaboration_timeout: int = 60
    max_collaboration_participants: int = 5
    
    # 功能开关
    enable_mcp: bool = True
    enable_hooks: bool = True
    enable_awakening: bool = True
    enable_collaboration: bool = True


class ZenAgent:
    """
    ZenAgent 核心类
    
    整合所有模块的统一入口
    """
    
    def __init__(self, config: Optional[ZenAgentConfig] = None):
        """
        初始化 ZenAgent
        
        Args:
            config: 配置对象
        """
        self.config = config or ZenAgentConfig()
        
        # MCP 模块
        self._protocol: Optional[MCPProtocol] = None
        self._session_manager: Optional[MCPSessionManager] = None
        self._handler_registry: Optional[MCPHandlerRegistry] = None
        self._agent_registry: Optional[AgentRegistry] = None
        
        # Hooks 模块
        self._hook_manager: Optional[HookManager] = None
        self._lifecycle_manager: Optional[LifecycleManager] = None
        self._logging_hook: Optional[LoggingHook] = None
        self._metrics_hook: Optional[MetricsHook] = None
        self._rate_limit_hook: Optional[RateLimitHook] = None
        self._monitoring_hook: Optional[MonitoringHook] = None
        
        # Awakening 模块
        self._awakening_adapter: Optional[AwakeningAdapter] = None
        self._capability_registry: Optional[CapabilityRegistry] = None
        self._evolution_engine: Optional[EvolutionEngine] = None
        
        # Collaboration 模块
        self._collaboration_protocol: Optional[CollaborationProtocol] = None
        self._negotiator: Optional[CollaborationNegotiator] = None
        self._task_router: Optional[TaskRouter] = None
        
        # 初始化所有模块
        self._initialize_modules()
    
    def _initialize_modules(self) -> None:
        """初始化所有模块"""
        # MCP 模块
        if self.config.enable_mcp:
            self._protocol = MCPProtocol(version=self.config.mcp_protocol_version)
            self._session_manager = MCPSessionManager()
            self._handler_registry = MCPHandlerRegistry()
            self._agent_registry = get_registry()
        
        # Hooks 模块
        if self.config.enable_hooks:
            self._hook_manager = get_hook_manager()
            self._lifecycle_manager = LifecycleManager(self._hook_manager)
            
            if self.config.enable_logging:
                self._logging_hook = get_logging_hook()
            if self.config.enable_metrics:
                self._metrics_hook = get_metrics_hook()
            if self.config.enable_rate_limit:
                self._rate_limit_hook = get_rate_limit_hook()
            self._monitoring_hook = get_monitoring_hook()
        
        # Awakening 模块
        if self.config.enable_awakening:
            self._awakening_adapter = get_adapter(self.config.agent_id)
            self._capability_registry = get_capability_registry()
            self._evolution_engine = get_evolution_engine()
            
            # 设置适配器的注册表和引擎
            if self._awakening_adapter:
                self._awakening_adapter.set_capability_registry(
                    self._capability_registry
                )
                self._awakening_adapter.set_evolution_engine(
                    self._evolution_engine
                )
                self._awakening_adapter.context.awakening_threshold = (
                    self.config.awakening_threshold
                )
        
        # Collaboration 模块
        if self.config.enable_collaboration:
            self._collaboration_protocol = CollaborationProtocol()
            self._negotiator = get_negotiator()
            self._task_router = get_router()
            
            # 设置路由器的注册表
            if self._task_router and self._agent_registry:
                self._task_router.set_registry(self._agent_registry)
    
    # ====================
    # MCP 访问器
    # ====================
    
    @property
    def protocol(self) -> Optional[MCPProtocol]:
        """获取 MCP 协议"""
        return self._protocol
    
    @property
    def session_manager(self) -> Optional[MCPSessionManager]:
        """获取会话管理器"""
        return self._session_manager
    
    @property
    def handler_registry(self) -> Optional[MCPHandlerRegistry]:
        """获取处理器注册表"""
        return self._handler_registry
    
    @property
    def agent_registry(self) -> Optional[AgentRegistry]:
        """获取 Agent 注册表"""
        return self._agent_registry
    
    # ====================
    # Hooks 访问器
    # ====================
    
    @property
    def hook_manager(self) -> Optional[HookManager]:
        """获取钩子管理器"""
        return self._hook_manager
    
    @property
    def lifecycle_manager(self) -> Optional[LifecycleManager]:
        """获取生命周期管理器"""
        return self._lifecycle_manager
    
    @property
    def metrics(self) -> Optional[MetricsHook]:
        """获取指标钩子"""
        return self._metrics_hook
    
    # ====================
    # Awakening 访问器
    # ====================
    
    @property
    def awakening(self) -> Optional[AwakeningAdapter]:
        """获取觉醒适配器"""
        return self._awakening_adapter
    
    @property
    def capabilities(self) -> Optional[CapabilityRegistry]:
        """获取能力注册表"""
        return self._capability_registry
    
    @property
    def evolution(self) -> Optional[EvolutionEngine]:
        """获取进化引擎"""
        return self._evolution_engine
    
    # ====================
    # Collaboration 访问器
    # ====================
    
    @property
    def collaboration_protocol(self) -> Optional[CollaborationProtocol]:
        """获取协作协议"""
        return self._collaboration_protocol
    
    @property
    def negotiator(self) -> Optional[CollaborationNegotiator]:
        """获取协商器"""
        return self._negotiator
    
    @property
    def task_router(self) -> Optional[TaskRouter]:
        """获取任务路由器"""
        return self._task_router
    
    # ====================
    # 便捷方法
    # ====================
    
    def register_handler(
        self,
        method: str,
        handler: Callable,
        **kwargs
    ) -> None:
        """
        注册 MCP 处理器
        
        Args:
            method: 方法名
            handler: 处理函数
            **kwargs: 其他参数
        """
        if self._handler_registry:
            self._handler_registry.register(method, handler, **kwargs)
    
    def register_hook(
        self,
        event: LifecycleEvent,
        handler: Callable,
        **kwargs
    ) -> None:
        """
        注册生命周期钩子
        
        Args:
            event: 生命周期事件
            handler: 处理函数
            **kwargs: 其他参数
        """
        if self._hook_manager:
            self._hook_manager.register(event.value, handler, **kwargs)
    
    def register_agent(
        self,
        metadata: AgentMetadata,
        endpoint: Optional[str] = None
    ) -> Optional[RegisteredAgent]:
        """
        注册 Agent
        
        Args:
            metadata: Agent 元数据
            endpoint: 连接端点
            
        Returns:
            Optional[RegisteredAgent]: 注册的 Agent
        """
        if self._agent_registry:
            return self._agent_registry.register(metadata, endpoint)
        return None
    
    async def emit_lifecycle_event(
        self,
        event: LifecycleEvent,
        **data
    ) -> None:
        """
        触发生命周期事件
        
        Args:
            event: 生命周期事件
            **data: 事件数据
        """
        if self._lifecycle_manager:
            await self._hook_manager.trigger(
                event_name=event.value,
                data=data,
                source=self.config.agent_id,
            )
    
    def route_task(
        self,
        task_type: str,
        **kwargs
    ) -> Optional[TaskRoute]:
        """
        路由任务
        
        Args:
            task_type: 任务类型
            **kwargs: 其他参数
            
        Returns:
            Optional[TaskRoute]: 路由结果
        """
        if self._task_router:
            return self._task_router.route(task_type, **kwargs)
        return None
    
    def create_collaboration_request(
        self,
        task_type: str,
        task_description: str,
        **kwargs
    ) -> Optional[CollaborationRequest]:
        """
        创建协作请求
        
        Args:
            task_type: 任务类型
            task_description: 任务描述
            **kwargs: 其他参数
            
        Returns:
            Optional[CollaborationRequest]: 协作请求
        """
        if self._collaboration_protocol:
            return self._collaboration_protocol.create_request(
                requester_id=self.config.agent_id,
                requester_name=self.config.agent_name,
                task_type=task_type,
                task_description=task_description,
                **kwargs
            )
        return None
    
    def get_full_status(self) -> Dict[str, Any]:
        """
        获取完整状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        status = {
            "agent_id": self.config.agent_id,
            "agent_name": self.config.agent_name,
            "agent_type": self.config.agent_type,
            "timestamp": datetime.now().isoformat(),
        }
        
        # MCP 状态
        if self._session_manager:
            status["mcp"] = self._session_manager.get_stats()
        
        # Hooks 状态
        if self._hook_manager:
            status["hooks"] = self._hook_manager.get_stats()
        
        # Metrics 状态
        if self._metrics_hook:
            status["metrics"] = self._metrics_hook.get_summary()
        
        # Awakening 状态
        if self._awakening_adapter:
            status["awakening"] = self._awakening_adapter.get_info()
        
        # Evolution 状态
        if self._evolution_engine:
            status["evolution"] = self._evolution_engine.get_progress(
                self.config.agent_id
            )
        
        # Agent Registry 状态
        if self._agent_registry:
            status["registry"] = self._agent_registry.get_stats()
        
        # Collaboration 状态
        if self._negotiator:
            status["collaboration"] = self._negotiator.get_stats()
        
        if self._task_router:
            status["routing"] = self._task_router.get_stats()
        
        return status
    
    def reset(self) -> None:
        """重置 ZenAgent"""
        # 重置所有模块
        if self._hook_manager:
            self._hook_manager.reset_once_hooks()
            self._hook_manager.clear_history()
        
        if self._metrics_hook:
            self._metrics_hook.reset()
        
        if self._rate_limit_hook:
            self._rate_limit_hook.reset()
        
        if self._monitoring_hook:
            self._monitoring_hook.clear_alerts()
        
        if self._awakening_adapter:
            self._awakening_adapter.reset()
        
        if self._evolution_engine:
            self._evolution_engine.reset(self.config.agent_id)


# 全局 ZenAgent 实例
_default_agent: Optional[ZenAgent] = None


def get_zenaagent(config: Optional[ZenAgentConfig] = None) -> ZenAgent:
    """
    获取 ZenAgent 实例
    
    Args:
        config: 配置对象
        
    Returns:
        ZenAgent: ZenAgent 实例
    """
    global _default_agent
    if _default_agent is None:
        _default_agent = ZenAgent(config)
    return _default_agent


def create_zenaagent(**kwargs) -> ZenAgent:
    """
    创建新的 ZenAgent 实例
    
    Args:
        **kwargs: 配置参数
        
    Returns:
        ZenAgent: 新的 ZenAgent 实例
    """
    config = ZenAgentConfig(**kwargs)
    return ZenAgent(config)
