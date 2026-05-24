"""
四维评分路由 (M10 Phase B)

设计依据: 智能体集群运行机制 v1.2

Score = Capability×0.4 + Availability×0.3 + Load×0.2 + Specialty×0.1
"""

from typing import Optional
from .registry import AgentRegistry, AgentProfile


class FourDimensionRouter:
    """
    四维评分路由器

    维度权重:
    - Capability (能力匹配): 40% — 关键词交集 × 能力数
    - Availability (可用性): 30% — 在线 + 空闲槽位
    - Load (当前负载): 20% — 1 - active_tasks/max_concurrent
    - Specialty (卦位专精度): 10% — 卦位+团队匹配加分
    """

    W_CAPABILITY = 0.4
    W_AVAILABILITY = 0.3
    W_LOAD = 0.2
    W_SPECIALTY = 0.1

    def __init__(self, registry: Optional[AgentRegistry] = None):
        self.registry = registry or AgentRegistry()
        self._loads: dict[str, int] = {}  # agent_id → active_tasks

    def set_load(self, agent_id: str, active_tasks: int):
        self._loads[agent_id] = max(0, active_tasks)

    def get_load(self, agent_id: str) -> int:
        return self._loads.get(agent_id, 0)

    def score(self, agent: AgentProfile, keywords: list[str]) -> float:
        """四维综合评分"""
        # 1. Capability: 关键词匹配
        cap_hits = sum(1 for kw in keywords
                       if any(kw.lower() in c.lower() for c in agent.capabilities))
        cap_score = min(cap_hits / max(len(keywords), 1), 1.0)

        # 2. Availability: 在线 + 槽位
        online = 1.0 if self.registry.is_online(agent.agent_id) else 0.3
        avail_score = online

        # 3. Load: 空闲率
        active = self._loads.get(agent.agent_id, 0)
        max_conc = max(agent.max_concurrent_tasks, 1)
        load_score = max(0.0, 1.0 - active / max_conc)

        # 4. Specialty: 卦位 + 团队加分
        spec_score = 0.5  # baseline
        leader = self.registry.get_team(agent.team)
        if leader and agent.agent_id == leader.get("leader"):
            spec_score = 1.0

        return (
            cap_score * self.W_CAPABILITY +
            avail_score * self.W_AVAILABILITY +
            load_score * self.W_LOAD +
            spec_score * self.W_SPECIALTY
        )

    def route(self, keywords: list[str], team_id: Optional[str] = None,
              top_k: int = 3) -> list[tuple[AgentProfile, float]]:
        """
        路由: 返回 Top-K Agent + 评分

        Args:
            keywords: 任务关键词
            team_id: 限定团队 (可选)
            top_k: 返回 Top-K

        Returns:
            [(AgentProfile, score), ...]
        """
        if team_id:
            candidates = self.registry.get_team_members(team_id)
        else:
            candidates = list(self.registry.all_agents.values())

        if not candidates:
            return []

        scored = [(a, self.score(a, keywords)) for a in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def best(self, keywords: list[str], team_id: Optional[str] = None) -> Optional[AgentProfile]:
        results = self.route(keywords, team_id, top_k=1)
        return results[0][0] if results else None
