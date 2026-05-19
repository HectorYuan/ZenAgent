"""
指标收集器

设计依据: E2E_OPTIMIZATION_DESIGN §模块8 - 关键节点 Metrics

预定义指标:
- llm_request_total / llm_request_duration_seconds
- llm_tokens_total
- circuit_breaker_state
- rate_limiter_rejected_total
- hook_duration_seconds
"""

import time
import logging
import threading
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"        # 只增不减的计数器
    HISTOGRAM = "histogram"    # 分布统计（延迟、大小）
    GAUGE = "gauge"            # 可增可减的仪表盘


@dataclass
class CounterData:
    """计数器数据"""
    value: float = 0.0

    def inc(self, amount: float = 1.0):
        self.value += amount

    def to_dict(self) -> dict:
        return {"value": self.value}


@dataclass
class HistogramData:
    """直方图数据"""
    values: List[float] = field(default_factory=list)

    def record(self, value: float):
        self.values.append(value)
        # 只保留最近 1000 个值
        if len(self.values) > 1000:
            self.values = self.values[-1000:]

    def to_dict(self) -> dict:
        if not self.values:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}
        sorted_vals = sorted(self.values)
        count = len(sorted_vals)
        return {
            "count": count,
            "sum": round(sum(sorted_vals), 4),
            "avg": round(sum(sorted_vals) / count, 4),
            "min": round(sorted_vals[0], 4),
            "max": round(sorted_vals[-1], 4),
            "p50": round(sorted_vals[count // 2], 4),
            "p95": round(sorted_vals[int(count * 0.95)], 4),
            "p99": round(sorted_vals[int(count * 0.99)], 4),
        }


@dataclass
class GaugeData:
    """仪表盘数据"""
    value: float = 0.0

    def set(self, value: float):
        self.value = value

    def inc(self, amount: float = 1.0):
        self.value += amount

    def dec(self, amount: float = 1.0):
        self.value -= amount

    def to_dict(self) -> dict:
        return {"value": self.value}


class MetricsCollector:
    """
    指标收集器

    线程安全的指标收集，支持 Counter / Histogram / Gauge 三种类型。
    标签(tags)用于多维度聚合。
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._counters: Dict[str, CounterData] = {}
        self._histograms: Dict[str, HistogramData] = {}
        self._gauges: Dict[str, GaugeData] = {}

    def _make_key(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """生成指标键名（含标签）"""
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}{{{tag_str}}}"

    def inc_counter(self, name: str, amount: float = 1.0, tags: Optional[Dict[str, str]] = None):
        """增加计数器"""
        key = self._make_key(name, tags)
        with self._lock:
            if key not in self._counters:
                self._counters[key] = CounterData()
            self._counters[key].inc(amount)

    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """记录直方图值"""
        key = self._make_key(name, tags)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = HistogramData()
            self._histograms[key].record(value)

    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """设置仪表盘值"""
        key = self._make_key(name, tags)
        with self._lock:
            if key not in self._gauges:
                self._gauges[key] = GaugeData()
            self._gauges[key].set(value)

    def inc_gauge(self, name: str, amount: float = 1.0, tags: Optional[Dict[str, str]] = None):
        """增加仪表盘值"""
        key = self._make_key(name, tags)
        with self._lock:
            if key not in self._gauges:
                self._gauges[key] = GaugeData()
            self._gauges[key].inc(amount)

    def dec_gauge(self, name: str, amount: float = 1.0, tags: Optional[Dict[str, str]] = None):
        """减少仪表盘值"""
        key = self._make_key(name, tags)
        with self._lock:
            if key not in self._gauges:
                self._gauges[key] = GaugeData()
            self._gauges[key].dec(amount)

    def get_metrics(self) -> dict:
        """获取所有指标"""
        with self._lock:
            return {
                "counters": {k: v.to_dict() for k, v in self._counters.items()},
                "histograms": {k: v.to_dict() for k, v in self._histograms.items()},
                "gauges": {k: v.to_dict() for k, v in self._gauges.items()},
            }

    def get_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """获取计数器值"""
        key = self._make_key(name, tags)
        with self._lock:
            if key in self._counters:
                return self._counters[key].value
            return 0.0

    def get_gauge(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """获取仪表盘值"""
        key = self._make_key(name, tags)
        with self._lock:
            if key in self._gauges:
                return self._gauges[key].value
            return 0.0

    def reset(self):
        """重置所有指标"""
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._gauges.clear()
