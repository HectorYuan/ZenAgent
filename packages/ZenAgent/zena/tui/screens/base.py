"""
BaseScreen — 统一屏幕基类

Header + NavSidebar + Content + Footer 布局
参考: ZenSkill screens/base.py
"""

from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Footer
from textual.binding import Binding


class BaseScreen(Screen):
    """基础屏幕 — Header + NavSidebar + Content + Footer"""

    BINDINGS = [
        Binding("escape", "blur_or_back", "返回", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            from ..app import NavSidebar
            yield NavSidebar()
            yield from self.compose_content()
        yield Footer()

    def compose_content(self) -> ComposeResult:
        """子类覆写：提供主体内容"""
        from textual.widgets import Static
        yield Static("")

    def action_blur_or_back(self):
        """Escape: 先失焦，再返回"""
        focused = getattr(self.app, 'focused', None)
        if focused is not None and hasattr(focused, 'blur'):
            focused.blur()
        elif len(getattr(self.app, 'screen_stack', [])) > 1:
            self.app.pop_screen()

    def refresh_screen(self):
        """子类覆写：刷新数据"""
        pass
