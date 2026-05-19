"""
Runtime 可观测性模块
全链路 Trace ID + 关键节点 Metrics

设计依据: E2E_OPTIMIZATION_DESIGN §模块8 - Hook 链路可观测性
"""
from .tracer import TraceContext, Span, Tracer
from .metrics import MetricsCollector, MetricType

__all__ = [
    'TraceContext',
    'Span',
    'Tracer',
    'MetricsCollector',
    'MetricType',
]
