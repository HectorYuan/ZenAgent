"""SwarmFly↔SoulTeam 桥接 (M10 Phase V)"""
from ..SwarmFly.swarmfly import SwarmFly
from .registry import AgentRegistry

class SoulTeamBridge:
    """双向桥接: SwarmFly L4 ↔ SoulTeam L5"""
    def __init__(self, swarmfly: SwarmFly = None, registry: AgentRegistry = None):
        self._sf = swarmfly or SwarmFly()
        self._reg = registry or AgentRegistry()

    def sync_agents(self):
        """将 SoulTeam 注册的 Agent 同步到 SwarmFly"""
        for aid, profile in self._reg.all_agents.items():
            self._sf.register_agent(aid, role=profile.category.value)

    def get_swarm_status(self) -> dict:
        return {"swarmfly": self._sf.get_status(), "soulteam": self._reg.get_stats()}
