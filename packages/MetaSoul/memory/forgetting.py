"""
遗忘机制

自然遗忘和重要记忆保留的实现
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import threading
import random


class ForgettingPolicy(Enum):
    """遗忘策略"""
    NATURAL = "natural"           # 自然遗忘 - 基于时间的衰减
    IMPORTANCE_BASED = "importance"  # 基于重要性 - 重要记忆保留更久
    USAGE_BASED = "usage"        # 基于使用频率 - 常用记忆保留
    EMOTIONAL = "emotional"      # 基于情感 - 情感记忆保留
    ADAPTIVE = "adaptive"        # 自适应 - 综合多种因素


@dataclass
class ForgettingCurve:
    """遗忘曲线配置"""
    initial_retention: float = 1.0  # 初始 retention
    decay_rate: float = 0.1  # 衰减率
    half_life_days: float = 7.0  # 半衰期（天）
    
    def calculate_retention(
        self,
        days_elapsed: float,
        importance: float = 0.5,
        usage_frequency: float = 0.5,
        emotional_valence: float = 0.0,
    ) -> float:
        """
        计算保留率
        
        Args:
            days_elapsed: 经过的天数
            importance: 重要性 (0-1)
            usage_frequency: 使用频率 (0-1)
            emotional_valence: 情感效价 (-1 to 1)
            
        Returns:
            float: 保留率 (0-1)
        """
        # 基于指数衰减的基本遗忘曲线
        retention = self.initial_retention * (
            0.5 ** (days_elapsed / self.half_life_days)
        )
        
        # 重要性保护
        importance_factor = 1.0 + importance * 0.5
        
        # 使用频率保护
        usage_factor = 1.0 + usage_frequency * 0.3
        
        # 情感保护（强情感记忆更难遗忘）
        emotional_factor = 1.0 + abs(emotional_valence) * 0.4
        
        # 综合保留率
        adjusted_retention = retention * importance_factor * usage_factor * emotional_factor
        
        return min(1.0, max(0.0, adjusted_retention))


@dataclass
class MemoryConsolidation:
    """记忆整合"""
    consolidation_id: str
    source_memory_ids: List[str]
    consolidated_content: str
    created_at: datetime = field(default_factory=datetime.now)
    strength: float = 1.0  # 整合强度
    metadata: Dict[str, Any] = field(default_factory=dict)


class ForgettingMechanism:
    """
    遗忘机制
    
    实现自然遗忘和重要记忆保留的功能
    """
    
    def __init__(
        self,
        memory_store,
        policy: ForgettingPolicy = ForgettingPolicy.ADAPTIVE,
    ):
        """
        初始化遗忘机制
        
        Args:
            memory_store: 记忆存储
            policy: 遗忘策略
        """
        self.memory_store = memory_store
        self.policy = policy
        self.forgetting_curve = ForgettingCurve()
        
        # 整合存储
        self._consolidations: Dict[str, MemoryConsolidation] = {}
        
        # 保护的记忆
        self._protected_memories: set = set()
        
        self._lock = threading.RLock()
    
    def protect_memory(self, memory_id: str) -> None:
        """
        保护记忆不被遗忘
        
        Args:
            memory_id: 记忆 ID
        """
        with self._lock:
            self._protected_memories.add(memory_id)
    
    def unprotect_memory(self, memory_id: str) -> None:
        """
        取消记忆保护
        
        Args:
            memory_id: 记忆 ID
        """
        with self._lock:
            self._protected_memories.discard(memory_id)
    
    def is_protected(self, memory_id: str) -> bool:
        """检查记忆是否被保护"""
        return memory_id in self._protected_memories
    
    def calculate_decay(self, memory_data: Dict[str, Any]) -> float:
        """
        计算记忆衰减
        
        Args:
            memory_data: 记忆数据
            
        Returns:
            float: 衰减分数 (0-1, 越高越容易被遗忘)
        """
        # 计算经过的时间
        created_at_str = memory_data.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_at_str)
            days_elapsed = (datetime.now() - created_at).total_seconds() / (24 * 3600)
        except Exception:
            days_elapsed = 0
        
        # 获取各种因素
        importance = memory_data.get("importance", 3) / 5.0  # 归一化
        access_count = memory_data.get("access_count", 0)
        usage_frequency = min(access_count / 10.0, 1.0)
        emotional_valence = memory_data.get("emotional_valence", 0.0)
        
        # 计算保留率
        retention = self.forgetting_curve.calculate_retention(
            days_elapsed=days_elapsed,
            importance=importance,
            usage_frequency=usage_frequency,
            emotional_valence=emotional_valence,
        )
        
        # 衰减 = 1 - 保留率
        return 1.0 - retention
    
    def should_forget(self, memory_data: Dict[str, Any]) -> bool:
        """
        判断记忆是否应该被遗忘
        
        Args:
            memory_data: 记忆数据
            
        Returns:
            bool: 是否应该遗忘
        """
        memory_id = memory_data.get("memory_id", "")
        
        # 保护的记忆不遗忘
        if self.is_protected(memory_id):
            return False
        
        # 计算衰减
        decay = self.calculate_decay(memory_data)
        
        # 根据策略决定遗忘阈值
        if self.policy == ForgettingPolicy.NATURAL:
            threshold = 0.8
        elif self.policy == ForgettingPolicy.IMPORTANCE_BASED:
            importance = memory_data.get("importance", 3)
            threshold = 0.9 - (importance - 1) * 0.1
        elif self.policy == ForgettingPolicy.USAGE_BASED:
            access = memory_data.get("access_count", 0)
            threshold = 0.7 - min(access * 0.02, 0.3)
        elif self.policy == ForgettingPolicy.EMOTIONAL:
            emotion = abs(memory_data.get("emotional_valence", 0.0))
            threshold = 0.9 - emotion * 0.4
        else:  # ADAPTIVE
            threshold = 0.75
        
        return decay >= threshold
    
    def run_forgetting_cycle(self, batch_size: int = 10) -> Dict[str, Any]:
        """
        运行遗忘周期
        
        Args:
            batch_size: 每批处理的记忆数量
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        with self._lock:
            result = {
                "forgotten": [],
                "preserved": [],
                "consolidated": [],
            }
            
            # 获取所有记忆
            all_memories = self.memory_store._backend.query({})
            
            # 排序：最容易遗忘的在前面
            memories_with_decay = []
            for memory in all_memories:
                decay = self.calculate_decay(memory)
                memories_with_decay.append((decay, memory))
            
            memories_with_decay.sort(key=lambda x: x[0], reverse=True)
            
            # 处理记忆
            for decay, memory in memories_with_decay[:batch_size]:
                memory_id = memory.get("memory_id", "")
                
                if self.should_forget(memory):
                    if self.memory_store.delete(memory_id):
                        result["forgotten"].append(memory_id)
                else:
                    result["preserved"].append(memory_id)
            
            return result
    
    def consolidate_memories(
        self,
        memory_ids: List[str],
        summary: str,
    ) -> Optional[str]:
        """
        整合多个记忆
        
        Args:
            memory_ids: 记忆 ID 列表
            summary: 整合后的摘要
            
        Returns:
            Optional[str]: 整合 ID
        """
        with self._lock:
            consolidation_id = f"consolidation_{len(self._consolidations)}"
            
            consolidation = MemoryConsolidation(
                consolidation_id=consolidation_id,
                source_memory_ids=memory_ids,
                consolidated_content=summary,
            )
            
            self._consolidations[consolidation_id] = consolidation
            
            # 可以选择删除源记忆
            # for memory_id in memory_ids:
            #     self.memory_store.delete(memory_id)
            
            return consolidation_id
    
    def get_consolidation(self, consolidation_id: str) -> Optional[MemoryConsolidation]:
        """获取整合结果"""
        return self._consolidations.get(consolidation_id)
    
    def reinforce_memory(self, memory_id: str, amount: float = 0.1) -> None:
        """
        强化记忆
        
        减少记忆的衰减速度
        
        Args:
            memory_id: 记忆 ID
            amount: 强化量
        """
        memory = self.memory_store.retrieve(memory_id)
        if memory:
            # 增加访问次数来强化
            memory["access_count"] = memory.get("access_count", 0) + int(amount * 10)
            self.memory_store._backend.save(memory_id, memory)
    
    def get_forgetting_report(self) -> Dict[str, Any]:
        """获取遗忘报告"""
        all_memories = self.memory_store._backend.query({})
        
        report = {
            "total_memories": len(all_memories),
            "protected_memories": len(self._protected_memories),
            "consolidations": len(self._consolidations),
            "memory_health": {},
        }
        
        # 计算记忆健康度分布
        health_buckets = {
            "healthy": 0,      # decay < 0.3
            "stable": 0,       # 0.3 <= decay < 0.5
            "fading": 0,      # 0.5 <= decay < 0.7
            "at_risk": 0,     # 0.7 <= decay < 0.9
            "forgotten": 0,   # decay >= 0.9
        }
        
        for memory in all_memories:
            decay = self.calculate_decay(memory)
            
            if decay < 0.3:
                health_buckets["healthy"] += 1
            elif decay < 0.5:
                health_buckets["stable"] += 1
            elif decay < 0.7:
                health_buckets["fading"] += 1
            elif decay < 0.9:
                health_buckets["at_risk"] += 1
            else:
                health_buckets["forgotten"] += 1
        
        report["memory_health"] = health_buckets
        
        return report
