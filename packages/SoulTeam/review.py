"""评审角色系统 (M10 Phase R) — 6 角色 + 加权聚合 + Z 分数"""
import math
from dataclasses import dataclass, field

@dataclass
class ReviewRole:
    name: str; weight: float; expertise: list[str]

ROLES = [
    ReviewRole("产品经理", 0.25, ["feasibility", "value"]),
    ReviewRole("架构师", 0.20, ["architecture", "scalability"]),
    ReviewRole("设计师", 0.15, ["design", "ux"]),
    ReviewRole("开发者", 0.15, ["implementation", "complexity"]),
    ReviewRole("测试工程师", 0.15, ["quality", "coverage"]),
    ReviewRole("评审专家", 0.10, ["overall", "risk"]),
]

class ReviewAggregator:
    def aggregate(self, role_scores: dict[str, float]) -> dict:
        total_w = sum(r.weight for r in ROLES if r.name in role_scores)
        if total_w == 0: return {"score": 0, "decision": "REJECT"}
        weighted = sum(role_scores.get(r.name, 0) * r.weight for r in ROLES)
        score = weighted / total_w
        scores_list = list(role_scores.values())
        mean = sum(scores_list) / len(scores_list)
        std = math.sqrt(sum((s - mean) ** 2 for s in scores_list) / len(scores_list)) if len(scores_list) > 1 else 1
        anomalies = [r for r, s in role_scores.items() if abs(s - mean) / max(std, 0.01) > 2.0]
        decision = "APPROVE" if score >= 0.7 else "CONDITIONAL" if score >= 0.5 else "REVISE"
        return {"score": round(score, 3), "decision": decision, "anomalies": anomalies}
