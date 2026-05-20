"""
档案管理器

设计依据: M8_P3_MEMORY_HIERARCHY_DESIGN.md §五.4

分层摘要 + 批量归档 + 容量管理
"""

import asyncio
import json
import os
import time
import logging
from typing import Optional, List
from dataclasses import dataclass

from .hierarchical_store import HierarchicalStore, MemoryEntry

logger = logging.getLogger(__name__)


class SummaryLevel:
    """摘要级别"""
    QUICK = "quick"       # 规则快速摘要: $0
    BATCH = "batch"       # 批量摘要 (50条): $0.002
    DEEP = "deep"         # 深度摘要 (500条): $0.01


@dataclass
class ArchiveStats:
    """归档统计"""
    total_archived: int = 0
    quick_summaries: int = 0
    batch_summaries: int = 0
    deep_summaries: int = 0
    total_files: int = 0


class ArchivalManager:
    """
    档案管理器

    功能:
    - L2 容量达到阈值 → 选择候选 → 摘要压缩 → 写入 L4
    - 分层摘要: 规则快速 ($0) / 批量 LLM ($0.002) / 深度 LLM ($0.01)
    - L2 活跃度计数器: access_count > 3 优先保留
    """

    L2_ARCHIVE_THRESHOLD = 800     # L2 容量触发阈值
    BATCH_SIZE = 50                # 批量摘要每批大小
    DEEP_BATCH_SIZE = 500          # 深度摘要阈值

    def __init__(
        self,
        store: HierarchicalStore,
        archive_dir: str = "/tmp/memory_archive"
    ):
        self._store = store
        self._archive_dir = archive_dir
        self._stats = ArchiveStats()
        os.makedirs(archive_dir, exist_ok=True)

    @property
    def stats(self) -> dict:
        return {
            "total_archived": self._stats.total_archived,
            "quick_summaries": self._stats.quick_summaries,
            "batch_summaries": self._stats.batch_summaries,
            "deep_summaries": self._stats.deep_summaries,
            "total_files": self._stats.total_files,
        }

    async def should_archive(self) -> bool:
        """检查是否应该触发归档 (L2 > 800)"""
        return self._store.stats["l2_size"] >= self.L2_ARCHIVE_THRESHOLD

    async def select_candidates(self, limit: int = 200) -> list[MemoryEntry]:
        """
        选择归档候选

        策略: 取 access_count 最低 + idle 最长的条目
        """
        candidates = list(self._store._l2.values())

        # 保护活跃条目: access_count > 3 免于归档
        candidates = [e for e in candidates if e.access_count <= 3]

        # 按 idle_seconds 降序 (最久未访问优先)，access_count 升序
        candidates.sort(
            key=lambda e: (-e.idle_seconds, e.access_count)
        )

        return candidates[:limit]

    async def quick_summarize(self, entries: list[MemoryEntry]) -> list[dict]:
        """
        规则快速摘要 ($0 成本)

        提取关键字段: topic, type, outcome
        """
        summaries = []
        for entry in entries:
            meta = entry.metadata
            summary = {
                "entry_id": entry.entry_id,
                "content_preview": entry.content[:100],
                "type": meta.get("type", "unknown"),
                "topic": meta.get("topic", ""),
                "importance": entry.importance,
                "access_count": entry.access_count,
                "timestamp": entry.created_at,
            }
            summaries.append(summary)

        self._stats.quick_summaries += len(summaries)
        return summaries

    async def batch_summarize(self, entries: list[MemoryEntry]) -> list[dict]:
        """
        批量摘要 (LLM 可选, 当前降级为规则摘要)
        """
        # TODO: 接入 LLM 生成汇总段落 ($0.002)
        # 当前降级为规则摘要
        return await self.quick_summarize(entries)

    async def deep_summarize(self, entries: list[MemoryEntry]) -> list[dict]:
        """
        深度摘要 (LLM, 当前降级为规则摘要)
        """
        # TODO: 接入 LLM 生成结构化叙事 ($0.01)
        return await self.quick_summarize(entries)

    async def write_archive(self, summaries: list[dict]) -> str:
        """
        写入归档文件 (JSONL)
        """
        timestamp = int(time.time())
        filename = os.path.join(
            self._archive_dir,
            f"archive_{timestamp}_{len(summaries)}.jsonl"
        )

        with open(filename, "w") as f:
            for summary in summaries:
                f.write(json.dumps(summary) + "\n")

        self._stats.total_files += 1
        self._stats.total_archived += len(summaries)

        # 写入 L4 存储层
        for summary in summaries:
            await self._store.store_l4(
                f"archive:{summary['entry_id']}",
                summary
            )

        logger.info(f"Archived {len(summaries)} entries to {filename}")
        return filename

    async def compact(self):
        """执行完整的压缩归档流程"""
        if not await self.should_archive():
            logger.debug("L2 size below threshold, skipping archive")
            return None

        # 1. 选择候选
        candidates = await self.select_candidates(limit=200)

        if not candidates:
            return None

        # 2. 快速摘要
        summaries = await self.quick_summarize(candidates)

        # 3. 写入归档
        filename = await self.write_archive(summaries)

        # 4. 从 L2 移除已归档条目
        for entry in candidates:
            self._store._l2.pop(entry.entry_id, None)

        # 5. 更新统计
        self._store._stats.l2_size = len(self._store._l2)

        logger.info(
            f"Compaction complete: {len(candidates)} entries archived, "
            f"L2 size now {self._store.stats['l2_size']}"
        )

        return filename
