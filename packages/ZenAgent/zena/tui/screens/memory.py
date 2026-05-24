"""
MemoryScreen — 记忆管理屏幕 (T3)

四层热度图 + 搜索 + SPO 三元组浏览 + 淘汰/整合
"""
from .base import BaseScreen


from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Label, Input, Button
from textual.binding import Binding


class MemoryScreen(BaseScreen):
    """记忆管理屏幕"""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("e", "evict", "Evict"),
        Binding("c", "consolidate", "Consolidate"),
    ]

    DEFAULT_CSS = """
    MemoryScreen {
        background: $surface;
    }
    #mem-header {
        dock: top;
        height: 1;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }
    #mem-content {
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
    }
    #mem-search-area {
        dock: bottom;
        height: 3;
        background: $panel;
        padding: 1;
    }
    .mem-tier {
        color: $primary;
        margin: 1 0 0 0;
    }
    .mem-item {
        color: $text;
        margin: 0 0 0 2;
    }
    .mem-meta {
        color: $text-disabled;
        margin: 0 0 0 4;
    }
    .mem-triple {
        color: $accent;
        margin: 0 0 0 2;
    }
    """

    def __init__(self):
        super().__init__()
        self._adapter = None

    def _get_adapter(self):
        if self._adapter is None:
            from ...core.adapter import ZenaDataAdapter
            self._adapter = ZenaDataAdapter()
        return self._adapter

    def compose_content(self) -> ComposeResult:
        yield Label("🧠 Memory · L1(Hot) L2(Warm) L3(Semantic) L4(Archive)", id="mem-header")
        with ScrollableContainer(id="mem-content"):
            yield Static("Press [r] to refresh, [e] to evict, [c] to consolidate", classes="mem-meta")
        with Horizontal(id="mem-search-area"):
            yield Input(placeholder="Search memory...", id="mem-search")
            yield Button("Search", id="mem-search-btn", variant="primary")
            yield Button("Stats", id="mem-stats-btn", variant="default")
            yield Button("Triples", id="mem-triples-btn", variant="default")

    def on_mount(self):
        self.refresh_data()

    async def on_button_pressed(self, event):
        btn = event.button.id
        if btn == "mem-search-btn":
            await self._do_search()
        elif btn == "mem-stats-btn":
            await self._show_stats()
        elif btn == "mem-triples-btn":
            await self._show_triples()

    async def on_input_submitted(self, event):
        if event.input.id == "mem-search":
            await self._do_search()

    async def _do_search(self):
        query = self.query_one("#mem-search", Input).value.strip()
        if not query:
            return
        adapter = self._get_adapter()
        results = adapter.memory_search(query, limit=20)
        content = self.query_one("#mem-content", ScrollableContainer)
        content.remove_children()
        await content.mount(Static(f"🔍 Results for: {query} ({len(results)} found)", classes="mem-meta"))
        if not results:
            await content.mount(Static("  [no results]", classes="mem-meta"))
        for r in results:
            await content.mount(Static(f"  📝 {r.get('content', '')[:120]}", classes="mem-item"))
            await content.mount(Static(f"     type={r.get('type','?')} importance={r.get('importance','?')}",
                                       classes="mem-meta"))

    async def _show_stats(self):
        adapter = self._get_adapter()
        stats = adapter.memory_stats()
        content = self.query_one("#mem-content", ScrollableContainer)
        content.remove_children()
        await content.mount(Static("📊 Memory Statistics", classes="mem-tier"))
        items = [
            f"L1 Hot:  {stats.get('working_memory_count', '?')}",
            f"L2 Warm: {stats.get('episodic_memory_count', '?')}",
            f"L3 Semantic: {stats.get('semantic_memory_count', '?')}",
            f"L4 Archive: {stats.get('procedural_memory_count', '?')}",
            f"Total: {stats.get('total_memories', '?')}",
        ]
        for item in items:
            await content.mount(Static(f"  {item}", classes="mem-item"))

        # Hotspot info if available
        hotspot = stats.get("hotspot", {})
        if hotspot:
            await content.mount(Static(f"  Cache Hit Rate: {hotspot.get('hit_rate', 0):.1%}", classes="mem-meta"))
            await content.mount(Static(f"  Hot Keys: {hotspot.get('hot_keys', 0)}", classes="mem-meta"))

    async def _show_triples(self):
        adapter = self._get_adapter()
        kb_stats = adapter.knowledge_stats()
        content = self.query_one("#mem-content", ScrollableContainer)
        content.remove_children()
        await content.mount(Static("📚 Knowledge Base (SPO Triples)", classes="mem-tier"))
        await content.mount(Static(f"  Total Triples: {kb_stats.get('total_triples', 0)}", classes="mem-item"))
        await content.mount(Static(f"  Total Entities: {kb_stats.get('total_entities', 0)}", classes="mem-item"))
        await content.mount(Static(f"  Conflicts: {kb_stats.get('total_conflicts', 0)}", classes="mem-meta"))

    def action_refresh(self):
        self.refresh_data()

    def refresh_data(self):
        import asyncio
        asyncio.create_task(self._show_stats())

    def action_evict(self):
        """运行记忆淘汰"""
        adapter = self._get_adapter()
        agent = adapter._get_agent()
        if agent.memory:
            result = agent.memory.run_eviction_cycle()
            self.notify(f"Evicted: {result.get('evicted', 0)} memories")
            import asyncio
            asyncio.create_task(self._show_stats())

    def action_consolidate(self):
        """运行记忆整合"""
        adapter = self._get_adapter()
        agent = adapter._get_agent()
        if agent.memory and hasattr(agent.memory, 'pipeline') and agent.memory.pipeline:
            import asyncio
            asyncio.create_task(agent.memory.pipeline.flush())
            self.notify("Consolidation triggered")
            asyncio.create_task(self._show_stats())
