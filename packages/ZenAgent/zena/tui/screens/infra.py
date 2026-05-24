"""
InfraScreen — 基础设施屏幕 (T6)

Provider 健康 + Agent 列表 + 缓存状态 + 配置
"""

from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Horizontal
from textual.widgets import Static, Label, Button
from textual.binding import Binding


class InfraScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
    ]

    DEFAULT_CSS = """
    InfraScreen { background: $surface; }
    #infra-header { dock: top; height: 1; background: $panel; color: $text-muted; padding: 0 1; }
    #infra-content { height: 1fr; overflow-y: auto; padding: 0 1; }
    #infra-actions { dock: bottom; height: 3; background: $panel; padding: 1; }
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
        yield Label("⚙ Infra · Providers & Agents", id="infra-header")
        with ScrollableContainer(id="infra-content"):
            yield Static("Press [r] to refresh, click buttons for details")
        with Horizontal(id="infra-actions"):
            yield Button("Providers", id="btn-prov", variant="primary")
            yield Button("Cache", id="btn-cache", variant="default")
            yield Button("Agents", id="btn-agents", variant="default")
            yield Button("Doctor", id="btn-doctor", variant="default")

    def on_mount(self):
        self._show_default()

    async def on_button_pressed(self, event):
        btn = event.button.id
        if btn == "btn-prov": await self._show_providers()
        elif btn == "btn-cache": await self._show_cache()
        elif btn == "btn-agents": await self._show_agents()
        elif btn == "btn-doctor": await self._show_doctor()

    def action_refresh(self): self._show_default()

    def _show_default(self):
        content = self.query_one("#infra-content", ScrollableContainer)
        content.remove_children()
        content.mount(Static("⚙ Infrastructure Dashboard"))
        content.mount(Static(""))
        content.mount(Static("  L0 LLMInfra · Providers / Cache / Circuit Breakers"))
        content.mount(Static("  L1 Runtime  · Sessions / Checkpoints / HTL"))
        content.mount(Static("  L2 SwarmFly · Agents / Teams / Tasks"))
        content.mount(Static("  L3 MetaSoul · Memory / Personality / Learning"))
        content.mount(Static(""))
        content.mount(Static("  Click buttons below or press [r] to refresh"))

    async def _show_providers(self):
        adapter = self._get_adapter()
        content = self.query_one("#infra-content", ScrollableContainer)
        content.remove_children()
        content.mount(Static("🔌 Providers"))
        providers = adapter.provider_list()
        if providers:
            for p in providers:
                content.mount(Static(f"  🟢 {p}"))
        else:
            content.mount(Static("  No providers configured"))
        health = adapter.provider_health()
        if health.get("circuit_breakers"):
            content.mount(Static("\n  Circuit Breakers:"))
            for name, cb in health["circuit_breakers"].items():
                state = cb.get("state", "?")
                icon = "🟢" if state == "closed" else "🔴"
                content.mount(Static(f"  {icon} {name}: {state}"))

    async def _show_cache(self):
        adapter = self._get_adapter()
        content = self.query_one("#infra-content", ScrollableContainer)
        content.remove_children()
        content.mount(Static("📦 Cache"))
        stats = adapter.cache_stats()
        hotspot = stats.get("hotspot", {})
        content.mount(Static(f"  Hit Rate: {hotspot.get('hit_rate', 0):.1%}"))
        content.mount(Static(f"  Hot Keys: {hotspot.get('hot_keys', 0)}"))
        content.mount(Static(f"  Warm Keys: {hotspot.get('warm_keys', 0)}"))
        content.mount(Static(f"  Precache Tasks: {stats.get('precache', {}).get('total_tasks', 0)}"))

    async def _show_agents(self):
        adapter = self._get_adapter()
        content = self.query_one("#infra-content", ScrollableContainer)
        content.remove_children()
        content.mount(Static("🤖 Agents"))
        agents = adapter.agents_list()
        if agents:
            for a in agents:
                content.mount(Static(f"  🟢 {a}"))
        else:
            content.mount(Static("  No agents registered"))
        sessions = adapter.sessions_list()
        if sessions:
            content.mount(Static(f"\n  Sessions: {len(sessions)} active"))

    async def _show_doctor(self):
        adapter = self._get_adapter()
        content = self.query_one("#infra-content", ScrollableContainer)
        content.remove_children()
        content.mount(Static("🩺 System Health"))
        health = adapter.get_system_health()
        for name, info in health.items():
            icon = "🟢" if info.get("healthy") else "🔴"
            content.mount(Static(f"  {icon} {name}: {info.get('name', name)}"))
