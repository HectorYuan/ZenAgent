"""
MetaSoul 核心类

灵魂记忆、经验积累和人格演化的核心实现
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum
import threading
import uuid
import hashlib
import logging

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """记忆类型"""
    WORKING = "working"           # 工作记忆 - 当前正在处理的信息
    EPISODIC = "episodic"         # 情景记忆 - 具体的事件和经历
    SEMANTIC = "semantic"         # 语义记忆 - 概念和知识
    PROCEDURAL = "procedural"     # 程序记忆 - 技能和习惯


class MemoryImportance(Enum):
    """记忆重要性等级"""
    CRITICAL = 5    # 关键记忆 - 不可遗忘
    HIGH = 4        # 重要记忆 - 长期保留
    NORMAL = 3      # 普通记忆 - 标准处理
    LOW = 2         # 次要记忆 - 可被遗忘
    MINIMAL = 1     # 边缘记忆 - 快速遗忘


@dataclass
class MemoryEntry:
    """
    记忆条目
    
    Attributes:
        memory_id: 记忆唯一标识
        content: 记忆内容
        memory_type: 记忆类型
        importance: 重要性等级
        created_at: 创建时间
        access_count: 访问次数
        last_accessed: 最后访问时间
        emotional_valence: 情感效价 (-1 to 1)
        associations: 关联记忆 ID 列表
        metadata: 元数据
    """
    memory_id: str
    content: str
    memory_type: MemoryType
    importance: MemoryImportance = MemoryImportance.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    emotional_valence: float = 0.0
    associations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    
    def access(self) -> None:
        """更新访问信息"""
        self.access_count += 1
        self.last_accessed = datetime.now()
    
    def add_association(self, memory_id: str) -> None:
        """添加关联"""
        if memory_id not in self.associations:
            self.associations.append(memory_id)
    
    def get_decay_score(self) -> float:
        """
        计算衰减分数
        
        基于时间、访问频率和重要性计算记忆的自然衰减程度
        
        Returns:
            float: 衰减分数 (0-1, 越高越容易被遗忘)
        """
        # 时间衰减
        time_delta = (datetime.now() - self.created_at).total_seconds()
        time_decay = min(time_delta / (7 * 24 * 3600), 1.0)  # 最多7天完全衰减
        
        # 访问频率保护
        access_protection = min(self.access_count / 10, 1.0)
        
        # 重要性保护
        importance_protection = self.importance.value / 5.0
        
        # 综合衰减分数
        decay = (time_decay * 0.5) - (access_protection * 0.3) - (importance_protection * 0.2)
        return max(0.0, min(decay, 1.0))


@dataclass
class SoulExperience:
    """
    灵魂经验
    
    记录一次完整的经验，包括感知、思考、行动和结果
    """
    experience_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 经验内容
    context: str = ""
    action: str = ""
    result: str = ""
    reflection: str = ""
    
    # 经验评估
    outcome: float = 0.0  # 结果评分 (-1 to 1)
    learning: List[str] = field(default_factory=list)  # 学到的知识点
    
    # 关联
    related_memories: List[str] = field(default_factory=list)
    emotional_impact: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "experience_id": self.experience_id,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "action": self.action,
            "result": self.result,
            "reflection": self.reflection,
            "outcome": self.outcome,
            "learning": self.learning,
            "related_memories": self.related_memories,
            "emotional_impact": self.emotional_impact,
        }


@dataclass 
class SoulMemory:
    """
    灵魂记忆容器
    
    存储和管理灵魂的所有记忆
    """
    soul_id: str
    memories: Dict[str, MemoryEntry] = field(default_factory=dict)
    experiences: Dict[str, SoulExperience] = field(default_factory=dict)
    personality_evolution: List[Dict[str, Any]] = field(default_factory=list)
    
    # 统计
    total_memories: int = 0
    total_experiences: int = 0
    
    def add_memory(self, memory: MemoryEntry) -> None:
        """添加记忆"""
        self.memories[memory.memory_id] = memory
        self.total_memories += 1
    
    def add_experience(self, experience: SoulExperience) -> None:
        """添加经验"""
        self.experiences[experience.experience_id] = experience
        self.total_experiences += 1
    
    def get_memories_by_type(self, memory_type: MemoryType) -> List[MemoryEntry]:
        """按类型获取记忆"""
        return [
            m for m in self.memories.values()
            if m.memory_type == memory_type
        ]
    
    def get_recent_memories(self, limit: int = 10) -> List[MemoryEntry]:
        """获取最近的记忆"""
        sorted_memories = sorted(
            self.memories.values(),
            key=lambda m: m.created_at,
            reverse=True
        )
        return sorted_memories[:limit]


class MetaSoul:
    """
    MetaSoul 核心类
    
    实现灵魂记忆、经验积累和人格演化的核心功能
    """
    
    def __init__(
        self,
        soul_id: Optional[str] = None,
        name: str = "MetaSoul",
    ):
        """
        初始化 MetaSoul
        
        Args:
            soul_id: 灵魂 ID
            name: 灵魂名称
        """
        self.soul_id = soul_id or str(uuid.uuid4())
        self.name = name
        self.soul_memory = SoulMemory(soul_id=self.soul_id)
        self._lock = threading.RLock()
        
        # 配置
        self._max_working_memories = 100
        self._max_episodic_memories = 1000
        self._max_semantic_memories = 5000
        self._max_procedural_memories = 500

        # 回调
        self._on_memory_stored: List[callable] = []
        self._on_memory_accessed: List[callable] = []
        self._on_experience_created: List[callable] = []

        # 统一评分器（延迟导入避免循环）
        self._scorer = None

        # M8 P3: 新记忆架构 (HierarchicalStore + Retriever + Pipeline + Archiver)
        self._enable_v2_architecture: bool = True
        self._hierarchical_store = None
        self._memory_retriever = None
        self._consolidation_pipeline = None
        self._archival_manager = None
        self._init_v2_architecture()

    def _init_v2_architecture(self):
        """初始化 M8 P3 新记忆架构"""
        if not self._enable_v2_architecture:
            return
        try:
            from .hierarchical_store import HierarchicalStore, MemoryTier
            from .memory_retriever import MemoryRetriever, RetrieveIntent
            from .semantic_kb import SemanticKnowledgeBase
            from .knowledge_extractor import KnowledgeExtractor
            from .consolidation import ConsolidationPipeline
            from .archival_manager import ArchivalManager

            self._hierarchical_store = HierarchicalStore()
            self._memory_retriever = MemoryRetriever(self._hierarchical_store)
            kb = SemanticKnowledgeBase()
            extractor = KnowledgeExtractor()
            self._consolidation_pipeline = ConsolidationPipeline(
                self._hierarchical_store, kb, extractor
            )
            self._archival_manager = ArchivalManager(self._hierarchical_store)
        except Exception as e:
            logger.debug(f"V2 architecture init skipped: {e}")
            self._enable_v2_architecture = False

    @property
    def store_v2(self):
        """获取 HierarchicalStore (v2)"""
        return self._hierarchical_store

    @property
    def retriever(self):
        """获取 MemoryRetriever"""
        return self._memory_retriever

    @property
    def pipeline(self):
        """获取 ConsolidationPipeline"""
        return self._consolidation_pipeline

    @property
    def archiver(self):
        """获取 ArchivalManager"""
        return self._archival_manager

    async def remember_v2(self, content: str, metadata: dict = None):
        """V2 存储记忆: L1 → 管线下沉"""
        if not self._hierarchical_store:
            return None
        return await self._hierarchical_store.store(
            entry_id=f"mem_{id(content)}",
            content=content,
            metadata=metadata or {},
        )

    async def recall_v2(self, query: str, intent=None, top_k=10):
        """V2 检索记忆: 意图分流 + 三路加权"""
        if not self._memory_retriever:
            return []
        from .memory_retriever import RetrieveIntent
        return await self._memory_retriever.retrieve(
            query, intent=intent or RetrieveIntent.FULL_STACK, top_k=top_k
        )

    async def consolidate(self):
        """手动触发记忆整合"""
        if self._archival_manager:
            await self._archival_manager.compact()

    def store_memory(
        self,
        content: str,
        memory_type: MemoryType,
        importance: MemoryImportance = MemoryImportance.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        emotional_valence: float = 0.0,
    ) -> str:
        """
        存储记忆
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型
            importance: 重要性等级
            metadata: 元数据
            emotional_valence: 情感效价
            
        Returns:
            str: 记忆 ID
        """
        with self._lock:
            # 生成记忆 ID
            memory_id = hashlib.md5(
                f"{content}{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]
            
            # 创建记忆条目
            memory = MemoryEntry(
                memory_id=memory_id,
                content=content,
                memory_type=memory_type,
                importance=importance,
                emotional_valence=emotional_valence,
                metadata=metadata or {},
            )
            
            # 添加到记忆存储
            self.soul_memory.add_memory(memory)
            
            # 触发回调
            for callback in self._on_memory_stored:
                try:
                    callback(memory)
                except Exception:
                    pass
            
            # 检查容量限制
            self._enforce_capacity(memory_type)
            
            return memory_id
    
    def store_experience(
        self,
        context: str,
        action: str,
        result: str,
        reflection: str = "",
        outcome: float = 0.0,
        learning: Optional[List[str]] = None,
    ) -> str:
        """
        存储经验
        
        Args:
            context: 上下文
            action: 行动
            result: 结果
            reflection: 反思
            outcome: 结果评分
            learning: 学习到的知识点
            
        Returns:
            str: 经验 ID
        """
        with self._lock:
            experience = SoulExperience(
                context=context,
                action=action,
                result=result,
                reflection=reflection,
                outcome=outcome,
                learning=learning or [],
            )
            
            self.soul_memory.add_experience(experience)
            
            # 触发回调
            for callback in self._on_experience_created:
                try:
                    callback(experience)
                except Exception:
                    pass
            
            return experience.experience_id
    
    def retrieve(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """
        检索记忆
        
        Args:
            query: 查询内容
            memory_type: 记忆类型过滤
            limit: 返回数量限制
            
        Returns:
            List[MemoryEntry]: 记忆条目列表
        """
        with self._lock:
            # 过滤记忆
            candidates = list(self.soul_memory.memories.values())
            
            if memory_type:
                candidates = [
                    m for m in candidates
                    if m.memory_type == memory_type
                ]
            
            # 简单的关键词匹配（实际应用中应该用向量相似度）
            query_words = set(query.lower().split())
            scored_memories = []
            
            for memory in candidates:
                memory_words = set(memory.content.lower().split())
                overlap = len(query_words & memory_words)
                
                if overlap > 0:
                    # 结合访问频率和重要性评分
                    score = (
                        overlap * 0.3 +
                        min(memory.access_count / 10, 1.0) * 0.2 +
                        memory.importance.value / 5.0 * 0.3 +
                        (1.0 - memory.get_decay_score()) * 0.2
                    )
                    scored_memories.append((score, memory))
            
            # 排序并返回
            scored_memories.sort(key=lambda x: x[0], reverse=True)
            results = [m for _, m in scored_memories[:limit]]
            
            # 更新访问
            for memory in results:
                memory.access()
            
            return results
    
    def associate_memories(
        self,
        memory_id1: str,
        memory_id2: str,
    ) -> bool:
        """
        关联两个记忆
        
        Args:
            memory_id1: 记忆 ID 1
            memory_id2: 记忆 ID 2
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            if memory_id1 not in self.soul_memory.memories:
                return False
            if memory_id2 not in self.soul_memory.memories:
                return False
            
            self.soul_memory.memories[memory_id1].add_association(memory_id2)
            self.soul_memory.memories[memory_id2].add_association(memory_id1)
            
            return True
    
    def get_related_memories(
        self,
        memory_id: str,
        limit: int = 5,
    ) -> List[MemoryEntry]:
        """
        获取相关记忆
        
        Args:
            memory_id: 记忆 ID
            limit: 返回数量限制
            
        Returns:
            List[MemoryEntry]: 相关记忆列表
        """
        with self._lock:
            if memory_id not in self.soul_memory.memories:
                return []
            
            memory = self.soul_memory.memories[memory_id]
            related = []
            
            for related_id in memory.associations:
                if related_id in self.soul_memory.memories:
                    related.append(self.soul_memory.memories[related_id])
            
            return related[:limit]
    
    def evolve_from_experience(
        self,
        experience: SoulExperience,
    ) -> Dict[str, Any]:
        """
        从经验中演化
        
        Args:
            experience: 经验数据
            
        Returns:
            Dict[str, Any]: 演化结果
        """
        evolution_result = {
            "experience_id": experience.experience_id,
            "timestamp": datetime.now().isoformat(),
            "personality_delta": {},
            "new_memories": [],
            "insights": [],
        }
        
        # 基于结果更新重要性
        if experience.outcome > 0.5:
            importance = MemoryImportance.HIGH
        elif experience.outcome < -0.5:
            importance = MemoryImportance.CRITICAL  # 从失败中学习
        else:
            importance = MemoryImportance.NORMAL
        
        # 创建经验记忆
        memory_content = f"经验: {experience.context} -> {experience.action} -> {experience.result}"
        memory_id = self.store_memory(
            content=memory_content,
            memory_type=MemoryType.EPISODIC,
            importance=importance,
            emotional_valence=experience.emotional_impact,
        )
        evolution_result["new_memories"].append(memory_id)
        
        # 存储反思
        if experience.reflection:
            reflection_id = self.store_memory(
                content=f"反思: {experience.reflection}",
                memory_type=MemoryType.SEMANTIC,
                importance=MemoryImportance.HIGH,
            )
            evolution_result["new_memories"].append(reflection_id)
        
        # 添加学习点
        for learning_point in experience.learning:
            learning_id = self.store_memory(
                content=f"学习: {learning_point}",
                memory_type=MemoryType.SEMANTIC,
                importance=importance,
            )
            evolution_result["new_memories"].append(learning_id)
        
        return evolution_result
    
    def _enforce_capacity(self, memory_type: MemoryType) -> None:
        """强制执行容量限制"""
        max_capacity = {
            MemoryType.WORKING: self._max_working_memories,
            MemoryType.EPISODIC: self._max_episodic_memories,
            MemoryType.SEMANTIC: self._max_semantic_memories,
            MemoryType.PROCEDURAL: self._max_procedural_memories,
        }
        
        capacity = max_capacity.get(memory_type, 1000)
        memories_of_type = self.soul_memory.get_memories_by_type(memory_type)
        
        if len(memories_of_type) > capacity:
            # 按衰减分数降序排列，高衰减（最容易遗忘）的优先淘汰
            sorted_memories = sorted(
                memories_of_type,
                key=lambda m: (m.get_decay_score(), -m.importance.value),
                reverse=True,
            )
            
            # 保留重要记忆
            to_remove = len(memories_of_type) - capacity
            removed = 0
            
            for memory in sorted_memories:
                if memory.importance == MemoryImportance.CRITICAL:
                    continue
                
                del self.soul_memory.memories[memory.memory_id]
                self.soul_memory.total_memories -= 1
                removed += 1
                
                if removed >= to_remove:
                    break
    
    @property
    def scorer(self):
        """延迟初始化评分器"""
        if self._scorer is None:
            from .memory_scorer import MemoryScorer
            self._scorer = MemoryScorer()
        return self._scorer

    def run_eviction_cycle(self, threshold: float = 0.3) -> Dict[str, Any]:
        """
        运行淘汰周期：对所有记忆评分，淘汰低分记忆。

        Args:
            threshold: 评分低于此值的记忆被淘汰 (0-1)

        Returns:
            淘汰统计
        """
        evicted_ids = []
        scores = {}

        with self._lock:
            all_memories = list(self.soul_memory.memories.values())

            for memory in all_memories:
                score = self.scorer.score(memory)
                scores[memory.memory_id] = score

                if self.scorer.should_evict(memory, threshold):
                    del self.soul_memory.memories[memory.memory_id]
                    self.soul_memory.total_memories -= 1
                    evicted_ids.append(memory.memory_id)

        logger.info(
            "淘汰周期完成: 评估 %d 条, 淘汰 %d 条, 阈值 %.2f",
            len(all_memories), len(evicted_ids), threshold,
        )

        return {
            "total_evaluated": len(all_memories),
            "evicted_count": len(evicted_ids),
            "retained_count": len(all_memories) - len(evicted_ids),
            "evicted_ids": evicted_ids,
            "scores": scores,
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        stats = {
            "soul_id": self.soul_id,
            "name": self.name,
            "total_memories": self.soul_memory.total_memories,
            "total_experiences": self.soul_memory.total_experiences,
            "memories_by_type": {},
        }
        
        for memory_type in MemoryType:
            memories = self.soul_memory.get_memories_by_type(memory_type)
            stats["memories_by_type"][memory_type.value] = len(memories)
        
        return stats
    
    def clear(self) -> None:
        """清空记忆"""
        with self._lock:
            self.soul_memory = SoulMemory(soul_id=self.soul_id)
    
    # ==================== 事件注册 ====================
    
    def on_memory_stored(self, callback: callable) -> None:
        """注册记忆存储回调"""
        self._on_memory_stored.append(callback)
    
    def on_memory_accessed(self, callback: callable) -> None:
        """注册记忆访问回调"""
        self._on_memory_accessed.append(callback)
    
    def on_experience_created(self, callback: callable) -> None:
        """注册经验创建回调"""
        self._on_experience_created.append(callback)
