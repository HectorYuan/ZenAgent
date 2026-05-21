"""
CommandRegistry — 命令注册表

声明式命令元数据，同时驱动 CLI argparse 和 TUI 命令面板。
设计参考: ZenSkill commands.py
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, Any


@dataclass
class CommandArg:
    """命令参数元数据"""
    name: str
    arg_type: str = "string"  # string, int, float, choice, file
    required: bool = False
    default: Any = None
    description: str = ""
    choices: Optional[list[str]] = None


@dataclass
class CommandEntry:
    """命令条目 — CLI/TUI 统一元数据"""
    namespace: str              # 如 "memory"
    name: str                   # 如 "search"
    display_name: str           # 如 "Search Memory"
    description: str = ""
    category: str = "general"
    icon: str = "📋"
    action_type: str = "output"  # "output" | "screen" | "action"
    handler_name: str = ""      # cmd_* 函数名
    args: list[CommandArg] = field(default_factory=list)
    flags: dict = field(default_factory=dict)


class CommandRegistry:
    """
    命令注册表

    集中管理所有 CLI/TUI 命令的元数据。
    用于 Textual 命令面板和 Rich 命令模式。
    """

    def __init__(self):
        self._commands: dict[str, CommandEntry] = {}
        self._register_all()

    def _register_all(self):
        """注册所有命令"""
        commands = [
            # Chat
            CommandEntry("chat", "send", "Chat", "发送消息给 ZenAgent",
                         "chat", "💬", "screen",
                         args=[CommandArg("message", description="消息内容")]),
            CommandEntry("chat", "clear", "Clear History", "清空对话历史",
                         "chat", "🗑", "action", handler_name="cmd_chat_clear"),

            # Status
            CommandEntry("status", "show", "Status Dashboard", "系统状态仪表盘",
                         "system", "📊", "screen"),

            # Memory
            CommandEntry("memory", "search", "Search Memory", "搜索记忆",
                         "memory", "🔍", "output",
                         args=[CommandArg("query", required=True)]),
            CommandEntry("memory", "add", "Add Memory", "存储记忆",
                         "memory", "➕", "action",
                         args=[CommandArg("content", required=True)]),
            CommandEntry("memory", "stats", "Memory Stats", "记忆统计",
                         "memory", "📈", "output"),

            # Personality
            CommandEntry("personality", "show", "Show Traits", "查看 Big Five",
                         "personality", "🎭", "output"),
            CommandEntry("personality", "set", "Set Trait", "调整特质",
                         "personality", "✏", "action",
                         args=[CommandArg("trait", arg_type="choice",
                                          choices=["openness", "conscientiousness",
                                                   "extraversion", "agreeableness", "neuroticism"]),
                               CommandArg("value", arg_type="float")]),
            CommandEntry("personality", "scenario", "Set Scenario", "切换场景",
                         "personality", "🎬", "action",
                         args=[CommandArg("name", arg_type="choice",
                                          choices=["casual_chat", "technical_qa", "creative",
                                                   "decision", "debate", "teaching",
                                                   "emotional_support", "code_review"])]),

            # Provider
            CommandEntry("provider", "list", "List Providers", "列出 Provider",
                         "infra", "📋", "output"),
            CommandEntry("provider", "health", "Provider Health", "Provider 健康",
                         "infra", "🏥", "output"),

            # Knowledge
            CommandEntry("knowledge", "search", "Search Knowledge", "搜索知识库",
                         "memory", "🔍", "output",
                         args=[CommandArg("query", required=True)]),
            CommandEntry("knowledge", "stats", "Knowledge Stats", "知识库统计",
                         "memory", "📊", "output"),

            # Doctor
            CommandEntry("doctor", "run", "Doctor", "系统健康检查",
                         "system", "🩺", "output"),
        ]

        for cmd in commands:
            key = f"{cmd.namespace}:{cmd.name}"
            self._commands[key] = cmd

    def get(self, key: str) -> Optional[CommandEntry]:
        return self._commands.get(key)

    def get_by_category(self, category: str) -> list[CommandEntry]:
        return [c for c in self._commands.values() if c.category == category]

    @property
    def all_commands(self) -> dict[str, CommandEntry]:
        return dict(self._commands)

    def search(self, query: str) -> list[CommandEntry]:
        q = query.lower()
        return [c for c in self._commands.values()
                if q in c.display_name.lower() or q in c.description.lower()]


# 全局单例
_registry: Optional[CommandRegistry] = None


def get_registry() -> CommandRegistry:
    global _registry
    if _registry is None:
        _registry = CommandRegistry()
    return _registry
