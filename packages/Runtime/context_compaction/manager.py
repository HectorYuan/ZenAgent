"""
上下文管理器 - Context Manager

管理对话上下文的生命周期，包括自动压缩和清理
"""


from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .summarizer import Summarizer, SummarizerStrategy, MessageSummary
from .compressor import Compressor, CompressionLevel, CompressionResult


class ContextState(Enum):
    """上下文状态"""
    NORMAL = "normal"           # 正常状态
    WARNING = "warning"         # 接近阈值
    COMPRESSING = "compressing"  # 压缩中
    COMPRESSED = "compressed"   # 已压缩
    ERROR = "error"             # 错误状态


@dataclass
class ContextConfig:
    """上下文配置"""
    max_tokens: int = 8000              # 最大 Token 数
    warning_threshold: float = 0.8       # 警告阈值（百分比）
    compression_threshold: float = 0.9   # 压缩阈值（百分比）
    auto_compress: bool = True          # 自动压缩
    compression_level: CompressionLevel = CompressionLevel.MEDIUM
    summarizer_strategy: SummarizerStrategy = SummarizerStrategy.HYBRID
    preserve_recent: int = 5             # 保留最近消息数
    check_interval: int = 1              # 检查间隔（消息数）


@dataclass
class ContextStats:
    """上下文统计"""
    current_tokens: int = 0
    message_count: int = 0
    state: ContextState = ContextState.NORMAL
    compression_count: int = 0
    last_compression_time: Optional[datetime] = None
    total_saved_tokens: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "current_tokens": self.current_tokens,
            "message_count": self.message_count,
            "state": self.state.value,
            "compression_count": self.compression_count,
            "last_compression_time": self.last_compression_time.isoformat() if self.last_compression_time else None,
            "total_saved_tokens": self.total_saved_tokens
        }


class ContextManager:
    """
    上下文管理器
    
    负责管理对话上下文，支持自动压缩、状态监控和统计。
    """
    
    def __init__(self, config: Optional[ContextConfig] = None):
        """
        初始化上下文管理器
        
        Args:
            config: 上下文配置
        """
        self.config = config or ContextConfig()
        self.summarizer = Summarizer(
            strategy=self.config.summarizer_strategy,
            preserve_recent_count=self.config.preserve_recent
        )
        self.compressor = Compressor(
            level=self.config.compression_level,
            preserve_recent=self.config.preserve_recent
        )
        
        self._messages: List[Dict[str, Any]] = []
        self._stats = ContextStats()
        self._compression_history: List[CompressionResult] = []
        self._last_summary: Optional[MessageSummary] = None
        self._message_count_since_check = 0
        self._hooks: Dict[str, List[Callable]] = {
            "before_compress": [],
            "after_compress": [],
            "warning": [],
            "error": []
        }
    
    def add_message(self, message: Dict[str, Any]) -> ContextStats:
        """
        添加消息
        
        Args:
            message: 消息字典
            
        Returns:
            ContextStats: 当前统计状态
        """
        self._messages.append(message)
        self._message_count_since_check += 1
        self._update_stats()
        
        # 检查是否需要压缩
        if (self.config.auto_compress and 
            self._stats.state == ContextState.COMPRESSING):
            self.compress()
        
        return self._stats
    
    def add_messages(self, messages: List[Dict[str, Any]]) -> ContextStats:
        """
        批量添加消息
        
        Args:
            messages: 消息列表
            
        Returns:
            ContextStats: 当前统计状态
        """
        for msg in messages:
            self.add_message(msg)
        return self._stats
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """获取所有消息"""
        return self._messages.copy()
    
    def get_recent_messages(self, count: int = 10) -> List[Dict[str, Any]]:
        """获取最近的 N 条消息"""
        return self._messages[-count:] if self._messages else []
    
    def clear(self) -> None:
        """清空上下文"""
        self._messages.clear()
        self._update_stats()
    
    def compress(
        self,
        force: bool = False,
        task_context: Optional[str] = None
    ) -> CompressionResult:
        """
        压缩上下文
        
        Args:
            force: 是否强制压缩
            task_context: 任务上下文
            
        Returns:
            CompressionResult: 压缩结果
        """
        # 触发前置钩子
        self._trigger_hooks("before_compress", self._messages)
        
        self._stats.state = ContextState.COMPRESSING
        
        try:
            # 生成摘要
            summary = self.summarizer.summarize(
                self._messages,
                task_context=task_context
            )
            self._last_summary = summary
            
            # 执行压缩
            result = self.compressor.compress(
                self._messages,
                summary=summary.content
            )
            
            # 更新消息
            self._messages = result.compressed_messages
            
            # 更新统计
            self._compression_history.append(result)
            self._stats.compression_count += 1
            self._stats.last_compression_time = datetime.now()
            self._stats.total_saved_tokens += result.removed_count * 100  # 估算
            self._stats.state = ContextState.COMPRESSED
            
            # 触发后置钩子
            self._trigger_hooks("after_compress", result)
            
            # 更新状态
            self._update_stats()
            
            return result
            
        except Exception as e:
            self._stats.state = ContextState.ERROR
            self._trigger_hooks("error", e)
            raise
    
    def get_stats(self) -> ContextStats:
        """获取统计信息"""
        self._update_stats()
        return self._stats
    
    def get_summary(self) -> Optional[MessageSummary]:
        """获取当前摘要"""
        return self._last_summary
    
    def get_compression_history(self) -> List[CompressionResult]:
        """获取压缩历史"""
        return self._compression_history.copy()
    
    def register_hook(self, event: str, callback: Callable) -> None:
        """
        注册事件钩子
        
        Args:
            event: 事件名称
            callback: 回调函数
        """
        if event in self._hooks:
            self._hooks[event].append(callback)
    
    def unregister_hook(self, event: str, callback: Callable) -> None:
        """
        注销事件钩子
        
        Args:
            event: 事件名称
            callback: 回调函数
        """
        if event in self._hooks and callback in self._hooks[event]:
            self._hooks[event].remove(callback)
    
    def should_compress(self) -> bool:
        """检查是否应该压缩"""
        return (self._stats.current_tokens / self.config.max_tokens >= 
                self.config.compression_threshold)
    
    def _update_stats(self) -> None:
        """更新统计信息"""
        self._stats.message_count = len(self._messages)
        self._stats.current_tokens = self._estimate_tokens()
        
        # 更新状态
        token_ratio = self._stats.current_tokens / self.config.max_tokens
        
        if self._stats.state == ContextState.COMPRESSING:
            pass  # 保持压缩中状态
        elif token_ratio >= self.config.compression_threshold:
            self._stats.state = ContextState.COMPRESSING
        elif token_ratio >= self.config.warning_threshold:
            if self._stats.state != ContextState.WARNING:
                self._stats.state = ContextState.WARNING
                self._trigger_hooks("warning", self._stats)
        else:
            self._stats.state = ContextState.NORMAL
        
        self._message_count_since_check = 0
    
    def _estimate_tokens(self) -> int:
        """估算当前 Token 数"""
        total = 0
        for msg in self._messages:
            content = msg.get("content", "")
            total += self._summarizer._estimate_tokens(content) if hasattr(self, '_summarizer') else len(content) // 4
        return total
    
    def _trigger_hooks(self, event: str, *args, **kwargs) -> None:
        """触发钩子"""
        if event in self._hooks:
            for callback in self._hooks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception:
                    pass  # 忽略钩子执行错误
    
    def get_state(self) -> ContextState:
        """获取当前状态"""
        self._update_stats()
        return self._stats.state
    
    def reset_stats(self) -> None:
        """重置统计"""
        self._stats = ContextStats()
        self._compression_history.clear()
    
    def export_state(self) -> Dict[str, Any]:
        """
        导出完整状态
        
        Returns:
            Dict: 包含消息、统计和历史的完整状态
        """
        return {
            "messages": self._messages,
            "stats": self._stats.to_dict(),
            "summary": self._last_summary.to_dict() if self._last_summary else None,
            "compression_history": [r.to_dict() for r in self._compression_history],
            "config": {
                "max_tokens": self.config.max_tokens,
                "auto_compress": self.config.auto_compress,
                "compression_level": self.config.compression_level.value
            }
        }
    
    def import_state(self, state: Dict[str, Any]) -> None:
        """
        导入状态
        
        Args:
            state: 之前导出的完整状态
        """
        self._messages = state.get("messages", [])
        
        summary_dict = state.get("summary")
        if summary_dict:
            self._last_summary = MessageSummary.from_dict(summary_dict)
        
        self._compression_history = [
            CompressionResult(
                original_messages=h.get("original_messages", []),
                compressed_messages=h.get("compressed_messages", []),
                summary=h.get("summary"),
                removed_count=h.get("removed_count", 0),
                compression_ratio=h.get("compression_ratio", 0.0)
            )
            for h in state.get("compression_history", [])
        ]
        
        self._update_stats()
