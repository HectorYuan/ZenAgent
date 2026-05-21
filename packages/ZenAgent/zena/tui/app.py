"""
ZenaTUIApp — ZenAgent Textual 应用

设计参考: ZenSkill app.py (Textual App + CommandPalette)

用法: ./zena tui
"""

_has_textual = False
try:
    from textual.app import App, ComposeResult
    from textual.widgets import Header, Footer, Static, Label, Input, Button
    from textual.containers import Container, Horizontal, Vertical
    from textual.binding import Binding
    from textual.screen import Screen
    _has_textual = True
except ImportError:
    pass


if _has_textual:

    class ChatScreen(Screen):
        """Chat 核心交互屏幕"""
        BINDINGS = [
            Binding("escape", "app.pop_screen", "Back"),
        ]

        def compose(self) -> ComposeResult:
            yield Header()
            yield Label("💬 Chat · 0 turns", id="chat-header")
            with Vertical(id="chat-messages"):
                yield Static("🧘 ZenAgent ready. Type a message and press Enter.")
            with Horizontal():
                yield Input(placeholder="输入消息... (Enter 发送)", id="chat-input")
                yield Button("Send", id="send-btn", variant="primary")

        async def on_button_pressed(self, event):
            await self._send_message()

        async def on_input_submitted(self, event):
            await self._send_message()

        async def _send_message(self):
            inp = self.query_one("#chat-input", Input)
            text = inp.value.strip()
            if not text:
                return
            inp.value = ""
            msgs = self.query_one("#chat-messages", Vertical)
            await msgs.mount(Static(f"🧑 {text}"))

            # 调用 ZenAgent think
            try:
                from ...core.adapter import ZenaDataAdapter
                adapter = ZenaDataAdapter()
                result = await adapter.chat(text, use_history=False)
                await msgs.mount(Static(f"🧘 {result['content']}"))
            except Exception as e:
                await msgs.mount(Static(f"❌ Error: {e}"))


    class DashboardScreen(Screen):
        """系统仪表盘屏幕"""
        BINDINGS = [
            Binding("escape", "app.pop_screen", "Back"),
        ]

        def compose(self) -> ComposeResult:
            yield Header()
            yield Static("📊 Dashboard — 系统概览")
            with Vertical():
                yield Static("🟢 L0 LLMInfra    · Provider Chain + Cache")
                yield Static("🟢 L1 Runtime     · Sessions + Checkpoint")
                yield Static("🟢 L2 ZenAgent    · Intent Router + Hooks")
                yield Static("🟢 L3 MetaSoul    · Memory L1-L4 + Personality")
                yield Static("⚪ L4 SwarmFly    · No agents registered")
            yield Static("─" * 40 + "\n[Ctrl+R Refresh | 0-5 Switch Screen]")


    class ZenaTUIApp(App):
        """ZenAgent TUI 主应用"""

        TITLE = "ZenAgent"
        SUB_TITLE = "六层智能体平台"
        CSS = """
        Screen { background: #121212; }
        Label { color: #e0e0e0; }
        Static { color: #b0b0b0; }
        Input { background: #2a2a3a; color: #e0e0e0; border: solid #4fc3f7; }
        Button { background: #4fc3f7; color: #121212; }
        """

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
