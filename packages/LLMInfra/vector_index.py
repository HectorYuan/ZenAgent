"""
向量索引

设计依据: M9e — HNSW 向量索引 (模块3)

支持后端:
- BuiltinIndex: 纯 Python 余弦相似度 (零依赖, 自动降级)
- HNSWIndex: hnswlib 高性能索引 (pip install hnswlib)
"""

import math
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class BuiltinIndex:
    """
    纯 Python 余弦相似度索引

    适用于 < 10000 条缓存的小规模场景。
    无外部依赖，自动降级。
    """

    def __init__(self, dim: int = 1536):
        self._dim = dim
        self._vectors: dict[str, list[float]] = {}
        self._keys_order: list[str] = []

    @property
    def size(self) -> int:
        return len(self._vectors)

    def add(self, key: str, vector: list[float]):
        if len(self._vectors) >= 10000:
            # FIFO 淘汰
            oldest = self._keys_order.pop(0)
            self._vectors.pop(oldest, None)
        self._vectors[key] = vector
        if key not in self._keys_order:
            self._keys_order.append(key)

    @staticmethod
    def cosine_sim(a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, vector: list[float], k: int = 5) -> list[tuple[str, float]]:
        """返回 top-k (key, cosine_sim)"""
        if not self._vectors:
            return []
        scored = [
            (key, self.cosine_sim(vector, vec))
            for key, vec in self._vectors.items()
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]


# 可选 HNSW 高性能索引
try:
    import hnswlib as _hnsw

    class HNSWIndex:
        """hnswlib 高性能向量索引"""

        def __init__(self, dim: int = 1536, space: str = "cosine", max_elements: int = 10000):
            self._dim = dim
            self._index = _hnsw.Index(space=space, dim=dim)
            self._index.init_index(max_elements=max_elements, M=16, ef_construction=200)
            self._id_map: dict[int, str] = {}
            self._next_id = 0
            self._size = 0

        @property
        def size(self) -> int:
            return self._size

        def add(self, key: str, vector: list[float]):
            self._index.add_items([vector], [self._next_id])
            self._id_map[self._next_id] = key
            self._next_id += 1
            self._size += 1

        def search(self, vector: list[float], k: int = 5) -> list[tuple[str, float]]:
            labels, distances = self._index.knn_query([vector], k=k)
            results = []
            for label, dist in zip(labels[0], distances[0]):
                if label >= 0 and label in self._id_map:
                    sim = 1.0 - dist if dist <= 2.0 else 0.0
                    results.append((self._id_map[label], sim))
            return results

except ImportError:
    HNSWIndex = None
    logger.info("hnswlib not installed, using builtin cosine index")


def create_vector_index(dim: int = 1536, prefer_hnsw: bool = True):
    """工厂方法: 优先 HNSW，降级 Builtin"""
    if prefer_hnsw and HNSWIndex:
        return HNSWIndex(dim=dim)
    return BuiltinIndex(dim=dim)
