"""
链路追踪与指标收集测试

设计依据: E2E_OPTIMIZATION_DESIGN §模块8
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import asyncio

from tracing.tracer import Tracer, SpanStatus, TraceContext, Span
from tracing.metrics import MetricsCollector, MetricType


class TestTracer:
    """链路追踪器测试"""

    def test_start_trace(self):
        """创建追踪"""
        tracer = Tracer()
        ctx = tracer.start_trace(tags={"service": "test"})
        assert ctx.trace_id.startswith("trace-")
        assert ctx.tags == {"service": "test"}

    def test_start_trace_custom_id(self):
        """自定义 trace_id"""
        tracer = Tracer()
        ctx = tracer.start_trace(trace_id="my-trace-001")
        assert ctx.trace_id == "my-trace-001"

    def test_start_span(self):
        """创建 Span"""
        tracer = Tracer()
        tracer.start_trace()
        span = tracer.start_span("llm.chat")
        assert span.name == "llm.chat"
        assert span.span_id.startswith("span-")
        assert span.start_time > 0

    def test_span_parent(self):
        """Span 父子关系"""
        tracer = Tracer()
        tracer.start_trace()
        parent = tracer.start_span("request")
        child = tracer.start_span("llm.chat", parent=parent)
        assert child.parent_span_id == parent.span_id

    def test_end_span(self):
        """结束 Span"""
        tracer = Tracer()
        tracer.start_trace()
        span = tracer.start_span("test")
        tracer.end_span(span, SpanStatus.OK)
        assert span.duration > 0
        assert span.status == SpanStatus.OK

    def test_end_span_with_error(self):
        """带错误结束 Span"""
        tracer = Tracer()
        tracer.start_trace()
        span = tracer.start_span("test")
        tracer.end_span(span, SpanStatus.ERROR, error="connection refused")
        assert span.status == SpanStatus.ERROR
        assert span.error == "connection refused"

    def test_slow_span_warning(self, caplog):
        """慢操作告警"""
        tracer = Tracer(slow_threshold=0.01)
        tracer.start_trace()
        span = tracer.start_span("slow_op")
        import time
        time.sleep(0.02)
        with caplog.at_level("WARNING"):
            tracer.end_span(span)
        assert "Slow span" in caplog.text

    def test_get_trace(self):
        """查询追踪记录"""
        tracer = Tracer()
        ctx = tracer.start_trace(trace_id="t1")
        tracer.start_span("a")
        tracer.start_span("b")
        result = tracer.get_trace("t1")
        assert result is not None
        assert len(result.spans) == 2

    def test_trace_duration(self):
        """追踪总时长"""
        tracer = Tracer()
        tracer.start_trace()
        s1 = tracer.start_span("a")
        tracer.end_span(s1)
        ctx = tracer.get_current_trace()
        assert ctx.duration > 0

    def test_trace_to_dict(self):
        """追踪序列化"""
        tracer = Tracer()
        ctx = tracer.start_trace(trace_id="t1")
        span = tracer.start_span("test")
        tracer.end_span(span, SpanStatus.OK)
        d = ctx.to_dict()
        assert d["trace_id"] == "t1"
        assert d["span_count"] == 1
        assert d["spans"][0]["status"] == "ok"

    def test_stats(self):
        """统计信息"""
        tracer = Tracer()
        tracer.start_trace()
        tracer.start_span("a")
        tracer.start_span("b")
        stats = tracer.get_stats()
        assert stats["total_traces"] == 1
        assert stats["total_spans"] == 2

    def test_clear(self):
        """清除追踪"""
        tracer = Tracer()
        tracer.start_trace()
        tracer.clear()
        assert tracer.get_current_trace() is None
        assert tracer.get_stats()["active_traces"] == 0


class TestMetricsCollector:
    """指标收集器测试"""

    def test_counter(self):
        """计数器"""
        m = MetricsCollector()
        m.inc_counter("requests")
        m.inc_counter("requests")
        m.inc_counter("requests", amount=3)
        assert m.get_counter("requests") == 5.0

    def test_counter_with_tags(self):
        """带标签的计数器"""
        m = MetricsCollector()
        m.inc_counter("requests", tags={"status": "200"})
        m.inc_counter("requests", tags={"status": "200"})
        m.inc_counter("requests", tags={"status": "500"})
        assert m.get_counter("requests", tags={"status": "200"}) == 2.0
        assert m.get_counter("requests", tags={"status": "500"}) == 1.0

    def test_histogram(self):
        """直方图"""
        m = MetricsCollector()
        for v in [0.1, 0.2, 0.3, 0.4, 0.5]:
            m.record_histogram("latency", v)
        metrics = m.get_metrics()
        h = metrics["histograms"]["latency"]
        assert h["count"] == 5
        assert h["min"] == 0.1
        assert h["max"] == 0.5
        assert h["avg"] == 0.3

    def test_histogram_percentiles(self):
        """直方图百分位"""
        m = MetricsCollector()
        for i in range(100):
            m.record_histogram("latency", float(i))
        metrics = m.get_metrics()
        h = metrics["histograms"]["latency"]
        assert h["p50"] == 50.0
        assert h["p95"] == 95.0

    def test_gauge(self):
        """仪表盘"""
        m = MetricsCollector()
        m.set_gauge("queue_depth", 42)
        assert m.get_gauge("queue_depth") == 42.0
        m.inc_gauge("queue_depth", 8)
        assert m.get_gauge("queue_depth") == 50.0
        m.dec_gauge("queue_depth", 10)
        assert m.get_gauge("queue_depth") == 40.0

    def test_gauge_with_tags(self):
        """带标签的仪表盘"""
        m = MetricsCollector()
        m.set_gauge("circuit_state", 1, tags={"provider": "openai"})
        m.set_gauge("circuit_state", 0, tags={"provider": "anthropic"})
        assert m.get_gauge("circuit_state", tags={"provider": "openai"}) == 1.0
        assert m.get_gauge("circuit_state", tags={"provider": "anthropic"}) == 0.0

    def test_get_metrics_full(self):
        """获取全部指标"""
        m = MetricsCollector()
        m.inc_counter("requests", tags={"method": "chat"})
        m.record_histogram("latency", 0.5)
        m.set_gauge("connections", 3)
        metrics = m.get_metrics()
        assert "counters" in metrics
        assert "histograms" in metrics
        assert "gauges" in metrics
        assert len(metrics["counters"]) == 1
        assert len(metrics["histograms"]) == 1
        assert len(metrics["gauges"]) == 1

    def test_reset(self):
        """重置"""
        m = MetricsCollector()
        m.inc_counter("requests")
        m.record_histogram("latency", 0.5)
        m.set_gauge("connections", 3)
        m.reset()
        metrics = m.get_metrics()
        assert metrics["counters"] == {}
        assert metrics["histograms"] == {}
        assert metrics["gauges"] == {}

    def test_histogram_max_values(self):
        """直方图最大值限制"""
        m = MetricsCollector()
        for i in range(1500):
            m.record_histogram("test", float(i))
        metrics = m.get_metrics()
        assert metrics["histograms"]["test"]["count"] == 1000

    def test_default_zero(self):
        """未设置的指标返回 0"""
        m = MetricsCollector()
        assert m.get_counter("nonexistent") == 0.0
        assert m.get_gauge("nonexistent") == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
