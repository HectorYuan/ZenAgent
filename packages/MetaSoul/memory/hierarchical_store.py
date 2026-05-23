"""
分层记忆存储

设计依据: M8_P3_MEMORY_HIERARCHY_DESIGN.md

四层存储 + 可插拔后端 + L3→L1 预热回填
"""

import asyncio
import time
import logging
from typing import Optional, Any, Dict, List, Deque
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================
# 数据结构
# ============================================================

class MemoryTier(str, Enum):
    L1_HOT = "l1_hot"           # 热记忆: 当前会话
    L2_WARM = "l2_warm"          # 温记忆: 跨会话情景
    L3_SEMANTIC = "l3_semantic"  # 语义知识: 结构化
    L4_ARCHIVE = "l4_archive"    # 档案归档: 长期


@dataclass
class MemoryEntry:
    """统一记忆条目"""
    entry_id: str
    content: str
    tier: MemoryTier
    created_at: float = field(default_factory=time.monotonic)
    last_accessed: float = field(default_factory=time.monotonic)
    access_count: int = 0
    importance: float = 0.5          # MemoryScorer 评分
    metadata: dict = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)   # 来源记忆 ID

    def touch(self):
        self.last_accessed = time.monotonic()
        self.access_count += 1

    @property
    def idle_seconds(self) -> float:
        return time.monotonic() - self.last_accessed


# ============================================================
# 可插拔后端
# ============================================================

from abc import ABC, abstractmethod

class BackendProtocol(ABC):
    """后端接口协议"""

    @abstractmethod
    async def get(self, key: str) -> Optional[dict]:
        ...

    @abstractmethod
    async def set(self, key: str, value: dict, ttl: int = 86400) -> None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    async def keys(self, pattern: str = "*") -> list[str]:
        ...

    @abstractmethod
    async def size(self) -> int:
        ...


class MemoryBackend(BackendProtocol):
    """内存后端（默认）"""

    def __init__(self):
        self._data: dict[str, tuple[dict, float]] = {}

    async def get(self, key: str) -> Optional[dict]:
        if key not in self._data:
            return None
        value, expire_at = self._data[key]
        if time.time() > expire_at:
            del self._data[key]
            return None
        return value

    async def set(self, key: str, value: dict, ttl: int = 86400) -> None:
        self._data[key] = (value, time.time() + ttl)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def exists(self, key: str) -> bool:
        if key not in self._data:
            return False
        _, expire_at = self._data[key]
        if time.time() > expire_at:
            del self._data[key]
            return False
        return True

    async def keys(self, pattern: str = "*") -> list[str]:
        return list(self._data.keys())

    async def size(self) -> int:
        return len(self._data)


class RedisBackend(BackendProtocol):
    """Redis 后端（可选）"""

    def __init__(self, redis_url: str = "redis://localhost:6379/1"):
        self._redis_url = redis_url
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = await aioredis.from_url(self._redis_url)
            except ImportError:
                raise RuntimeError("redis not installed")
        return self._redis

    async def get(self, key: str) -> Optional[dict]:
        try:
            import json
            redis = await self._get_redis()
            data = await redis.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    async def set(self, key: str, value: dict, ttl: int = 86400) -> None:
        try:
            import json
            redis = await self._get_redis()
            await redis.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.debug(f"Redis set failed: {e}")

    async def delete(self, key: str) -> None:
        try:
            redis = await self._get_redis()
            await redis.delete(key)
        except Exception:
            pass

    async def exists(self, key: str) -> bool:
        try:
            redis = await self._get_redis()
            return bool(await redis.exists(key))
        except Exception:
            return False

    async def keys(self, pattern: str = "*") -> list[str]:
        try:
            redis = await self._get_redis()
            return [k.decode() for k in await redis.keys(pattern)]
        except Exception:
            return []

    async def size(self) -> int:
        try:
            redis = await self._get_redis()
            return await redis.dbsize()
        except Exception:
            return 0


# ============================================================
# HierarchicalStore — 四层统一存储
# ============================================================

@dataclass
class StoreStats:
    """存储统计"""
    l1_size: int = 0
    l2_size: int = 0
    l3_size: int = 0
    l4_size: int = 0
    total_stored: int = 0
    total_retrieved: int = 0
    l1_evictions: int = 0
    consolidations: int = 0
    warmups: int = 0


class HierarchicalStore:
    """
    四层分层存储

    L1: deque (FIFO), 容量 20, <0.1ms
    L2: dict + Backend, 容量 1000, <1ms
    L3: dict (SPO 三元组占位), 无限制, <5ms
    L4: dict (档案摘要占位), 无限制, <30s
    """

    L1_CAPACITY = 20
    L2_CAPACITY = 1000
    L1_CONSOLIDATION_THRESHOLD = 15  # L1 超过此值触发 L1→L2
    L2_ARCHIVE_THRESHOLD = 800       # L2 超过此值触发归档候选

    def __init__(
        self,
        l2_backend: Optional[BackendProtocol] = None,
        l4_dir: str = "/tmp/memory_archive"
    ):
        # L1: 热记忆 (deque FIFO)
        self._l1: Deque[MemoryEntry] = deque(maxlen=self.L1_CAPACITY)

        # L2: 温记忆 (dict + 后端)
        self._l2: dict[str, MemoryEntry] = {}
        self._l2_backend = l2_backend or MemoryBackend()

        # L3: 语义知识 (占位，Phase 2 替换为 SemanticKnowledgeBase)
        self._l3: dict[str, dict] = {}

        # L4: 档案归档 (占位，Phase 3 替换为 ArchivalManager)
        self._l4: dict[str, dict] = {}
        self._l4_dir = l4_dir

        # 统计
        self._stats = StoreStats()
        self._lock = asyncio.Lock()

    @property
    def stats(self) -> dict:
        return {
            "l1_size": self._stats.l1_size,
            "l2_size": self._stats.l2_size,
            "l3_size": self._stats.l3_size,
            "l4_size": self._stats.l4_size,
            "total_stored": self._stats.total_stored,
            "total_retrieved": self._stats.total_retrieved,
            "l1_evictions": self._stats.l1_evictions,
            "consolidations": self._stats.consolidations,
            "warmups": self._stats.warmups,
        }

    # ==================== L1 热记忆 ====================

    async def store_l1(self, entry: MemoryEntry) -> Optional[MemoryEntry]:
        """存储到 L1，FIFO 自动淘汰"""
        async with self._lock:
            entry.tier = MemoryTier.L1_HOT
            evicted = None

            if len(self._l1) >= self.L1_CAPACITY:
                evicted = self._l1[0]  # 最旧的
                self._stats.l1_evictions += 1

            self._l1.append(entry)
            self._stats.l1_size = len(self._l1)
            self._stats.total_stored += 1

            # 超过整合阈值 → 触发 L1→L2
            if len(self._l1) >= self.L1_CONSOLIDATION_THRESHOLD:
                asyncio.create_task(self._consolidate_l1_to_l2())

        return evicted

    async def _consolidate_l1_to_l2(self):
        """L1→L2 整合：取最早 5 条压缩为摘要"""
        async with self._lock:
            if len(self._l1) < self.L1_CONSOLIDATION_THRESHOLD:
                return

            # 取最早 5 条
            to_consolidate = []
            for _ in range(min(5, len(self._l1))):
                to_consolidate.append(self._l1.popleft())
            self._stats.l1_size = len(self._l1)

        # 生成规则摘要并写入 L2
        for entry in to_consolidate:
            summary_text = self._quick_summarize(entry)
            summary_entry = MemoryEntry(
                entry_id=entry.entry_id,
                content=summary_text,
                tier=MemoryTier.L2_WARM,
                importance=entry.importance,
                metadata=entry.metadata,
                sources=[entry.entry_id],
            )
            await self.store_l2(summary_entry)

        self._stats.consolidations += 1
        logger.debug(f"L1→L2 consolidated {len(to_consolidate)} entries")

    @staticmethod
    def _quick_summarize(entry: MemoryEntry) -> str:
        """规则快速摘要：截断 + 保留关键字段"""
        content = entry.content[:200]
        meta = entry.metadata
        parts = [content]
        if meta.get("type"):
            parts.append(f"[{meta['type']}]")
        if meta.get("topic"):
            parts.append(f"topic:{meta['topic']}")
        return " | ".join(parts)

    async def search_l1(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        """检索 L1（全量返回最近条目）"""
        async with self._lock:
            results = list(self._l1)
        # 简单关键词过滤
        if query:
            query_lower = query.lower()
            results = [e for e in results if query_lower in e.content.lower()]
        # 返回最近的
        results = list(reversed(results))[:limit]
        for e in results:
            e.touch()
        self._stats.total_retrieved += len(results)
        return results

    # ==================== L2 温记忆 ====================

    async def store_l2(self, entry: MemoryEntry) -> None:
        """存储到 L2"""
        async with self._lock:
            entry.tier = MemoryTier.L2_WARM
            self._l2[entry.entry_id] = entry
            self._stats.l2_size = len(self._l2)

            # 同步到后端
            try:
                await self._l2_backend.set(
                    f"mem:l2:{entry.entry_id}",
                    {
                        "entry_id": entry.entry_id,
                        "content": entry.content,
                        "created_at": entry.created_at,
                        "importance": entry.importance,
                        "metadata": entry.metadata,
                    }
                )
            except Exception as e:
                logger.debug(f"L2 backend sync failed: {e}")

    async def search_l2(self, query: str, limit: int = 20) -> list[MemoryEntry]:
        """检索 L2（关键词 + 活跃度排序）"""
        async with self._lock:
            candidates = list(self._l2.values())

        if query:
            query_lower = query.lower()
            candidates = [
                e for e in candidates
                if query_lower in e.content.lower()
                or any(query_lower in str(v).lower() for v in e.metadata.values())
            ]

        # 活跃度排序：access_count 高优先，idle 短优先
        candidates.sort(
            key=lambda e: (e.access_count, -e.idle_seconds),
            reverse=True
        )
        results = candidates[:limit]
        for e in results:
            e.touch()
        self._stats.total_retrieved += len(results)
        return results

    # ==================== L3 语义知识（占位） ====================

    async def store_l3(self, key: str, data: dict) -> None:
        """存储到 L3 语义知识库"""
        async with self._lock:
            self._l3[key] = data
            self._stats.l3_size = len(self._l3)

    async def search_l3(self, query: str, top_k: int = 5) -> list[dict]:
        """检索 L3（关键词匹配，Phase 2 替换为 SPO 向量检索）"""
        async with self._lock:
            query_lower = query.lower()
            results = []
            for key, data in self._l3.items():
                if query_lower in key.lower() or query_lower in str(data).lower():
                    results.append(data)
            self._stats.total_retrieved += len(results)
            return results[:top_k]

    # ==================== L4 档案归档（占位） ====================

    async def store_l4(self, key: str, data: dict) -> None:
        """存储到 L4 档案"""
        async with self._lock:
            self._l4[key] = data
            self._stats.l4_size = len(self._l4)

    async def search_l4(self, query: str, limit: int = 10) -> list[dict]:
        """检索 L4（关键词匹配，Phase 3 替换为文件索引检索）"""
        async with self._lock:
            query_lower = query.lower()
            results = []
            for key, data in self._l4.items():
                if query_lower in key.lower() or query_lower in str(data).lower():
                    results.append(data)
            self._stats.total_retrieved += len(results)
            return results[:limit]

    # ==================== 统一接口 ====================

    async def store(
        self,
        entry_id: str,
        content: str,
        tier: MemoryTier = MemoryTier.L1_HOT,
        importance: float = 0.5,
        metadata: Optional[dict] = None,
    ) -> MemoryEntry:
        """统一存储入口"""
        entry = MemoryEntry(
            entry_id=entry_id,
            content=content,
            tier=tier,
            importance=importance,
            metadata=metadata or {},
        )

        if tier == MemoryTier.L1_HOT:
            await self.store_l1(entry)
        elif tier == MemoryTier.L2_WARM:
            await self.store_l2(entry)
        elif tier == MemoryTier.L3_SEMANTIC:
            await self.store_l3(entry_id, {"content": content, "metadata": metadata or {}})
        elif tier == MemoryTier.L4_ARCHIVE:
            await self.store_l4(entry_id, {"content": content, "metadata": metadata or {}})

        return entry

    async def warmup_l1(self, entry_id: str, content: str, priority: float = 0.5):
        """L3/L4 命中后回填 L1（专家 #2: 数据升温）"""
        entry = MemoryEntry(
            entry_id=f"warmup:{entry_id}",
            content=content,
            tier=MemoryTier.L1_HOT,
            importance=priority,
            metadata={"source": "archive_warmup", "original_id": entry_id},
        )
        await self.store_l1(entry)
        self._stats.warmups += 1
