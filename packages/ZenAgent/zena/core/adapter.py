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
        import atexit
        atexit.register(self._cleanup)

    def _cleanup(self):
        """退出时清理资源（关闭 aiohttp session）"""
        import asyncio
        if self._agent and self._agent.llm_client:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    return  # 事件循环还在运行，不强行关闭
            except RuntimeError:
                return

    @staticmethod
    def _detect_available_provider() -> str:
        """自动检测可用的 LLM Provider，补全缺失的 env var"""
        import os
        # DeepSeek: 尝试 OpenAI 兼容端点 (deepseek 提供 /v1 兼容端点)
        for prefix in ["DEEPSEEK", "MIMO", "VOLC"]:
            token = os.getenv(f"{prefix}_ANTHROPIC_AUTH_TOKEN")
            if token and not os.getenv("OPENAI_API_KEY"):
                os.environ["OPENAI_API_KEY"] = token
                if not os.getenv("OPENAI_BASE_URL"):
                    os.environ["OPENAI_BASE_URL"] = "https://api.deepseek.com/v1"
                break
        # 优先级: openai > anthropic > modelnexus > mock
        if os.getenv("OPENAI_API_KEY"):
            return "openai"
        if os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_BASE_URL"):
            return "anthropic"
        if os.getenv("MODELNEXUS_API_KEY"):
            return "modelnexus"
        return "mock"

    # ---------- Lazy Init ----------

    @staticmethod
    def _detect_model(provider: str) -> str:
        """自动检测可用模型，并补全 env var"""
        import os
        import re
        model = os.getenv("ZENA_MODEL")  # CLI --model overlay
        if not model:
            model = os.getenv(f"{provider.upper()}_MODEL")
        if not model:
            model = os.getenv("DEEPSEEK_MODEL")
        if not model:
            model = os.getenv("MIMO_MODEL")
        # 清理模型名: 去掉 reasoning 标记 [1m], [2m] 等
        if model:
            model = re.sub(r'\[\d+m\]', '', model).strip()
        # 补全 {PROVIDER}_DEFAULT_MODEL（LLMInfra config 使用的 key）
        if model and not os.getenv(f"{provider.upper()}_DEFAULT_MODEL"):
            os.environ[f"{provider.upper()}_DEFAULT_MODEL"] = model
        if not model:
            model = "gpt-3.5-turbo"
        return model

    def _get_agent(self):
        if self._agent is None:
            from packages.ZenAgent.core import ZenAgent, ZenAgentConfig
            provider = self._detect_available_provider()
            model = self._detect_model(provider)
            config = ZenAgentConfig(
                agent_id=self.agent_id,
                enable_llm=True,
                llm_provider=provider,
                llm_model=model,
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

    async def chat_stream(self, prompt: str, use_history: bool = True,
                          system_prompt: str = None):
        """
        流式聊天 — 逐 token yield

        Yields:
            {"type": "token", "content": str}
            {"type": "done", "provider": str, "model": str, "usage": dict, "cost": float}
            {"type": "error", "message": str}
        """
        agent = self._get_agent()
        if not agent.llm_client:
            yield {"type": "error", "message": "LLM not initialized"}
            return

        messages = []
        if system_prompt:
            from packages.LLMInfra.core import Message, MessageRole
            messages.append(Message(role=MessageRole.SYSTEM, content=system_prompt))
        if use_history and agent.conversation_history:
            messages.extend(agent.conversation_history)
        from packages.LLMInfra.core import Message, MessageRole
        messages.append(Message(role=MessageRole.USER, content=prompt))

        full_content = ""
        try:
            async for chunk in agent.llm_client.chat_stream(messages=messages):
                full_content += chunk
                yield {"type": "token", "content": chunk}

            # 更新对话历史
            if use_history:
                agent._conversation_history.append(
                    Message(role=MessageRole.USER, content=prompt)
                )
                agent._conversation_history.append(
                    Message(role=MessageRole.ASSISTANT, content=full_content)
                )

            yield {"type": "done", "content": full_content,
                   "provider": "stream", "model": "stream",
                   "usage": {}, "cost": 0}
        except Exception as e:
            yield {"type": "error", "message": str(e)}
        finally:
            await self._close_provider_session()

    # ---------- Thinking Stream (Reasoning) ----------

    async def think_stream(self, prompt: str, use_history: bool = True,
                           system_prompt: str = None):
        """
        思考流式 — 含推理过程

        使用 chat_deep (CoT) 生成可折叠的推理+答案

        Yields:
            {"type": "reasoning", "content": str}
            {"type": "token", "content": str}
            {"type": "done", ...}
            {"type": "error", ...}
        """
        agent = self._get_agent()
        if not agent.llm_client:
            yield {"type": "error", "message": "LLM not initialized"}
            return

        # 对于需要推理的问题，先走 DeepPath 生成推理
        try:
            result = await self.chat(prompt, use_history=use_history,
                                     system_prompt=system_prompt)
            # 尝试检测推理标记
            content = result.get("content", "")
            if "think" in content.lower()[:100] or "reasoning" in content.lower()[:100]:
                yield {"type": "reasoning", "content": content[:500]}
                yield {"type": "token", "content": content}
            else:
                # 没有明显推理，直接返回（模拟流式）
                for i in range(0, len(content), 3):
                    yield {"type": "token", "content": content[i:i+3]}
            yield {"type": "done", **result}
        except Exception as e:
            yield {"type": "error", "message": str(e)}
        finally:
            await self._close_provider_session()

    async def chat(self, prompt: str, use_history: bool = True,
                   system_prompt: str = None) -> dict:
        agent = self._get_agent()
        response = await agent.think(prompt, system_prompt=system_prompt,
                                      use_history=use_history)
        result = {
            "content": response.content if response else "",
            "provider": response.provider if response else "none",
            "model": response.model if response else "none",
            "usage": response.usage if response else {},
            "cost": response.cost if response else 0,
        }
        # 关闭底层 aiohttp session 避免 Unclosed warning
        await self._close_provider_session()
        return result

    async def _close_provider_session(self):
        """关闭 Provider 的 aiohttp session"""
        try:
            agent = self._agent
            if agent and agent.llm_client:
                provider = agent.llm_client.provider_factory.get_provider(
                    agent.llm_client.settings.default_provider
                )
                if hasattr(provider, 'close'):
                    await provider.close()
        except Exception:
            pass

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
