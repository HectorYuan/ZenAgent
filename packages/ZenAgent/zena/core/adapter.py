"""
ZenaDataAdapter — 统一数据访问层

所有 CLI/TUI 命令通过此适配器访问底层系统。
封装 L0-L4 层 API，提供统一的数据获取接口。
"""

import asyncio
from typing import Optional, Any, List, Dict


class ZenaDataAdapter:
    """
    ZenAgent 统一数据适配器

    封装所有底层系统的访问，TUI 屏幕不直接调用系统 API。
    模式: ZenSkill TuiDataAdapter
    """

    def __init__(self, agent_id: str = "zena-default"):
        self.agent_id = agent_id
        self._agent = None
        self._runtime = None
        self._swarmfly = None

    # ---------- Lazy Init ----------

    def _get_agent(self):
        if self._agent is None:
            from packages.ZenAgent.core import ZenAgent, ZenAgentConfig
            config = ZenAgentConfig(
                agent_id=self.agent_id,
                enable_llm=True,
                llm_provider="mock",
                enable_memory=True,
                enable_awakening=False,
                enable_collaboration=False,
            )
            self._agent = ZenAgent(config)
        return self._agent

    def _get_runtime(self):
        if self._runtime is None:
            from packages.Runtime.runtime import Runtime, RuntimeConfig
            self._runtime = Runtime(RuntimeConfig())
        return self._runtime

    def _get_swarmfly(self):
        if self._swarmfly is None:
            from packages.SwarmFly.swarmfly import SwarmFly
            self._swarmfly = SwarmFly()
        return self._swarmfly

    # ---------- Chat ----------

    async def chat(self, prompt: str, use_history: bool = True,
                   system_prompt: str = None) -> dict:
        agent = self._get_agent()
        response = await agent.think(prompt, system_prompt=system_prompt,
                                      use_history=use_history)
        return {
            "content": response.content if response else "",
            "provider": response.provider if response else "none",
            "model": response.model if response else "none",
            "usage": response.usage if response else {},
            "cost": response.cost if response else 0,
        }

    async def clear_history(self):
        agent = self._get_agent()
        agent.clear_conversation()

    # ---------- Status ----------

    def get_full_status(self) -> dict:
        agent = self._get_agent()
        return agent.get_full_status()

    def get_system_health(self) -> dict:
        """各子系统健康摘要"""
        status = self.get_full_status()
        health = {
            "agent": {"name": status.get("agent_name", ""), "healthy": True},
            "llm": {"healthy": status.get("intent_router", {}) != {}},
            "memory": {"healthy": status.get("memory_layers", {}) != {}},
            "personality": {"healthy": True},
            "runtime": {"healthy": True},
        }
        return health

    # ---------- Memory ----------

    def memory_stats(self) -> dict:
        agent = self._get_agent()
        mem = agent.memory
        if mem:
            return mem.get_stats()
        return {"error": "Memory not initialized"}

    def memory_search(self, query: str, limit: int = 10) -> list[dict]:
        agent = self._get_agent()
        results = agent.recall(query, limit=limit)
        return [
            {"id": getattr(m, "memory_id", ""),
             "content": getattr(m, "content", str(m)),
             "type": str(getattr(m, "memory_type", "")),
             "importance": str(getattr(m, "importance", ""))}
            for m in results
        ]

    def memory_store(self, content: str, mem_type: str = "EPISODIC") -> str:
        agent = self._get_agent()
        from packages.MetaSoul.memory.meta_soul import MemoryType
        return agent.remember(content, memory_type=getattr(MemoryType, mem_type, MemoryType.EPISODIC))

    # ---------- Personality ----------

    def personality_traits(self) -> dict:
        agent = self._get_agent()
        pers = agent.personality
        if pers:
            return pers.get_traits()
        return {}

    def personality_set(self, trait: str, value: float):
        agent = self._get_agent()
        pers = agent.personality
        if pers:
            pers.set_trait(trait, max(0.0, min(1.0, value)))

    # ---------- Provider ----------

    def provider_list(self) -> list[str]:
        agent = self._get_agent()
        if agent.llm_client:
            return agent.llm_client.provider_factory.get_available_providers()
        return []

    def provider_health(self) -> dict:
        agent = self._get_agent()
        if agent.llm_client and hasattr(agent.llm_client, 'provider_chain'):
            return agent.llm_client.get_chain_health()
        return {}

    # ---------- Knowledge ----------

    def knowledge_stats(self) -> dict:
        agent = self._get_agent()
        if agent.memory and hasattr(agent.memory, 'store_v2') and agent.memory.store_v2:
            if hasattr(agent.memory, 'pipeline') and agent.memory.pipeline:
                return agent.memory.pipeline.get_kb_stats()
        return {"total_triples": 0, "total_entities": 0}

    def knowledge_search(self, query: str, top_k: int = 5) -> list[dict]:
        """搜索 SPO 三元组"""
        agent = self._get_agent()
        if agent.memory and hasattr(agent.memory, 'store_v2') and agent.memory.store_v2:
            results = agent.memory.store_v2.search_l3(query, top_k)
            return results
        return []

    # ---------- Agent Management (SwarmFly) ----------

    def agents_list(self) -> list[str]:
        sf = self._get_swarmfly()
        return sf.get_registered_agents()

    def agent_register(self, agent_id: str, role: str = "worker") -> bool:
        sf = self._get_swarmfly()
        return sf.register_agent(agent_id, role)

    # ---------- Cache ----------

    def cache_stats(self) -> dict:
        agent = self._get_agent()
        if agent.llm_client:
            return agent.llm_client.get_cache_health()
        return {}

    # ---------- Session (Runtime) ----------

    def sessions_list(self) -> list[dict]:
        rt = self._get_runtime()
        active = rt.list_active_sessions()
        return [{"id": s.session_id, "user": s.user_id, "state": str(s.state)} for s in active]
