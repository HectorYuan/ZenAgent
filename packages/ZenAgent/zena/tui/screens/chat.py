"""
ChatScreen — 核心交互中枢 (T2)

流式渲染 + 推理折叠 + 对话历史 + 输入历史 + 三级降级
参考: ZenSkill ChatScreen 模式
"""

from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Label, Header, Input, Button
from textual.binding import Binding

import asyncio


class ReasoningWidget(Static):
    """推理折叠组件 — 点击展开/折叠"""

    DEFAULT_CSS = """
    ReasoningWidget {
        color: $text-muted;
        margin: 1 0;
        padding: 1;
        border: solid $primary-darken-2;
        height: auto;
    }
    ReasoningWidget > .reasoning-preview {
        color: $text-muted;
        text-style: italic;
    }
    ReasoningWidget > .reasoning-full {
        color: $text-disabled;
        margin-top: 1;
    }
    """

    def __init__(self, content: str):
        super().__init__()
        self._content = content
        self._expanded = False
        self._preview = content[:150].replace("\n", " ") + "..."

    def on_click(self):
        self._expanded = not self._expanded
        self.update(self._render())

    def _render(self):
        if self._expanded:
            return f"💭 Reasoning:\n{self._content}\n[click to collapse]"
        return f"💭 {self._preview} [click to expand]"

    def on_mount(self):
        self.update(self._render())


class ChatScreen(Screen):
    """Chat 核心交互屏幕 — 流式 + 推理折叠 + 历史"""

    BINDINGS = [
        Binding("escape", "blur_input", "Blur"),
        Binding("ctrl+n", "new_session", "New Session"),
        Binding("ctrl+s", "save_session", "Save"),
    ]

    DEFAULT_CSS = """
    ChatScreen {
        background: $surface;
    }
    #chat-header {
        dock: top;
        height: 1;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }
    #chat-messages {
        height: 1fr;
        overflow-y: auto;
    }
    #chat-input-area {
        dock: bottom;
        height: auto;
        background: $panel;
        padding: 1;
    }
    #chat-input {
        width: 1fr;
    }
    .msg-user {
        color: $text;
        margin: 1 0 0 4;
    }
    .msg-agent {
        color: $success;
        margin: 1 4 0 0;
    }
    .msg-streaming {
        color: $success-lighten-1;
        text-style: italic;
    }
    .msg-meta {
        color: $text-disabled;
        text-style: italic;
        margin-bottom: 1;
    }
    .msg-error {
        color: $error;
        margin: 1 0;
    }
    .msg-system {
        color: $text-muted;
        text-style: italic;
        margin: 0 0;
    }
    """

    def __init__(self):
        super().__init__()
        self.turn_count = 0
        self._input_history: list[str] = []
        self._history_idx = -1
        self._streaming = False
        self._adapter = None

    def compose(self) -> ComposeResult:
        yield Label("💬 Chat · 0 turns · provider: auto", id="chat-header")
        with ScrollableContainer(id="chat-messages"):
            yield Static("🧘 ZenAgent ready. Type and press Enter to start.", classes="msg-system")
        with Horizontal(id="chat-input-area"):
            yield Input(placeholder="Enter message... (Enter send, Ctrl+N new)", id="chat-input")
            yield Button("Send", id="send-btn", variant="primary")

    def on_mount(self):
        self._adapter = None  # Lazy init on first send
        self.query_one("#chat-input").focus()

    def _get_adapter(self):
        if self._adapter is None:
            from ...core.adapter import ZenaDataAdapter
            self._adapter = ZenaDataAdapter()
        return self._adapter

    # ---- Event Handlers ----

    async def on_button_pressed(self, event):
        if event.button.id == "send-btn":
            await self._send()

    async def on_input_submitted(self, event):
        await self._send()

    def on_key(self, event):
        """全局快捷键处理"""
        if event.key == "escape":
            self.query_one("#chat-input").blur()

    # ---- Send Message ----

    async def _send(self):
        if self._streaming:
            return
        inp = self.query_one("#chat-input", Input)
        text = inp.value.strip()
        if not text:
            return
        inp.value = ""
        self._input_history.append(text)

        # Display user message
        msgs = self.query_one("#chat-messages", ScrollableContainer)
        await msgs.mount(Static(f"🧑 {text}", classes="msg-user"))

        # Try streaming first, fall back to regular chat
        try:
            await self._stream_response(text, msgs)
        except Exception:
            try:
                await self._fallback_chat(text, msgs)
            except Exception as e:
                await msgs.mount(Static(f"❌ {e}", classes="msg-error"))

        # Scroll to bottom
        msgs.scroll_end(animate=False)

    async def _stream_response(self, text: str, msgs: ScrollableContainer):
        """流式渲染 (三级降级: stream → think_stream → fallback)"""
        adapter = self._get_adapter()
        self._streaming = True

        # 尝试真正的流式 API (chat_stream)
        try:
            streaming_widget = None
            full_content = ""

            async for chunk in adapter.chat_stream(text, use_history=True):
                if chunk["type"] == "token":
                    full_content += chunk["content"]
                    if streaming_widget is None:
                        streaming_widget = Static(f"🧘 {full_content}", classes="msg-streaming")
                        await msgs.mount(streaming_widget)
                    else:
                        # 截断显示避免 UI 卡顿
                        display = full_content[-500:] if len(full_content) > 500 else full_content
                        streaming_widget.update(f"🧘 {display}")
                    await asyncio.sleep(0.01)  # 给 UI 刷新时间

                elif chunk["type"] == "done":
                    if streaming_widget:
                        streaming_widget.remove()
                    await msgs.mount(Static(f"🧘 {full_content}", classes="msg-agent"))
                    await self._add_meta(msgs, chunk, len(full_content))

                elif chunk["type"] == "error":
                    raise Exception(chunk["message"])

            self._streaming = False
            self.turn_count += 1
            self._update_header()
            return

        except Exception:
            self._streaming = False
            # 降级到 think_stream (推理+答案)
            async for chunk in adapter.think_stream(text, use_history=True):
                if chunk["type"] == "reasoning":
                    await msgs.mount(ReasoningWidget(chunk["content"]))
                elif chunk["type"] == "token":
                    pass  # think_stream handles display internally
                elif chunk["type"] == "done":
                    await msgs.mount(Static(f"🧘 {chunk.get('content', '')}", classes="msg-agent"))
                    await self._add_meta(msgs, chunk, len(chunk.get("content", "")))
                elif chunk["type"] == "error":
                    raise Exception(chunk["message"])
            self.turn_count += 1
            self._update_header()

    async def _fallback_chat(self, text: str, msgs: ScrollableContainer):
        """最终降级: 阻塞式单次调用"""
        adapter = self._get_adapter()
        result = await adapter.chat(text, use_history=True)
        content = result.get("content", "")
        await msgs.mount(Static(f"🧘 {content}", classes="msg-agent"))
        await self._add_meta(msgs, result, len(content))
        self.turn_count += 1
        self._update_header()

    async def _add_meta(self, msgs, result: dict, content_len: int):
        """添加元数据行"""
        provider = result.get("provider", "?")
        model = result.get("model", "?")
        usage = result.get("usage", {})
        cost = result.get("cost", 0)
        in_tok = usage.get("prompt_tokens", "?")
        out_tok = usage.get("completion_tokens", content_len // 4)
        meta = f"   [{provider} | {model} | in:{in_tok} out:{out_tok} | ${cost:.4f} | {content_len} chars]"
        await msgs.mount(Static(meta, classes="msg-meta"))

    def _update_header(self):
        hdr = self.query_one("#chat-header", Label)
        provider = self._get_adapter()._detect_available_provider()
        hdr.update(f"💬 Chat · {self.turn_count} turns · provider: {provider}")

    # ---- Actions ----

    def action_blur_input(self):
        self.query_one("#chat-input").blur()

    def action_new_session(self):
        """新建会话"""
        adapter = self._get_adapter()
        import asyncio
        asyncio.create_task(adapter.clear_history())
        self.turn_count = 0
        self._input_history = []
        self._history_idx = -1
        msgs = self.query_one("#chat-messages", ScrollableContainer)
        msgs.remove_children()
        asyncio.create_task(msgs.mount(Static("🆕 New session started.", classes="msg-system")))
        self._update_header()

    def action_save_session(self):
        """保存当前会话 (伪: 打印到 stdout)"""
        msgs = self.query_one("#chat-messages", ScrollableContainer)
        self.notify(f"Session: {self.turn_count} turns. Use Ctrl+S in terminal to save scrollback.")
