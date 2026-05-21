"""
BaseScreen — TUI 屏幕基类

设计参考: ZenSkill BaseScreen
提供统一布局: Header + NavSidebar + Content + Footer
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer, Static


class BaseScreen(Screen):
    """
    基础屏幕

    布局:
      Header
      Horizontal(NavSidebar | Content)
      Footer
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield Static("")  # Nav placeholder (overridden)
            yield Container(self.compose_content(), id="content")
        yield Footer()

    def compose_content(self):
        """Override: return main content widget"""
        return Static("Content Area")

    def action_refresh(self):
        """Ctrl+R 刷新"""
        self.refresh_data()

    def refresh_data(self):
        """Override: 从 adapter 刷新数据"""
        pass

    def action_quit(self):
        self.app.exit()
