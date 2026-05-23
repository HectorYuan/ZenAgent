"""
语义缓存层 (L2)

设计依据: E2E_OPTIMIZATION_DESIGN §模块3 (M9e)

架构:
  CacheManager.get():
    1. L1 精确匹配 (RingBuffer, <0.1ms) — M8 P1
    2. L2 语义匹配 (VectorIndex, <5ms)   — M9e NEW
    3. LLM 调用 (200ms+)
"""

import asyncio
import logging
from typing import Optional, Callable, Any

from .core import ChatRequest, LLMResponse
from .vector_index import create_vector_index, BuiltinIndex

logger = logging.getLogger(__name__)


class SemanticCacheLayer:
    """
    L2 语义缓存层

    工作流程:
    - get(): embed(request) → vector search → cosine_sim > threshold → 命中
    - set(): embed(request) → add to index
    - 相似度阈值: 0.92 (cosine)
    """

    SIMILARITY_THRESHOLD = 0.92  # 余弦相似度阈值
    MAX_CACHE_SIZE = 10000

    def __init__(
        self,
        embed_fn: Optional[Callable] = None,
        dim: int = 1536,
    ):
        self._index = create_vector_index(dim=dim, prefer_hnsw=True)
        self._embed_fn = embed_fn
        self._dim = dim
        self._cache: dict[str, dict] = {}  # key → response data
        self._hits = 0
        self._misses = 0

    @property
    def stats(self) -> dict:
        return {
            "index_size": self._index.size,
            "cache_size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / max(self._hits + self._misses, 1),
            "threshold": self.SIMILARITY_THRESHOLD,
            "backend": type(self._index).__name__,
        }

    async def get(self, request: ChatRequest) -> Optional[LLMResponse]:
        """语义缓存查询"""
        if not self._embed_fn:
            return None

        try:
            vector = await self._embed_fn(self._request_to_text(request))
            if not vector:
                return None
        except Exception:
            return None

        results = self._index.search(vector, k=3)
        for key, sim in results:
            if sim >= self.SIMILARITY_THRESHOLD and key in self._cache:
                self._hits += 1
                data = self._cache[key]
                return LLMResponse(**data)

        self._misses += 1
        return None

    async def set(self, request: ChatRequest, response: LLMResponse):
        """写入语义缓存"""
        if not self._embed_fn:
            return

        try:
            vector = await self._embed_fn(self._request_to_text(request))
            if not vector:
                return
        except Exception:
            return

        cache_key = f"sem:{hash(self._request_to_text(request))}"
        self._index.add(cache_key, vector)
        self._cache[cache_key] = response.model_dump()

        if len(self._cache) > self.MAX_CACHE_SIZE:
            # 简单清理: 删掉最早的一半
            keys = list(self._cache.keys())[:self.MAX_CACHE_SIZE // 2]
            for k in keys:
                self._cache.pop(k, None)

    @staticmethod
    def _request_to_text(request: ChatRequest) -> str:
        """提取请求的文本表示 (用于 embedding)"""
        parts = []
        for msg in request.messages:
            content = getattr(msg, 'content', str(msg))
            parts.append(content)
        return " ".join(parts[-3:])  # 只用最后 3 条消息


# 简单的文本 embedding (降级方案: hash-based, 非真实向量)
async def simple_embed_fn(text: str, dim: int = 1536) -> list[float]:
    """
    简单文本 embedding (降级方案)

    使用字符 n-gram hash 生成伪向量。
    真实生产环境应替换为 OpenAI/本地 embedding。
    """
    import hashlib
    if not text:
        return [0.0] * dim

    result = []
    for i in range(dim):
        seed = f"{text}:{i}"
        h = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
        result.append((h / 0xFFFFFFFF) * 2 - 1)  # normalize to [-1, 1]
    return result
