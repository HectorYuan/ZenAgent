"""
记忆索引

向量索引和语义检索的实现
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import threading
import math
import hashlib


@dataclass
class SemanticSearchResult:
    """语义搜索结果"""
    memory_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    vector_distance: Optional[float] = None


@dataclass
class IndexEntry:
    """索引条目"""
    memory_id: str
    content: str
    keywords: List[str] = field(default_factory=list)
    vector: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


class InvertedIndex:
    """
    倒排索引
    
    基于关键词的快速查找
    """
    
    def __init__(self):
        """初始化倒排索引"""
        self._index: Dict[str, List[str]] = {}  # 关键词 -> 记忆 ID 列表
        self._memory_keywords: Dict[str, List[str]] = {}  # 记忆 ID -> 关键词列表
        self._lock = threading.RLock()
    
    def add(self, memory_id: str, content: str, keywords: Optional[List[str]] = None) -> None:
        """
        添加到索引
        
        Args:
            memory_id: 记忆 ID
            content: 内容
            keywords: 关键词列表
        """
        with self._lock:
            # 提取关键词
            if keywords is None:
                keywords = self._extract_keywords(content)
            
            # 更新倒排索引
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower not in self._index:
                    self._index[keyword_lower] = []
                if memory_id not in self._index[keyword_lower]:
                    self._index[keyword_lower].append(memory_id)
            
            # 记录记忆的关键词
            self._memory_keywords[memory_id] = keywords
    
    def remove(self, memory_id: str) -> None:
        """
        从索引移除
        
        Args:
            memory_id: 记忆 ID
        """
        with self._lock:
            if memory_id in self._memory_keywords:
                keywords = self._memory_keywords[memory_id]
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if keyword_lower in self._index:
                        if memory_id in self._index[keyword_lower]:
                            self._index[keyword_lower].remove(memory_id)
                        if not self._index[keyword_lower]:
                            del self._index[keyword_lower]
                del self._memory_keywords[memory_id]
    
    def search(self, query: str, limit: int = 10) -> List[str]:
        """
        搜索
        
        Args:
            query: 查询字符串
            limit: 结果数量限制
            
        Returns:
            List[str]: 记忆 ID 列表
        """
        with self._lock:
            query_keywords = self._extract_keywords(query)
            
            if not query_keywords:
                return []
            
            # 统计每个记忆的匹配次数
            memory_scores: Dict[str, int] = {}
            for keyword in query_keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in self._index:
                    for memory_id in self._index[keyword_lower]:
                        memory_scores[memory_id] = memory_scores.get(memory_id, 0) + 1
            
            # 排序
            sorted_memories = sorted(
                memory_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            return [mid for mid, _ in sorted_memories[:limit]]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的分词
        words = text.lower().split()
        
        # 过滤停用词
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "is", "was",
            "are", "were", "be", "been", "being", "have", "has",
            "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can",
            "i", "you", "he", "she", "it", "we", "they", "this",
            "that", "these", "those", "what", "which", "who",
            "when", "where", "why", "how", "not", "no", "yes"
        }
        
        return [w for w in words if len(w) > 2 and w not in stop_words]


class VectorIndex:
    """
    向量索引
    
    基于向量相似度的快速查找
    """
    
    def __init__(self, dimension: int = 128):
        """
        初始化向量索引
        
        Args:
            dimension: 向量维度
        """
        self.dimension = dimension
        self._vectors: Dict[str, List[float]] = {}
        self._lock = threading.RLock()
    
    def add(self, memory_id: str, vector: List[float]) -> None:
        """
        添加向量
        
        Args:
            memory_id: 记忆 ID
            vector: 向量
        """
        with self._lock:
            if len(vector) != self.dimension:
                raise ValueError(f"Vector dimension must be {self.dimension}")
            self._vectors[memory_id] = vector.copy()
    
    def remove(self, memory_id: str) -> None:
        """
        移除向量
        
        Args:
            memory_id: 记忆 ID
        """
        with self._lock:
            if memory_id in self._vectors:
                del self._vectors[memory_id]
    
    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        exclude_ids: Optional[List[str]] = None,
    ) -> List[Tuple[str, float]]:
        """
        搜索最相似的向量
        
        Args:
            query_vector: 查询向量
            limit: 结果数量限制
            exclude_ids: 排除的记忆 ID
            
        Returns:
            List[Tuple[str, float]]: (记忆ID, 距离) 列表
        """
        with self._lock:
            if len(query_vector) != self.dimension:
                raise ValueError(f"Query vector dimension must be {self.dimension}")
            
            exclude_ids = set(exclude_ids or [])
            
            distances = []
            for memory_id, vector in self._vectors.items():
                if memory_id in exclude_ids:
                    continue
                
                distance = self._cosine_distance(query_vector, vector)
                distances.append((memory_id, distance))
            
            # 按距离排序（越小越相似）
            distances.sort(key=lambda x: x[1])
            
            return distances[:limit]
    
    def _cosine_distance(self, v1: List[float], v2: List[float]) -> float:
        """计算余弦距离"""
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(a * a for a in v2))
        
        if norm1 == 0 or norm2 == 0:
            return 1.0
        
        similarity = dot_product / (norm1 * norm2)
        return 1.0 - similarity  # 转换为距离
    
    def generate_vector(self, content: str) -> List[float]:
        """
        生成内容的向量表示
        
        Args:
            content: 内容
            
        Returns:
            List[float]: 向量
        """
        # 简单的基于哈希的向量生成
        # 实际应用中应该使用预训练模型如 BERT、Sentence-BERT 等
        hash_bytes = hashlib.md5(content.encode()).digest()
        
        vector = []
        for i in range(self.dimension):
            byte_index = i % len(hash_bytes)
            value = (hash_bytes[byte_index] / 255.0) * 2 - 1  # 归一化到 [-1, 1]
            vector.append(value)
        
        # L2 归一化
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector


class MemoryIndex:
    """
    记忆索引管理器
    
    统一的索引接口，结合倒排索引和向量索引
    """
    
    def __init__(self, vector_dim: int = 128):
        """
        初始化记忆索引
        
        Args:
            vector_dim: 向量维度
        """
        self.vector_dim = vector_dim
        self._inverted_index = InvertedIndex()
        self._vector_index = VectorIndex(dimension=vector_dim)
        self._memory_content: Dict[str, str] = {}  # memory_id -> content
        self._memory_metadata: Dict[str, Dict[str, Any]] = {}  # memory_id -> metadata
        self._lock = threading.RLock()
    
    def index(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        索引记忆
        
        Args:
            memory_id: 记忆 ID
            content: 内容
            metadata: 元数据
        """
        with self._lock:
            # 存储内容和元数据
            self._memory_content[memory_id] = content
            self._memory_metadata[memory_id] = metadata or {}
            
            # 添加到倒排索引
            keywords = metadata.get("keywords", []) if metadata else []
            self._inverted_index.add(memory_id, content, keywords)
            
            # 生成并添加向量
            vector = self._vector_index.generate_vector(content)
            self._vector_index.add(memory_id, vector)
    
    def remove(self, memory_id: str) -> None:
        """
        移除索引
        
        Args:
            memory_id: 记忆 ID
        """
        with self._lock:
            if memory_id in self._memory_content:
                del self._memory_content[memory_id]
            
            if memory_id in self._memory_metadata:
                del self._memory_metadata[memory_id]
            
            self._inverted_index.remove(memory_id)
            self._vector_index.remove(memory_id)
    
    def search_by_keywords(
        self,
        query: str,
        limit: int = 10,
    ) -> List[str]:
        """
        按关键词搜索
        
        Args:
            query: 查询字符串
            limit: 结果数量限制
            
        Returns:
            List[str]: 记忆 ID 列表
        """
        return self._inverted_index.search(query, limit)
    
    def search_by_semantic(
        self,
        query: str,
        limit: int = 10,
        exclude_ids: Optional[List[str]] = None,
    ) -> List[SemanticSearchResult]:
        """
        按语义搜索
        
        Args:
            query: 查询字符串
            limit: 结果数量限制
            exclude_ids: 排除的记忆 ID
            
        Returns:
            List[SemanticSearchResult]: 搜索结果
        """
        with self._lock:
            query_vector = self._vector_index.generate_vector(query)
            distances = self._vector_index.search(
                query_vector,
                limit=limit,
                exclude_ids=exclude_ids,
            )
            
            results = []
            for memory_id, distance in distances:
                results.append(SemanticSearchResult(
                    memory_id=memory_id,
                    content=self._memory_content.get(memory_id, ""),
                    score=1.0 - distance,
                    metadata=self._memory_metadata.get(memory_id, {}),
                    vector_distance=distance,
                ))
            
            return results
    
    def search_hybrid(
        self,
        query: str,
        keyword_weight: float = 0.3,
        semantic_weight: float = 0.7,
        limit: int = 10,
    ) -> List[SemanticSearchResult]:
        """
        混合搜索
        
        结合关键词搜索和语义搜索的结果
        
        Args:
            query: 查询字符串
            keyword_weight: 关键词权重
            semantic_weight: 语义权重
            limit: 结果数量限制
            
        Returns:
            List[SemanticSearchResult]: 搜索结果
        """
        with self._lock:
            # 关键词搜索
            keyword_ids = set(self._inverted_index.search(query, limit * 2))
            
            # 语义搜索
            semantic_results = self.search_by_semantic(
                query,
                limit=limit * 2,
            )
            
            # 计算综合分数
            hybrid_scores: Dict[str, float] = {}
            
            # 关键词分数
            for memory_id in keyword_ids:
                hybrid_scores[memory_id] = hybrid_scores.get(memory_id, 0) + keyword_weight
            
            # 语义分数
            for result in semantic_results:
                score = result.score * semantic_weight
                hybrid_scores[result.memory_id] = hybrid_scores.get(
                    result.memory_id, 0
                ) + score
            
            # 排序
            sorted_ids = sorted(
                hybrid_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            # 构建结果
            results = []
            for memory_id, score in sorted_ids[:limit]:
                results.append(SemanticSearchResult(
                    memory_id=memory_id,
                    content=self._memory_content.get(memory_id, ""),
                    score=score,
                    metadata=self._memory_metadata.get(memory_id, {}),
                ))
            
            return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_indexed": len(self._memory_content),
            "vector_dimension": self.vector_dim,
            "inverted_index_size": len(self._inverted_index._index),
        }
    
    def clear(self) -> None:
        """清空索引"""
        with self._lock:
            self._memory_content.clear()
            self._memory_metadata.clear()
            self._inverted_index = InvertedIndex()
            self._vector_index = VectorIndex(dimension=self.vector_dim)
