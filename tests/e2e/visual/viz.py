"""
ZenAgent E2E 可视化原语

提供所有测试 Phase 共用的终端输出格式化工具。
设计目标: 让智能体交互过程透明可见——路由决策、记忆召回、人格影响等。
"""
from __future__ import annotations

import os
import sys
import json
import time
import textwrap
from typing import Any, Optional

# ---------- 颜色支持 ----------

_USE_COLOR = os.environ.get("NO_COLOR", "") == "" and hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _c(code: int, text: str) -> str:
    """ANSI 颜色包装"""
    if _USE_COLOR:
        return f"\033[{code}m{text}\033[0m"
    return text


def green(t: str) -> str:  return _c(32, t)
def red(t: str) -> str:    return _c(31, t)
def yellow(t: str) -> str: return _c(33, t)
def blue(t: str) -> str:   return _c(34, t)
def cyan(t: str) -> str:   return _c(36, t)
def magenta(t: str) -> str:return _c(35, t)
def white(t: str) -> str:  return _c(37, t)
def bold(t: str) -> str:   return _c(1, t)
def dim(t: str) -> str:    return _c(2, t)
def gray(t: str) -> str:   return _c(90, t)

# ---------- 状态指示 ----------

def ok(msg: str = "") -> str:
    return f"{green('✓')} {msg}" if msg else green("✓")

def fail(msg: str = "") -> str:
    return f"{red('✗')} {msg}" if msg else red("✗")

def warn(msg: str) -> str:
    return f"{yellow('⚠')} {msg}"

def info(msg: str) -> str:
    return f"{blue('ℹ')} {msg}"

def check(condition: bool) -> str:
    return ok() if condition else fail()

# ---------- 分隔线 ----------

def hr(char: str = "─", width: int = 70) -> str:
    return dim(char * width)

def blank():
    print()

# ---------- Phase Banner ----------

def phase_banner(phase: str, title: str, layer: str = ""):
    """Phase 阶段横幅"""
    label = f"Phase {phase}: {title}"
    if layer:
        label += f"  [{layer}]"
    width = 72
    print()
    print(bold(cyan("╔" + "═" * (width - 2) + "╗")))
    print(bold(cyan("║")) + f"  {bold(label)}".ljust(width - 2) + bold(cyan("║")))
    print(bold(cyan("╚" + "═" * (width - 2) + "╝")))
    print()


def scenario_header(name: str, num: int = 0, total: int = 0):
    """场景标题"""
    prefix = f"[{num}/{total}]" if total else ""
    print(f"\n{bold(yellow('▶'))} {bold(name)} {dim(prefix)}")
    print(f"  {dim(hr(width=60))}")


# ---------- 步骤 ----------

def step(num: int, total: int, desc: str):
    """步骤计数器"""
    print(f"  {bold(f'[{num}/{total}]')} {desc}")


# ---------- 数据展示 ----------

def kv_table(items: list[tuple[str, Any]], indent: int = 4):
    """键值对表格"""
    prefix = " " * indent
    for k, v in items:
        print(f"{prefix}{bold(k + ':')} {v}")


def bar_chart(value: float, width: int = 30, max_val: float = 1.0, label: str = ""):
    """比例条形图"""
    filled = int(min(max(value / max(max_val, 0.01), 0.0), 1.0) * width)
    empty = width - filled
    bar_str = green("█" * filled) + dim("░" * empty)
    lbl = f"{label:<22}" if label else ""
    print(f"  {lbl} {bar_str} {bold(f'{value:.2f}')}")


def personality_bars(traits: dict[str, float]):
    """Big Five 人格条形图"""
    print(f"  {bold('Big Five Personality:')}")
    print()
    labels = {
        "openness": "开放性 (O)",
        "conscientiousness": "尽责性 (C)",
        "extraversion": "外向性 (E)",
        "agreeableness": "宜人性 (A)",
        "neuroticism": "情绪稳定性 (N)",
    }
    for trait, value in traits.items():
        lbl = labels.get(trait, trait)
        bar_chart(value, width=30, label=lbl)
    # 交叉效应
    cross = _cross_effects(traits)
    if cross:
        print(f"\n  {bold('交叉效应:')} {dim(' | '.join(cross))}")


def _cross_effects(traits: dict) -> list[str]:
    effects = []
    o, c, e, a, n = (traits.get(k, 0.5) for k in
                     ["openness", "conscientiousness", "extraversion",
                      "agreeableness", "neuroticism"])
    if o > 0.6 and e > 0.6: effects.append("O+E: Explorer-Social")
    if o > 0.6 and c > 0.6: effects.append("O+C: Creative Executor")
    if c > 0.6 and n > 0.6: effects.append("C+N: Perfectionist")
    if a < 0.4 and c > 0.6: effects.append("低A+C: Rigorous Direct")
    if e > 0.6 and a > 0.6: effects.append("E+A: Warm Collaborator")
    if o > 0.6 and n < 0.4: effects.append("O+低N: Calm Explorer")
    if o > 0.6 and a > 0.6: effects.append("O+A: Empathic Creator")
    return effects


# ---------- 管线追踪 ----------

def pipeline_trace(stages: list[dict], current: int = -1):
    """水平管线追踪: [Stage1] → [Stage2] → [Stage3]"""
    parts = []
    for i, s in enumerate(stages):
        name = s.get("name", str(s))
        status = s.get("status", "")
        if status == "hit":
            name = green(f"✓{name}")
        elif status == "miss":
            name = dim(name)
        elif status == "error":
            name = red(f"✗{name}")
        elif i == current:
            name = bold(cyan(name))

        timing = s.get("timing_ms")
        suffix = f" {dim(f'{timing:.0f}ms')}" if timing is not None else ""
        parts.append(f"[{name}{suffix}]")

    print(f"  {' ' + yellow('→') + ' '.join(parts)}")


def pipeline_stage_detail(stages: list[dict]):
    """管线阶段详情（含计时）"""
    print(f"  {bold('Pipeline Stage Details:')}")
    for s in stages:
        name = s.get("name", "?")
        status = s.get("status", "-")
        timing = s.get("timing_ms", 0)
        meta = s.get("meta", "")
        status_icon = ok() if status in ("ok", "hit") else (dim("·") if status == "skip" else fail())
        timing_str = f"{timing:.0f}ms" if timing else dim("-")
        print(f"    {status_icon} {name:<20} {dim(timing_str):>10}  {gray(meta)}")


# ---------- 路由决策 ----------

def routing_decision(intent: str, confidence: float, path: str, reason: str = ""):
    """路由决策可视化"""
    print(f"  {bold('Intent Router')}:")
    print(f"    {dim('Input')} → {bold(intent)} ({cyan(f'{confidence:.2f}')})")
    print(f"    {dim('Path  ')} → {bold(path)}")
    if reason:
        print(f"    {dim('Reason')} → {gray(reason)}")


# ---------- 响应展示 ----------

def response_box(content: str, meta: dict = None, max_lines: int = 12):
    """响应框（含 provider/model/tokens/cost）"""
    meta = meta or {}
    width = 70
    lines = content.strip().split("\n")
    # 截断过长响应
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [dim("... (truncated)")]

    print(f"  {bold('Response:')}")
    print(f"  {dim('┌' + '─' * (width - 4) + '┐')}")
    for line in lines:
        # 处理超长行
        if len(line) > width - 6:
            line = line[:width - 9] + dim("...")
        print(f"  {dim('│')} {line}".ljust(width + 2) + dim("│"))
    print(f"  {dim('└' + '─' * (width - 4) + '┘')}")
    print()

    # 元数据行
    provider = meta.get("provider", "?")
    model = meta.get("model", "?")
    usage = meta.get("usage", {})
    cost = meta.get("cost", 0)
    elapsed = meta.get("elapsed_ms", 0)

    parts = [
        f"provider: {cyan(provider)}",
        f"model: {cyan(model)}",
        f"in: {usage.get('prompt_tokens', '?')}",
        f"out: {usage.get('completion_tokens', '?')}",
        f"cost: {yellow(f'${cost:.4f}')}" if cost else "",
        f"time: {dim(f'{elapsed:.0f}ms')}" if elapsed else "",
    ]
    print(f"  {dim('·').join(p for p in parts if p)}")


# ---------- 记忆展示 ----------

def memory_table(results: list[dict], max_rows: int = 10):
    """记忆搜索结果表"""
    if not results:
        print(f"  {dim('(no memories found)')}")
        return

    print(f"  {bold(f'Memories ({len(results)} results):')}")
    for i, r in enumerate(results[:max_rows]):
        content = r.get("content", str(r))[:80]
        mem_type = r.get("type", "?")
        importance = r.get("importance", "?")
        type_colors = {
            "WORKING": cyan, "EPISODIC": yellow, "SEMANTIC": green,
            "PROCEDURAL": magenta,
            "working": cyan, "episodic": yellow, "semantic": green,
            "procedural": magenta,
        }
        tc = type_colors.get(str(mem_type), white)
        print(f"  {dim(f'[{i+1}]')} {tc(f'[{mem_type}]')} {content}")
        print(f"  {dim('     importance=' + str(importance))}")
    if len(results) > max_rows:
        print(f"  {dim(f'... and {len(results) - max_rows} more')}")


# ---------- 分析盒 ----------

def analysis(text: str):
    """分析标注盒"""
    width = 68
    print()
    print(f"  {bold(magenta('┌─ Analysis ' + '─' * (width - 14) + '┐'))}")
    for line in textwrap.wrap(text, width=width - 4):
        print(f"  {magenta('│')} {line}".ljust(width + 2) + magenta("│"))
    print(f"  {bold(magenta('└' + '─' * (width - 2) + '┘'))}")
    print()


# ---------- 摘要盒 ----------

def summary_box(title: str, items: list[str]):
    """摘要信息盒"""
    print(f"  {bold(title)}:")
    for item in items:
        print(f"    {item}")


# ---------- ASCII 流程图 ----------

def flow_diagram(steps: list[str], highlight: int = -1):
    """垂直流程图"""
    for i, s in enumerate(steps):
        if i == highlight:
            print(f"  {bold(cyan('┌─ ' + s + ' ─┐'))}")
        else:
            print(f"  {dim('  ' + s)}")
        if i < len(steps) - 1:
            connector = bold(yellow("  │")) if i == highlight - 1 else dim("  │")
            print(connector)
            print(dim("  ▼"))


# ---------- 堆叠进度 ----------

class Timer:
    """简单计时器"""
    def __init__(self):
        self.start = time.monotonic()

    @property
    def elapsed_ms(self) -> float:
        return (time.monotonic() - self.start) * 1000

    def __str__(self) -> str:
        return f"{self.elapsed_ms:.0f}ms"


# ---------- 汇总输出 ----------

def final_summary(results: dict):
    """最终汇总报告"""
    total = sum(r.get("passed", 0) for r in results.values())
    failed = sum(r.get("failed", 0) for r in results.values())
    warnings = sum(r.get("warnings", 0) for r in results.values())
    issues: list[str] = []
    for r in results.values():
        issues.extend(r.get("issues", []))

    print()
    print(bold(cyan("╔" + "═" * 70 + "╗")))
    print(bold(cyan("║")) + f"  {bold('ZenAgent E2E Test Report')}".ljust(70) + bold(cyan("║")))
    print(bold(cyan("╚" + "═" * 70 + "╝")))
    print()

    phases_count = len(results)
    print(f"  Phases: {bold(str(phases_count))} completed    "
          f"Passed: {bold(green(str(total)))}    "
          f"Failed: {bold(red(str(failed)))}    "
          f"Warnings: {bold(yellow(str(warnings)))}")

    if issues:
        print(f"\n  {bold(yellow('Issues Found:'))}")
        for i, issue in enumerate(issues, 1):
            print(f"    {i}. {yellow('⚠')} {issue}")

    all_pass = failed == 0
    status = green("ALL PASSED") if all_pass else red(f"{failed} FAILED")
    print(f"\n  {bold('Result:')} {bold(status)}")
    print()


# ---------- JSON 导出 ----------

def json_export(data: Any, filepath: str):
    """导出结果为 JSON"""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"  {info(f'Exported to {filepath}')}")
