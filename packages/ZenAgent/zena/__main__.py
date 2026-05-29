"""
zena CLI 入口 — ZenAgent 命令行界面

用法: python -m packages.ZenAgent.zena <command> [options]

设计参考: ZenSkill __main__.py (argparse + cmd_* dispatcher)
"""

import sys
import os
import argparse
import asyncio

from .core.adapter import ZenaDataAdapter
from .cli_utils import (
    section_header, box_card, kv_list, empty_state, json_output, maybe_json,
    status_icon, bar_chart, simple_table, level_icon
)

_adapter: ZenaDataAdapter = None


def _cleanup_adapter():
    """安全关闭 adapter 资源（aiohttp sessions）"""
    global _adapter
    if _adapter and _adapter._agent and _adapter._agent.llm_client:
        try:
            provider = _adapter._agent.llm_client.provider_factory.get_provider(
                _adapter._agent.llm_client.settings.default_provider
            )
            if hasattr(provider, '_session') and provider._session:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(provider.close())
                    else:
                        loop.run_until_complete(provider.close())
                except RuntimeError:
                    pass
        except Exception:
            pass
    _adapter = None


def get_adapter() -> ZenaDataAdapter:
    global _adapter
    if _adapter is None:
        _adapter = ZenaDataAdapter()
    return _adapter


def safe_execute(func, args):
    """安全执行包装器（ZenSkill safe_execute 模式）"""
    try:
        if asyncio.iscoroutinefunction(func):
            return asyncio.run(func(args))
        return func(args)
    except KeyboardInterrupt:
        print("\n中断。")
        _cleanup_adapter()
    except Exception as e:
        msg = str(e) if getattr(args, "debug", False) else str(e)[:200]
        print(f"❌ 错误: {msg}")
        if getattr(args, "debug", False):
            import traceback
            traceback.print_exc()


# ============================================================
# 命令处理函数
# ============================================================

# ---------- chat ----------

async def cmd_chat(args):
    adapter = get_adapter()
    from packages.LLMInfra.modelnexus_core_config import detect_available_provider

    prompt = " ".join(args.message) if args.message else None
    provider = args.provider or detect_available_provider()

    if not prompt:
        # 交互模式
        print(f"🧘 ZenAgent Chat  |  Provider: {provider}")
        print("  (输入 'q' 退出, 'clear' 清空历史)")
        while True:
            try:
                line = input("\n🧑 > ")
            except (EOFError, KeyboardInterrupt):
                break
            if line.lower() == "q":
                break
            if line.lower() == "clear":
                await adapter.clear_history()
                print("  历史已清空。")
                continue
            result = await adapter.chat(line, use_history=not args.no_history,
                                         system_prompt=args.system_prompt)
            print(f"\n🧘 {result['content']}")
            print(f"   [{result.get('provider', '?')} | {result.get('model', '?')} | "
                  f"input={result.get('usage', {}).get('prompt_tokens', '?')} "
                  f"out={result.get('usage', {}).get('completion_tokens', '?')}]")
    else:
        # 单次调用
        result = await adapter.chat(prompt, use_history=not args.no_history,
                                     system_prompt=args.system_prompt)
        if getattr(args, "json_output", False):
            json_output(result)
        else:
            print(result["content"])


# ---------- status ----------

def cmd_status(args):
    adapter = get_adapter()
    status = adapter.get_full_status()
    if getattr(args, "json_output", False):
        return json_output(status)

    print(section_header("ZenAgent Status"))
    print(kv_list([
        ("Agent", status.get("agent_name", "")),
        ("Agent ID", status.get("agent_id", "")),
        ("Timestamp", status.get("timestamp", "")),
    ]))

    # M11: ModelNexusCore 管线状态
    core = adapter.core_health()
    if core.get("enabled"):
        print(section_header("ModelNexusCore"))
        pipeline = core.get("pipeline", [])
        stage_names = " → ".join(s["name"] for s in pipeline)
        print(f"  管线: {stage_names}")

    # 人格路由统计
    ir = status.get("intent_router", {})
    if ir:
        print(section_header("Intent Router"))
        print(kv_list([
            ("Requests", ir.get("total_requests", 0)),
            ("Fast Path", ir.get("fast_path", 0)),
            ("Deep Path", ir.get("deep_path", 0)),
            ("Fallbacks", ir.get("fallback", 0)),
            ("L2 Triggers", ir.get("l2_triggered_count", 0)),
        ]))


# ---------- memory ----------

def cmd_memory(args):
    adapter = get_adapter()

    if args.mem_action == "add":
        adapter.memory_store(args.content, args.type)
        print("✅ 记忆已存储。")
    elif args.mem_action == "search":
        results = adapter.memory_search(args.query, args.limit or 10)
        if getattr(args, "json_output", False):
            return json_output(results)
        if not results:
            print(empty_state("没有匹配的记忆。", "zena memory add <content>"))
            return
        print(section_header("Memory Search Results"))
        for r in results:
            print(f"  📝 {r['content'][:100]}")
            print(f"     [type={r['type']}, importance={r['importance']}]")
    elif args.mem_action == "stats":
        stats = adapter.memory_stats()
        by_type = stats.get("memories_by_type", {})
        maybe_json(args, stats, lambda d: kv_list([
            ("Total Memories", d.get("total_memories", "?")),
            ("L1 Working", by_type.get("working", d.get("working_memory_count", "?"))),
            ("L2 Episodic", by_type.get("episodic", d.get("episodic_memory_count", "?"))),
            ("L3 Semantic", by_type.get("semantic", d.get("semantic_memory_count", "?"))),
            ("L4 Procedural", by_type.get("procedural", d.get("procedural_memory_count", "?"))),
        ]))


# ---------- personality ----------

def cmd_personality(args):
    adapter = get_adapter()

    if args.pers_action == "show":
        traits = adapter.personality_traits()
        if getattr(args, "json_output", False):
            return json_output(traits)
        print(section_header("Personality · Big Five"))
        for trait, val in traits.items():
            print(f"  {trait:<20} {bar_chart(val, width=30)} {val:.2f}")

    elif args.pers_action == "set":
        adapter.personality_set(args.trait, args.value)
        print(f"✅ {args.trait} → {args.value}")

    elif args.pers_action == "scenario":
        # 打印场景列表
        from packages.MetaSoul.personality.personality_matrix import Scenario
        print(section_header("Scenarios"))
        for s in Scenario:
            print(f"  {status_icon(True)} {s.value:<20} {s.name}")


# ---------- provider ----------

def cmd_provider(args):
    adapter = get_adapter()

    if args.prov_action == "list":
        providers = adapter.provider_list()
        if getattr(args, "json_output", False):
            return json_output(providers)
        print(section_header("Providers"))
        for p in providers:
            print(f"  {status_icon(True)} {p}")

    elif args.prov_action == "health":
        health = adapter.provider_health()
        maybe_json(args, health, lambda h: (
            box_card("Provider Health", [
                f"Enabled: {h.get('enabled', False)}",
                f"Circuit Breakers: {len(h.get('circuit_breakers', {}))}",
                f"Health: {h.get('provider_health', {})}",
            ])
        ))


# ---------- knowledge ----------

def cmd_knowledge(args):
    adapter = get_adapter()

    if args.know_action == "stats":
        stats = adapter.knowledge_stats()
        maybe_json(args, stats, lambda s: kv_list([
            ("Total Triples", s.get("total_triples", 0)),
            ("Total Entities", s.get("total_entities", 0)),
            ("Conflicts", s.get("total_conflicts", 0)),
        ]))
    elif args.know_action == "search":
        results = adapter.knowledge_search(args.query, args.topk or 5)
        if getattr(args, "json_output", False):
            return json_output(results)
        if not results:
            print(empty_state("没有匹配的知识。"))
            return
        print(section_header("Knowledge Search Results"))
        for r in results:
            print(f"  📚 {r}")


# ---------- agent / team / cache / config ----------

def cmd_agent(args):
    adapter = get_adapter()
    if args.agent_action == "list":
        agents = adapter.agents_list()
        maybe_json(args, agents, lambda a: (
            section_header(f"Registered Agents ({len(a)})") + "\n" +
            "\n".join(f"  {status_icon(True)} {agent}" for agent in (a or []))
            or empty_state("没有注册的 Agent。", "zena agent register <id>")
        ))


def cmd_cache(args):
    adapter = get_adapter()
    stats = adapter.cache_stats()
    hs = stats.get("hotspot", {})
    maybe_json(args, stats, lambda s: (
        box_card("Cache Stats", [
            f"Hit Rate: {hs.get('hit_rate', 0):.1%}",
            f"Hot Keys: {hs.get('hot_keys', 0)}",
            f"Warm Keys: {hs.get('warm_keys', 0)}",
            f"Precache Tasks: {hs.get('precache_tasks', 0)}",
        ])
    ))


def cmd_config(args):
    adapter = get_adapter()
    status = adapter.get_full_status()
    print(section_header("Configuration"))
    print(kv_list([
        ("Agent Name", status.get("agent_name", "")),
        ("Agent Type", status.get("agent_type", "")),
        ("LLM Provider", status.get("llm", {}).get("provider", "mock")),
    ]))


def cmd_doctor(args):
    adapter = get_adapter()
    health = adapter.get_system_health()
    print(section_header("Doctor · System Health"))
    for subsystem, info in health.items():
        icon = status_icon(info.get("healthy", False))
        name = info.get("name", subsystem)
        print(f"  {icon} {subsystem:<15} {name}")


# ---------- tui ----------

def cmd_tui(args):
    """启动 TUI（如果 Textual 可用）"""
    try:
        from .tui.app import launch_tui
        launch_tui(args.agent_id)
    except ImportError as e:
        print(f"TUI not available: {e}")
        print("Install: pip install textual>=0.40.0")


# ---------- e2e ----------

def cmd_e2e(args):
    """端到端可视化测试"""
    try:
        from tests.e2e.visual.runner import main as e2e_main
        # 将 args 转发给 e2e runner
        import sys
        sys.argv = [
            "zena-e2e",
            *(["--phase", args.phase] if args.phase else []),
            *(["--all"] if args.all else []),
            *(["--real-llm"] if args.real_llm else []),
        ]
        e2e_main()
    except ImportError as e:
        print(f"E2E runner not available: {e}")
        print("Ensure tests/e2e/visual/ exists")


# ============================================================
# 命令行参数解析
# ============================================================

def build_parser():
    parser = argparse.ArgumentParser(
        prog="zena",
        description="🧘 ZenAgent CLI — 六层智能体平台命令行界面",
    )
    parser.add_argument("--version", "-V", action="version", version="zena v1.0.0")
    parser.add_argument("--debug", action="store_true", help="显示调试信息")
    parser.add_argument("--json", dest="json_output", action="store_true", help="JSON 输出模式")
    parser.add_argument("--agent-id", default="zena-default", help="Agent 实例 ID")

    sub = parser.add_subparsers(dest="command", title="commands")

    # ---- chat ----
    p_chat = sub.add_parser("chat", help="AI 对话")
    p_chat.add_argument("message", nargs="*", help="消息内容（空→交互模式）")
    p_chat.add_argument("--provider", "-p", help="Provider (openai/anthropic/modelnexus/mock, 默认自动检测)")
    p_chat.add_argument("--model", "-m", help="模型名称")
    p_chat.add_argument("--ab-group", choices=["A", "B"], help="A/B 实验分组")
    p_chat.add_argument("--system-prompt", help="系统提示")
    p_chat.add_argument("--no-history", action="store_true", help="不使用对话历史")
    p_chat.set_defaults(func=cmd_chat)

    # ---- status ----
    p_status = sub.add_parser("status", help="系统状态仪表盘")
    p_status.set_defaults(func=cmd_status)

    # ---- memory ----
    p_mem = sub.add_parser("memory", help="记忆管理")
    mem_sub = p_mem.add_subparsers(dest="mem_action")
    mem_sub.add_parser("stats").set_defaults(func=cmd_memory)
    p_add = mem_sub.add_parser("add", help="存储记忆")
    p_add.add_argument("content", help="内容")
    p_add.add_argument("--type", default="EPISODIC", help="记忆类型")
    p_add.set_defaults(func=cmd_memory)
    p_search = mem_sub.add_parser("search", help="搜索记忆")
    p_search.add_argument("query", help="查询")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.set_defaults(func=cmd_memory)

    # ---- personality ----
    p_pers = sub.add_parser("personality", help="人格管理")
    pers_sub = p_pers.add_subparsers(dest="pers_action")
    pers_sub.add_parser("show").set_defaults(func=cmd_personality)
    p_set = pers_sub.add_parser("set", help="调整特质")
    p_set.add_argument("trait", help="特质名称")
    p_set.add_argument("value", type=float, help="值 (0-1)")
    p_set.set_defaults(func=cmd_personality)
    pers_sub.add_parser("scenario").set_defaults(func=cmd_personality)

    # ---- provider ----
    p_prov = sub.add_parser("provider", help="Provider 管理")
    prov_sub = p_prov.add_subparsers(dest="prov_action")
    prov_sub.add_parser("list").set_defaults(func=cmd_provider)
    prov_sub.add_parser("health").set_defaults(func=cmd_provider)

    # ---- knowledge ----
    p_know = sub.add_parser("knowledge", help="知识库管理")
    know_sub = p_know.add_subparsers(dest="know_action")
    know_sub.add_parser("stats").set_defaults(func=cmd_knowledge)
    p_ks = know_sub.add_parser("search", help="搜索 SPO 三元组")
    p_ks.add_argument("query")
    p_ks.add_argument("--topk", type=int, default=5)
    p_ks.set_defaults(func=cmd_knowledge)

    # ---- agent ----
    p_agent = sub.add_parser("agent", help="Agent 管理")
    agent_sub = p_agent.add_subparsers(dest="agent_action")
    agent_sub.add_parser("list").set_defaults(func=cmd_agent)

    # ---- cache ----
    p_cache = sub.add_parser("cache", help="缓存管理")
    p_cache.set_defaults(func=cmd_cache)

    # ---- config ----
    p_conf = sub.add_parser("config", help="配置管理")
    p_conf.set_defaults(func=cmd_config)

    # ---- doctor ----
    p_doc = sub.add_parser("doctor", help="健康检查")
    p_doc.set_defaults(func=cmd_doctor)

    # ---- tui ----
    p_tui = sub.add_parser("tui", help="启动 TUI 界面")
    p_tui.set_defaults(func=cmd_tui)

    # ---- e2e ----
    p_e2e = sub.add_parser("e2e", help="端到端可视化测试")
    p_e2e.add_argument("--phase", help="Phase 编号 (1-10 或 L0-L5/cli/tui/full/core/all)")
    p_e2e.add_argument("--all", action="store_true", help="运行全部 Phase")
    p_e2e.add_argument("--real-llm", action="store_true", help="使用真实 LLM (DeepSeek)")
    p_e2e.set_defaults(func=cmd_e2e)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func") or not args.func:
        args.func = cmd_status

    try:
        safe_execute(args.func, args)
    finally:
        _cleanup_adapter()


if __name__ == "__main__":
    main()
