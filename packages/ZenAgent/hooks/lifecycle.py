"""
生命周期钩子
提供 Agent 生命周期的标准钩子定义和装饰器
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any, Optional, Dict
from functools import wraps

from .hook_manager import HookManager, HookPriority, HookEvent


class LifecycleEvent(Enum):
    """Agent 生命周期事件枚举"""
    # 创建阶段
    ON_CREATE = "agent.on_create"           # Agent 创建时
    ON_INITIALIZE = "agent.on_initialize"   # Agent 初始化时
    
    # 启动阶段
    ON_START = "agent.on_start"             # Agent 启动时
    ON_READY = "agent.on_ready"             # Agent 就绪时
    
    # 运行阶段
    ON_MESSAGE = "agent.on_message"        # 收到消息时
    ON_RESPONSE = "agent.on_response"      # 生成响应时
    ON_TOOL_CALL = "agent.on_tool_call"     # 调用工具时
    
    # 错误处理
    ON_ERROR = "agent.on_error"             # 发生错误时
    ON_WARNING = "agent.on_warning"         # 发生警告时
    
    # 协作阶段
    ON_COLLABORATION_REQUEST = "agent.on_collab_request"  # 协作请求时
    ON_TASK_DELEGATION = "agent.on_task_delegation"      # 任务委派时
    
    # 觉醒阶段
    ON_AWAKENING = "agent.on_awakening"     # 觉醒触发时
    ON_EVOLUTION = "agent.on_evolution"     # 进化发生时
    
    # 关闭阶段
    ON_SHUTDOWN = "agent.on_shutdown"        # Agent 关闭时
    ON_CLEANUP = "agent.on_cleanup"          # 清理资源时


@dataclass
class LifecycleHook:
    """
    生命周期钩子定义
    
    提供标准化的生命周期钩子接口
    """
    event: LifecycleEvent
    handler: Callable[..., Any]
    name: Optional[str] = None
    priority: HookPriority = HookPriority.NORMAL
    enabled: bool = True
    
    def __post_init__(self):
        """初始化后自动注册到全局钩子管理器"""
        from .hook_manager import get_hook_manager
        manager = get_hook_manager()
        
        hook_name = self.name or getattr(
            self.handler, "__name__", 
            f"lifecycle_{self.event.value}"
        )
        
        manager.register(
            event_name=self.event.value,
            handler=self.handler,
            name=hook_name,
            priority=self.priority,
        )


def on_create(
    handler: Optional[Callable[..., Any]] = None,
    *,
    name: Optional[str] = None,
    priority: HookPriority = HookPriority.NORMAL
) -> Any:
    """
    on_create 钩子装饰器
    
    Agent 创建时触发
    
    用法:
        @on_create()
        def my_handler(event):
            print(f"Agent created: {event.data}")
        
        # 或者带参数
        @on_create(name="my_handler", priority=HookPriority.HIGH)
        async def my_handler(event):
            ...
    """
    def decorator(func: Callable[..., Any]) -> LifecycleHook:
        hook = LifecycleHook(
            event=LifecycleEvent.ON_CREATE,
            handler=func,
            name=name,
            priority=priority,
        )
        return hook
    
    if handler is None:
        # 带参数调用
        return decorator
    else:
        # 直接装饰
        return decorator(handler)


def on_start(
    handler: Optional[Callable[..., Any]] = None,
    *,
    name: Optional[str] = None,
    priority: HookPriority = HookPriority.NORMAL
) -> Any:
    """
    on_start 钩子装饰器
    
    Agent 启动时触发
    
    用法:
        @on_start()
        def my_handler(event):
            print(f"Agent starting: {event.data}")
    """
    def decorator(func: Callable[..., Any]) -> LifecycleHook:
        hook = LifecycleHook(
            event=LifecycleEvent.ON_START,
            handler=func,
            name=name,
            priority=priority,
        )
        return hook
    
    if handler is None:
        return decorator
    else:
        return decorator(handler)


def on_message(
    handler: Optional[Callable[..., Any]] = None,
    *,
    name: Optional[str] = None,
    priority: HookPriority = HookPriority.NORMAL
) -> Any:
    """
    on_message 钩子装饰器
    
    收到消息时触发
    
    用法:
        @on_message()
        def my_handler(event):
            print(f"Received message: {event.data.get('message')}")
    """
    def decorator(func: Callable[..., Any]) -> LifecycleHook:
        hook = LifecycleHook(
            event=LifecycleEvent.ON_MESSAGE,
            handler=func,
            name=name,
            priority=priority,
        )
        return hook
    
    if handler is None:
        return decorator
    else:
        return decorator(handler)


def on_response(
    handler: Optional[Callable[..., Any]] = None,
    *,
    name: Optional[str] = None,
    priority: HookPriority = HookPriority.NORMAL
) -> Any:
    """
    on_response 钩子装饰器
    
    生成响应时触发
    
    用法:
        @on_response()
        def my_handler(event):
            print(f"Response generated: {event.data.get('response')}")
    """
    def decorator(func: Callable[..., Any]) -> LifecycleHook:
        hook = LifecycleHook(
            event=LifecycleEvent.ON_RESPONSE,
            handler=func,
            name=name,
            priority=priority,
        )
        return hook
    
    if handler is None:
        return decorator
    else:
        return decorator(handler)


def on_error(
    handler: Optional[Callable[..., Any]] = None,
    *,
    name: Optional[str] = None,
    priority: HookPriority = HookPriority.HIGH  # 错误处理默认高优先级
) -> Any:
    """
    on_error 钩子装饰器
    
    发生错误时触发
    
    用法:
        @on_error()
        def my_handler(event):
            print(f"Error occurred: {event.data.get('error')}")
    """
    def decorator(func: Callable[..., Any]) -> LifecycleHook:
        hook = LifecycleHook(
            event=LifecycleEvent.ON_ERROR,
            handler=func,
            name=name,
            priority=priority,
        )
        return hook
    
    if handler is None:
        return decorator
    else:
        return decorator(handler)


def on_shutdown(
    handler: Optional[Callable[..., Any]] = None,
    *,
    name: Optional[str] = None,
    priority: HookPriority = HookPriority.LOWEST  # 关闭时默认低优先级
) -> Any:
    """
    on_shutdown 钩子装饰器
    
    Agent 关闭时触发
    
    用法:
        @on_shutdown()
        def my_handler(event):
            print(f"Agent shutting down: {event.data}")
    """
    def decorator(func: Callable[..., Any]) -> LifecycleHook:
        hook = LifecycleHook(
            event=LifecycleEvent.ON_SHUTDOWN,
            handler=func,
            name=name,
            priority=priority,
        )
        return hook
    
    if handler is None:
        return decorator
    else:
        return decorator(handler)


class LifecycleManager:
    """
    生命周期管理器
    
    提供生命周期事件的便捷触发方法
    """
    
    def __init__(self, hook_manager: Optional[HookManager] = None):
        """
        初始化生命周期管理器
        
        Args:
            hook_manager: 钩子管理器（可选，默认使用全局管理器）
        """
        self._hook_manager = hook_manager
    
    @property
    def hook_manager(self) -> HookManager:
        """获取钩子管理器"""
        if self._hook_manager is None:
            from .hook_manager import get_hook_manager
            self._hook_manager = get_hook_manager()
        return self._hook_manager
    
    async def emit_create(
        self,
        agent_id: str,
        agent_type: str,
        **kwargs
    ) -> None:
        """触发 on_create 事件"""
        await self.hook_manager.trigger(
            event_name=LifecycleEvent.ON_CREATE.value,
            data={
                "agent_id": agent_id,
                "agent_type": agent_type,
                **kwargs,
            },
            source=agent_id,
        )
    
    async def emit_start(
        self,
        agent_id: str,
        **kwargs
    ) -> None:
        """触发 on_start 事件"""
        await self.hook_manager.trigger(
            event_name=LifecycleEvent.ON_START.value,
            data={
                "agent_id": agent_id,
                **kwargs,
            },
            source=agent_id,
        )
    
    async def emit_message(
        self,
        agent_id: str,
        message: Dict[str, Any],
        **kwargs
    ) -> None:
        """触发 on_message 事件"""
        await self.hook_manager.trigger(
            event_name=LifecycleEvent.ON_MESSAGE.value,
            data={
                "agent_id": agent_id,
                "message": message,
                **kwargs,
            },
            source=agent_id,
        )
    
    async def emit_response(
        self,
        agent_id: str,
        response: Dict[str, Any],
        **kwargs
    ) -> None:
        """触发 on_response 事件"""
        await self.hook_manager.trigger(
            event_name=LifecycleEvent.ON_RESPONSE.value,
            data={
                "agent_id": agent_id,
                "response": response,
                **kwargs,
            },
            source=agent_id,
        )
    
    async def emit_error(
        self,
        agent_id: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """触发 on_error 事件"""
        await self.hook_manager.trigger(
            event_name=LifecycleEvent.ON_ERROR.value,
            data={
                "agent_id": agent_id,
                "error": str(error),
                "error_type": type(error).__name__,
                "context": context or {},
                **kwargs,
            },
            source=agent_id,
        )
    
    async def emit_shutdown(
        self,
        agent_id: str,
        reason: Optional[str] = None,
        **kwargs
    ) -> None:
        """触发 on_shutdown 事件"""
        await self.hook_manager.trigger(
            event_name=LifecycleEvent.ON_SHUTDOWN.value,
            data={
                "agent_id": agent_id,
                "reason": reason,
                **kwargs,
            },
            source=agent_id,
        )
