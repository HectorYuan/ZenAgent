"""
FLY-3 趋势层 - 数据采集模块
Data Collection Module
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import aiohttp

from implementation.shared.logging import get_logger

logger = get_logger("DataCollector")


@dataclass
class CollectedData:
    """采集数据"""
    source: str
    data_type: str
    timestamp: datetime
    raw_data: Any
    processed_data: Optional[Dict] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectionTask:
    """采集任务"""
    task_id: str
    source: str
    endpoint: str
    interval: int  # 秒
    last_collection: Optional[datetime] = None
    enabled: bool = True


class ExternalAPICollector:
    """外部API采集器"""
    
    def __init__(self):
        self._tasks: Dict[str, CollectionTask] = {}
        self._collectors: Dict[str, asyncio.Task] = {}
        self._data_buffer: Dict[str, List[CollectedData]] = {}
        
        self.config = {
            "max_retries": 3,
            "timeout": 30,
            "rate_limit": 100,  # 每分钟请求数
            "batch_size": 10
        }
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False
    
    async def start(self):
        """启动采集器"""
        self._session = aiohttp.ClientSession()
        self._running = True
        logger.info("外部API采集器已启动")
    
    async def stop(self):
        """停止采集器"""
        self._running = False
        
        # 取消所有采集任务
        for task in self._collectors.values():
            task.cancel()
        
        if self._session:
            await self._session.close()
        
        logger.info("外部API采集器已停止")
    
    def add_task(
        self,
        task_id: str,
        source: str,
        endpoint: str,
        interval: int = 60
    ):
        """添加采集任务"""
        task = CollectionTask(
            task_id=task_id,
            source=source,
            endpoint=endpoint,
            interval=interval
        )
        self._tasks[task_id] = task
        
        # 启动采集协程
        if self._running:
            self._start_collection(task)
    
    def _start_collection(self, task: CollectionTask):
        """启动采集"""
        async def collect_loop():
            while self._running and task.enabled:
                try:
                    data = await self._fetch_data(task)
                    self._store_data(task.source, data)
                    task.last_collection = datetime.now()
                except Exception as e:
                    logger.error(f"采集失败: {task.task_id}, {e}")
                
                await asyncio.sleep(task.interval)
        
        self._collectors[task.task_id] = asyncio.create_task(collect_loop())
    
    async def _fetch_data(self, task: CollectionTask) -> CollectedData:
        """获取数据"""
        if not self._session:
            raise RuntimeError("Session not initialized")
        
        async with self._session.get(
            task.endpoint,
            timeout=aiohttp.ClientTimeout(total=self.config["timeout"])
        ) as response:
            response.raise_for_status()
            data = await response.json()
            
            return CollectedData(
                source=task.source,
                data_type="api",
                timestamp=datetime.now(),
                raw_data=data
            )
    
    def _store_data(self, source: str, data: CollectedData):
        """存储数据"""
        if source not in self._data_buffer:
            self._data_buffer[source] = []
        
        self._data_buffer[source].append(data)
        
        # 限制缓冲区大小
        if len(self._data_buffer[source]) > 1000:
            self._data_buffer[source] = self._data_buffer[source][-1000:]
    
    async def trigger_collection(self, source: str) -> Optional[CollectedData]:
        """触发式采集"""
        task = next((t for t in self._tasks.values() if t.source == source), None)
        if not task:
            return None
        
        return await self._fetch_data(task)
    
    def get_latest_data(self, source: str, limit: int = 10) -> List[CollectedData]:
        """获取最新数据"""
        return self._data_buffer.get(source, [])[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_tasks": len(self._tasks),
            "active_collectors": len(self._collectors),
            "buffer_sizes": {k: len(v) for k, v in self._data_buffer.items()}
        }


class InternalDataCollector:
    """内部数据采集器"""
    
    def __init__(self):
        self._metrics: Dict[str, List] = {}
        self._callbacks: List[Callable] = []
        
        # 默认采集指标
        self._default_metrics = [
            "request_count",
            "response_time",
            "error_rate",
            "active_agents",
            "queue_depth",
            "cpu_usage",
            "memory_usage"
        ]
    
    def record_metric(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict] = None
    ):
        """记录指标"""
        if metric_name not in self._metrics:
            self._metrics[metric_name] = []
        
        entry = {
            "timestamp": datetime.now(),
            "value": value,
            "tags": tags or {}
        }
        
        self._metrics[metric_name].append(entry)
        
        # 限制历史长度
        if len(self._metrics[metric_name]) > 10000:
            self._metrics[metric_name] = self._metrics[metric_name][-5000:]
    
    def get_metrics(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        """获取指标"""
        metrics = self._metrics.get(metric_name, [])
        
        if start_time:
            metrics = [m for m in metrics if m["timestamp"] >= start_time]
        if end_time:
            metrics = [m for m in metrics if m["timestamp"] <= end_time]
        
        return metrics
    
    def get_aggregated_metrics(
        self,
        metric_name: str,
        window: timedelta = timedelta(minutes=5)
    ) -> Dict[str, float]:
        """获取聚合指标"""
        metrics = self._metrics.get(metric_name, [])
        if not metrics:
            return {}
        
        # 按时间窗口聚合
        now = datetime.now()
        cutoff = now - window
        
        recent = [m["value"] for m in metrics if m["timestamp"] >= cutoff]
        
        if not recent:
            return {}
        
        import statistics
        
        return {
            "count": len(recent),
            "mean": statistics.mean(recent),
            "min": min(recent),
            "max": max(recent),
            "stdev": statistics.stdev(recent) if len(recent) > 1 else 0,
            "p50": statistics.median(recent),
            "p95": self._percentile(recent, 95),
            "p99": self._percentile(recent, 99)
        }
    
    def _percentile(self, values: List[float], p: float) -> float:
        """计算百分位数"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * p / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def record_behavior(
        self,
        agent_id: str,
        action: str,
        metadata: Optional[Dict] = None
    ):
        """记录行为"""
        behavior_key = f"behavior_{agent_id}"
        
        entry = {
            "timestamp": datetime.now(),
            "action": action,
            "metadata": metadata or {}
        }
        
        self.record_metric(behavior_key, 1.0, {"action": action})
    
    def subscribe(self, callback: Callable):
        """订阅数据更新"""
        self._callbacks.append(callback)


class RealTimeMonitor:
    """实时监控"""
    
    def __init__(self):
        self._thresholds: Dict[str, Dict] = {}
        self._alerts: List[Dict] = []
        self._subscribers: List[Callable] = []
        
        self.config = {
            "check_interval": 10,  # 秒
            "consecutive_violations": 3  # 连续违规次数
        }
    
    def set_threshold(
        self,
        metric_name: str,
        threshold: float,
        comparison: str = "gt",  # gt, lt, eq
        severity: str = "warning"
    ):
        """设置阈值"""
        self._thresholds[metric_name] = {
            "threshold": threshold,
            "comparison": comparison,
            "severity": severity,
            "violations": 0
        }
    
    def check_value(self, metric_name: str, value: float) -> Optional[Dict]:
        """检查值是否超过阈值"""
        if metric_name not in self._thresholds:
            return None
        
        threshold_info = self._thresholds[metric_name]
        threshold = threshold_info["threshold"]
        comparison = threshold_info["comparison"]
        
        violated = False
        
        if comparison == "gt" and value > threshold:
            violated = True
        elif comparison == "lt" and value < threshold:
            violated = True
        elif comparison == "eq" and abs(value - threshold) < 0.001:
            violated = True
        
        if violated:
            threshold_info["violations"] += 1
            
            if threshold_info["violations"] >= self.config["consecutive_violations"]:
                alert = {
                    "metric": metric_name,
                    "value": value,
                    "threshold": threshold,
                    "severity": threshold_info["severity"],
                    "timestamp": datetime.now()
                }
                self._alerts.append(alert)
                self._notify_subscribers(alert)
                
                # 重置计数
                threshold_info["violations"] = 0
                
                return alert
        else:
            # 重置计数
            threshold_info["violations"] = 0
        
        return None
    
    def subscribe(self, callback: Callable):
        """订阅告警"""
        self._subscribers.append(callback)
    
    def _notify_subscribers(self, alert: Dict):
        """通知订阅者"""
        for callback in self._subscribers:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"告警通知异常: {e}")
    
    def get_alerts(self, limit: int = 100) -> List[Dict]:
        """获取告警历史"""
        return self._alerts[-limit:]
