"""
语言配置 — 中英文支持

用法:
    from .i18n import T
    print(T("chat.title", turns=5))  # "💬 对话 · 5 轮"
"""

import os

# 当前语言: zh / en
LANG = os.environ.get("ZENA_LANG", "zh")

STRINGS = {
    "zh": {
        # ---- 导航 ----
        "nav.chat": "💬 0",
        "nav.dashboard": "📊 1",
        "nav.memory": "🧠 2",
        "nav.personality": "🎭 3",
        "nav.learning": "📚 4",
        "nav.infra": "⚙ 5",

        # ---- 全局快捷键 ----
        "key.chat": "对话",
        "key.dashboard": "仪表盘",
        "key.memory": "记忆",
        "key.personality": "人格",
        "key.learning": "学习",
        "key.infra": "设施",
        "key.refresh": "刷新",
        "key.quit": "退出",
        "key.back": "返回",
        "key.send": "发送",
        "key.new_session": "新会话",

        # ---- Chat ----
        "chat.title": "💬 对话 · {turns} 轮",
        "chat.ready": "🧘 ZenAgent 就绪。输入消息后按 Enter 发送。",
        "chat.hint": "[Ctrl+N] 新会话  [0-5] 切屏  [q] 退出",
        "chat.input_placeholder": "输入消息...",
        "chat.send_btn": "发送",
        "chat.new_session_ok": "新会话已开始",
        "chat.reasoning_expand": "[点击展开]",
        "chat.reasoning_collapse": "[点击折叠]",
        "chat.reasoning_title": "💭 思考过程",
        "chat.streaming_prefix": "🧘 ",

        # ---- Dashboard ----
        "dash.title": "📊 仪表盘 · 系统概览",
        "dash.l0": "🟢 L0 LLMInfra    │ Provider 责任链 + 熔断器 正常",
        "dash.l1": "🟢 L1 Runtime     │ 意图路由: {requests} 请求, Fast:{fast} Deep:{deep}",
        "dash.l2": "🟢 L2 ZenAgent    │ 钩子系统 + 觉醒 + MCP 正常",
        "dash.l3": "🟢 L3 MetaSoul    │ 记忆 L1-L4 + 人格矩阵 正常",
        "dash.l4": "⚪ L4 SwarmFly    │ Agent: {agents}",
        "dash.help": "─" * 50 + "\n[💬0 对话 | 📊1 仪表盘 | 🧠2 记忆 | 🎭3 人格 | 📚4 学习 | ⚙5 设施 | q 退出]",

        # ---- Memory ----
        "mem.title": "🧠 记忆 · L1(热) L2(温) L3(语义) L4(归档)",
        "mem.search_placeholder": "搜索记忆...",
        "mem.search_btn": "搜索",
        "mem.stats_btn": "统计",
        "mem.triples_btn": "三元组",
        "mem.results": "🔍 {query} 结果 ({count} 条)",
        "mem.no_results": "  [无结果]",
        "mem.stats_title": "📊 记忆统计",
        "mem.l1": "L1 热记忆:",
        "mem.l2": "L2 温记忆:",
        "mem.l3": "L3 语义:",
        "mem.l4": "L4 归档:",
        "mem.total": "总计:",
        "mem.kb_title": "📚 知识库 (SPO 三元组)",
        "mem.triples": "三元组总数:",
        "mem.entities": "实体总数:",
        "mem.conflicts": "冲突:",

        # ---- Personality ----
        "pers.title": "🎭 人格 · Big Five",
        "pers.cross_title": "  交叉效应:",

        # ---- Learning ----
        "learn.title": "📚 学习 & 进化",
        "learn.cycle_btn": "学习周期",
        "learn.reflect_btn": "反思",
        "learn.stats_btn": "统计",
        "learn.skills_btn": "技能",
        "learn.cycle_title": "🔄 学习周期 (观察→反思→归纳→验证→整合)",
        "learn.cycles": "学习周期: {count} 轮交互",
        "learn.next_cross": "下次跨会话整合: {turns} 轮后",
        "learn.reflect_title": "🔍 反思深度",
        "learn.surface": "表象: 即时反应分析",
        "learn.causal": "因果: 为何产生此结果?",
        "learn.meaning": "意义: 有哪些可推广的经验?",
        "learn.transformative": "蜕变: 如何根本性改进?",
        "learn.skills_title": "🛠 技能等级",
        "learn.novice": "🌱 入门     → 理解基础",
        "learn.apprentice": "🌿 学徒 → 指导练习",
        "learn.adept": "🪴 熟练     → 独立执行",
        "learn.expert": "🌳 专家     → 指导他人",
        "learn.master": "🏆 大师     → 创新",

        # ---- Infra ----
        "infra.title": "⚙ 设施 · Provider & Agent",
        "infra.providers_btn": "Provider",
        "infra.cache_btn": "缓存",
        "infra.agents_btn": "Agent",
        "infra.doctor_btn": "体检",
        "infra.providers_title": "🔌 Provider 列表",
        "infra.cache_title": "📦 缓存状态",
        "infra.cache_hit_rate": "命中率:",
        "infra.cache_hot_keys": "热点键:",
        "infra.agents_title": "🤖 Agent 列表",
        "infra.doctor_title": "🩺 系统健康",

        # ---- CLI ----
        "cli.chat_title": "🧘 ZenAgent 对话",
        "cli.chat_quit_hint": "(输入 'q' 退出, 'clear' 清空历史)",
        "cli.interrupted": "中断。",
    },

    "en": {
        "nav.chat": "💬 0",
        "nav.dashboard": "📊 1",
        "nav.memory": "🧠 2",
        "nav.personality": "🎭 3",
        "nav.learning": "📚 4",
        "nav.infra": "⚙ 5",

        "key.chat": "Chat",
        "key.dashboard": "Dashboard",
        "key.memory": "Memory",
        "key.personality": "Personality",
        "key.learning": "Learning",
        "key.infra": "Infra",
        "key.refresh": "Refresh",
        "key.quit": "Quit",
        "key.back": "Back",
        "key.send": "Send",
        "key.new_session": "New Session",

        "chat.title": "💬 Chat · {turns} turns",
        "chat.ready": "🧘 ZenAgent ready. Type and press Enter to send.",
        "chat.hint": "[Ctrl+N] New Session  [0-5] Switch  [q] Quit",
        "chat.input_placeholder": "Enter message...",
        "chat.send_btn": "Send",
        "chat.new_session_ok": "New session started",
        "chat.reasoning_expand": "[click to expand]",
        "chat.reasoning_collapse": "[click to collapse]",
        "chat.reasoning_title": "💭 Reasoning",
        "chat.streaming_prefix": "🧘 ",

        "dash.title": "📊 Dashboard · System Overview",
        "dash.l0": "🟢 L0 LLMInfra    │ Provider Chain + Circuit Breaker OK",
        "dash.l1": "🟢 L1 Runtime     │ Router: {requests} reqs, Fast:{fast} Deep:{deep}",
        "dash.l2": "🟢 L2 ZenAgent    │ Hooks + Awakening + MCP OK",
        "dash.l3": "🟢 L3 MetaSoul    │ Memory L1-L4 + Personality OK",
        "dash.l4": "⚪ L4 SwarmFly    │ Agents: {agents}",
        "dash.help": "─" * 50 + "\n[💬0 Chat | 📊1 Dash | 🧠2 Mem | 🎭3 Pers | 📚4 Learn | ⚙5 Infra | q Quit]",

        "mem.title": "🧠 Memory · L1(Hot) L2(Warm) L3(Semantic) L4(Archive)",
        "mem.search_placeholder": "Search memory...",
        "mem.search_btn": "Search",
        "mem.stats_btn": "Stats",
        "mem.triples_btn": "Triples",
        "mem.results": "🔍 {query} results ({count} found)",
        "mem.no_results": "  [no results]",
        "mem.stats_title": "📊 Memory Statistics",
        "mem.l1": "L1 Hot:",
        "mem.l2": "L2 Warm:",
        "mem.l3": "L3 Semantic:",
        "mem.l4": "L4 Archive:",
        "mem.total": "Total:",
        "mem.kb_title": "📚 Knowledge Base (SPO Triples)",
        "mem.triples": "Total Triples:",
        "mem.entities": "Total Entities:",
        "mem.conflicts": "Conflicts:",

        "pers.title": "🎭 Personality · Big Five",
        "pers.cross_title": "  Cross Effects:",

        "learn.title": "📚 Learning & Evolution",
        "learn.cycle_btn": "Learn Cycle",
        "learn.reflect_btn": "Reflect",
        "learn.stats_btn": "Stats",
        "learn.skills_btn": "Skills",
        "learn.cycle_title": "🔄 Learning Cycle (OBSERVE→REFLECT→GENERALIZE→VERIFY→INTEGRATE)",
        "learn.cycles": "Interactions: {count}",
        "learn.next_cross": "Next cross-session: {turns} turns",
        "learn.reflect_title": "🔍 Reflection Depths",
        "learn.surface": "SURFACE: Immediate reaction analysis",
        "learn.causal": "CAUSAL: Why did this occur?",
        "learn.meaning": "MEANING: Broader lessons?",
        "learn.transformative": "TRANSFORMATIVE: How to improve?",
        "learn.skills_title": "🛠 Skill Levels",
        "learn.novice": "🌱 NOVICE → basics",
        "learn.apprentice": "🌿 APPRENTICE → guided",
        "learn.adept": "🪴 ADEPT → independent",
        "learn.expert": "🌳 EXPERT → teaching",
        "learn.master": "🏆 MASTER → innovation",

        "infra.title": "⚙ Infra · Providers & Agents",
        "infra.providers_btn": "Providers",
        "infra.cache_btn": "Cache",
        "infra.agents_btn": "Agents",
        "infra.doctor_btn": "Doctor",
        "infra.providers_title": "🔌 Providers",
        "infra.cache_title": "📦 Cache",
        "infra.cache_hit_rate": "Hit Rate:",
        "infra.cache_hot_keys": "Hot Keys:",
        "infra.agents_title": "🤖 Agents",
        "infra.doctor_title": "🩺 System Health",

        "cli.chat_title": "🧘 ZenAgent Chat",
        "cli.chat_quit_hint": "(Enter 'q' to quit, 'clear' to clear history)",
        "cli.interrupted": "Interrupted.",
    }
}


def T(key: str, **kwargs) -> str:
    """获取本地化字符串"""
    strings = STRINGS.get(LANG, STRINGS["zh"])
    text = strings.get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


def set_language(lang: str):
    """切换语言"""
    global LANG
    if lang in STRINGS:
        LANG = lang
