"""
记忆层次结构

工作记忆、情景记忆、语义记忆、程序记忆的实现
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import threading
import time


class MemoryTier(Enum):
    """记忆层级"""
    WORKING = "working"       # 工作记忆 - 即时信息
    EPISODIC = "episodic"     # 情景记忆 - 事件序列
    SEMANTIC = "semantic"     # 语义记忆 - 概念知识
    PROCEDURAL = "procedural" # 程序记忆 - 技能习惯


@dataclass
class WorkingMemoryEntry:
    """工作记忆条目"""
    entry_id: str
    content: Any
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    attention_weight: float = 1.0
    expires_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def access(self) -> None:
        """更新访问时间"""
        self.last_accessed = datetime.now()


@dataclass
class EpisodicMemoryEntry:
    """情景记忆条目"""
    episode_id: str
    title: str
    narrative: str  # 叙事性描述
    start_time: datetime
    end_time: Optional[datetime] = None
    location: str = ""
    participants: List[str] = field(default_factory=list)
    emotions: List[str] = field(default_factory=list)
    key_events: List[Dict[str, Any]] = field(default_factory=list)
    outcomes: List[str] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    importance: float = 0.5  # 0-1
    coherence: float = 0.5   # 叙事连贯性


@dataclass
class SemanticMemoryEntry:
    """语义记忆条目"""
    concept_id: str
    concept: str           # 核心概念
    definition: str        # 定义
    examples: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    relations: Dict[str, List[str]] = field(default_factory=dict)  # 关系类型 -> 关联概念
    confidence: float = 1.0
    source: str = ""
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ProceduralMemoryEntry:
    """程序记忆条目"""
    skill_id: str
    skill_name: str
    description: str
    steps: List[str] = field(default_factory=list)  # 步骤描述
    conditions: Dict[str, Any] = field(default_factory=dict)  # 适用条件
    outcomes: Dict[str, Any] = field(default_factory=dict)  # 预期结果
    proficiency: float = 0.0  # 0-1, 熟练度
    practice_count: int = 0
    last_practiced: Optional[datetime] = None
    prerequisites: List[str] = field(default_factory=list)  # 前置技能


class WorkingMemory:
    """
    工作记忆
    
    短期、高注意力权重、快速访问的记忆
    """
    
    def __init__(self, capacity: int = 7):
        """
        初始化工作记忆
        
        Args:
            capacity: 容量限制 (Miller's Law: 7±2)
        """
        self.capacity = capacity
        self._entries: Dict[str, WorkingMemoryEntry] = {}
        self._attention_focus: Optional[str] = None
        self._lock = threading.RLock()
    
    def store(self, entry_id: str, content: Any, ttl: Optional[int] = None) -> None:
        """
        存储到工作记忆
        
        Args:
            entry_id: 条目 ID
            content: 内容
            ttl: 生存时间（秒）
        """
        with self._lock:
            expires_at = None
            if ttl:
                expires_at = datetime.fromtimestamp(time.time() + ttl)
            
            entry = WorkingMemoryEntry(
                entry_id=entry_id,
                content=content,
                expires_at=expires_at,
            )
            
            self._entries[entry_id] = entry
            
            # 如果超过容量，移除最低注意权重的
            if len(self._entries) > self.capacity:
                self._evict_lowest_attention()
    
    def retrieve(self, entry_id: str) -> Optional[Any]:
        """
        从工作记忆检索
        
        Args:
            entry_id: 条目 ID
            
        Returns:
            Optional[Any]: 内容
        """
        with self._lock:
            if entry_id not in self._entries:
                return None
            
            entry = self._entries[entry_id]
            
            # 检查过期
            if entry.is_expired():
                del self._entries[entry_id]
                return None
            
            entry.access()
            return entry.content
    
    def update_attention(self, entry_id: str, weight: float) -> None:
        """
        更新注意力权重
        
        Args:
            entry_id: 条目 ID
            weight: 注意力权重
        """
        with self._lock:
            if entry_id in self._entries:
                self._entries[entry_id].attention_weight = weight
    
    def set_attention_focus(self, entry_id: Optional[str]) -> None:
        """
        设置注意力焦点
        
        Args:
            entry_id: 条目 ID
        """
        self._attention_focus = entry_id
    
    def clear(self) -> None:
        """清空工作记忆"""
        with self._lock:
            self._entries.clear()
            self._attention_focus = None
    
    def _evict_lowest_attention(self) -> None:
        """移除最低注意力的条目"""
        if not self._entries:
            return
        
        lowest = min(
            self._entries.values(),
            key=lambda e: e.attention_weight
        )
        del self._entries[lowest.entry_id]
    
    def get_all(self) -> List[WorkingMemoryEntry]:
        """获取所有条目"""
        with self._lock:
            return list(self._entries.values())


class EpisodicMemory:
    """
    情景记忆
    
    存储和管理个人经历的事件序列
    """
    
    def __init__(self):
        """初始化情景记忆"""
        self._episodes: Dict[str, EpisodicMemoryEntry] = {}
        self._timeline: List[str] = []  # 按时间排序
        self._lock = threading.RLock()
    
    def store_episode(self, episode: EpisodicMemoryEntry) -> None:
        """
        存储情景记忆
        
        Args:
            episode: 情景记忆条目
        """
        with self._lock:
            self._episodes[episode.episode_id] = episode
            self._timeline.append(episode.episode_id)
    
    def retrieve_episode(self, episode_id: str) -> Optional[EpisodicMemoryEntry]:
        """
        检索情景记忆
        
        Args:
            episode_id: 情景 ID
            
        Returns:
            Optional[EpisodicMemoryEntry]: 情景记忆
        """
        with self._lock:
            return self._episodes.get(episode_id)
    
    def retrieve_by_time_range(
        self,
        start: datetime,
        end: datetime,
    ) -> List[EpisodicMemoryEntry]:
        """
        按时间范围检索
        
        Args:
            start: 开始时间
            end: 结束时间
            
        Returns:
            List[EpisodicMemoryEntry]: 情景记忆列表
        """
        with self._lock:
            return [
                ep for ep in self._episodes.values()
                if start <= ep.start_time <= end
            ]
    
    def retrieve_by_emotion(
        self,
        emotion: str,
    ) -> List[EpisodicMemoryEntry]:
        """
        按情感检索
        
        Args:
            emotion: 情感标签
            
        Returns:
            List[EpisodicMemoryEntry]: 情景记忆列表
        """
        with self._lock:
            return [
                ep for ep in self._episodes.values()
                if emotion in ep.emotions
            ]
    
    def get_recent_episodes(self, limit: int = 10) -> List[EpisodicMemoryEntry]:
        """获取最近的经历"""
        with self._lock:
            recent_ids = self._timeline[-limit:]
            return [
                self._episodes[eid] 
                for eid in reversed(recent_ids)
                if eid in self._episodes
            ]


class SemanticMemory:
    """
    语义记忆
    
    存储概念、定义和事实知识
    """
    
    def __init__(self):
        """初始化语义记忆"""
        self._concepts: Dict[str, SemanticMemoryEntry] = {}
        self._lock = threading.RLock()
    
    def store_concept(self, concept: SemanticMemoryEntry) -> None:
        """
        存储概念
        
        Args:
            concept: 语义记忆条目
        """
        with self._lock:
            self._concepts[concept.concept_id] = concept
    
    def retrieve_concept(self, concept_id: str) -> Optional[SemanticMemoryEntry]:
        """
        检索概念
        
        Args:
            concept_id: 概念 ID
            
        Returns:
            Optional[SemanticMemoryEntry]: 概念
        """
        with self._lock:
            return self._concepts.get(concept_id)
    
    def search_concepts(self, keyword: str) -> List[SemanticMemoryEntry]:
        """
        搜索概念
        
        Args:
            keyword: 关键词
            
        Returns:
            List[SemanticMemoryEntry]: 概念列表
        """
        with self._lock:
            keyword_lower = keyword.lower()
            return [
                c for c in self._concepts.values()
                if keyword_lower in c.concept.lower() or
                   keyword_lower in c.definition.lower()
            ]
    
    def update_confidence(self, concept_id: str, delta: float) -> None:
        """
        更新置信度
        
        Args:
            concept_id: 概念 ID
            delta: 变化量
        """
        with self._lock:
            if concept_id in self._concepts:
                concept = self._concepts[concept_id]
                concept.confidence = max(0.0, min(1.0, concept.confidence + delta))
                concept.last_updated = datetime.now()


class ProceduralMemory:
    """
    程序记忆
    
    存储技能、习惯和操作步骤
    """
    
    def __init__(self):
        """初始化程序记忆"""
        self._skills: Dict[str, ProceduralMemoryEntry] = {}
        self._lock = threading.RLock()
    
    def store_skill(self, skill: ProceduralMemoryEntry) -> None:
        """
        存储技能
        
        Args:
            skill: 程序记忆条目
        """
        with self._lock:
            self._skills[skill.skill_id] = skill
    
    def retrieve_skill(self, skill_id: str) -> Optional[ProceduralMemoryEntry]:
        """
        检索技能
        
        Args:
            skill_id: 技能 ID
            
        Returns:
            Optional[ProceduralMemoryEntry]: 技能
        """
        with self._lock:
            return self._skills.get(skill_id)
    
    def practice_skill(self, skill_id: str, success: bool) -> None:
        """
        练习技能
        
        Args:
            skill_id: 技能 ID
            success: 是否成功
        """
        with self._lock:
            if skill_id in self._skills:
                skill = self._skills[skill_id]
                skill.practice_count += 1
                skill.last_practiced = datetime.now()
                
                # 更新熟练度
                if success:
                    skill.proficiency = min(1.0, skill.proficiency + 0.05)
                else:
                    skill.proficiency = max(0.0, skill.proficiency - 0.02)
    
    def get_skills_by_proficiency(self, min_proficiency: float = 0.0) -> List[ProceduralMemoryEntry]:
        """获取达到一定熟练度的技能"""
        with self._lock:
            return [
                s for s in self._skills.values()
                if s.proficiency >= min_proficiency
            ]


class MemoryHierarchy:
    """
    记忆层次结构管理器
    
    协调管理所有记忆层级的统一接口
    """
    
    def __init__(
        self,
        working_capacity: int = 7,
        episodic_limit: int = 1000,
        semantic_limit: int = 5000,
        procedural_limit: int = 500,
    ):
        """
        初始化记忆层次结构
        
        Args:
            working_capacity: 工作记忆容量
            episodic_limit: 情景记忆数量限制
            semantic_limit: 语义记忆数量限制
            procedural_limit: 程序记忆数量限制
        """
        self.working_memory = WorkingMemory(capacity=working_capacity)
        self.episodic_memory = EpisodicMemory()
        self.semantic_memory = SemanticMemory()
        self.procedural_memory = ProceduralMemory()
        
        self._limits = {
            MemoryTier.EPISODIC: episodic_limit,
            MemoryTier.SEMANTIC: semantic_limit,
            MemoryTier.PROCEDURAL: procedural_limit,
        }
    
    def store(
        self,
        tier: MemoryTier,
        entry_id: str,
        content: Any,
        **kwargs
    ) -> None:
        """
        存储到指定记忆层级
        
        Args:
            tier: 记忆层级
            entry_id: 条目 ID
            content: 内容
            **kwargs: 其他参数
        """
        if tier == MemoryTier.WORKING:
            ttl = kwargs.get("ttl")
            self.working_memory.store(entry_id, content, ttl)
        
        elif tier == MemoryTier.EPISODIC:
            episode = EpisodicMemoryEntry(
                episode_id=entry_id,
                title=kwargs.get("title", ""),
                narrative=str(content),
                start_time=kwargs.get("start_time", datetime.now()),
                **kwargs
            )
            self.episodic_memory.store_episode(episode)
        
        elif tier == MemoryTier.SEMANTIC:
            concept = SemanticMemoryEntry(
                concept_id=entry_id,
                concept=kwargs.get("concept", ""),
                definition=str(content),
                **kwargs
            )
            self.semantic_memory.store_concept(concept)
        
        elif tier == MemoryTier.PROCEDURAL:
            skill = ProceduralMemoryEntry(
                skill_id=entry_id,
                skill_name=kwargs.get("skill_name", entry_id),
                description=str(content),
                **kwargs
            )
            self.procedural_memory.store_skill(skill)
    
    def retrieve(self, tier: MemoryTier, entry_id: str) -> Optional[Any]:
        """
        从指定层级检索
        
        Args:
            tier: 记忆层级
            entry_id: 条目 ID
            
        Returns:
            Optional[Any]: 内容
        """
        if tier == MemoryTier.WORKING:
            return self.working_memory.retrieve(entry_id)
        elif tier == MemoryTier.EPISODIC:
            entry = self.episodic_memory.retrieve_episode(entry_id)
            return entry.narrative if entry else None
        elif tier == MemoryTier.SEMANTIC:
            entry = self.semantic_memory.retrieve_concept(entry_id)
            return entry.definition if entry else None
        elif tier == MemoryTier.PROCEDURAL:
            entry = self.procedural_memory.retrieve_skill(entry_id)
            return entry.description if entry else None
        return None
    
    def consolidate(self) -> Dict[str, Any]:
        """
        记忆整合
        
        将工作记忆中的重要内容整合到长期记忆
        
        Returns:
            Dict[str, Any]: 整合结果
        """
        result = {
            "consolidated": [],
            "preserved": [],
        }
        
        # 从工作记忆获取高注意力权重的内容
        for entry in self.working_memory.get_all():
            if entry.attention_weight > 0.7:
                result["consolidated"].append(entry.entry_id)
                result["preserved"].append(entry.entry_id)
            elif entry.attention_weight < 0.3:
                # 低权重内容被遗忘
                pass
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "working_memory_count": len(self.working_memory.get_all()),
            "episodic_memory_count": len(self._limits[MemoryTier.EPISODIC]),
            "semantic_memory_count": len(self._limits[MemoryTier.SEMANTIC]),
            "procedural_memory_count": len(self._limits[MemoryTier.PROCEDURAL]),
        }
