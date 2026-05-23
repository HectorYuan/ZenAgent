"""LearningScreen — to be implemented in T6"""
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.binding import Binding


class LearningScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Back")]
    def compose(self): yield Label("Learning · Coming in T6"); yield Static("...")
