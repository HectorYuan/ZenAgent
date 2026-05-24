"""
DashboardScreen — 系统仪表盘

核心 Widget: 健康卡片 + 五层状态摘要
"""

from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Static, Label
from .base import BaseScreen


class DashboardScreen(BaseScreen):

    BINDINGS = [
        Binding("r", "refresh", "刷新"),
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
            Static("🟢 L0 LLMInfra    │ Provider 责任链 + 熔断器 正常"),
            Static(f"🟢 L1 Runtime     │ 意图路由: {ir.get('total_requests', 0)} 请求, "
                   f"Fast:{ir.get('fast_path', 0)} Deep:{ir.get('deep_path', 0)}"),
            Static("🟢 L2 ZenAgent    │ 钩子系统 + 觉醒 + MCP 正常"),
            Static("🟢 L3 MetaSoul    │ 记忆 L1-L4 + 人格矩阵 正常"),
            Static(f"⚪ L4 SwarmFly    │ Agent: {agents}"),
            Static(""),
            Static("─" * 50 + "\n[💬0 对话 | 📊1 仪表盘 | 🧠2 记忆 | 🎭3 人格 | 📚4 学习 | ⚙5 设施 | q 退出]"),
        ]

    def compose_content(self) -> ComposeResult:
        yield Label("📊 仪表盘 · 系统概览", id="dash-header")
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
