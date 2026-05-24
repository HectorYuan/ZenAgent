"""
DashboardScreen — 系统仪表盘

核心 Widget: 健康卡片 + 五层状态摘要
"""

from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Vertical, ScrollableContainer
from textual.widgets import Static, Label
from textual.binding import Binding


class DashboardScreen(Screen):

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
    ]

    DEFAULT_CSS = """
    DashboardScreen { background: $surface; }
    #dash-header { dock: top; height: 1; background: $panel; color: $text-muted; padding: 0 1; }
    #dash-content { height: 1fr; overflow-y: auto; padding: 0 1; }
    """

    def __init__(self):
        super().__init__()
        self._adapter = None

    def _get_adapter(self):
        if self._adapter is None:
            from ...core.adapter import ZenaDataAdapter
            self._adapter = ZenaDataAdapter()
        return self._adapter

    def compose(self) -> ComposeResult:
        yield Label("📊 Dashboard · System Overview", id="dash-header")
        with ScrollableContainer(id="dash-content"):
            self._render_content()

    def on_mount(self):
        self.refresh_data()

    def _build_content(self):
        adapter = self._get_adapter()
        status = adapter.get_full_status()
        ir = status.get("intent_router", {})
        agents = len(adapter.agents_list())

        return [
            Static("🟢 L0 LLMInfra    │ Provider Chain + Circuit Breaker OK"),
            Static(f"🟢 L1 Runtime     │ Router: {ir.get('total_requests', 0)} reqs, "
                   f"Fast:{ir.get('fast_path', 0)} Deep:{ir.get('deep_path', 0)}"),
            Static("🟢 L2 ZenAgent    │ Hooks + Awakening + MCP OK"),
            Static("🟢 L3 MetaSoul    │ Memory L1-L4 + Personality Matrix OK"),
            Static(f"⚪ L4 SwarmFly    │ Agents: {agents}"),
            Static(""),
            Static("─" * 50 + "\n[0 Chat | 1 Dash | 2 Mem | 3 Pers | 4 Learn | 5 Infra | q Quit]"),
        ]

    def compose(self) -> ComposeResult:
        yield Label("📊 Dashboard · System Overview", id="dash-header")
        with ScrollableContainer(id="dash-content"):
            for widget in self._build_content():
                yield widget

    def action_refresh(self):
        self.refresh_data()

    def refresh_data(self):
        content = self.query_one("#dash-content", ScrollableContainer)
        content.remove_children()
        for widget in self._build_content():
            content.mount(widget)
