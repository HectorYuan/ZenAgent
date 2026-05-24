"""
Rich 命令模式 — 非 TTY 终端降级方案 (T8)

当 Textual 不可用或终端不支持时，使用 Rich 进行渲染。
支持: 单字符快捷键 + 斜杠命令
"""

import sys
import os

_HAS_RICH = False
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.layout import Layout
    from rich.live import Live
    from rich import box
    _HAS_RICH = True
except ImportError:
    pass


if _HAS_RICH:

    def launch_command_mode(agent_id: str = "zena-default"):
        """启动 Rich 命令模式"""
        console = Console()
        console.print(Panel.fit(
            "[bold cyan]🧘 ZenAgent Command Mode[/]\n"
            "[dim]非 TTY 终端降级方案[/]\n\n"
            "Commands:\n"
            "  /chat <msg>   Send message to ZenAgent\n"
            "  /status       System status\n"
            "  /memory       Memory stats\n"
            "  /personality  Personality traits\n"
            "  /doctor       Health check\n"
            "  /help         This help\n"
            "  /quit         Exit\n\n"
            "Shortcuts:\n"
            "  1 Dashboard  2 Memory  3 Personality\n"
            "  q Quit  r Refresh",
            title="ZenAgent CLI Mode",
            border_style="cyan"
        ))

        from ...core.adapter import ZenaDataAdapter
        adapter = ZenaDataAdapter(agent_id=agent_id)

        while True:
            try:
                cmd = console.input("\n[cyan]> [/]").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not cmd:
                continue

            if cmd == "/quit" or cmd == "q":
                break
            elif cmd == "/help":
                console.print("[dim]Type /<command> or use shortcuts (1-3, q, r)[/]")
            elif cmd == "/status" or cmd == "1":
                status = adapter.get_full_status()
                table = Table(title="ZenAgent Status", box=box.SIMPLE)
                table.add_column("Key", style="cyan")
                table.add_column("Value")
                for k in ["agent_id", "agent_name", "agent_type"]:
                    table.add_row(k, str(status.get(k, "")))
                console.print(table)
            elif cmd == "/memory" or cmd == "2":
                stats = adapter.memory_stats()
                for k, v in stats.items():
                    console.print(f"  {k}: {v}")
            elif cmd == "/personality" or cmd == "3":
                traits = adapter.personality_traits()
                for trait, val in traits.items():
                    bar_fill = int(val * 30)
                    bar = "█" * bar_fill + "░" * (30 - bar_fill)
                    console.print(f"  {trait:<20} {bar} {val:.2f}")
            elif cmd == "/doctor" or cmd == "r":
                health = adapter.get_system_health()
                for name, info in health.items():
                    icon = "🟢" if info.get("healthy") else "🔴"
                    console.print(f"  {icon} {name}")
            elif cmd.startswith("/chat "):
                prompt = cmd[6:]
                console.print(f"[dim]Sending: {prompt}[/]")
                import asyncio
                result = asyncio.run(adapter.chat(prompt, use_history=False))
                console.print(Panel(result.get("content", ""), title="ZenAgent", border_style="green"))
            else:
                console.print(f"[red]Unknown: {cmd}. Type /help[/]")

    console = Console()
    console.print("[yellow]Session ended.[/]")


else:

    def launch_command_mode(agent_id: str = "zena-default"):
        print("Rich not installed. Install: pip install rich")
        print("Using CLI mode: ./zena chat")
