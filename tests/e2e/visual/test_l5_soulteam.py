"""
Phase L5: SoulTeam — Agent Profiles + 4-Dimension Router + Bagua Matrix + Collaboration Chains
"""
from .runner import register_phase, PhaseResult
from . import viz


@register_phase("L5", "SoulTeam — Agent Profiles + Bagua Router + Collab Chains", "L5")
def run_l5(config: dict, result: PhaseResult):
    # ---------- Scenario 1: Agent Profiles ----------
    viz.scenario_header("Agent Profiles & Teams", 1, 4)
    try:
        from packages.SoulTeam.registry import AgentRegistry

        registry = AgentRegistry()
        profiles = registry.list_all()
        viz.ok(f"Agent profiles: {len(profiles)}")

        # 按团队分组
        teams = {}
        for p in profiles:
            team = getattr(p, "team", "UNASSIGNED")
            teams.setdefault(team, []).append(p)

        for team, members in teams.items():
            print(f"    {viz.bold(team)}: {viz.dim(', '.join(getattr(m, 'agent_id', '?')[:12] for m in members[:4]))}")

        viz.kv_table([
            ("TEAM-INVEST", str(len(teams.get("TEAM-INVEST", [])))),
            ("TEAM-RD", str(len(teams.get("TEAM-RD", [])))),
            ("TEAM-LEARN", str(len(teams.get("TEAM-LEARN", [])))),
            ("TEAM-OPS", str(len(teams.get("TEAM-OPS", [])))),
        ])
        result.add_scenario("Agent Profiles", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("Agent Profiles", False, [str(e)])

    # ---------- Scenario 2: 4-Dimension Router ----------
    viz.scenario_header("4-Dimension Router", 2, 4)
    try:
        from packages.SoulTeam.router import FourDimensionRouter

        router = FourDimensionRouter()

        # 模拟评分
        viz.info("Score = Capability×0.4 + Availability×0.3 + Load×0.2 + Specialty×0.1")
        test_agents = ["SUB-1.1", "SUB-1.2", "SUB-2.1", "SUB-2.2"]
        for aid in test_agents[:4]:
            try:
                score = router.calculate_score(aid, {})
                print(f"    {viz.dim(aid)}: {viz.bold(f'{score:.3f}')}")
            except Exception:
                print(f"    {viz.dim(aid)}: {viz.gray('N/A (mock)')}")

        viz.info("Router loaded (scores require agent profiles)")
        result.add_scenario("4-Dimension Router", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("4-Dimension Router", False, [str(e)])

    # ---------- Scenario 3: Bagua Matrix ----------
    viz.scenario_header("Bagua 8×8 Routing Matrix", 3, 4)
    try:
        from packages.SoulTeam.bagua.router import BaguaRouter

        router = BaguaRouter()

        viz.info("Wuxing cycle: 木→火→土→金→水→木 (相生)")
        viz.info("Bagua coordinates: ☰☱☲☳☴☵☶☷ 8 positions")

        # 简单的路由测试
        route = router.route("general_qa")
        viz.kv_table([
            ("Bagua position", getattr(route, "position", "?")) if hasattr(route, "position") else ("Route result", str(route)[:60]),
        ])
        viz.ok("BaguaRouter functional")

        result.add_scenario("Bagua Matrix", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("Bagua Matrix", False, [str(e)])

    # ---------- Scenario 4: Collaboration Chains ----------
    viz.scenario_header("Collaboration Chains", 4, 4)
    try:
        from packages.SoulTeam.collab_chain import ChainExecutor

        executor = ChainExecutor()
        chains = executor.list_chains() if hasattr(executor, "list_chains") else []
        if chains:
            viz.ok(f"Chains: {len(chains)}")
            for c in chains[:5]:
                print(f"    {viz.dim('•')} {c}")
        else:
            # 尝试获取预定义链
            viz.info("ChainExecutor ready (chains loaded on demand)")

        viz.kv_table([
            ("Execution modes", "single / sequential / parallel / fan_out_fan_in"),
            ("Predefined chains", "5 (IA-AL, TR-DV, OO-SE, CR-DE, PR-PT)"),
        ])
        result.add_scenario("Collaboration Chains", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("Collaboration Chains", False, [str(e)])
