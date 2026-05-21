"""
ChatScreen — 核心交互中枢

设计参考: ZenSkill ChatScreen
三级降级: LLM Stream → Mock → Error
"""

_has_textual = False
try:
    import textual
    from textual.app import ComposeResult
    from textual.containers import Container, Vertical, Horizontal
    from textual.widgets import Static, Input, Button, Label
    _has_textual = True
except ImportError:
    pass


if _has_textual:

    class ChatMessage(Static):
        """单条对话消息"""

        def __init__(self, role: str, content: str, meta: str = ""):
            super().__init__()
            self.role = role
            self.content_text = content
            self.meta_text = meta

        def compose(self) -> ComposeResult:
            prefix = "🧘" if self.role == "assistant" else "🧑"
            yield Static(f"{prefix} {self.content_text}", classes=f"msg-{self.role}")
            if self.meta_text:
                yield Static(f"  {self.meta_text}", classes="msg-meta")


    class ChatInput(Static):
        """对话输入区域"""

        def compose(self) -> ComposeResult:
            with Horizontal():
                yield Input(placeholder="输入消息... (Ctrl+Enter 发送)", id="chat-input")
                yield Button("Send", id="send-btn", variant="primary")


    class ChatScreen(Container):
        """Chat 屏幕 — 核心交互"""

        BINDINGS = [
            ("ctrl+enter", "send", "Send"),
            ("ctrl+n", "new_session", "New"),
            ("ctrl+h", "history", "History"),
        ]

        def __init__(self):
            super().__init__()
            self.messages: list[dict] = []
            self.turn_count = 0

        def compose(self) -> ComposeResult:
            yield Label("💬 Chat · 0 turns", id="chat-header")
            yield Container(id="chat-messages")
            yield ChatInput()

        async def on_button_pressed(self, event):
            if event.button.id == "send-btn":
                await self.action_send()

        async def action_send(self):
            inp = self.query_one("#chat-input", Input)
            text = inp.value.strip()
            if not text:
                return
            inp.value = ""
            await self.add_message("user", text)

        async def add_message(self, role: str, content: str, meta: str = ""):
            self.messages.append({"role": role, "content": content})
            self.turn_count += 1
            container = self.query_one("#chat-messages")
            prefix = "🧘" if role == "assistant" else "🧑"
            await container.mount(Static(f"{prefix} {content}"))
            if meta:
                await container.mount(Static(f"  {meta}", classes="msg-meta"))
            self.query_one("#chat-header").update(f"💬 Chat · {self.turn_count} turns")

        def action_new_session(self):
            self.messages.clear()
            self.turn_count = 0
            container = self.query_one("#chat-messages")
            container.remove_children()
            self.query_one("#chat-header").update("💬 Chat · 0 turns")

        def refresh_data(self):
            pass
