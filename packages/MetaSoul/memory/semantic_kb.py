"""
语义知识库 — SPO 三元组 + 来源追踪 + 冲突检测

设计依据: M8_P3_MEMORY_HIERARCHY_DESIGN.md §三(专家 #1: 知识图谱)
"""

import time
import logging
from typing import Optional, List, Dict, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeTriple:
    """SPO 三元组"""
    subject: str
    predicate: str
    object: str
    confidence: float = 0.5          # 0-1
    sources: list[str] = field(default_factory=list)   # 来源记忆 ID
    first_seen: float = field(default_factory=time.monotonic)
    last_seen: float = field(default_factory=time.monotonic)
    seen_count: int = 1

    @property
    def key(self) -> str:
        return f"{self.subject}::{self.predicate}::{self.object}"

    @property
    def sp_key(self) -> str:
        """(subject, predicate) pair key, 用于冲突检测"""
        return f"{self.subject}::{self.predicate}"

    @property
    def age_days(self) -> float:
        return (time.monotonic() - self.last_seen) / 86400.0

    def confirm(self, source_id: str):
        """确认已有知识: seen_count++，更新置信度和来源"""
        self.seen_count += 1
        self.last_seen = time.monotonic()
        if source_id not in self.sources:
            self.sources.append(source_id)
        # 置信度提升（上限 0.95）
        self.confidence = min(0.95, self.confidence + 0.05)

    def decay(self, factor: float = 0.9):
        """知识老化衰减"""
        if self.age_days > 30:
            self.confidence *= factor

    def is_stale(self, threshold: float = 0.3) -> bool:
        return self.confidence < threshold


class SemanticKnowledgeBase:
    """
    语义知识库

    存储 SPO 三元组，支持 upsert/冲突检测/语义检索/老化衰减
    """

    def __init__(self):
        self._triples: dict[str, KnowledgeTriple] = {}  # key = "s::p::o"
        self._entity_index: dict[str, set[str]] = {}     # entity → triple keys
        self._pending_conflicts: dict[str, list[KnowledgeTriple]] = {}  # sp_key → conflicting triples

    # ==================== 写入 ====================

    def upsert(self, subject: str, predicate: str, object: str,
               confidence: float = 0.5, source_id: str = "") -> KnowledgeTriple:
        """
        Upsert 三元组: 已存在则确认，不存在则新建

        Returns:
            最终的三元组
        """
        triple_key = f"{subject}::{predicate}::{object}"
        sp_key = f"{subject}::{predicate}"

        if triple_key in self._triples:
            # 已存在: 确认
            existing = self._triples[triple_key]
            existing.confirm(source_id)
            logger.debug(f"Confirmed triple: {subject}::{predicate}::{object} (count={existing.seen_count})")
            return existing

        # 冲突检测: 同 (s,p) 不同 object
        if sp_key in self._pending_conflicts:
            conflicts = self._pending_conflicts[sp_key]
            for c in conflicts:
                if c.object != object:
                    logger.info(f"Conflict detected: {subject}::{predicate} = {c.object} vs {object}")
                    self._add_conflict(c, subject, predicate, object, confidence, source_id)
                    return c  # 保留旧的

        # 新三元组
        triple = KnowledgeTriple(
            subject=subject,
            predicate=predicate,
            object=object,
            confidence=confidence,
            sources=[source_id] if source_id else [],
        )

        self._triples[triple_key] = triple

        # 更新实体索引
        for entity in (subject, object):
            if entity not in self._entity_index:
                self._entity_index[entity] = set()
            self._entity_index[entity].add(triple_key)

        logger.debug(f"New triple: {subject}::{predicate}::{object}")
        return triple

    def _add_conflict(self, existing: KnowledgeTriple,
                      subject: str, predicate: str, object: str,
                      confidence: float, source_id: str):
        """添加冲突记录"""
        sp_key = existing.sp_key
        conflicting = KnowledgeTriple(
            subject=subject, predicate=predicate, object=object,
            confidence=confidence, sources=[source_id] if source_id else [],
        )
        if sp_key not in self._pending_conflicts:
            self._pending_conflicts[sp_key] = []
        if conflicting not in self._pending_conflicts[sp_key]:
            self._pending_conflicts[sp_key].append(conflicting)

    # ==================== 检索 ====================

    def get_by_entity(self, entity: str) -> list[KnowledgeTriple]:
        """按实体检索所有相关三元组（大小写不敏感）"""
        entity_lower = entity.lower()
        results = []
        for key, triple in self._triples.items():
            if (triple.subject.lower() == entity_lower or
                triple.object.lower() == entity_lower):
                results.append(triple)
        return results

    def get_by_sp(self, subject: str, predicate: str) -> Optional[KnowledgeTriple]:
        """按 (subject, predicate) 检索"""
        # 查找匹配的三元组
        sp_prefix = f"{subject}::{predicate}::"
        for key, triple in self._triples.items():
            if key.startswith(sp_prefix):
                return triple
        return None

    def semantic_search(self, query: str, top_k: int = 5) -> list[KnowledgeTriple]:
        """
        语义检索 (关键词级别)

        检索 subject/predicate/object 中包含 query 词的三元组
        """
        query_lower = query.lower()
        results = []

        for triple in self._triples.values():
            text = f"{triple.subject} {triple.predicate} {triple.object}".lower()
            if query_lower in text:
                results.append(triple)

        # 按 (confidence × log(seen_count+1)) 排序
        import math
        results.sort(
            key=lambda t: t.confidence * math.log(t.seen_count + 1),
            reverse=True
        )
        return results[:top_k]

    # ==================== 维护 ====================

    def decay_all(self, factor: float = 0.9):
        """全局衰减老化知识"""
        stale_keys = []
        for key, triple in self._triples.items():
            triple.decay(factor)
            if triple.is_stale():
                stale_keys.append(key)

        for key in stale_keys:
            self._remove(key)

        if stale_keys:
            logger.info(f"Decayed {len(stale_keys)} stale triples")

    def _remove(self, triple_key: str):
        """删除三元组"""
        if triple_key not in self._triples:
            return
        triple = self._triples[triple_key]
        for entity in (triple.subject, triple.object):
            if entity in self._entity_index:
                self._entity_index[entity].discard(triple_key)
        del self._triples[triple_key]

    def get_pending_conflicts(self) -> dict[str, list[dict]]:
        """获取待验证的冲突列表"""
        return {
            sp_key: [
                {"subject": t.subject, "predicate": t.predicate,
                 "object": t.object, "confidence": t.confidence}
                for t in triples
            ]
            for sp_key, triples in self._pending_conflicts.items()
        }

    def resolve_conflict(self, sp_key: str, accepted_object: str):
        """解决冲突：保留选中的 object，移除其他"""
        if sp_key in self._pending_conflicts:
            del self._pending_conflicts[sp_key]
        # 移除未选中的三元组
        sp_prefix = sp_key + "::"
        keys_to_remove = [
            k for k in self._triples
            if k.startswith(sp_prefix) and not k.endswith(f"::{accepted_object}")
        ]
        for k in keys_to_remove:
            self._remove(k)

    # ==================== 统计 ====================

    @property
    def total_triples(self) -> int:
        return len(self._triples)

    @property
    def total_entities(self) -> int:
        return len(self._entity_index)

    @property
    def total_conflicts(self) -> int:
        return len(self._pending_conflicts)

    def get_stats(self) -> dict:
        return {
            "total_triples": self.total_triples,
            "total_entities": self.total_entities,
            "total_conflicts": self.total_conflicts,
            "avg_confidence": (
                sum(t.confidence for t in self._triples.values()) / max(self.total_triples, 1)
            ),
            "avg_seen_count": (
                sum(t.seen_count for t in self._triples.values()) / max(self.total_triples, 1)
            ),
        }
