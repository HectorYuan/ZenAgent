"""
CLI 格式化工具

设计参考: ZenSkill cli_utils.py
视觉语言: 框线卡片 / 条形图 / 状态指示器
"""

import json
import sys
from typing import Any, Optional


# ---------- 状态指示器 ----------

def status_icon(healthy: bool, enabled: bool = True) -> str:
    if not enabled:
        return "⚪"
    return "🟢" if healthy else "🔴"


def level_icon(level: str) -> str:
    icons = {"L0": "📊", "L1": "📡", "L2": "🧘", "L3": "🧠", "L4": "🕊"}
    return icons.get(level, "📦")


def bar_chart(value: float, width: int = 20, max_val: float = 1.0) -> str:
    """比例条形图: ████░░░░"""
    filled = int(min(value / max(max_val, 0.01), 1.0) * width)
    empty = width - filled
    return "█" * filled + "░" * empty


# ---------- 框线卡片 ----------

def box_card(title: str, lines: list[str], indent: int = 2) -> str:
    """┌─ title ─┐ / │ line │ / └──┘ 格式"""
    prefix = " " * indent
    top = f"{prefix}┌─ {title} "
    top += "─" * max(0, 60 - len(top)) + "┐"
    bottom = f"{prefix}└" + "─" * (len(top) - indent - 1) + "┘"
    body = "\n".join(f"{prefix}│ {line:<60} │" for line in lines)
    return f"{top}\n{body}\n{bottom}"


def section_header(title: str, emoji: str = "▪") -> str:
    return f"\n{emoji} {title}\n{'=' * (len(title) + 2)}"


# ---------- 键值对 ----------

def kv_list(items: list[tuple[str, Any]], indent: int = 2) -> str:
    prefix = " " * indent
    return "\n".join(f"{prefix}{k}: {v}" for k, v in items)


# ---------- 空状态 ----------

def empty_state(message: str, next_hint: str = "") -> str:
    lines = [f"[no data] {message}"]
    if next_hint:
        lines.append(f"       → {next_hint}")
    return "\n".join(lines)


# ---------- JSON 输出 ----------

def json_output(data: Any):
    """标准 JSON 输出"""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def maybe_json(args, data: Any, formatter, *fmt_args):
    """根据 --json 标志选择输出格式"""
    if getattr(args, "json_output", False):
        json_output(data)
    else:
        print(formatter(data, *fmt_args))


# ---------- 表格 ----------

def simple_table(headers: list[str], rows: list[list[Any]], indent: int = 2) -> str:
    """简单对齐表格"""
    prefix = " " * indent
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    sep = "  "
    header_line = prefix + sep.join(h.ljust(w) for h, w in zip(headers, col_widths))
    divider = prefix + sep.join("─" * w for w in col_widths)
    body = "\n".join(
        prefix + sep.join(str(c).ljust(w) for c, w in zip(row, col_widths))
        for row in rows
    )
    return f"{header_line}\n{divider}\n{body}"
