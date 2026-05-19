"""
链路追踪器

设计依据: E2E_OPTIMIZATION_DESIGN §模块8 - Hook 链路可观测性

核心能力:
- 全链路 Trace ID 透传
- Span 嵌套（父子关系）
- 每个 Span 耗时、状态、异常记录
- 慢操作告警（>5s）
"""

import uuid
import time
import logging
import contextvars
from enum import Enum
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Trace 上下文传播（跨 async 边界）
_trace_ctx: contextvars.ContextVar[Optional['TraceContext']] = contextvars.ContextVar(
    'trace_ctx', default=None
)


class SpanStatus(Enum):
    """Span 状态"""
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class Span:
    """追踪 Span"""
    span_id: str
    trace_id: str
    name: str
    parent_span_id: Optional[str] = None
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    status: SpanStatus = SpanStatus.OK
    error: Optional[str] = None
    tags: Dict[str, Any] = field(default_factory=dict)

    def finish(self, status: SpanStatus = SpanStatus.OK, error: Optional[str] = None):
        """结束 Span"""
        self.end_time = time.monotonic()
        self.duration = self.end_time - self.start_time
        self.status = status
        if error:
            self.error = error

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "name": self.name,
            "parent_span_id": self.parent_span_id,
            "start_time": round(self.start_time, 6),
            "duration_ms": round(self.duration * 1000, 2),
            "status": self.status.value,
            "error": self.error,
            "tags": self.tags,
        }


@dataclass
class TraceContext:
    """追踪上下文"""
    trace_id: str
    spans: List[Span] = field(default_factory=list)
    start_time: float = 0.0
    tags: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        if not self.spans:
            return 0.0
        return max(s.end_time for s in self.spans if s.end_time > 0) - self.start_time

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "span_count": len(self.spans),
            "duration_ms": round(self.duration * 1000, 2),
            "tags": self.tags,
            "spans": [s.to_dict() for s in self.spans],
        }


class Tracer:
    """
    链路追踪器

    管理 Trace 和 Span 的创建、结束、查询。
    通过 contextvars 实现跨 async 边界的上下文传播。
    """

    SLOW_THRESHOLD = 5.0  # 慢操作告警阈值（秒）

    def __init__(self, slow_threshold: float = 5.0):
        self._traces: Dict[str, TraceContext] = {}
        self._slow_threshold = slow_threshold
        self._total_traces = 0
        self._total_spans = 0

    def start_trace(self, trace_id: Optional[str] = None, tags: Optional[Dict] = None) -> TraceContext:
        """开始新的追踪"""
        trace_id = trace_id or f"trace-{uuid.uuid4().hex[:16]}"
        ctx = TraceContext(
            trace_id=trace_id,
            start_time=time.monotonic(),
            tags=tags or {},
        )
        self._traces[trace_id] = ctx
        self._total_traces += 1
        _trace_ctx.set(ctx)
        return ctx

    def start_span(self, name: str, parent: Optional[Span] = None,
                   tags: Optional[Dict] = None) -> Span:
        """开始新的 Span"""
        ctx = _trace_ctx.get()
        if ctx is None:
            ctx = self.start_trace()

        span = Span(
            span_id=f"span-{uuid.uuid4().hex[:12]}",
            trace_id=ctx.trace_id,
            name=name,
            parent_span_id=parent.span_id if parent else None,
            start_time=time.monotonic(),
            tags=tags or {},
        )
        ctx.spans.append(span)
        self._total_spans += 1
        return span

    def end_span(self, span: Span, status: SpanStatus = SpanStatus.OK,
                 error: Optional[str] = None):
        """结束 Span"""
        span.finish(status, error)

        # 慢操作告警
        if span.duration > self._slow_threshold:
            logger.warning(
                f"Slow span detected: {span.name} took {span.duration:.2f}s "
                f"(trace_id={span.trace_id})"
            )

    def get_trace(self, trace_id: str) -> Optional[TraceContext]:
        """获取追踪记录"""
        return self._traces.get(trace_id)

    def get_current_trace(self) -> Optional[TraceContext]:
        """获取当前追踪上下文"""
        return _trace_ctx.get()

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_traces": self._total_traces,
            "total_spans": self._total_spans,
            "active_traces": len(self._traces),
            "slow_threshold": self._slow_threshold,
        }

    def clear(self):
        """清除所有追踪记录"""
        self._traces.clear()
        _trace_ctx.set(None)
