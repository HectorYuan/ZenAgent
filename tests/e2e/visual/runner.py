"""
ZenAgent E2E 可视化测试 — 主运行器

用法:
    python -m tests.e2e.visual.runner              # 全部 Phase
    python -m tests.e2e.visual.runner --phase 1    # 单个 Phase
    python -m tests.e2e.visual.runner --all --real-llm  # 全部 + 真实 LLM
"""
from __future__ import annotations

import sys
import os
import time
import argparse
import traceback
from collections import OrderedDict
from typing import Callable

# 确保项目根目录在 path 中
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from . import viz


# ============================================================
# Phase 注册表
# ============================================================

PHASES: dict[str, dict] = OrderedDict()


def register_phase(phase_id: str, name: str, layer: str):
    """装饰器：注册 test phase"""
    def decorator(fn: Callable):
        PHASES[phase_id] = {"id": phase_id, "name": name, "layer": layer, "fn": fn}
        return fn
    return decorator


# ============================================================
# 从 phase 模块加载
# ============================================================

def _load_phase_modules():
    """导入所有 phase 测试模块（触发 @register_phase 注册）"""
    import importlib
    phase_modules = [
        "tests.e2e.visual.test_l0_llminfra",
        "tests.e2e.visual.test_l1_runtime",
        "tests.e2e.visual.test_l2_zenagent",
        "tests.e2e.visual.test_l3_metasoul",
        "tests.e2e.visual.test_l4_swarmfly",
        "tests.e2e.visual.test_l5_soulteam",
        "tests.e2e.visual.test_cli_commands",
        "tests.e2e.visual.test_tui_verify",
        "tests.e2e.visual.test_full_chain",
        "tests.e2e.visual.test_modelnexus_core",
    ]
    for mod in phase_modules:
        try:
            importlib.import_module(mod)
        except ImportError:
            pass


# ============================================================
# Runner
# ============================================================

class PhaseResult:
    def __init__(self, phase_id: str, name: str, layer: str):
        self.phase_id = phase_id
        self.name = name
        self.layer = layer
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.issues: list[str] = []
        self.duration_ms = 0
        self.scenarios: list[dict] = []
        self.error: str | None = None

    def add_scenario(self, name: str, passed: bool, issues: list[str] = None):
        self.scenarios.append({"name": name, "passed": passed, "issues": issues or []})
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        if issues:
            self.warnings += len(issues)

    def to_dict(self) -> dict:
        return {
            "phase": self.phase_id,
            "name": self.name,
            "layer": self.layer,
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "issues": self.issues,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


def run_phase(phase_id: str, config: dict) -> PhaseResult:
    """运行单个 Phase"""
    info = PHASES.get(phase_id)
    if not info:
        r = PhaseResult(phase_id, "Unknown", "?")
        r.error = f"Phase '{phase_id}' not found"
        return r

    result = PhaseResult(phase_id, info["name"], info["layer"])
    viz.phase_banner(phase_id, info["name"], info["layer"])

    timer = viz.Timer()
    try:
        info["fn"](config, result)
    except Exception as e:
        result.error = str(e)
        if config.get("debug"):
            traceback.print_exc()
        viz.analysis(f"Phase {phase_id} error: {e}")

    result.duration_ms = timer.elapsed_ms
    _print_phase_summary(result)
    return result


def _print_phase_summary(r: PhaseResult):
    """打印 Phase 摘要"""
    total = r.passed + r.failed
    status = viz.ok(f"{total}/{total}") if r.failed == 0 else viz.fail(f"{r.passed}/{total}")
    print(f"  {status} scenarios passed  {viz.dim(f'({r.duration_ms:.0f}ms)')}")
    if r.issues:
        for issue in r.issues:
            print(f"    {viz.warn(issue)}")
    if r.error:
        print(f"    {viz.fail(f'Error: {r.error}')}")


def run_all(config: dict) -> dict[str, PhaseResult]:
    """运行所有注册的 Phase"""
    results = OrderedDict()
    for phase_id in PHASES:
        results[phase_id] = run_phase(phase_id, config)
    return results


# ============================================================
# CLI
# ============================================================

def build_parser():
    p = argparse.ArgumentParser(
        prog="zena-e2e",
        description="ZenAgent End-to-End Visual Test Runner",
    )
    p.add_argument("--phase", help="Phase ID to run (e.g. 1, L0, cli, all)")
    p.add_argument("--all", action="store_true", help="Run all phases")
    p.add_argument("--real-llm", action="store_true", help="Use real LLM (DeepSeek)")
    p.add_argument("--debug", action="store_true", help="Show full traceback on errors")
    p.add_argument("--json", action="store_true", help="Export results as JSON")
    return p


def main():
    _load_phase_modules()

    parser = build_parser()
    args = parser.parse_args()

    if not PHASES:
        print("No test phases registered. Check that phase modules exist.")
        sys.exit(1)

    config = {
        "real_llm": args.real_llm,
        "debug": args.debug,
    }

    if args.phase:
        # 支持多种引用方式
        pid = args.phase.strip().lower()
        # 映射别名
        aliases = {
            "1": "L0", "2": "L1", "3": "L2", "4": "L3", "5": "L4", "6": "L5",
            "7": "cli", "8": "tui", "9": "full", "10": "core",
            "l0": "L0", "l1": "L1", "l2": "L2", "l3": "L3", "l4": "L4", "l5": "L5",
        }
        pid = aliases.get(pid, pid)

        if pid in PHASES:
            results = {pid: run_phase(pid, config)}
        else:
            print(f"Unknown phase: {args.phase}")
            print(f"Available: {', '.join(PHASES.keys())}")
            sys.exit(1)
    else:
        results = run_all(config)

    # 最终汇总
    all_results = {k: v.to_dict() for k, v in results.items()}
    viz.final_summary(all_results)

    if args.json:
        import json as _json
        print(_json.dumps(all_results, indent=2, ensure_ascii=False, default=str))

    # 退出码
    has_failure = any(r.failed > 0 or r.error for r in results.values())
    sys.exit(1 if has_failure else 0)


if __name__ == "__main__":
    main()
