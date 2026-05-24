"""
LearningScreen — 学习/进化屏幕 (T6)

学习周期 + 技能树 + 洞察时间线 + 反思
"""

from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Horizontal
from textual.widgets import Static, Label, Button
from textual.binding import Binding


class LearningScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("l", "learn", "Learn"),
        Binding("f", "reflect", "Reflect"),
    ]

    DEFAULT_CSS = """
    LearningScreen { background: $surface; }
    #learn-header { dock: top; height: 1; background: $panel; color: $text-muted; padding: 0 1; }
    #learn-content { height: 1fr; overflow-y: auto; padding: 0 1; }
    #learn-actions { dock: bottom; height: 3; background: $panel; padding: 1; }
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
        yield Label("📚 Learning & Evolution", id="learn-header")
        with ScrollableContainer(id="learn-content"):
            yield Static("Press [r] refresh  [l] learn cycle  [f] reflect")
        with Horizontal(id="learn-actions"):
            yield Button("Learn Cycle", id="btn-learn", variant="primary")
            yield Button("Reflect", id="btn-reflect", variant="default")
            yield Button("Stats", id="btn-stats", variant="default")
            yield Button("Skills", id="btn-skills", variant="default")

    def on_mount(self):
        self._show_default()

    async def on_button_pressed(self, event):
        btn = event.button.id
        if btn == "btn-learn": await self._show_learn()
        elif btn == "btn-reflect": await self._show_reflect()
        elif btn == "btn-stats": await self._show_stats()
        elif btn == "btn-skills": await self._show_skills()

    def action_refresh(self): self._show_default()

    def _show_default(self):
        content = self.query_one("#learn-content", ScrollableContainer)
        content.remove_children()
        content.mount(Static("📖 Learning & Reflection Dashboard"))
        content.mount(Static(""))
        content.mount(Static("  OBSERVE → REFLECT → GENERALIZE → VERIFY → INTEGRATE"))
        content.mount(Static(""))
        content.mount(Static("  [l] Run learning cycle on recent interactions"))
        content.mount(Static("  [f] Run reflection on recent experiences"))
        content.mount(Static("  Click buttons below for details"))

    async def _show_learn(self):
        content = self.query_one("#learn-content", ScrollableContainer)
        content.remove_children()
        content.mount(Static("🔄 Learning Cycle (O-R-G-V-I)"))
        content.mount(Static("  1. OBSERVE: Analyze recent interactions"))
        content.mount(Static("  2. REFLECT: Find patterns in outcomes"))
        content.mount(Static("  3. GENERALIZE: Extract reusable insights"))
        content.mount(Static("  4. VERIFY: Test against past experience"))
        content.mount(Static("  5. INTEGRATE: Store in semantic memory"))

        adapter = self._get_adapter()
        agent = adapter._get_agent()
        if agent._experience_loop:
            stats = agent._experience_loop.get_stats()
            content.mount(Static(f"\n  Experience Loop: {stats['interaction_count']} interactions"))
            content.mount(Static(f"  Next cross-session: {stats['next_cross_session']} turns"))
        content.mount(Static("\n  ℹ Learning runs automatically after each interaction"))

    async def _show_reflect(self):
        content = self.query_one("#learn-content", ScrollableContainer)
        content.remove_children()
        content.mount(Static("🔍 Reflection Depths"))
        content.mount(Static("  SURFACE: Immediate reaction analysis"))
        content.mount(Static("  CAUSAL: Why did this outcome occur?"))
        content.mount(Static("  MEANING: What broader lessons apply?"))
        content.mount(Static("  TRANSFORMATIVE: How to fundamentally improve?"))
        content.mount(Static(""))
        content.mount(Static("  Reflection runs automatically; insights stored in L3 semantic memory"))

    async def _show_stats(self):
        content = self.query_one("#learn-content", ScrollableContainer)
        content.remove_children()
        content.mount(Static("📊 Learning Statistics"))
        adapter = self._get_adapter()
        agent = adapter._get_agent()
        loop_stats = {}
        if agent._experience_loop:
            loop_stats = agent._experience_loop.get_stats()
        content.mount(Static(f"  Interactions: {loop_stats.get('interaction_count', 0)}"))
        content.mount(Static(f"  Learner: {loop_stats.get('learner', '?')}"))
        content.mount(Static(f"  Reflector: {loop_stats.get('reflector', '?')}"))
        content.mount(Static(f"  Pipeline: {loop_stats.get('pipeline', '?')}"))

        kb = agent.memory.pipeline.get_kb_stats() if agent.memory and hasattr(agent.memory, 'pipeline') and agent.memory.pipeline else {}
        content.mount(Static(f"  Knowledge Triples: {kb.get('total_triples', '?')}"))
        content.mount(Static(f"  Entities: {kb.get('total_entities', '?')}"))

    async def _show_skills(self):
        content = self.query_one("#learn-content", ScrollableContainer)
        content.remove_children()
        content.mount(Static("🛠 Skill Levels"))
        content.mount(Static("  🌱 NOVICE     → understanding basics"))
        content.mount(Static("  🌿 APPRENTICE → guided practice"))
        content.mount(Static("  🪴 ADEPT      → independent execution"))
        content.mount(Static("  🌳 EXPERT     → teaching others"))
        content.mount(Static("  🏆 MASTER     → innovation"))
        content.mount(Static(""))
        content.mount(Static("  Skills evolve through interaction history and feedback"))

    def action_learn(self):
        import asyncio
        asyncio.create_task(self._show_learn())
        self.notify("Learning cycle triggered")

    def action_reflect(self):
        import asyncio
        asyncio.create_task(self._show_reflect())
        self.notify("Reflection triggered")
