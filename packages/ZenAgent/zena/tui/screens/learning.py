"""
LearningScreen — 学习/进化屏幕 (T6)
"""
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Horizontal
from textual.widgets import Static, Label, Button
from textual.binding import Binding
from .base import BaseScreen


class LearningScreen(BaseScreen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "返回"),
        Binding("r", "refresh", "刷新"),
        Binding("l", "learn", "学习"),
        Binding("f", "reflect", "反思"),
    ]
    DEFAULT_CSS = """
    LearningScreen { background: $surface; }
    #learn-header { dock: top; height: 1; background: $panel; color: $text-muted; padding: 0 1; }
    #learn-content { height: 1fr; overflow-y: auto; padding: 0 1; }
    #learn-actions { dock: bottom; height: 3; background: $panel; padding: 1; }
    """

    def __init__(self): super().__init__(); self._adapter = None
    def _get_adapter(self):
        if self._adapter is None:
            from ...core.adapter import ZenaDataAdapter
            self._adapter = ZenaDataAdapter()
        return self._adapter

    def compose_content(self) -> ComposeResult:
        yield Label("📚 学习 & 进化", id="learn-header")
        with ScrollableContainer(id="learn-content"):
            yield Static("按 [r] 刷新  [l] 学习周期  [f] 反思")
        with Horizontal(id="learn-actions"):
            yield Button("学习周期", id="btn-learn", variant="primary")
            yield Button("反思", id="btn-reflect", variant="default")
            yield Button("统计", id="btn-stats", variant="default")
            yield Button("技能", id="btn-skills", variant="default")

    def on_mount(self): self._show_default()
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
        content.mount(Static("📖 学习 & 反思面板"))
        content.mount(Static("  OBSERVE → REFLECT → GENERALIZE → VERIFY → INTEGRATE"))
        content.mount(Static("  [l] 运行学习周期  [f] 运行反思"))

    async def _show_learn(self):
        content = self.query_one("#learn-content", ScrollableContainer)
        content.remove_children()
        content.mount(Static("🔄 学习周期 (O-R-G-V-I)"))
        for i, step in enumerate(["观察: 分析近期交互", "反思: 发现结果模式",
                                   "归纳: 提取可复用洞察", "验证: 对照历史经验",
                                   "整合: 存入语义记忆"], 1):
            content.mount(Static(f"  {i}. {step}"))
        adapter = self._get_adapter(); agent = adapter._get_agent()
        if agent._experience_loop:
            stats = agent._experience_loop.get_stats()
            content.mount(Static(f"\n  经验循环: {stats['interaction_count']} 轮交互"))
            content.mount(Static(f"  下次跨会话: {stats['next_cross_session']} 轮后"))

    async def _show_reflect(self):
        content = self.query_one("#learn-content", ScrollableContainer)
        content.remove_children()
        content.mount(Static("🔍 反思深度"))
        for depth in ["表象: 即时反应分析", "因果: 为何产生此结果?", "意义: 可推广的经验?", "蜕变: 如何根本改进?"]:
            content.mount(Static(f"  {depth}"))

    async def _show_stats(self):
        content = self.query_one("#learn-content", ScrollableContainer)
        content.remove_children()
        content.mount(Static("📊 学习统计"))
        adapter = self._get_adapter(); agent = adapter._get_agent()
        loop_stats = {}
        if agent._experience_loop: loop_stats = agent._experience_loop.get_stats()
        content.mount(Static(f"  交互: {loop_stats.get('interaction_count', 0)}"))
        content.mount(Static(f"  学习器: {loop_stats.get('learner', '?')}"))
        content.mount(Static(f"  反思器: {loop_stats.get('reflector', '?')}"))
        content.mount(Static(f"  管线: {loop_stats.get('pipeline', '?')}"))
        kb = agent.memory.pipeline.get_kb_stats() if agent.memory and hasattr(agent.memory, 'pipeline') and agent.memory.pipeline else {}
        content.mount(Static(f"  知识三元组: {kb.get('total_triples', '?')}"))
        content.mount(Static(f"  实体: {kb.get('total_entities', '?')}"))

    async def _show_skills(self):
        content = self.query_one("#learn-content", ScrollableContainer)
        content.remove_children()
        content.mount(Static("🛠 技能等级"))
        for level in ["🌱 入门 → 理解基础", "🌿 学徒 → 指导练习", "🪴 熟练 → 独立执行", "🌳 专家 → 指导他人", "🏆 大师 → 创新"]:
            content.mount(Static(f"  {level}"))

    def action_learn(self):
        import asyncio; asyncio.create_task(self._show_learn()); self.notify("学习周期已触发")
    def action_reflect(self):
        import asyncio; asyncio.create_task(self._show_reflect()); self.notify("反思已触发")
