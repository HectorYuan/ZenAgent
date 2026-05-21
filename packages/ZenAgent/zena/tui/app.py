"""
ZenaTUIApp — ZenAgent Textual 应用

设计参考: ZenSkill app.py (Textual App + CommandPalette)
"""

from textual.app import App, ComposeResult
from textual.command import CommandPalette
from textual.binding import Binding

_has_textual = False
try:
    import textual
    _has_textual = True
except ImportError:
    pass

if _has_textual:
    from textual.widgets import Footer
    from .screens.chat import ChatScreen
    from .screens.dashboard import DashboardScreen

    class ZenaTUIApp(App):
        """ZenAgent TUI 主应用"""

        TITLE = "ZenAgent"
        SUB_TITLE = "六层智能体平台"
        CSS = """
        Screen { background: #121212; }
        #content { width: 1fr; height: 1fr; }
        """

        BINDINGS = [
            Binding("0", "switch_screen('chat')", "Chat"),
            Binding("1", "switch_screen('dashboard')", "Dashboard"),
            Binding("2", "switch_screen('memory')", "Memory"),
            Binding("3", "switch_screen('personality')", "Personality"),
            Binding("4", "switch_screen('learning')", "Learning"),
            Binding("5", "switch_screen('infra')", "Infra"),
            Binding("q", "quit", "Quit"),
            Binding("f1", "help", "Help"),
            Binding("ctrl+r", "refresh", "Refresh"),
        ]

        COMMANDS = {ZenaTUIApp}

        def __init__(self, agent_id: str = "zena-default"):
            super().__init__()
            self.agent_id = agent_id
            self._screens = {}

        def on_mount(self):
            self.push_screen(ChatScreen())

        def action_switch_screen(self, name: str):
            screens = {
                "chat": ChatScreen,
                "dashboard": DashboardScreen,
            }
            screen_cls = screens.get(name)
            if screen_cls:
                self.push_screen(screen_cls())

        def action_refresh(self):
            if self.screen:
                getattr(self.screen, "refresh_data", lambda: None)()

        def action_help(self):
            # 显示帮助覆盖
            pass


def launch_tui(agent_id: str = "zena-default"):
    """启动 TUI"""
    if not _has_textual:
        print("Textual not installed. Install: pip install textual>=0.40.0")
        print("Falling back to CLI mode.")
        return
    app = ZenaTUIApp(agent_id=agent_id)
    app.run()
