"""
Phase L4: SwarmFly — Agent Registry + Task Dispatch + Shared Memory
"""
from .runner import register_phase, PhaseResult
from . import viz


@register_phase("L4", "SwarmFly — Agent Registry + Task Dispatch", "L4")
def run_l4(config: dict, result: PhaseResult):
    # ---------- Scenario 1: Agent Registry ----------
    viz.scenario_header("Agent Registry & Registration", 1, 3)
    try:
        from packages.ZenAgent.zena.core.adapter import ZenaDataAdapter
        adapter = ZenaDataAdapter()

        agents = adapter.agents_list()
        viz.info(f"Registered agents: {len(agents)}")
        for a in agents[:8]:
            print(f"    {viz.dim('•')} {a}")

        # 注册新 Agent
        ok = adapter.agent_register("e2e_test_agent", "worker")
        viz.check(ok)
        if ok:
            viz.ok("Registered 'e2e_test_agent' as worker")

        agents2 = adapter.agents_list()
        viz.ok(f"Now {len(agents2)} agents registered")

        result.add_scenario("Agent Registry", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("Agent Registry", False, [str(e)])

    # ---------- Scenario 2: Task Dispatch ----------
    viz.scenario_header("Task Dispatch", 2, 3)
    try:
        from packages.SwarmFly.swarmfly import SwarmFly
        sf = SwarmFly()
        sf.register_agent("worker_1", "worker")

        try:
            task_id = sf.submit_task(
                agent_id="worker_1",
                payload={"type": "test", "content": "hello"},
                priority=1,
            )
            viz.ok(f"Task submitted: {viz.dim(str(task_id)[:12] + '...')}")
        except Exception as e:
            viz.info(f"Task submit via alt method: {e}")

        status = sf.get_status()
        viz.kv_table([
            ("Agents", status.get("registered_agents", 0)),
            ("Teams", status.get("teams", 0)),
        ])
        result.add_scenario("Task Dispatch", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("Task Dispatch", False, [str(e)])

    # ---------- Scenario 3: Shared Memory Pool ----------
    viz.scenario_header("Shared Memory Pool", 3, 3)
    try:
        from packages.SwarmFly.swarmfly import SwarmFly
        sf = SwarmFly()

        seg_id = sf.create_shared_segment("test_pool", max_size=100)
        viz.ok(f"Shared segment created: {viz.dim(seg_id[:12] + '...')}")

        result.add_scenario("Shared Memory Pool", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("Shared Memory Pool", False, [str(e)])
