"""
记忆检索系统

设计依据: M8_P3_MEMORY_HIERARCHY_DESIGN.md §四

意图分流 + 四层并行 + 三路加权融合
"""

import asyncio
import math
import time
import logging
from typing import Optional, List
from enum import Enum

from .hierarchical_store import HierarchicalStore, MemoryEntry

logger = logging.getLogger(__name__)


class RetrieveIntent(str, Enum):
    """检索意图"""
    RECENT_CONTEXT = "recent"          # 仅 L1+L2（当前对话上下文）
    SEMANTIC_KNOWLEDGE = "semantic"    # 仅 L3（结构化知识）
    HISTORICAL = "historical"          # 仅 L4（长期档案）
    FULL_STACK = "full"                # 四层并行


class MemoryRetriever:
    """
    记忆检索器

    检索策略:
    - RECENT_CONTEXT: L1 + L2 并发
    - SEMANTIC_KNOWLEDGE: L3 单独
    - HISTORICAL: L4 单独
    - FULL_STACK: L1/L2/L3/L4 四层并行 → 三路加权融合

    延迟 = max(L1, L2, L3, L4) 而非 sum (专家 #4: 检索性能)
    """

    # 三路加权系数
    SIM_WEIGHT = 0.5
    TIME_DECAY_WEIGHT = 0.3
    IMPORTANCE_WEIGHT = 0.2
    TIME_DECAY_LAMBDA = 0.01  # 遗忘系数 λ

    def __init__(self, store: HierarchicalStore):
        self._store = store

    async def retrieve(
        self,
        query: str,
        intent: RetrieveIntent = RetrieveIntent.FULL_STACK,
        top_k: int = 10,
    ) -> list[MemoryEntry]:
        """
        检索入口

        Args:
            query: 检索查询
            intent: 检索意图
            top_k: 返回 top-K 结果

        Returns:
            融合排序后的 MemoryEntry 列表
        """
        if intent == RetrieveIntent.RECENT_CONTEXT:
            results = await asyncio.gather(
                self._store.search_l1(query, limit=top_k),
                self._store.search_l2(query, limit=top_k),
            )
            l1_results, l2_results = results
            all_results = l1_results + l2_results

        elif intent == RetrieveIntent.SEMANTIC_KNOWLEDGE:
            all_results = await self._store.search_l3(query, top_k=top_k)
            # L3 返回的是 dict，需要转换
            l1_warmup = await self._store.search_l1(query, limit=top_k)
            return l1_warmup  # 暂时返回 L1，Phase 2 完善

        elif intent == RetrieveIntent.HISTORICAL:
            all_results = await self._store.search_l4(query, limit=top_k)
            return []  # Phase 3 完善

        elif intent == RetrieveIntent.FULL_STACK:
            # 四层并行
            l1_task = self._store.search_l1(query, limit=top_k)
            l2_task = self._store.search_l2(query, limit=top_k)
            l3_task = self._store.search_l3(query, top_k=top_k)
            l4_task = self._store.search_l4(query, limit=top_k)

            l1_results, l2_results, l3_dicts, l4_dicts = await asyncio.gather(
                l1_task, l2_task, l3_task, l4_task
            )

            # Merge: L1+L2 优先，L3/L4 dict 转 MemoryEntry
            all_results = list(l1_results) + list(l2_results)
            for d in l3_dicts:
                if isinstance(d, dict):
                    all_results.append(MemoryEntry(
                        entry_id=str(d.get("entry_id", "l3")),
                        content=str(d.get("content", "")),
                        tier="l3_semantic",
                        importance=0.7,
                        metadata=d.get("metadata", {}),
                    ))

            # L3/L4 命中 → 异步回填 L1
            if l3_dicts or l4_dicts:
                asyncio.create_task(self._warmup_l1_from_archive(query, l3_dicts, l4_dicts))

        else:
            all_results = []

        # 三路加权融合排序
        scored = self._weighted_fusion(all_results, query)
        scored.sort(key=lambda x: x[1], reverse=True)

        return [entry for entry, score in scored[:top_k]]

    async def _warmup_l1_from_archive(
        self,
        query: str,
        l3_results: list[dict],
        l4_results: list[dict]
    ):
        """L3/L4 命中后异步回填 L1（专家 #2: 数据升温）"""
        for d in l3_results[:3]:
            await self._store.warmup_l1(
                entry_id=d.get("entry_id", "l3"),
                content=d.get("content", "")[:200],
                priority=0.5
            )
        for d in l4_results[:3]:
            await self._store.warmup_l1(
                entry_id=d.get("entry_id", "l4"),
                content=d.get("content", "")[:200],
                priority=0.5
            )

    def _weighted_fusion(
        self,
        entries: list[MemoryEntry],
        query: str
    ) -> list[tuple[MemoryEntry, float]]:
        """
        三路加权融合

        score = sim * 0.5 + time_decay * 0.3 + importance * 0.2
        """
        query_lower = query.lower()
        scored = []

        for entry in entries:
            # 1. 文本相似度 (Jaccard 近似)
            sim = self._jaccard_sim(query_lower, entry.content.lower())

            # 2. 时间衰减 (遗忘曲线)
            elapsed = entry.idle_seconds / 3600.0  # 转换为小时
            time_decay = math.exp(-self.TIME_DECAY_LAMBDA * elapsed * 3600)

            # 3. 重要性评分
            importance = entry.importance

            score = (
                sim * self.SIM_WEIGHT +
                time_decay * self.TIME_DECAY_WEIGHT +
                importance * self.IMPORTANCE_WEIGHT
            )
            scored.append((entry, score))

        return scored

    @staticmethod
    def _jaccard_sim(a: str, b: str) -> float:
        """Jaccard 相似度（单词级别）"""
        set_a = set(a.split())
        set_b = set(b.split())
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0
