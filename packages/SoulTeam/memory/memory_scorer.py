"""
统一记忆评分器

整合 ForgettingCurve 指数衰减模型，提供综合评分和淘汰判定。
"""

import logging
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Any

from .meta_soul import MemoryEntry, MemoryImportance
from .forgetting import ForgettingCurve

logger = logging.getLogger(__name__)


@dataclass
class EvictionResult:
    """淘汰结果"""
    total_evaluated: int
    evicted_count: int
    retained_count: int
    evicted_ids: List[str]
    scores: Dict[str, float]


class MemoryScorer:
    """统一记忆评分器"""

    def __init__(self, curve: ForgettingCurve = None):
        self._curve = curve or ForgettingCurve()

    def score(self, memory: MemoryEntry) -> float:
        """
        综合评分 0-1，越高越值得保留。

        权重：
        - 重要性 0.3
        - 访问频率 0.2
        - 时效性（指数衰减） 0.3
        - 情感加成 0.2
        """
        importance = memory.importance.value / 5.0
        frequency = min(memory.access_count / 10, 1.0)

        days_elapsed = (datetime.now() - memory.created_at).total_seconds() / 86400
        retention = self._curve.calculate_retention(
            days_elapsed=days_elapsed,
            importance=importance,
            usage_frequency=frequency,
            emotional_valence=memory.emotional_valence,
        )

        emotional = min(abs(memory.emotional_valence), 1.0)

        return (
            importance * 0.3
            + frequency * 0.2
            + retention * 0.3
            + emotional * 0.2
        )

    def should_evict(self, memory: MemoryEntry, threshold: float = 0.3) -> bool:
        """评分低于阈值则应淘汰。CRITICAL 记忆永不淘汰。"""
        if memory.importance == MemoryImportance.CRITICAL:
            return False
        return self.score(memory) < threshold

    def rank_memories(self, memories: List[MemoryEntry]) -> List[tuple]:
        """按评分升序排列（最值得淘汰的在前）。"""
        scored = [(m, self.score(m)) for m in memories]
        scored.sort(key=lambda x: x[1])
        return scored
