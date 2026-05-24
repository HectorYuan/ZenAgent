from .base import BaseScreen
"""
PersonalityScreen — 人格管理屏幕 (T4)

Big Five 条形图 + 场景选择 + 交叉效应面板
"""


from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Label, Button
from textual.binding import Binding

SCENARIO_NAMES = [
    "casual_chat", "technical_qa", "creative", "decision",
    "debate", "teaching", "emotional_support", "code_review",
]


def _bar(value: float, width: int = 30) -> str:
    filled = int(min(value, 1.0) * width)
    return "█" * filled + "░" * (width - filled)


class PersonalityScreen(BaseScreen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
    ]

    DEFAULT_CSS = """
    PersonalityScreen { background: $surface; }
    #pers-header { dock: top; height: 1; background: $panel; color: $text-muted; padding: 0 1; }
    #pers-content { height: 1fr; overflow-y: auto; padding: 0 1; }
    #pers-scenarios { dock: bottom; height: 3; background: $panel; padding: 1; }
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
        yield Label("🎭 Personality · Big Five", id="pers-header")
        with ScrollableContainer(id="pers-content"):
            yield Static("Press [r] to refresh", classes="pers-trait")
        with Vertical(id="pers-scenarios"):
            with Horizontal():
                for s in SCENARIO_NAMES[:4]:
                    yield Button(s, id=f"s-{s}")
            with Horizontal():
                for s in SCENARIO_NAMES[4:]:
                    yield Button(s, id=f"s-{s}")

    def on_mount(self):
        self.refresh_data()

    async def on_button_pressed(self, event):
        if event.button.id and event.button.id.startswith("s-"):
            self.notify(f"Scenario: {event.button.id[2:]}")

    def action_refresh(self):
        self.refresh_data()

    def refresh_data(self):
        adapter = self._get_adapter()
        traits = adapter.personality_traits()
        content = self.query_one("#pers-content", ScrollableContainer)
        content.remove_children()

        for trait, val in traits.items():
            bar = _bar(val)
            content.mount(Static(f"  {trait:<20} {bar} {val:.2f}"))

        # Cross effects
        o, c, e, a, n = (traits.get(k, 0.5) for k in
                          ["openness", "conscientiousness", "extraversion",
                           "agreeableness", "neuroticism"])
        effects = []
        if o > .65 and e > .65: effects.append("O+E: Explorer-Social")
        if o > .65 and c > .65: effects.append("O+C: Creative Executor")
        if c > .65 and n > .65: effects.append("C+N: Perfectionist")
        if a > .65 and e > .65: effects.append("A+E: Natural Connector")
        if o > .65 and n < .35: effects.append("O+LowN: Creative Fearless")
        if e < .35 and o > .65: effects.append("LowE+O: Deep Thinker")
        if a < .35 and c > .65: effects.append("LowA+C: Rigorous Direct")
        if effects:
            content.mount(Static("  Cross Effects:", classes=""))
            for ef in effects:
                content.mount(Static(f"  • {ef}"))
