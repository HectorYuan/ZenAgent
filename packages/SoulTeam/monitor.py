"""集群监控采集 (M10 Phase S) — 9 指标"""
import time
from dataclasses import dataclass, field

@dataclass
class ClusterMetrics:
    total_agents: int = 16
    online_agents: int = 0
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_response_ms: float = 0.0
    bagua_energy_avg: float = 100.0
    chain_success_rate: float = 1.0
    uptime_seconds: float = 0.0
    start_time: float = field(default_factory=time.time)

    def snapshot(self) -> dict:
        self.uptime_seconds = time.time() - self.start_time
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

class ClusterMonitor:
    def __init__(self):
        self.metrics = ClusterMetrics()

    def collect(self) -> dict:
        return self.metrics.snapshot()

    def record_task(self, success: bool, latency_ms: float):
        self.metrics.active_tasks += 1
        if success:
            self.metrics.completed_tasks += 1
        else:
            self.metrics.failed_tasks += 1
        n = max(self.metrics.completed_tasks + self.metrics.failed_tasks, 1)
        self.metrics.avg_response_ms = (self.metrics.avg_response_ms * (n-1) + latency_ms) / n
        self.metrics.active_tasks = max(0, self.metrics.active_tasks - 1)

    def record_chain(self, success: bool):
        n = max(self.metrics.completed_tasks, 1)
        self.metrics.chain_success_rate = (self.metrics.chain_success_rate * (n-1) + (1.0 if success else 0)) / n
