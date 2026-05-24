"""
ZenaTUIApp — ZenAgent Textual 应用

设计参考: ZenSkill app.py (Textual App + Screen switching)

用法: ./zena tui
"""

import sys

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
    from .screens.memory import MemoryScreen
    from .screens.personality import PersonalityScreen
    from .screens.learning import LearningScreen
    from .screens.infra import InfraScreen

    class ZenaTUIApp(App):
        """ZenAgent TUI 主应用"""

        TITLE = "ZenAgent"
        SUB_TITLE = "六层智能体平台"

        BINDINGS = [
            Binding("0", "switch_screen('chat')", "Chat"),
            Binding("1", "switch_screen('dashboard')", "Dashboard"),
            Binding("2", "switch_screen('memory')", "Memory"),
            Binding("3", "switch_screen('personality')", "Personality"),
            Binding("4", "switch_screen('learning')", "Learning"),
            Binding("5", "switch_screen('infra')", "Infra"),
            Binding("q", "quit", "Quit"),
            Binding("ctrl+r", "refresh", "Refresh"),
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
            if screen_cls:
                self.push_screen(screen_cls())


def launch_tui(agent_id: str = "zena-default"):
    """启动 TUI (带 Rich 降级)"""
    # 检测 TTY
    if not _has_textual or not sys.stdout.isatty():
        print("Textual unavailable or non-TTY terminal.")
        print("Falling back to Rich command mode...")
        from .command_mode import launch_command_mode as _launch_rich
        _launch_rich(agent_id)
        return

    try:
        app = ZenaTUIApp()
        app.run()
    except Exception as e:
        print(f"TUI failed: {e}")
        print("Falling back to Rich command mode...")
        from .command_mode import launch_command_mode as _launch_rich
        _launch_rich(agent_id)
