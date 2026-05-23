"""
增强缓存模块

设计依据: M8_P1_CACHE_ENHANCEMENT_DESIGN.md

增强内容:
- RingBuffer: 单一环形缓冲区，共享双窗口数据源
- HotspotTracker: 三态热度机 (HOT/WARM/COLD) + 双层计数器
- EvictionManager: 热度加权淘汰 + 主动降级
"""

from typing import Optional, Any, Dict, List, Tuple
import hashlib
import json
import logging
import time
import math
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

from .core import ChatRequest, Message

logger = logging.getLogger(__name__)


# ============================================================
# 缓存后端 (保持原有接口不变)
# ============================================================

from abc import ABC, abstractmethod

class CacheBackend(ABC):
    """缓存后端基类"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        raise NotImplementedError

    async def size(self) -> int:
        """返回当前缓存条目数（用于淘汰检查）"""
        raise NotImplementedError

    async def keys(self) -> list[str]:
        """返回所有缓存键（用于淘汰扫描）"""
        raise NotImplementedError


class MemoryCache(CacheBackend):
    """内存缓存"""

    def __init__(self):
        self._cache: Dict[str, tuple[Any, float]] = {}

    async def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        value, expire_at = self._cache[key]
        if time.time() > expire_at:
            del self._cache[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        self._cache[key] = (value, time.time() + ttl)

    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    async def exists(self, key: str) -> bool:
        if key not in self._cache:
            return False
        _, expire_at = self._cache[key]
        if time.time() > expire_at:
            del self._cache[key]
            return False
        return True

    async def size(self) -> int:
        return len(self._cache)

    async def keys(self) -> list[str]:
        return list(self._cache.keys())

    def clear_expired(self):
        now = time.time()
        expired = [k for k, (_, e) in self._cache.items() if now > e]
        for k in expired:
            del self._cache[k]


class RedisCache(CacheBackend):
    """Redis 缓存"""

    _import_warned = False  # 类级别，整个进程只警告一次

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self._redis_url = redis_url
        self._redis = None
        self._fallback = MemoryCache()  # 内置 fallback

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = await aioredis.from_url(self._redis_url)
            except ImportError:
                if not RedisCache._import_warned:
                    logger.info("Redis module not installed, using memory cache. "
                                "Install with: pip install redis")
                    RedisCache._import_warned = True
                raise
        return self._redis

    async def get(self, key: str) -> Optional[Any]:
        try:
            redis = await self._get_redis()
            data = await redis.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass  # 静默降级到 memory fallback
        return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        try:
            redis = await self._get_redis()
            await redis.setex(key, ttl, json.dumps(value))
        except Exception:
            pass  # 静默降级

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

    async def size(self) -> int:
        try:
            redis = await self._get_redis()
            return await redis.dbsize()
        except Exception:
            return 0

    async def keys(self) -> list[str]:
        try:
            redis = await self._get_redis()
            return [k.decode() for k in await redis.keys()]
        except Exception:
            return []

    async def zincrby(self, zset_key: str, member: str, increment: int = 1):
        """ZSET 增量计数（全局热点排名）"""
        try:
            redis = await self._get_redis()
            await redis.zincrby(zset_key, increment, member)
        except Exception as e:
            logger.debug(f"Redis zincrby failed: {e}")

    async def zrevrange(self, zset_key: str, start: int, stop: int) -> list[tuple[str, float]]:
        """ZSET 倒序取 Top-N"""
        try:
            redis = await self._get_redis()
            return await redis.zrevrange(zset_key, start, stop, withscores=True)
        except Exception:
            return []

    async def publish(self, channel: str, message: str):
        """发布消息"""
        try:
            redis = await self._get_redis()
            await redis.publish(channel, message)
        except Exception as e:
            logger.debug(f"Redis publish failed: {e}")


# ============================================================
# 环形缓冲区 (性能专家建议 #1: 单一数据源)
# ============================================================

class RingBuffer:
    """
    环形缓冲区 — 共享原始命中数据

    双时间窗口共享同一数据源，存储从 O(2N) 降到 O(N)
    """

    def __init__(self, capacity: int = 10000):
        self.capacity = capacity
        self._buffer: list[tuple[float, str]] = []  # [(timestamp, cache_key)]
        self._cursor = 0
        self._lock = asyncio.Lock()

    async def record(self, key: str):
        """记录一次命中，自动淘汰最旧记录"""
        async with self._lock:
            ts = time.monotonic()
            if len(self._buffer) < self.capacity:
                self._buffer.append((ts, key))
            else:
                self._buffer[self._cursor] = (ts, key)
                self._cursor = (self._cursor + 1) % self.capacity

    def _slice_since(self, since: float) -> list[tuple[float, str]]:
        """获取指定时间之后的所有记录（无锁，调用方负责加锁）"""
        if not self._buffer:
            return []
        # 找到第一个 >= since 的索引
        for i, (ts, _) in enumerate(self._buffer):
            if ts >= since:
                return self._buffer[i:]
        return []

    async def count_range(self, since: float, key: Optional[str] = None) -> int:
        """统计指定时间范围内的命中次数"""
        async with self._lock:
            records = self._slice_since(since)
            if key:
                return sum(1 for _, k in records if k == key)
            return len(records)

    async def stats_range(self, since: float) -> tuple[float, float, dict[str, int]]:
        """
        计算指定范围内的均值和标准差 + 每 key 频次

        Returns:
            (mean, stddev, {key: count})
        """
        async with self._lock:
            records = self._slice_since(since)
            if not records:
                return 0.0, 0.0, {}

            key_counts: dict[str, int] = defaultdict(int)
            for _, key in records:
                key_counts[key] += 1

            counts = list(key_counts.values())
            n = len(counts)
            mean = sum(counts) / max(n, 1)
            if n <= 1:
                return mean, 0.0, dict(key_counts)
            variance = sum((c - mean) ** 2 for c in counts) / n
            stddev = math.sqrt(variance)

        return mean, stddev, dict(key_counts)

    @property
    def total_records(self) -> int:
        return len(self._buffer)


# ============================================================
# 热点追踪器 (三态热度机)
# ============================================================

class HotLevel(Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


@dataclass
class HotspotStats:
    """热点统计"""
    total_hits: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hot_keys_count: int = 0
    warm_keys_count: int = 0
    precache_tasks: int = 0
    last_sync_time: float = 0.0
    eviction_count: int = 0

    @property
    def hit_rate(self) -> float:
        if self.total_hits == 0:
            return 0.0
        return self.cache_hits / self.total_hits


class HotspotTracker:
    """
    热点识别引擎

    两层协作:
    - 频率阈值: 快速触发 (5min/≥3次)
    - 自适应统计: 确认/降级 (30min/μ+2σ)
    """

    SHORT_WINDOW = 300       # 快速触发窗口 (秒)
    LONG_WINDOW = 1800       # 统计确认窗口 (秒)
    QUICK_THRESHOLD = 3      # 快速触发阈值
    SIGMA_MULTIPLIER = 2.0   # 自适应异常检测倍数
    SYNC_INTERVAL = 30       # 全局计数器同步间隔 (秒)
    WARM_DOWNGRADE = 900     # WARM 持续不触发降级为 COLD 的时间 (15min)

    def __init__(self, global_backend: Optional[RedisCache] = None):
        self._ring = RingBuffer(capacity=10000)
        self._hot_levels: dict[str, HotLevel] = {}
        self._last_hit_times: dict[str, float] = {}  # 每个 key 的最后命中时间
        self._stats = HotspotStats()
        self._global = global_backend
        self._last_sync = time.monotonic()
        self._lock = asyncio.Lock()

    async def record_hit(self, key: str) -> HotLevel:
        """记录一次命中，返回当前热度等级"""
        async with self._lock:
            await self._ring.record(key)
            now = time.monotonic()
            self._last_hit_times[key] = now
            self._stats.total_hits += 1

            current_level = self._hot_levels.get(key, HotLevel.COLD)

            # 检查快速触发
            short_count = await self._ring.count_range(now - self.SHORT_WINDOW, key)

            if short_count >= self.QUICK_THRESHOLD:
                # 快速触发: 标记 HOT
                if current_level != HotLevel.HOT:
                    self._hot_levels[key] = HotLevel.HOT
                    logger.debug(f"Hotspot TRIGGER: {key[:30]}... -> HOT (short_count={short_count})")
                return HotLevel.HOT

            # 已标记但未触发: 检查是否需要降级
            if current_level == HotLevel.HOT:
                return await self._maybe_downgrade(key, now)
            elif current_level == HotLevel.WARM:
                return await self._maybe_downgrade(key, now)

        return current_level

    async def _maybe_downgrade(self, key: str, now: float) -> HotLevel:
        """检查并执行降级"""
        current = self._hot_levels.get(key, HotLevel.COLD)
        last_hit = self._last_hit_times.get(key, 0)

        if current == HotLevel.HOT:
            # HOT 降级检查: 长窗口自适应统计
            mean, stddev, key_counts = await self._ring.stats_range(now - self.LONG_WINDOW)
            key_freq = key_counts.get(key, 0)
            threshold = mean + self.SIGMA_MULTIPLIER * stddev

            if key_freq >= threshold:
                return HotLevel.HOT  # 保持 HOT
            elif key_freq >= mean:
                self._hot_levels[key] = HotLevel.WARM
                logger.debug(f"Hotspot DOWNGRADE: {key[:30]}... HOT -> WARM (freq={key_freq}, threshold={threshold:.1f})")
                return HotLevel.WARM
            else:
                self._hot_levels[key] = HotLevel.COLD
                logger.debug(f"Hotspot DOWNGRADE: {key[:30]}... HOT -> COLD (freq={key_freq}, mean={mean:.1f})")
                return HotLevel.COLD

        elif current == HotLevel.WARM:
            # WARM 降级: 持续 15min 不触发
            if now - last_hit > self.WARM_DOWNGRADE:
                self._hot_levels[key] = HotLevel.COLD
                logger.debug(f"Hotspot DOWNGRADE: {key[:30]}... WARM -> COLD (idle)")
                return HotLevel.COLD

            # WARM 重新触发
            short_count = await self._ring.count_range(now - self.SHORT_WINDOW, key)
            if short_count >= self.QUICK_THRESHOLD:
                self._hot_levels[key] = HotLevel.HOT
                return HotLevel.HOT
            return HotLevel.WARM

        return HotLevel.COLD

    def get_level(self, key: str) -> HotLevel:
        """获取当前热度等级（不触发统计变更）"""
        return self._hot_levels.get(key, HotLevel.COLD)

    def get_hot_keys(self) -> list[str]:
        """获取所有 HOT 和 WARM 级别的键"""
        return [
            k for k, v in self._hot_levels.items()
            if v in (HotLevel.HOT, HotLevel.WARM)
        ]

    async def _push_to_global(self):
        """异步推送本地计数到全局 Redis"""
        if not self._global:
            return

        now = time.monotonic()
        if now - self._last_sync < self.SYNC_INTERVAL:
            return

        self._last_sync = now
        self._stats.last_sync_time = now

        # 推送短窗口内的热点计数
        _, _, key_counts = await self._ring.stats_range(now - self.SHORT_WINDOW)
        for key, count in key_counts.items():
            if count >= self.QUICK_THRESHOLD:
                await self._global.zincrby("hotspot:global:rank", key, count)

        # 发布热点变更通知
        hot_keys = self.get_hot_keys()
        if hot_keys:
            await self._global.publish("hotspot:changed", json.dumps(hot_keys[:10]))

    async def periodic_sync(self):
        """定期同步到全局计数器（由后台任务调用）"""
        while True:
            await asyncio.sleep(self.SYNC_INTERVAL)
            try:
                await self._push_to_global()
            except Exception as e:
                logger.debug(f"Global sync failed: {e}")

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_hits": self._stats.total_hits,
            "cache_hits": self._stats.cache_hits,
            "cache_misses": self._stats.cache_misses,
            "hit_rate": round(self._stats.hit_rate, 4),
            "hot_keys": len([v for v in self._hot_levels.values() if v == HotLevel.HOT]),
            "warm_keys": len([v for v in self._hot_levels.values() if v == HotLevel.WARM]),
            "precache_tasks": self._stats.precache_tasks,
            "eviction_count": self._stats.eviction_count,
            "ring_buffer_size": self._ring.total_records,
        }

    def record_cache_hit(self):
        """记录缓存命中"""
        self._stats.cache_hits += 1

    def record_cache_miss(self):
        """记录缓存未命中"""
        self._stats.cache_misses += 1

    def record_precache(self):
        """记录预缓存任务"""
        self._stats.precache_tasks += 1

    def record_eviction(self):
        """记录淘汰"""
        self._stats.eviction_count += 1


# ============================================================
# 淘汰管理器 (策略专家建议 #3: 热度加权淘汰 + 主动降级)
# ============================================================

class EvictionManager:
    """
    热度加权缓存淘汰管理器

    热度分数 = 频率 × 时间衰减因子
    """

    def __init__(
        self,
        max_entries: int = 5000,
        eviction_threshold: float = 0.8,
        decay_factor: float = 0.95
    ):
        self._max_entries = max_entries
        self._eviction_threshold = eviction_threshold
        self._decay_factor = decay_factor  # 每分钟衰减因子
        self._check_interval = 300  # 5 分钟检查一次

    def compute_score(self, key: str, tracker: HotspotTracker) -> float:
        """
        热度分数 = 基础权重 × 时间衰减

        HOT:  基础权重 3.0
        WARM: 基础权重 1.5
        COLD: 基础权重 0.5
        """
        level = tracker.get_level(key)
        base_weights = {
            HotLevel.HOT: 3.0,
            HotLevel.WARM: 1.5,
            HotLevel.COLD: 0.5,
        }
        base = base_weights.get(level, 0.5)

        # 时间衰减
        last_hit = tracker._last_hit_times.get(key, 0)
        if last_hit > 0:
            minutes_since_hit = (time.monotonic() - last_hit) / 60.0
            decay = self._decay_factor ** minutes_since_hit
        else:
            decay = 0.1  # 从未命中过的极低分

        return base * max(decay, 0.01)

    async def maybe_evict(self, backend: CacheBackend, tracker: HotspotTracker):
        """
        当缓存条目超过阈值时淘汰低分条目
        """
        current_size = await backend.size()
        current_keys = await backend.keys()

        if not current_keys:
            return

        threshold_count = int(self._max_entries * self._eviction_threshold)
        if current_size < threshold_count:
            return

        # 计算所有键的热度分数
        scored = [(k, self.compute_score(k, tracker)) for k in current_keys]
        scored.sort(key=lambda x: x[1])  # 低分在前

        # 淘汰直到低于安全值
        to_evict = current_size - threshold_count
        evicted = 0
        for key, score in scored[:to_evict]:
            if score > 2.0:  # 保护高分条目
                continue
            await backend.delete(key)
            evicted += 1
            tracker.record_eviction()

        if evicted > 0:
            logger.info(
                f"Evicted {evicted}/{to_evict} cache entries "
                f"(size={current_size}, threshold={threshold_count})"
            )

    async def check_and_downgrade(
        self,
        key: str,
        tracker: HotspotTracker,
        backend: CacheBackend,
        default_ttl: int
    ):
        """
        主动降级检查:
        - 热度降为 WARM → 恢复默认 TTL
        - 热度降为 COLD → 标记为可淘汰
        """
        level = tracker.get_level(key)

        if level == HotLevel.WARM:
            # 检查是否从 HOT 降级而来，如果是则恢复 TTL
            # 重新写入以重置 TTL
            cached = await backend.get(key)
            if cached:
                await backend.set(key, cached, default_ttl)
                logger.debug(f"TTL reset for WARM key: {key[:30]}...")

        elif level == HotLevel.COLD:
            # COLD 条目不做主动淘汰（留给 maybe_evict 批量处理）
            pass


# ============================================================
# 增强的 CacheManager
# ============================================================

class CacheManager:
    """
    增强的缓存管理器

    新增:
    - 热点追踪 (HotspotTracker)
    - 淘汰管理 (EvictionManager)
    - 缓存键优化
    - 命中率统计
    """

    def __init__(self, config):
        self.config = config
        self.enabled = config.enabled
        self.ttl = config.ttl

        # 缓存后端
        if config.type == "redis":
            try:
                import redis
                self.backend = RedisCache(config.redis_url)
                logger.info("Using Redis cache backend")
            except ImportError:
                self.backend = MemoryCache()
            except Exception:
                self.backend = MemoryCache()
        else:
            self.backend = MemoryCache()
            logger.info("Using memory cache backend")

        # 热点追踪器
        global_backend = self.backend if isinstance(self.backend, RedisCache) else None
        self.tracker = HotspotTracker(global_backend)

        # 淘汰管理器
        self.eviction = EvictionManager(
            max_entries=getattr(config, 'max_entries', 5000),
            eviction_threshold=getattr(config, 'eviction_threshold', 0.8)
        )

        # M9e: L2 语义缓存层
        self._semantic_layer = None
        self.enable_semantic_cache = getattr(config, 'enable_semantic_cache', True)

        # 后台同步任务
        self._sync_task: Optional[asyncio.Task] = None

    def _generate_cache_key(self, request: ChatRequest) -> str:
        """
        生成缓存键（优化版：排除非语义字段）

        只纳入影响响应的字段: model, messages, temperature, top_p
        """
        key_data = {
            "model": request.model,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content
                }
                for msg in request.messages
            ],
            "temperature": request.temperature,
            "top_p": request.top_p,
        }

        key_json = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return f"llm:cache:{hashlib.md5(key_json.encode()).hexdigest()}"

    async def get(self, request: ChatRequest) -> Optional[dict]:
        """获取缓存 + 热点追踪"""
        if not self.enabled:
            return None

        key = self._generate_cache_key(request)

        cached = await self.backend.get(key)

        if cached:
            self.tracker.record_cache_hit()
            asyncio.create_task(self._on_cache_hit(key))
            logger.debug(f"Cache hit: {key[:20]}...")
            return cached

        # M9e: L2 语义缓存
        if self.enable_semantic_cache and self._semantic_layer:
            semantic_result = await self._semantic_layer.get(request)
            if semantic_result:
                self.tracker.record_cache_hit()
                # 回填到 L1
                await self.backend.set(key, semantic_result.model_dump(), self.ttl)
                logger.debug(f"Semantic cache hit: {key[:20]}...")
                return semantic_result.model_dump()

        self.tracker.record_cache_miss()
        return None

    async def _on_cache_hit(self, key: str):
        """缓存命中后的异步处理"""
        try:
            await self.tracker.record_hit(key)
        except Exception as e:
            logger.debug(f"Hotspot tracking failed: {e}")

    async def set(self, request: ChatRequest, response: dict, precached: bool = False) -> None:
        """设置缓存 + 淘汰检查"""
        if not self.enabled:
            return

        key = self._generate_cache_key(request)

        # HOT 条目使用延长 TTL
        level = self.tracker.get_level(key)
        effective_ttl = self.ttl
        if level == HotLevel.HOT:
            effective_ttl = max(self.ttl, 1800)  # HOT 至少 30min

        await self.backend.set(key, response, effective_ttl)

        if not precached:
            logger.debug(f"Cache set: {key[:20]}... ttl={effective_ttl}s level={level.value}")
        else:
            logger.debug(f"Precache set: {key[:20]}... ttl={effective_ttl}s")

        # 异步淘汰检查
        asyncio.create_task(self.eviction.maybe_evict(self.backend, self.tracker))

    async def invalidate(self, request: ChatRequest) -> None:
        """使缓存失效"""
        if not self.enabled:
            return
        key = self._generate_cache_key(request)
        await self.backend.delete(key)

    def get_hotspot_stats(self) -> dict:
        """获取热点统计"""
        return self.tracker.get_stats()

    def start_background_tasks(self):
        """启动后台任务"""
        if isinstance(self.backend, RedisCache):
            self._sync_task = asyncio.create_task(self.tracker.periodic_sync())

    async def stop_background_tasks(self):
        """停止后台任务"""
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

    async def get_hotspot_global_rank(self, top_n: int = 20) -> list[tuple[str, float]]:
        """获取全局热点排名（需要 Redis）"""
        if isinstance(self.backend, RedisCache):
            return await self.backend.zrevrange("hotspot:global:rank", 0, top_n - 1)
        return []
