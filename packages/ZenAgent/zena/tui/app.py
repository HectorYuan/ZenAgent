"""
ZenaTUIApp — ZenAgent Textual 应用

设计参考: ZenSkill app.py（NavSidebar + 三层键绑定 + 中文优先）

用法: ./zena tui
"""

import sys

_has_textual = False
try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.widgets import Header, Footer, Button
    from textual.containers import Horizontal, Vertical
    from textual.screen import Screen
    _has_textual = True
except ImportError:
    pass

if _has_textual:

    # ---- NavSidebar ----
    NAV_ITEMS = [
        ("💬 0", "chat"),
        ("📊 1", "dashboard"),
        ("🧠 2", "memory"),
        ("🎭 3", "personality"),
        ("📚 4", "learning"),
        ("⚙ 5", "infra"),
    ]

    class NavSidebar(Vertical):
        DEFAULT_CSS = """
        NavSidebar {
            width: 10; height: 1fr;
            background: $surface;
            border-right: solid $primary-background;
        }
        NavSidebar Button { width: 100%; height: 3; margin: 0; }
        """
        BINDINGS = [
            Binding("up", "focus_prev", "上", show=False),
            Binding("down", "focus_next", "下", show=False),
            Binding("enter", "activate_current", "进入", show=False),
        ]

        def compose(self) -> ComposeResult:
            for label, screen_id in NAV_ITEMS:
                yield Button(label, id=f"nav-{screen_id}", variant="default")

        def on_mount(self):
            self.set_interval(0.5, self._refresh_active)

        def _refresh_active(self):
            app = self.app
            if not app or not app.screen:
                return
            for _, screen_id in NAV_ITEMS:
                btn = self.query_one(f"#nav-{screen_id}")
                is_active = app.screen.__class__.__name__.lower().startswith(screen_id)
                btn.variant = "primary" if is_active else "default"

        def action_focus_prev(self):
            btns = list(self.query(Button))
            if self.app.focused in btns:
                idx = btns.index(self.app.focused)
                btns[(idx - 1) % len(btns)].focus()

        def action_focus_next(self):
            btns = list(self.query(Button))
            if self.app.focused in btns:
                idx = btns.index(self.app.focused)
                btns[(idx + 1) % len(btns)].focus()

        def action_activate_current(self):
            if self.app.focused and hasattr(self.app.focused, 'press'):
                self.app.focused.press()

    # ---- Import screens ----
    from .screens.chat import ChatScreen
    from .screens.dashboard import DashboardScreen
    from .screens.memory import MemoryScreen
    from .screens.personality import PersonalityScreen
    from .screens.learning import LearningScreen
    from .screens.infra import InfraScreen

    # ---- Main App ----
    class ZenaTUIApp(App):
        TITLE = "ZenAgent"
        SUB_TITLE = "六层智能体平台"

        BINDINGS = [
            Binding("0", "switch_screen('chat')", "对话", show=True, priority=True),
            Binding("1", "switch_screen('dashboard')", "仪表盘", show=True, priority=True),
            Binding("2", "switch_screen('memory')", "记忆", show=True, priority=True),
            Binding("3", "switch_screen('personality')", "人格", show=True, priority=True),
            Binding("4", "switch_screen('learning')", "学习", show=True, priority=True),
            Binding("5", "switch_screen('infra')", "设施", show=True, priority=True),
            Binding("ctrl+r", "refresh", "刷新", show=True),
            Binding("q", "quit", "退出", show=True),
        ]

        SCREENS = {
            "chat": ChatScreen,
            "dashboard": DashboardScreen,
            "memory": MemoryScreen,
            "personality": PersonalityScreen,
            "learning": LearningScreen,
            "infra": InfraScreen,
        }

        def on_mount(self):
            self.push_screen(ChatScreen())

        def action_switch_screen(self, name: str):
            screen_cls = self.SCREENS.get(name)
            if not screen_cls:
                return
            current = self.screen
            if current and current.__class__ == screen_cls:
                return
            # Replace current screen (don't stack)
            for _ in range(len(self.screen_stack) - 1):
                self.pop_screen()
            self.switch_screen(screen_cls())

        def action_refresh(self):
            if self.screen and hasattr(self.screen, 'refresh_screen'):
                self.screen.refresh_screen()


def launch_tui(agent_id: str = "zena-default"):
    if not _has_textual or not sys.stdout.isatty():
        print("终端不支持 TUI。使用 CLI 模式: ./zena chat")
        return
    try:
        app = ZenaTUIApp()
        app.run()
    except Exception as e:
        print(f"TUI 启动失败: {e}")
        from .command_mode import launch_command_mode
        launch_command_mode(agent_id)
