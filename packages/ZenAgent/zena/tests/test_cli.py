"""zena CLI 基础测试 (M9)"""
import pytest
from packages.ZenAgent.zena.__main__ import build_parser
from packages.ZenAgent.zena.core.adapter import ZenaDataAdapter
from packages.ZenAgent.zena.cli_utils import bar_chart, box_card, status_icon

class TestParser:
    def test_parser_builds(self):
        parser = build_parser()
        assert parser is not None

    def test_chat_command(self):
        parser = build_parser()
        args = parser.parse_args(["chat", "hello"])
        assert args.command == "chat"
        assert args.message == ["hello"]

    def test_status_command(self):
        parser = build_parser()
        args = parser.parse_args(["status"])
        assert args.command == "status"

    def test_json_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--json", "status"])
        assert args.json_output is True

class TestCLIUtils:
    def test_bar_chart(self):
        result = bar_chart(0.5, width=10)
        assert len(result) == 10
        assert "█" in result
        assert "░" in result

    def test_bar_chart_full(self):
        result = bar_chart(1.0, width=5)
        assert "░" not in result

    def test_status_icon(self):
        assert status_icon(True) == "🟢"
        assert status_icon(False) == "🔴"

    def test_box_card(self):
        card = box_card("test", ["line1", "line2"])
        assert "test" in card
        assert "line1" in card
        assert "┌─" in card
