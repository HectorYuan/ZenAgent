"""
人格动态权重矩阵 — 5×8 场景矩阵 + EMA 平滑 + 自然语言注入

设计依据: E2E_OPTIMIZATION_DESIGN §模块10
专家优化:
- EMA 平滑过渡 (对话系统专家)
- 人格画像叙述 (提示词工程师)
- 维度交叉效应 (心理学专家)
"""

import logging
from typing import Dict, Optional
from enum import Enum

from .personality import BigFiveTraits

logger = logging.getLogger(__name__)


# ============================================================
# 场景定义
# ============================================================

class Scenario(str, Enum):
    CASUAL_CHAT = "casual_chat"
    TECHNICAL_QA = "technical_qa"
    CREATIVE = "creative"
    DECISION = "decision"
    DEBATE = "debate"
    TEACHING = "teaching"
    EMOTIONAL_SUPPORT = "emotional_support"
    CODE_REVIEW = "code_review"


# ============================================================
# 5×8 人格权重矩阵
# ============================================================

class PersonalityMatrix:
    """
    5 维度 × 8 场景人格权重矩阵

    每次场景中，五维度权重不同；乘以基线值得到该场景的有效人格。
    采用 EMA 平滑过渡，避免人设突变。
    """

    SCENARIOS = list(Scenario)

    # 默认基线权重矩阵: scenario → {trait: weight}
    DEFAULT_WEIGHTS: dict[str, dict[str, float]] = {
        "casual_chat": {
            "openness": 0.6, "conscientiousness": 0.3, "extraversion": 0.7,
            "agreeableness": 0.7, "neuroticism": 0.3,
        },
        "technical_qa": {
            "openness": 0.5, "conscientiousness": 0.9, "extraversion": 0.3,
            "agreeableness": 0.4, "neuroticism": 0.2,
        },
        "creative": {
            "openness": 1.0, "conscientiousness": 0.3, "extraversion": 0.6,
            "agreeableness": 0.5, "neuroticism": 0.4,
        },
        "decision": {
            "openness": 0.4, "conscientiousness": 0.9, "extraversion": 0.3,
            "agreeableness": 0.3, "neuroticism": 0.2,
        },
        "debate": {
            "openness": 0.7, "conscientiousness": 0.6, "extraversion": 0.6,
            "agreeableness": 0.2, "neuroticism": 0.3,
        },
        "teaching": {
            "openness": 0.6, "conscientiousness": 0.7, "extraversion": 0.5,
            "agreeableness": 0.8, "neuroticism": 0.2,
        },
        "emotional_support": {
            "openness": 0.4, "conscientiousness": 0.4, "extraversion": 0.5,
            "agreeableness": 0.95, "neuroticism": 0.3,
        },
        "code_review": {
            "openness": 0.4, "conscientiousness": 0.9, "extraversion": 0.2,
            "agreeableness": 0.3, "neuroticism": 0.1,
        },
    }

    def __init__(self, baseline: Optional[dict[str, float]] = None):
        """
        Args:
            baseline: 5 维度基线值 (0-1)，默认 0.5
        """
        self.baseline = baseline or {
            "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
            "agreeableness": 0.5, "neuroticism": 0.5,
        }
        self._ema_values: dict[str, float] = dict(self.baseline)
        self._ema_alpha = 0.3  # 平滑系数
        self._current_scenario = Scenario.CASUAL_CHAT

    def set_scenario(self, scenario: Scenario):
        """切换场景"""
        self._current_scenario = scenario

    def get_effective_traits(self) -> dict[str, float]:
        """获取当前场景下的有效人格值"""
        weights = self.DEFAULT_WEIGHTS.get(self._current_scenario.value, {})
        result = {}
        for trait in BigFiveTraits:
            t = trait.value
            w = weights.get(t, 0.5)
            # effective = baseline × scenario_weight (clamp 0-1)
            result[t] = min(1.0, max(0.0, self._ema_values[t] * w * 2))
        return result

    def adjust(self, trait: str, delta: float):
        """
        微调某维度（EMA 平滑过渡）

        Args:
            trait: 维度名称
            delta: 变化量
        """
        if trait not in self._ema_values:
            return
        target = min(1.0, max(0.0, self._ema_values[trait] + delta))
        self._ema_values[trait] = (
            self._ema_values[trait] * (1 - self._ema_alpha) +
            target * self._ema_alpha
        )

    def apply_dynamic_rules(self, rules: list[tuple[str, float]]):
        """批量应用动态规则"""
        for trait, delta in rules:
            self.adjust(trait, delta)

    def get_baseline(self) -> dict[str, float]:
        return dict(self._ema_values)

    @property
    def current_scenario(self) -> Scenario:
        return self._current_scenario

    def get_weight_matrix(self) -> dict:
        """获取完整权重矩阵（用于调试）"""
        return {
            "baseline": self.get_baseline(),
            "scenario": self._current_scenario.value,
            "weights": self.DEFAULT_WEIGHTS.get(self._current_scenario.value, {}),
            "effective": self.get_effective_traits(),
            "ema_alpha": self._ema_alpha,
        }


# ============================================================
# 动态调整器
# ============================================================

class DynamicAdjuster:
    """
    动态调整器

    根据对话上下文自动调整人格权重
    """

    def __init__(self, matrix: Optional[PersonalityMatrix] = None):
        self.matrix = matrix or PersonalityMatrix()
        self.dialogue_turns = 0

    def on_new_turn(self, user_message: str = ""):
        """
        每轮对话调用，自动调整人格

        规则:
        - 对话越长 → openness +0.02/轮
        - 用户情绪负面 → agreeableness +0.1
        - 涉及决策 → conscientiousness +0.1
        - 技术话题 → conscientiousness +0.1, openness -0.03
        """
        rules = []

        # 1. 对话轮数累积
        self.dialogue_turns += 1
        if self.dialogue_turns > 3:
            rules.append(("openness", 0.02))

        # 2. 用户情绪检测（关键词）
        negative_keywords = {"angry", "frustrated", "upset", "annoyed", "mad",
                             "生气", "烦", "郁闷", "难过", "沮丧", "不开心"}
        if any(kw in user_message.lower() for kw in negative_keywords):
            rules.append(("agreeableness", 0.1))
            rules.append(("neuroticism", 0.05))

        # 3. 决策语境检测
        decision_keywords = {"decide", "choose", "should i", "which one",
                             "recommend", "advise", "建议", "选择", "决定"}
        if any(kw in user_message.lower() for kw in decision_keywords):
            rules.append(("conscientiousness", 0.1))
            rules.append(("openness", -0.05))

        # 4. 技术语境
        tech_keywords = {"code", "function", "bug", "error", "debug", "api",
                         "代码", "函数", "错误", "调试", "编译"}
        if any(kw in user_message.lower() for kw in tech_keywords):
            rules.append(("conscientiousness", 0.1))
            rules.append(("openness", -0.03))

        if rules:
            self.matrix.apply_dynamic_rules(rules)

    def detect_scenario(self, user_message: str) -> Scenario:
        """从用户消息检测当前场景"""
        msg = user_message.lower()

        # 快速规则检测
        tech = {"code", "function", "bug", "error", "api", "代码", "函数", "报错"}
        if any(kw in msg for kw in tech):
            return Scenario.CODE_REVIEW if "code" in msg or "代码" in msg else Scenario.TECHNICAL_QA

        creative = {"write", "create", "story", "poem", "写", "创作", "编"}
        if any(kw in msg for kw in creative):
            return Scenario.CREATIVE

        decision = {"decide", "choose", "should", "recommend", "决定", "选择", "建议"}
        if any(kw in msg for kw in decision):
            return Scenario.DECISION

        debate = {"debate", "argue", "disagree", "but", "争论", "不同意", "反驳"}
        if any(kw in msg for kw in debate):
            return Scenario.DEBATE

        teach = {"explain", "teach", "how to", "what is", "解释", "教", "怎么", "是什么"}
        if any(kw in msg for kw in teach):
            return Scenario.TEACHING

        emotional = {"sad", "angry", "upset", "lonely", "help me", "难过", "伤心", "帮帮我"}
        if any(kw in msg for kw in emotional):
            return Scenario.EMOTIONAL_SUPPORT

        return Scenario.CASUAL_CHAT

    def reset(self):
        self.dialogue_turns = 0
        self.matrix = PersonalityMatrix()


# ============================================================
# 人格注入器 — 自然语言化 (专家 #2 + #3)
# ============================================================

class PersonalityInjector:
    """
    人格注入器

    将参数值转换为自然语言人格描述。
    包含维度交叉效应模板 (专家 #3: 心理学)
    """

    # 单维度描述模板
    TRAIT_NARRATIVES = {
        "openness": {
            "high": "You are naturally curious and open-minded. You enjoy exploring new ideas, "
                    "unconventional approaches, and creative possibilities.",
            "mid": "You balance curiosity with practicality, open to new ideas when they serve a clear purpose.",
            "low": "You prefer established methods and proven approaches. You value consistency and tradition.",
        },
        "conscientiousness": {
            "high": "You are highly organized, detail-oriented, and thorough. You take pride in "
                    "getting things right and meeting high standards.",
            "mid": "You are reasonably organized and reliable, balancing thoroughness with efficiency.",
            "low": "You prefer flexibility over rigid structure, adapting easily to changing circumstances.",
        },
        "extraversion": {
            "high": "You are outgoing, enthusiastic, and socially engaged. You thrive on interaction "
                    "and collaborative energy.",
            "mid": "You are comfortable in both social and solitary settings, adapting to the situation.",
            "low": "You are reflective and reserved, preferring deep one-on-one conversations or "
                    "quiet contemplation.",
        },
        "agreeableness": {
            "high": "You are warm, empathetic, and cooperative. You prioritize harmony and "
                    "genuinely care about others' wellbeing.",
            "mid": "You are generally cooperative while maintaining healthy boundaries.",
            "low": "You are direct, assertive, and willing to challenge ideas. You value intellectual "
                    "honesty over social comfort.",
        },
        "neuroticism": {
            "high": "You are sensitive to potential risks and emotionally attuned to subtle cues. "
                    "This makes you cautious but also deeply perceptive.",
            "mid": "You maintain reasonable emotional balance, with moderate sensitivity to stress.",
            "low": "You are calm, steady, and resilient under pressure. You maintain composure "
                    "in challenging situations.",
        },
    }

    # 交叉效应模板 (心理学专家 #3)
    CROSS_EFFECTS: dict[tuple[str, str, str, str], str] = {
        # (trait1, level1, trait2, level2) → narrative
        ("openness", "high", "extraversion", "high"):
            "Your curiosity and sociability combine to make you an enthusiastic explorer of "
            "new ideas through collaborative discussion.",
        ("openness", "high", "conscientiousness", "high"):
            "Your intellectual curiosity is paired with meticulous execution — you explore "
            "creatively but evaluate rigorously.",
        ("conscientiousness", "high", "neuroticism", "high"):
            "Your perfectionism means you hold yourself to extremely high standards. "
            "Be mindful that done is often better than perfect.",
        ("agreeableness", "high", "extraversion", "high"):
            "Your warmth and sociability make you a natural connector — you build rapport "
            "easily and make others feel heard.",
        ("openness", "high", "neuroticism", "low"):
            "Your creative fearlessness means you are willing to take intellectual risks "
            "that others might avoid, while staying calm under uncertainty.",
        ("extraversion", "low", "openness", "high"):
            "Your rich inner world fuels deep, original thinking. You may work best through "
            "quiet reflection rather than rapid back-and-forth.",
        ("agreeableness", "low", "conscientiousness", "high"):
            "Your directness is grounded in rigorous thinking — you challenge ideas not "
            "people, and your criticism comes from a place of high standards.",
    }

    @staticmethod
    def _get_level(value: float) -> str:
        if value >= 0.65:
            return "high"
        elif value >= 0.35:
            return "mid"
        return "low"

    def to_narrative(self, traits: dict[str, float], scenario: Optional[Scenario] = None) -> str:
        """
        人格参数 → 自然语言 persona description

        Args:
            traits: 五维度值 {trait_name: 0-1}
            scenario: 当前场景（可选）

        Returns:
            自然语言人格描述
        """
        parts = []

        # 1. 场景头
        if scenario:
            scenario_headers = {
                Scenario.CASUAL_CHAT: "You are having a casual conversation.",
                Scenario.TECHNICAL_QA: "You are providing technical guidance.",
                Scenario.CREATIVE: "You are in a creative brainstorming mode.",
                Scenario.DECISION: "You are helping make an important decision.",
                Scenario.DEBATE: "You are engaging in a thoughtful debate.",
                Scenario.TEACHING: "You are teaching and explaining concepts.",
                Scenario.EMOTIONAL_SUPPORT: "You are providing emotional support.",
                Scenario.CODE_REVIEW: "You are reviewing code and providing feedback.",
            }
            header = scenario_headers.get(scenario, "")
            if header:
                parts.append(header)

        # 2. 各维度描述
        for trait in BigFiveTraits:
            value = traits.get(trait.value, 0.5)
            level = self._get_level(value)
            narrative = self.TRAIT_NARRATIVES.get(trait.value, {}).get(level, "")
            if narrative:
                parts.append(narrative)

        # 3. 交叉效应 (最多 2 组)
        cross_count = 0
        trait_names = [t.value for t in BigFiveTraits]
        for i in range(len(trait_names)):
            if cross_count >= 2:
                break
            for j in range(i + 1, len(trait_names)):
                t1, t2 = trait_names[i], trait_names[j]
                l1 = self._get_level(traits.get(t1, 0.5))
                l2 = self._get_level(traits.get(t2, 0.5))
                effect = self.CROSS_EFFECTS.get((t1, l1, t2, l2))
                if not effect:
                    effect = self.CROSS_EFFECTS.get((t2, l2, t1, l1))
                if effect:
                    parts.append(effect)
                    cross_count += 1
                    if cross_count >= 2:
                        break

        return "\n".join(parts)

    def to_system_prompt(self, traits: dict[str, float], scenario: Optional[Scenario] = None) -> str:
        """生成可直接用作 system prompt 的人格描述"""
        narrative = self.to_narrative(traits, scenario)
        return (
            "[Persona]\n"
            f"{narrative}\n"
            "\nRespond in a way that is consistent with the personality described above."
        )
