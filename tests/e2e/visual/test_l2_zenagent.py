"""
Phase L2: ZenAgent — Intent Router + Personality + Real LLM Chat
"""
from .runner import register_phase, PhaseResult
from . import viz


@register_phase("L2", "ZenAgent — Intent Router + Personality + LLM", "L2")
def run_l2(config: dict, result: PhaseResult):
    use_real_llm = config.get("real_llm", False)

    # ---------- Scenario 1: Intent Router ----------
    viz.scenario_header("Intent Router Cascade", 1, 5)
    try:
        from packages.ZenAgent.zena.core.adapter import ZenaDataAdapter
        adapter = ZenaDataAdapter()

        # 测试意图路由存在
        agent = adapter._get_agent()
        ir = agent.get_full_status().get("intent_router", {})
        viz.ok("IntentRouter active")
        viz.kv_table([
            ("Total requests", ir.get("total_requests", 0)),
            ("Fast Path", ir.get("fast_path", 0)),
            ("Deep Path", ir.get("deep_path", 0)),
            ("Fallbacks", ir.get("fallback", 0)),
            ("L2 Triggers", ir.get("l2_triggered_count", 0)),
        ])
        result.add_scenario("Intent Router", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("Intent Router", False, [str(e)])

    # ---------- Scenario 2: Personality Injection ----------
    viz.scenario_header("Personality-Aware Prompt Injection", 2, 5)
    try:
        from packages.ZenAgent.zena.core.adapter import ZenaDataAdapter
        adapter = ZenaDataAdapter()

        traits = adapter.personality_traits()
        if traits:
            viz.personality_bars(traits)
            viz.ok(f"Big Five loaded ({len(traits)} traits)")
        else:
            viz.warn("No personality traits returned")

        # Cross effects
        cross = viz._cross_effects(traits)
        if cross:
            viz.info(f"Cross effects: {', '.join(cross)}")

        result.add_scenario("Personality Injection", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("Personality Injection", False, [str(e)])

    # ---------- Scenario 3: Provider Health ----------
    viz.scenario_header("Provider Health Check", 3, 5)
    try:
        from packages.ZenAgent.zena.core.adapter import ZenaDataAdapter
        adapter = ZenaDataAdapter()

        providers = adapter.provider_list()
        viz.info(f"Available: {', '.join(providers)}")

        health = adapter.provider_health()
        if health:
            cb = health.get("circuit_breakers", {})
            if cb:
                for name, state in cb.items():
                    print(f"    {viz.dim(name)}: {viz.cyan(str(state))}")
            viz.ok(f"Provider health: enabled={health.get('enabled', False)}")
        else:
            viz.warn("No provider health data")

        result.add_scenario("Provider Health", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("Provider Health", False, [str(e)])

    # ---------- Scenario 4: Config ----------
    viz.scenario_header("Configuration", 4, 5)
    try:
        from packages.ZenAgent.zena.core.adapter import ZenaDataAdapter
        adapter = ZenaDataAdapter()

        status = adapter.get_full_status()
        viz.kv_table([
            ("Agent Name", status.get("agent_name", "?")),
            ("Agent ID", status.get("agent_id", "?")),
            ("Agent Type", status.get("agent_type", "?")),
            ("LLM Provider", status.get("llm", {}).get("provider", "?")),
        ])
        result.add_scenario("Configuration", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("Configuration", False, [str(e)])

    # ---------- Scenario 5: Real LLM Chat ----------
    viz.scenario_header("Real LLM Chat (DeepSeek)", 5, 5)
    if not use_real_llm:
        viz.info("Skipped: use --real-llm to enable")
        result.add_scenario("Real LLM Chat", True, [])
        return

    try:
        import os
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_ANTHROPIC_AUTH_TOKEN")
        if not api_key:
            viz.warn("No API key found. Set OPENAI_API_KEY or DEEPSEEK_ANTHROPIC_AUTH_TOKEN")
            result.add_scenario("Real LLM Chat", True, ["No API key — skipped"])
            return

        from packages.ZenAgent.zena.core.adapter import ZenaDataAdapter
        adapter = ZenaDataAdapter()

        prompts = [
            "用一句话解释什么是递归",
        ]

        for prompt in prompts:
            viz.info(f"Prompt: \"{prompt}\"")
            timer = viz.Timer()
            resp = adapter.chat(prompt, use_history=False)
            elapsed = timer.elapsed_ms

            viz.response_box(
                resp.get("content", ""),
                {
                    "provider": resp.get("provider", "?"),
                    "model": resp.get("model", "?"),
                    "usage": resp.get("usage", {}),
                    "cost": resp.get("cost", 0),
                    "elapsed_ms": elapsed,
                }
            )

        adapter.clear_history()
        viz.ok("Real LLM chat completed")
        result.add_scenario("Real LLM Chat", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("Real LLM Chat", False, [str(e)])
