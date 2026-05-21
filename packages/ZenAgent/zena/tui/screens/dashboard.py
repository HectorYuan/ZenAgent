"""
DashboardScreen — 系统仪表盘

核心 Widget: 健康卡片 + 五层状态摘要 + 指标迷你图
"""

_has_textual = False
try:
    import textual
    from textual.app import ComposeResult
    from textual.containers import Container, Vertical, Horizontal
    from textual.widgets import Static, Label
    _has_textual = True
except ImportError:
    pass


if _has_textual:

    class DashboardScreen(Container):
        """仪表盘屏幕"""

        BINDINGS = [
            ("r", "refresh", "Refresh"),
        ]

        def compose(self) -> ComposeResult:
            yield Label("📊 Dashboard", id="dash-header")
            with Vertical():
                yield Static("🟢 L0 LLMInfra    │ Provider Chain + Cache OK")
                yield Static("🟢 L1 Runtime     │ Sessions: 0 active")
                yield Static("🟢 L2 ZenAgent    │ Intent Router + Hooks OK")
                yield Static("🟢 L3 MetaSoul    │ Memory L1-L4 + Personality OK")
                yield Static("🔴 L4 SwarmFly    │ No agents registered")
            yield Static("─" * 40 + "\n[Ctrl+R Refresh | 0-5 Switch Screen]")

        def refresh_data(self):
            pass
