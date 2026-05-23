"""
ZenaTUIApp — ZenAgent Textual 应用

设计参考: ZenSkill app.py (Textual App + Screen switching)

用法: ./zena tui
"""

_has_textual = False
try:
    from textual.app import App
    from textual.binding import Binding
    from textual.widgets import Footer
    _has_textual = True
except ImportError:
    pass


if _has_textual:

    from .screens.chat import ChatScreen
    from .screens.dashboard import DashboardScreen

    class ZenaTUIApp(App):
        """ZenAgent TUI 主应用"""

        TITLE = "ZenAgent"
        SUB_TITLE = "六层智能体平台"

        BINDINGS = [
            Binding("0", "switch_screen('chat')", "Chat"),
            Binding("1", "switch_screen('dashboard')", "Dashboard"),
            Binding("q", "quit", "Quit"),
            Binding("ctrl+r", "refresh", "Refresh"),
        ]

        SCREENS = {
            "chat": ChatScreen,
            "dashboard": DashboardScreen,
        }

        def on_mount(self):
            self.push_screen(ChatScreen())

        def action_switch_screen(self, name: str):
            screen_cls = self.SCREENS.get(name)
            if screen_cls:
                self.push_screen(screen_cls())


def launch_tui(agent_id: str = "zena-default"):
    """启动 TUI"""
    if not _has_textual:
        print("Textual not installed. Install: pip install textual>=0.40.0")
        return
    app = ZenaTUIApp()
    app.run()
