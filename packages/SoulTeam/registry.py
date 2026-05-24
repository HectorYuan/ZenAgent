"""
SoulTeam Agent 注册表 (M10 Phase A)

设计依据: 智能体集群运行机制 v1.2 + 子智能体运行机制 v1.0

16 Agent (SUB-1.1~3.9) + 4 团队
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class AgentCategory(str, Enum):
    BUSINESS = "business"       # 业务类 1.1-1.4
    MANAGEMENT = "management"   # 管理类 2.1-2.3
    PROFESSIONAL = "professional"  # 专业类 3.1-3.9


class BaguaPosition(str, Enum):
    QIAN = "乾☰"    # 天 — 领导/决策
    KUN = "坤☷"     # 地 — 执行/承载
    ZHEN = "震☳"    # 雷 — 启动/变革
    XUN = "巽☴"     # 风 — 传播/渗透
    KAN = "坎☵"     # 水 — 风险/深入
    LI = "離☲"      # 火 — 创意/照亮
    GEN = "艮☶"     # 山 — 稳定/沉淀
    DUI = "兌☱"     # 泽 — 沟通/协调


@dataclass
class AgentProfile:
    """Agent 画像"""
    agent_id: str           # SUB-1.1 等
    name: str               # 中文名
    category: AgentCategory
    bagua: BaguaPosition
    capabilities: list[str]
    team: str               # 所属团队
    priority: int = 3
    max_concurrent_tasks: int = 3
    schedule_binding: str = ""  # 日程绑定 (如 "invest_strategy")
    swagger_id: str = ""        # SwarmFly 集成 ID

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id, "name": self.name,
            "category": self.category.value, "bagua": self.bagua.value,
            "capabilities": self.capabilities, "team": self.team,
            "priority": self.priority,
            "max_concurrent_tasks": self.max_concurrent_tasks,
        }


# ---- 16 Agent 注册表 ----
AGENT_REGISTRY: dict[str, AgentProfile] = {
    # 业务类 (4)
    "SUB-1.1": AgentProfile("SUB-1.1", "投资策略师", AgentCategory.BUSINESS,
                            BaguaPosition.QIAN, ["invest", "strategy", "analyze"],
                            "TEAM-INVEST", schedule_binding="invest_strategy"),
    "SUB-1.2": AgentProfile("SUB-1.2", "市场研究员", AgentCategory.BUSINESS,
                            BaguaPosition.KAN, ["market", "research", "data"],
                            "TEAM-INVEST", schedule_binding="market_research"),
    "SUB-1.3": AgentProfile("SUB-1.3", "风险分析师", AgentCategory.BUSINESS,
                            BaguaPosition.LI, ["risk", "analyze", "model"],
                            "TEAM-INVEST", schedule_binding="risk_analysis"),
    "SUB-1.4": AgentProfile("SUB-1.4", "组合优化师", AgentCategory.BUSINESS,
                            BaguaPosition.GEN, ["portfolio", "optimize", "balance"],
                            "TEAM-INVEST", schedule_binding="portfolio_optimize"),

    # 管理类 (3)
    "SUB-2.1": AgentProfile("SUB-2.1", "任务协调者", AgentCategory.MANAGEMENT,
                            BaguaPosition.DUI, ["coordinate", "schedule", "dispatch"],
                            "TEAM-OPS", priority=1, schedule_binding="task_coordinate"),
    "SUB-2.2": AgentProfile("SUB-2.2", "质量审计师", AgentCategory.MANAGEMENT,
                            BaguaPosition.GEN, ["audit", "quality", "review"],
                            "TEAM-OPS", schedule_binding="quality_audit"),
    "SUB-2.3": AgentProfile("SUB-2.3", "资源配置师", AgentCategory.MANAGEMENT,
                            BaguaPosition.KUN, ["resource", "allocate", "plan"],
                            "TEAM-OPS", schedule_binding="resource_plan"),

    # 专业类 (9)
    "SUB-3.1": AgentProfile("SUB-3.1", "架构设计师", AgentCategory.PROFESSIONAL,
                            BaguaPosition.QIAN, ["architecture", "design", "system"],
                            "TEAM-RD", schedule_binding="arch_design"),
    "SUB-3.2": AgentProfile("SUB-3.2", "后端工程师", AgentCategory.PROFESSIONAL,
                            BaguaPosition.KUN, ["backend", "api", "database"],
                            "TEAM-RD", schedule_binding="backend_dev"),
    "SUB-3.3": AgentProfile("SUB-3.3", "前端工程师", AgentCategory.PROFESSIONAL,
                            BaguaPosition.LI, ["frontend", "ui", "ux"],
                            "TEAM-RD", schedule_binding="frontend_dev"),
    "SUB-3.4": AgentProfile("SUB-3.4", "数据科学家", AgentCategory.PROFESSIONAL,
                            BaguaPosition.KAN, ["data", "ml", "analyze"],
                            "TEAM-RD", schedule_binding="data_science"),
    "SUB-3.5": AgentProfile("SUB-3.5", "测试工程师", AgentCategory.PROFESSIONAL,
                            BaguaPosition.ZHEN, ["test", "qa", "automation"],
                            "TEAM-RD", schedule_binding="test_engineer"),
    "SUB-3.6": AgentProfile("SUB-3.6", "DevOps 工程师", AgentCategory.PROFESSIONAL,
                            BaguaPosition.XUN, ["devops", "deploy", "monitor"],
                            "TEAM-RD", schedule_binding="devops_engineer"),
    "SUB-3.7": AgentProfile("SUB-3.7", "知识管理者", AgentCategory.PROFESSIONAL,
                            BaguaPosition.GEN, ["knowledge", "document", "learn"],
                            "TEAM-LEARN", schedule_binding="knowledge_mgmt"),
    "SUB-3.8": AgentProfile("SUB-3.8", "技能导师", AgentCategory.PROFESSIONAL,
                            BaguaPosition.DUI, ["teach", "mentor", "train"],
                            "TEAM-LEARN", schedule_binding="skill_mentor"),
    "SUB-3.9": AgentProfile("SUB-3.9", "创新研究员", AgentCategory.PROFESSIONAL,
                            BaguaPosition.LI, ["innovate", "research", "prototype"],
                            "TEAM-LEARN", schedule_binding="innovation_lab"),
}

# ---- 4 团队定义 ----
TEAMS = {
    "TEAM-INVEST": {
        "name": "投研团队", "members": ["SUB-1.1", "SUB-1.2", "SUB-1.3", "SUB-1.4"],
        "leader": "SUB-1.1", "bagua_focus": [BaguaPosition.QIAN, BaguaPosition.KAN],
    },
    "TEAM-RD": {
        "name": "研发团队", "members": ["SUB-3.1", "SUB-3.2", "SUB-3.3", "SUB-3.4", "SUB-3.5", "SUB-3.6"],
        "leader": "SUB-3.1", "bagua_focus": [BaguaPosition.KUN, BaguaPosition.ZHEN],
    },
    "TEAM-LEARN": {
        "name": "学习团队", "members": ["SUB-3.7", "SUB-3.8", "SUB-3.9"],
        "leader": "SUB-3.7", "bagua_focus": [BaguaPosition.GEN, BaguaPosition.DUI],
    },
    "TEAM-OPS": {
        "name": "运营团队", "members": ["SUB-2.1", "SUB-2.2", "SUB-2.3"],
        "leader": "SUB-2.1", "bagua_focus": [BaguaPosition.XUN, BaguaPosition.KAN],
    },
}


class AgentRegistry:
    """Agent 注册表管理器"""

    def __init__(self):
        self._agents: dict[str, AgentProfile] = dict(AGENT_REGISTRY)
        self._teams: dict[str, dict] = dict(TEAMS)
        self._online: set[str] = set()

    def get(self, agent_id: str) -> Optional[AgentProfile]:
        return self._agents.get(agent_id)

    def get_team(self, team_id: str) -> Optional[dict]:
        return self._teams.get(team_id)

    def get_team_members(self, team_id: str) -> list[AgentProfile]:
        team = self._teams.get(team_id, {})
        return [self._agents[aid] for aid in team.get("members", []) if aid in self._agents]

    def get_by_category(self, category: AgentCategory) -> list[AgentProfile]:
        return [a for a in self._agents.values() if a.category == category]

    def get_by_bagua(self, position: BaguaPosition) -> list[AgentProfile]:
        return [a for a in self._agents.values() if a.bagua == position]

    def get_by_capability(self, keyword: str) -> list[AgentProfile]:
        kw = keyword.lower()
        return [a for a in self._agents.values()
                if any(kw in cap.lower() for cap in a.capabilities)]

    def set_online(self, agent_id: str):
        self._online.add(agent_id)

    def set_offline(self, agent_id: str):
        self._online.discard(agent_id)

    def is_online(self, agent_id: str) -> bool:
        return agent_id in self._online

    def list_online(self) -> list[str]:
        return list(self._online)

    @property
    def all_agents(self) -> dict[str, AgentProfile]:
        return dict(self._agents)

    @property
    def all_teams(self) -> dict[str, dict]:
        return dict(self._teams)

    def get_stats(self) -> dict:
        return {
            "total_agents": len(self._agents),
            "online": len(self._online),
            "total_teams": len(self._teams),
            "by_category": {c.value: len(self.get_by_category(c)) for c in AgentCategory},
        }
