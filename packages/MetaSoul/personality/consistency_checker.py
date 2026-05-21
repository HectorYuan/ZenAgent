"""
人格一致性校验器

设计依据: M8_P4_PERSONALITY_MATRIX_DESIGN.md §3.3

检测 LLM 响应中的语言模式是否与当前人格设定一致
"""

import re
import logging
from typing import Dict

from .personality import BigFiveTraits

logger = logging.getLogger(__name__)


class ConsistencyChecker:
    """
    人格一致性校验器

    每维度有高/中/低三档期望词汇，
    检测响应文本中期望词汇的命中率，计算匹配度评分 0-100。
    """

    FLAG_THRESHOLD = 40  # 低于 40 分标记为不一致

    # 每维度高/低档期望词汇表
    TRAIT_MARKERS: dict[str, dict[str, list[str]]] = {
        "openness": {
            "high": [
                "perhaps", "consider", "another angle", "alternatively",
                "creative", "explore", "imagine", "possibility",
                "或许", "另一个角度", "创造性", "探索", "想象", "可能性",
            ],
            "low": [
                "certainly", "the answer is", "proven", "established",
                "the fact is", "according to", "standard", "traditional",
                "确定", "答案是", "已证明", "既定事实", "根据", "标准", "传统",
            ],
        },
        "conscientiousness": {
            "high": [
                "carefully", "thorough", "detail", "precise", "step by step",
                "organized", "verify", "double-check", "accurate",
                "仔细", "详细", "精确", "逐步", "验证", "确认", "准确",
            ],
            "low": [
                "roughly", "approximately", "quick look", "flexible",
                "adaptive", "good enough", "大概", "差不多", "灵活",
            ],
        },
        "extraversion": {
            "high": [
                "let's", "together", "share", "discuss", "collaborate",
                "community", "excited", "engaging",
                "一起", "讨论", "分享", "合作", "兴奋", "参与",
            ],
            "low": [
                "I think", "in my analysis", "personally", "reflect",
                "upon reflection", "我认为", "在我分析中", "反思",
            ],
        },
        "agreeableness": {
            "high": [
                "I understand", "that's valid", "good point", "thank you",
                "I appreciate", "with respect", "collaborative",
                "理解", "有道理", "谢谢", "尊重", "合作",
            ],
            "low": [
                "I disagree", "that's incorrect", "the problem is",
                "challenge", "批判", "不同意", "问题是", "挑战",
            ],
        },
        "neuroticism": {
            "high": [
                "careful about", "potential risk", "might go wrong",
                "should be cautious", "sensitive to", "concerned",
                "小心", "风险", "可能出错", "谨慎", "敏感", "担心",
            ],
            "low": [
                "no need to worry", "calmly", "it will work out",
                "confident", "steady", "resilient",
                "不用担心", "冷静", "没问题", "自信", "稳定",
            ],
        },
    }

    @staticmethod
    def _get_level(value: float) -> str:
        if value >= 0.65:
            return "high"
        elif value >= 0.35:
            return "mid"
        return "low"

    def check_dimension(self, text: str, trait_name: str, expected_value: float) -> float:
        """
        单维度检查

        Returns:
            0-100 的匹配度评分
        """
        markers = self.TRAIT_MARKERS.get(trait_name, {})
        level = self._get_level(expected_value)

        # 中性无检查
        if level == "mid":
            return 75.0  # 中性默认偏高

        text_lower = text.lower()

        # 期望词汇
        expected_markers = markers.get(level, [])
        # 相反词汇
        opposite_level = "low" if level == "high" else "high"
        opposite_markers = markers.get(opposite_level, [])

        expected_hits = sum(1 for m in expected_markers if m.lower() in text_lower)
        opposite_hits = sum(1 for m in opposite_markers if m.lower() in text_lower)

        max_expected = max(len(expected_markers), 1)
        max_opposite = max(len(opposite_markers), 1)

        # 期望命中得高分，反向命中扣分，基础分 30
        score = 30 + (expected_hits / max_expected) * 60 - (opposite_hits / max_opposite) * 40
        return max(0.0, min(100.0, score))

    def overall_score(self, text: str, traits: dict[str, float]) -> float:
        """
        整体人格一致性评分 0-100

        Args:
            text: 响应文本
            traits: 五维度值

        Returns:
            0-100 分
        """
        if not text or not traits:
            return 50.0

        scores = []
        for trait in BigFiveTraits:
            value = traits.get(trait.value, 0.5)
            score = self.check_dimension(text, trait.value, value)
            scores.append(score)

        if not scores:
            return 50.0

        return sum(scores) / len(scores)

    def check_and_flag(self, text: str, traits: dict[str, float]) -> tuple[float, bool]:
        """
        检查并标记不一致

        Returns:
            (score, is_consistent)
        """
        score = self.overall_score(text, traits)
        is_consistent = score >= self.FLAG_THRESHOLD
        if not is_consistent:
            logger.info(
                "Personality inconsistency flagged: score=%.1f threshold=%d",
                score, self.FLAG_THRESHOLD
            )
        return score, is_consistent

    def get_dimension_breakdown(self, text: str, traits: dict[str, float]) -> dict[str, float]:
        """获取各维度详细评分"""
        result = {}
        for trait in BigFiveTraits:
            t = trait.value
            result[t] = self.check_dimension(text, t, traits.get(t, 0.5))
        result["overall"] = self.overall_score(text, traits)
        return result
