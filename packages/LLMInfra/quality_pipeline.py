"""
响应质量评分管道

设计依据: E2E_OPTIMIZATION_DESIGN §模块7 (M9b)

四阶段管道: 完整性 → 一致性 → 安全性 → 0-100 综合评分
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from .core import LLMResponse, ChatRequest, Message, MessageRole

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """质量报告"""
    score: float = 100.0           # 0-100 综合评分
    is_valid: bool = True          # 是否通过最低阈值 (60分)
    completeness: float = 100.0    # 完整性评分 0-100
    consistency: float = 100.0     # 一致性评分 0-100
    safety: float = 100.0          # 安全性评分 0-100
    issues: list[str] = field(default_factory=list)
    repair_hints: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def needs_retry(self) -> bool:
        return self.score < 60

    @property
    def needs_repair(self) -> bool:
        return self.score < 80 and not self.needs_retry


class ResponseQualityPipeline:
    """
    响应质量评分管道

    四阶段评分:
    1. 完整性检查 (40%): 截断/空响应/长度异常
    2. 一致性检查 (30%): 与历史矛盾/事实一致性
    3. 安全性检查 (30%): 有害内容/PII 泄漏
    4. 综合评分: weighted_average × 100

    阈值:
    - <60 分: 自动重试
    - 60-80 分: 标记待修复
    - ≥80 分: 通过
    """

    PASS_THRESHOLD = 60
    REPAIR_THRESHOLD = 80

    WEIGHTS = {
        "completeness": 0.4,
        "consistency": 0.3,
        "safety": 0.3,
    }

    # PII 模式
    _PII_PATTERNS = [
        (r'\b[\w.-]+@[\w.-]+\.\w{2,}\b', "email"),
        (r'\b\d{3}[-.]?\d{4}[-.]?\d{4}\b', "phone"),
        (r'\b\d{15,19}\b', "credit_card"),
        (r'\b[sk]-[a-f0-9]{32,}\b', "api_key"),
    ]

    def validate(
        self,
        response: LLMResponse,
        request: ChatRequest,
        history: Optional[List[Message]] = None,
    ) -> QualityReport:
        """
        执行完整质量校验

        Returns:
            QualityReport with 0-100 score
        """
        completeness = self._check_completeness(response)
        consistency = self._check_consistency(response, history or [])
        safety = self._check_safety(response)

        score = (
            completeness * self.WEIGHTS["completeness"] +
            consistency * self.WEIGHTS["consistency"] +
            safety * self.WEIGHTS["safety"]
        )

        issues, hints = self._collect_issues(completeness, consistency, safety, response)

        return QualityReport(
            score=round(score, 1),
            is_valid=score >= self.PASS_THRESHOLD,
            completeness=round(completeness, 1),
            consistency=round(consistency, 1),
            safety=round(safety, 1),
            issues=issues,
            repair_hints=hints,
            metadata={
                "finish_reason": response.finish_reason,
                "content_length": len(response.content),
                "usage": response.usage,
            }
        )

    # ---------- Stage 1: Completeness ----------

    def _check_completeness(self, response: LLMResponse) -> float:
        """检查响应完整性"""
        score = 100.0
        content = response.content or ""

        # 空响应
        if not content.strip():
            return 0.0

        # 截断检测
        fr = response.finish_reason or ""
        if fr == "length":
            score -= 40  # 严重扣分：显式截断
        elif fr == "content_filter":
            score -= 80  # 几乎致命

        # 截断标记
        truncation_markers = ["...", "continued", "to be continued", "[truncated]"]
        if any(m in content[-50:].lower() for m in truncation_markers):
            score -= 20

        # Token 比率检测 (output/max)
        usage = response.usage or {}
        output_tokens = usage.get("completion_tokens", 0)
        if output_tokens > 0:
            # 如果 output 接近 max (通常是 4096 或 8192)，可能是截断
            typical_max = 4096
            if output_tokens / typical_max > 0.95:
                score -= 15

        return max(0.0, score)

    # ---------- Stage 2: Consistency ----------

    def _check_consistency(
        self,
        response: LLMResponse,
        history: List[Message],
    ) -> float:
        """检查与对话历史的一致性"""
        score = 100.0
        content = response.content.lower()

        if not history:
            return score

        # 简单的矛盾检测: 检查响应是否与最近的用户消息矛盾
        last_user = ""
        for msg in reversed(history):
            if hasattr(msg, 'role') and str(msg.role) == 'user':
                last_user = getattr(msg, 'content', '').lower()
                break

        if not last_user:
            return score

        # 直接否定模式 (crude but effective)
        if "I don't know" in content and len(content) < 200:
            score -= 10  # 太简短的 "I don't know"
        if "I cannot" in content and "help" in content:
            score -= 15  # 拒绝帮助
        if "as an AI" in content[:100] and last_user:
            score -= 5  # 不必要的免责声明

        return max(0.0, score)

    # ---------- Stage 3: Safety ----------

    def _check_safety(self, response: LLMResponse) -> float:
        """安全检查"""
        score = 100.0
        content = response.content

        # PII 检测
        pii_count = 0
        import re
        for pattern, pii_type in self._PII_PATTERNS:
            matches = re.findall(pattern, content)
            pii_count += len(matches)

        if pii_count > 0:
            score -= min(pii_count * 10, 40)

        # 有害内容关键词检测 (简化版)
        harmful_patterns = [
            r'\b(hate|violence|attack|kill|harm)\b',
        ]
        for pattern in harmful_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                score -= 20

        return max(0.0, score)

    # ---------- Helpers ----------

    def _collect_issues(
        self,
        completeness: float,
        consistency: float,
        safety: float,
        response: LLMResponse,
    ) -> tuple[list[str], list[str]]:
        issues = []
        hints = []

        if completeness < 80:
            issues.append(f"Completeness low ({completeness:.0f}): response may be truncated")
            hints.append("Increase max_tokens or simplify the query")
        if consistency < 80:
            issues.append(f"Consistency low ({consistency:.0f}): may conflict with history")
            hints.append("Add explicit context from conversation history")
        if safety < 90:
            issues.append(f"Safety flag ({safety:.0f}): content may contain PII or harmful text")
            hints.append("Review response for sensitive information")

        return issues, hints
