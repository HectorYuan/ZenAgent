"""
统一整合管线

设计依据: M8_P3_MEMORY_HIERARCHY_DESIGN.md §五.2 (专家 #5: 数据一致性)

所有记忆降级操作经过统一管线，每条记忆只处理一次。
"""

import asyncio
import logging
from typing import Optional
from dataclasses import dataclass, field

from .hierarchical_store import HierarchicalStore, MemoryEntry, MemoryTier
from .semantic_kb import SemanticKnowledgeBase
from .knowledge_extractor import KnowledgeExtractor

logger = logging.getLogger(__name__)


@dataclass
class PipelineStats:
    """管线统计"""
    total_processed: int = 0
    facts_extracted: int = 0
    archived: int = 0
    errors: int = 0


class ConsolidationPipeline:
    """
    统一整合管线

    流程: L1 过期记忆 → 知识提取 → L3 语义库 → 归档缓冲区 → L4
    """

    def __init__(
        self,
        store: HierarchicalStore,
        kb: Optional[SemanticKnowledgeBase] = None,
        extractor: Optional[KnowledgeExtractor] = None,
    ):
        self._store = store
        self._kb = kb or SemanticKnowledgeBase()
        self._extractor = extractor or KnowledgeExtractor()
        self._archive_buffer: list[MemoryEntry] = []
        self._archive_threshold = 50  # 批量归档阈值
        self._stats = PipelineStats()
        self._lock = asyncio.Lock()

    @property
    def stats(self) -> dict:
        return {
            "total_processed": self._stats.total_processed,
            "facts_extracted": self._stats.facts_extracted,
            "archived": self._stats.archived,
            "buffer_size": len(self._archive_buffer),
            "errors": self._stats.errors,
        }

    async def process(self, entry: MemoryEntry):
        """
        处理一条记忆条目（统一入口）

        1. 实体识别 + 关系抽取
        2. SPO 三元组提取 → L3 语义库 (upsert)
        3. 累积归档缓冲区 → 达到阈值 → 批量归档 L4
        """
        async with self._lock:
            try:
                # Step 1-2: 知识提取 + 写入语义库
                facts = self._extractor.extract_and_upsert(
                    entry.content,
                    self._kb,
                    source_id=entry.entry_id
                )
                self._stats.facts_extracted += len(facts)

                # Step 3: 加入归档缓冲区
                self._archive_buffer.append(entry)
                self._stats.total_processed += 1

                # 达到阈值 → 触发批量归档
                if len(self._archive_buffer) >= self._archive_threshold:
                    asyncio.create_task(self._flush_archive())

            except Exception as e:
                self._stats.errors += 1
                logger.debug(f"Pipeline error for {entry.entry_id}: {e}")

    async def process_batch(self, entries: list[MemoryEntry]):
        """批量处理记忆条目"""
        for entry in entries:
            await self.process(entry)

    async def _flush_archive(self):
        """将归档缓冲区写入 L4"""
        if not self._archive_buffer:
            return

        batch = self._archive_buffer[:]
        self._archive_buffer.clear()

        # 批量写入 L4
        for entry in batch:
            archive_data = {
                "entry_id": entry.entry_id,
                "content": entry.content,
                "importance": entry.importance,
                "metadata": entry.metadata,
                "sources": entry.sources,
                "archived_at": entry.created_at,
            }
            await self._store.store_l4(
                f"archive:{entry.entry_id}",
                archive_data
            )

        self._stats.archived += len(batch)
        logger.debug(f"Archived {len(batch)} entries to L4")

    async def flush(self):
        """手动刷新归档缓冲区"""
        await self._flush_archive()

    def get_kb_stats(self) -> dict:
        """获取知识库统计"""
        return self._kb.get_stats()
