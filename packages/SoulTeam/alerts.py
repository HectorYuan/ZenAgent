"""集群监控告警 (M10 Phase T)"""
from enum import Enum
from dataclasses import dataclass

class AlertLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class AlertRule:
    name: str; metric: str; threshold: float; level: AlertLevel; message: str

RULES = [
    AlertRule("no_online", "online_agents", 0, AlertLevel.CRITICAL, "所有 Agent 离线"),
    AlertRule("high_fail", "failed_tasks", 5, AlertLevel.HIGH, "失败任务过多"),
    AlertRule("low_success", "chain_success_rate", 0.5, AlertLevel.MEDIUM, "协作链成功率 < 50%"),
    AlertRule("high_latency", "avg_response_ms", 5000, AlertLevel.MEDIUM, "平均延迟 > 5s"),
    AlertRule("low_energy", "bagua_energy_avg", 20, AlertLevel.LOW, "八卦能量低"),
]

class AlertManager:
    def __init__(self): self._fired: list[dict] = []
    def evaluate(self, metrics: dict) -> list[dict]:
        alerts = []
        for rule in RULES:
            val = metrics.get(rule.metric, 0)
            if (rule.threshold == 0 and val == 0) or (rule.threshold > 0 and val < rule.threshold):
                alerts.append({"rule": rule.name, "level": rule.level.value, "message": rule.message})
        self._fired.extend(alerts)
        return alerts
