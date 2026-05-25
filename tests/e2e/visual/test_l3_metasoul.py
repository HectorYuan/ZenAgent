"""
Phase L3: MetaSoul — Memory Layers + Big Five + Experience Loop + SPO
"""
from .runner import register_phase, PhaseResult
from . import viz


@register_phase("L3", "MetaSoul — Memory + Personality + Experience Loop", "L3")
def run_l3(config: dict, result: PhaseResult):
    # ---------- Scenario 1: Memory Layer Stats (Key Mismatch Fix) ----------
    viz.scenario_header("Memory Layer Stats & Key Mismatch Diagnostic", 1, 4)
    try:
        from packages.ZenAgent.zena.core.adapter import ZenaDataAdapter
        adapter = ZenaDataAdapter()

        stats = adapter.memory_stats()
        viz.info("Raw keys from MetaSoul.get_stats():")
        print(f"    {viz.dim(str(list(stats.keys())))}")

        # Diagnostic: check key structure
        by_type = stats.get("memories_by_type", {})
        has_flat_keys = any(k.endswith("_count") for k in stats)

        print()
        viz.kv_table([
            ("Total memories", stats.get("total_memories", "?")),
            ("memories_by_type exists", bool(by_type)),
            ("Flat _count keys", has_flat_keys),
        ])

        if by_type:
            viz.ok("Key mismatch FIXED: reading from memories_by_type")
            print()
            viz.kv_table([
                ("L1 Working (热)", by_type.get("working", "?")),
                ("L2 Episodic (温)", by_type.get("episodic", "?")),
                ("L3 Semantic (语义)", by_type.get("semantic", "?")),
                ("L4 Procedural (归档)", by_type.get("procedural", "?")),
            ])
        elif has_flat_keys:
            viz.ok("Using flat keys (backward compatible)")
            viz.kv_table([
                ("L1 Working", stats.get("working_memory_count", "?")),
                ("L2 Episodic", stats.get("episodic_memory_count", "?")),
                ("L3 Semantic", stats.get("semantic_memory_count", "?")),
                ("L4 Procedural", stats.get("procedural_memory_count", "?")),
            ])
        else:
            viz.warn("No memory data available (empty MetaSoul)")

        result.add_scenario("Memory Layer Stats", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("Memory Layer Stats", False, [str(e)])

    # ---------- Scenario 2: Memory Store & Search ----------
    viz.scenario_header("Memory Store & Search", 2, 4)
    try:
        from packages.ZenAgent.zena.core.adapter import ZenaDataAdapter
        adapter = ZenaDataAdapter()

        # 存储测试记忆
        test_content = f"E2E test memory: ZenAgent architecture has 6 layers"
        mem_id = adapter.memory_store(test_content, "EPISODIC")
        viz.ok(f"Stored: {viz.dim(mem_id[:16] + '...')}")

        # 搜索
        results = adapter.memory_search("ZenAgent", limit=5)
        viz.memory_table(results)
        viz.ok(f"Search returned {len(results)} results")

        result.add_scenario("Memory Store & Search", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("Memory Store & Search", False, [str(e)])

    # ---------- Scenario 3: Big Five Personality ----------
    viz.scenario_header("Big Five Personality Matrix", 3, 4)
    try:
        from packages.ZenAgent.zena.core.adapter import ZenaDataAdapter
        adapter = ZenaDataAdapter()

        traits = adapter.personality_traits()
        if traits:
            viz.personality_bars(traits)
            viz.ok(f"{len(traits)} traits loaded")
        else:
            # 设置默认值
            for t in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
                adapter.personality_set(t, 0.5)
            traits = adapter.personality_traits()
            viz.personality_bars(traits)
            viz.ok("Traits initialized to defaults")

        # 场景枚举
        from packages.MetaSoul.personality.personality_matrix import Scenario
        scenarios = [s.value for s in Scenario]
        viz.info(f"Scenarios: {', '.join(scenarios[:6])}...")

        result.add_scenario("Big Five Personality", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("Big Five Personality", False, [str(e)])

    # ---------- Scenario 4: SPO Knowledge Graph ----------
    viz.scenario_header("SPO Knowledge Graph", 4, 4)
    try:
        from packages.ZenAgent.zena.core.adapter import ZenaDataAdapter
        adapter = ZenaDataAdapter()

        kb = adapter.knowledge_stats()
        viz.kv_table([
            ("Triples", kb.get("total_triples", 0)),
            ("Entities", kb.get("total_entities", 0)),
        ])

        # 搜索（可能为空）
        search_results = adapter.knowledge_search("agent", top_k=3)
        if search_results:
            for r in search_results:
                print(f"    {viz.dim(str(r)[:100])}")
            viz.ok(f"{len(search_results)} triples found")
        else:
            viz.info("No triples (fresh MetaSoul)")

        result.add_scenario("SPO Knowledge Graph", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("SPO Knowledge Graph", False, [str(e)])
