"""InfraScreen — to be implemented in T6"""
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.binding import Binding


class InfraScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Back")]
    def compose(self): yield Label("Infra · Coming in T6"); yield Static("...")
