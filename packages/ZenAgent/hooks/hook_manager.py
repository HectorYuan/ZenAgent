"""
钩子管理器
提供统一的钩子注册、触发和管理功能
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime
import asyncio
import logging


class HookPriority(Enum):
    """钩子优先级枚举（数字越小优先级越高）"""
    HIGHEST = 0    # 最高优先级
    HIGH = 25      # 高优先级
    NORMAL = 50    # 普通优先级（默认）
    LOW = 75       # 低优先级
    LOWEST = 100   # 最低优先级


@dataclass
class HookRegistration:
    """钩子注册信息"""
    name: str
    handler: Callable[..., Any]
    priority: HookPriority = HookPriority.NORMAL
    enabled: bool = True
    once: bool = False  # 是否只执行一次
    _executed: bool = False
    
    def __post_init__(self):
        """初始化后按优先级排序"""
        pass
    
    def should_execute(self) -> bool:
        """检查是否应该执行"""
        if not self.enabled:
            return False
        if self.once and self._executed:
            return False
        return True
    
    def mark_executed(self) -> None:
        """标记为已执行"""
        self._executed = True


@dataclass
class HookEvent:
    """钩子事件"""
    event_name: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None  # 事件来源


class HookManager:
    """
    钩子管理器
    
    管理所有钩子的注册、触发和执行
    """
    
    def __init__(self):
        """初始化钩子管理器"""
        self._hooks: Dict[str, List[HookRegistration]] = {}
        self._global_enabled: bool = True
        self._execution_history: List[HookEvent] = []
        self._max_history: int = 1000
        self._logger = logging.getLogger(__name__)
    
    def register(
        self,
        event_name: str,
        handler: Callable[..., Any],
        name: Optional[str] = None,
        priority: HookPriority = HookPriority.NORMAL,
        once: bool = False
    ) -> str:
        """
        注册钩子
        
        Args:
            event_name: 事件名称
            handler: 处理函数
            name: 钩子名称（可选，默认使用 handler 的名称）
            priority: 优先级
            once: 是否只执行一次
            
        Returns:
            str: 钩子 ID
        """
        hook_name = name or getattr(handler, "__name__", f"hook_{id(handler)}")
        
        registration = HookRegistration(
            name=hook_name,
            handler=handler,
            priority=priority,
            once=once,
        )
        
        if event_name not in self._hooks:
            self._hooks[event_name] = []
        
        self._hooks[event_name].append(registration)
        
        # 按优先级排序
        self._hooks[event_name].sort(key=lambda x: x.priority.value)
        
        self._logger.debug(f"Registered hook '{hook_name}' for event '{event_name}'")
        
        return hook_name
    
    def unregister(self, event_name: str, hook_name: str) -> bool:
        """
        注销钩子
        
        Args:
            event_name: 事件名称
            hook_name: 钩子名称
            
        Returns:
            bool: 是否成功注销
        """
        if event_name not in self._hooks:
            return False
        
        hooks = self._hooks[event_name]
        for i, hook in enumerate(hooks):
            if hook.name == hook_name:
                hooks.pop(i)
                self._logger.debug(f"Unregistered hook '{hook_name}' from event '{event_name}'")
                return True
        
        return False
    
    def enable(self, event_name: str, hook_name: str) -> bool:
        """
        启用钩子
        
        Args:
            event_name: 事件名称
            hook_name: 钩子名称
            
        Returns:
            bool: 是否成功
        """
        hook = self._get_hook(event_name, hook_name)
        if hook is None:
            return False
        hook.enabled = True
        return True
    
    def disable(self, event_name: str, hook_name: str) -> bool:
        """
        禁用钩子
        
        Args:
            event_name: 事件名称
            hook_name: 钩子名称
            
        Returns:
            bool: 是否成功
        """
        hook = self._get_hook(event_name, hook_name)
        if hook is None:
            return False
        hook.enabled = False
        return True
    
    def is_enabled(self, event_name: str, hook_name: str) -> bool:
        """
        检查钩子是否启用
        
        Args:
            event_name: 事件名称
            hook_name: 钩子名称
            
        Returns:
            bool: 是否启用
        """
        hook = self._get_hook(event_name, hook_name)
        return hook.enabled if hook else False
    
    def _get_hook(self, event_name: str, hook_name: str) -> Optional[HookRegistration]:
        """获取钩子"""
        if event_name not in self._hooks:
            return None
        
        for hook in self._hooks[event_name]:
            if hook.name == hook_name:
                return hook
        
        return None
    
    async def trigger(
        self,
        event_name: str,
        data: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> List[Any]:
        """
        触发钩子
        
        Args:
            event_name: 事件名称
            data: 事件数据
            source: 事件来源
            
        Returns:
            List[Any]: 所有钩子的执行结果
        """
        if not self._global_enabled:
            return []
        
        # 记录事件
        event = HookEvent(
            event_name=event_name,
            data=data or {},
            source=source,
        )
        self._add_to_history(event)
        
        if event_name not in self._hooks:
            return []
        
        results = []
        hooks = self._hooks[event_name]
        
        for hook in hooks:
            if not hook.should_execute():
                continue
            
            try:
                # 判断是否异步函数
                if asyncio.iscoroutinefunction(hook.handler):
                    result = await hook.handler(event)
                else:
                    result = hook.handler(event)
                
                results.append(result)
                hook.mark_executed()
                
            except Exception as e:
                self._logger.error(
                    f"Error executing hook '{hook.name}' for event '{event_name}': {e}"
                )
                results.append({"error": str(e)})
        
        return results
    
    def trigger_sync(
        self,
        event_name: str,
        data: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> List[Any]:
        """
        同步触发钩子（用于非异步上下文）
        
        Args:
            event_name: 事件名称
            data: 事件数据
            source: 事件来源
            
        Returns:
            List[Any]: 所有钩子的执行结果
        """
        if not self._global_enabled:
            return []
        
        # 记录事件
        event = HookEvent(
            event_name=event_name,
            data=data or {},
            source=source,
        )
        self._add_to_history(event)
        
        if event_name not in self._hooks:
            return []
        
        results = []
        hooks = self._hooks[event_name]
        
        for hook in hooks:
            if not hook.should_execute():
                continue
            
            try:
                result = hook.handler(event)
                results.append(result)
                hook.mark_executed()
                
            except Exception as e:
                self._logger.error(
                    f"Error executing hook '{hook.name}' for event '{event_name}': {e}"
                )
                results.append({"error": str(e)})
        
        return results
    
    def list_hooks(self, event_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出钩子
        
        Args:
            event_name: 事件名称（可选）
            
        Returns:
            List[Dict[str, Any]]: 钩子信息列表
        """
        if event_name:
            if event_name not in self._hooks:
                return []
            hooks = self._hooks[event_name]
        else:
            hooks = []
            for event_hooks in self._hooks.values():
                hooks.extend(event_hooks)
        
        return [
            {
                "name": h.name,
                "priority": h.priority.name,
                "enabled": h.enabled,
                "once": h.once,
                "executed": h._executed,
            }
            for h in hooks
        ]
    
    def list_events(self) -> List[str]:
        """
        列出所有事件名称
        
        Returns:
            List[str]: 事件名称列表
        """
        return list(self._hooks.keys())
    
    def _add_to_history(self, event: HookEvent) -> None:
        """添加到历史记录"""
        self._execution_history.append(event)
        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]
    
    def get_history(
        self,
        event_name: Optional[str] = None,
        limit: int = 100
    ) -> List[HookEvent]:
        """
        获取执行历史
        
        Args:
            event_name: 事件名称筛选
            limit: 返回数量限制
            
        Returns:
            List[HookEvent]: 历史事件列表
        """
        history = self._execution_history
        
        if event_name:
            history = [e for e in history if e.event_name == event_name]
        
        return history[-limit:]
    
    def clear_history(self) -> None:
        """清除历史记录"""
        self._execution_history.clear()
    
    def enable_all(self) -> None:
        """启用所有钩子"""
        self._global_enabled = True
    
    def disable_all(self) -> None:
        """禁用所有钩子"""
        self._global_enabled = False
    
    def reset_once_hooks(self) -> None:
        """重置所有 once 钩子的执行状态"""
        for hooks in self._hooks.values():
            for hook in hooks:
                hook._executed = False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        total_hooks = sum(len(hooks) for hooks in self._hooks.values())
        enabled_hooks = 0
        for hooks in self._hooks.values():
            enabled_hooks += sum(1 for h in hooks if h.enabled)
        
        return {
            "total_events": len(self._hooks),
            "total_hooks": total_hooks,
            "enabled_hooks": enabled_hooks,
            "disabled_hooks": total_hooks - enabled_hooks,
            "history_size": len(self._execution_history),
            "global_enabled": self._global_enabled,
        }


# 全局钩子管理器实例
_default_hook_manager: Optional[HookManager] = None


def get_hook_manager() -> HookManager:
    """获取全局钩子管理器"""
    global _default_hook_manager
    if _default_hook_manager is None:
        _default_hook_manager = HookManager()
    return _default_hook_manager
