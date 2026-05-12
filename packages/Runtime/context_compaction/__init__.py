# Context Compaction - 上下文压缩模块
"""
上下文压缩模块，当 Token 超过阈值时自动压缩上下文

包含:
- summarizer: 摘要提取器
- compressor: 压缩器
- manager: 上下文管理器
"""

from .summarizer import Summarizer, SummarizerStrategy, MessageSummary
from .compressor import Compressor, CompressionLevel, CompressionResult
from .manager import ContextManager, ContextConfig, ContextStats, ContextState

__all__ = [
    "Summarizer",
    "SummarizerStrategy", 
    "MessageSummary",
    "Compressor",
    "CompressionLevel",
    "CompressionResult",
    "ContextManager",
    "ContextConfig",
    "ContextStats",
    "ContextState",
]
