"""
TUI 主题系统
"""
from typing import Optional


class ZenaTheme:
    """ZenAgent TUI 主题"""

    @staticmethod
    def get_colors(theme_name: str = "clean") -> dict:
        themes = {
            "clean": {
                "primary": "#4fc3f7",
                "secondary": "#81d4fa",
                "success": "#66bb6a",
                "warning": "#ffa726",
                "error": "#ef5350",
                "surface": "#1e1e2e",
                "background": "#121212",
                "text": "#e0e0e0",
                "muted": "#6e6e6e",
                "accent": "#ce93d8",
            },
            "dark": {
                "primary": "#7c4dff",
                "secondary": "#b388ff",
                "success": "#69f0ae",
                "warning": "#ffd740",
                "error": "#ff5252",
                "surface": "#263238",
                "background": "#141414",
                "text": "#f5f5f5",
                "muted": "#616161",
                "accent": "#ff80ab",
            },
        }
        return themes.get(theme_name, themes["clean"])


THEME_COLORS = ZenaTheme.get_colors("clean")
