"""
价值观演化

价值观的优先级和演化
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import threading


class ValuePriority(Enum):
    """价值优先级"""
    CRITICAL = 1   # 关键
    HIGH = 2       # 高
    MEDIUM = 3     # 中
    LOW = 4        # 低


@dataclass
class Value:
    """价值观"""
    value_id: str
    name: str
    description: str
    
    # 优先级
    priority: ValuePriority = ValuePriority.MEDIUM
    priority_score: float = 0.5  # 0-1
    
    # 关联
    related_beliefs: List[str] = field(default_factory=list)
    related_experiences: List[str] = field(default_factory=list)
    
    # 状态
    is_active: bool = True
    last_aligned: Optional[datetime] = None  # 最后一次与行为对齐
    
    # 历史
    priority_history: List[Tuple[datetime, float]] = field(default_factory=list)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_priority(
        self,
        new_priority: ValuePriority,
        reason: str = "",
    ) -> None:
        """更新优先级"""
        self.priority = new_priority
        
        # 更新分数
        if new_priority == ValuePriority.CRITICAL:
            self.priority_score = 1.0
        elif new_priority == ValuePriority.HIGH:
            self.priority_score = 0.8
        elif new_priority == ValuePriority.MEDIUM:
            self.priority_score = 0.5
        else:
            self.priority_score = 0.2
        
        # 记录历史
        self.priority_history.append((datetime.now(), self.priority_score))
    
    def align_with_action(
        self,
        action_aligned: bool,
    ) -> None:
        """与行动对齐"""
        self.last_aligned = datetime.now()
        
        if action_aligned:
            # 一致性强化
            self.priority_score = min(1.0, self.priority_score + 0.05)
        else:
            # 不一致弱化
            self.priority_score = max(0.0, self.priority_score - 0.1)


class ValueEvolution:
    """
    价值观演化
    
    管理价值观的优先级和演化
    """
    
    def __init__(self, belief_system=None):
        """
        初始化价值观演化
        
        Args:
            belief_system: 信念系统
        """
        self.belief_system = belief_system
        
        # 价值观存储
        self._values: Dict[str, Value] = {}
        
        # 核心价值观
        self._core_values: List[str] = []
        
        # 演化历史
        self._evolution_history: List[Dict[str, Any]] = []
        
        self._lock = threading.RLock()
    
    def create_value(
        self,
        name: str,
        description: str = "",
        priority: ValuePriority = ValuePriority.MEDIUM,
    ) -> str:
        """
        创建价值观
        
        Args:
            name: 名称
            description: 描述
            priority: 优先级
            
        Returns:
            str: 价值观 ID
        """
        import uuid
        
        with self._lock:
            value_id = str(uuid.uuid4())
            
            # 根据优先级设置分数
            if priority == ValuePriority.CRITICAL:
                priority_score = 1.0
            elif priority == ValuePriority.HIGH:
                priority_score = 0.8
            elif priority == ValuePriority.MEDIUM:
                priority_score = 0.5
            else:
                priority_score = 0.2
            
            value = Value(
                value_id=value_id,
                name=name,
                description=description,
                priority=priority,
                priority_score=priority_score,
            )
            
            self._values[value_id] = value
            
            return value_id
    
    def get_value(self, value_id: str) -> Optional[Value]:
        """获取价值观"""
        return self._values.get(value_id)
    
    def get_value_by_name(self, name: str) -> Optional[Value]:
        """通过名称获取价值观"""
        for value in self._values.values():
            if value.name == name:
                return value
        return None
    
    def set_as_core(self, value_id: str) -> bool:
        """
        设为核心价值观
        
        Args:
            value_id: 价值观 ID
            
        Returns:
            bool: 是否成功
        """
        if value_id not in self._values:
            return False
        
        if value_id not in self._core_values:
            self._core_values.append(value_id)
        
        # 更新优先级
        value = self._values[value_id]
        value.update_priority(ValuePriority.CRITICAL)
        
        return True
    
    def update_value_from_experience(
        self,
        value_id: str,
        experience: Dict[str, Any],
    ) -> Optional[float]:
        """
        从经验更新价值观
        
        Args:
            value_id: 价值观 ID
            experience: 经验数据
            
        Returns:
            Optional[float]: 优先级变化
        """
        value = self._values.get(value_id)
        if not value:
            return None
        
        outcome = experience.get("outcome", 0)
        sentiment = experience.get("sentiment", 0)
        aligned = experience.get("value_aligned", False)
        
        old_priority = value.priority_score
        
        # 基于经验调整
        if aligned:
            if outcome > 0 and sentiment > 0:
                value.priority_score = min(1.0, value.priority_score + 0.1)
            elif outcome < 0:
                value.priority_score = max(0.0, value.priority_score - 0.05)
        
        # 与行动对齐
        value.align_with_action(aligned)
        
        delta = value.priority_score - old_priority
        
        if abs(delta) > 0.01:
            # 记录演化
            self._record_evolution(value_id, experience, delta)
        
        return delta
    
    def _record_evolution(
        self,
        value_id: str,
        experience: Dict[str, Any],
        delta: float,
    ) -> None:
        """记录价值观演化"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "value_id": value_id,
            "experience_id": experience.get("id", ""),
            "delta": delta,
            "new_priority": self._values[value_id].priority_score,
        }
        
        self._evolution_history.append(record)
        
        # 限制历史长度
        if len(self._evolution_history) > 100:
            self._evolution_history = self._evolution_history[-50:]
    
    def align_behavior(
        self,
        action: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        评估行为与价值观的一致性
        
        Args:
            action: 行为数据
            
        Returns:
            Dict[str, Any]: 对齐结果
        """
        aligned_values: List[str] = []
        misaligned_values: List[str] = []
        
        action_values = action.get("values", [])  # 行动涉及的价值观
        
        for value in self._values.values():
            if not value.is_active:
                continue
            
            if value.name in action_values or value.value_id in action_values:
                if action.get("success", False):
                    aligned_values.append(value.name)
                    value.align_with_action(True)
                else:
                    misaligned_values.append(value.name)
                    value.align_with_action(False)
        
        return {
            "aligned": aligned_values,
            "misaligned": misaligned_values,
            "alignment_score": (
                len(aligned_values) / 
                max(len(aligned_values) + len(misaligned_values), 1)
            ),
        }
    
    def get_prioritized_values(
        self,
        limit: Optional[int] = None,
    ) -> List[Value]:
        """
        获取优先级排序的价值观
        
        Args:
            limit: 返回数量限制
            
        Returns:
            List[Value]: 价值观列表
        """
        sorted_values = sorted(
            self._values.values(),
            key=lambda v: v.priority_score,
            reverse=True
        )
        
        if limit:
            return sorted_values[:limit]
        
        return sorted_values
    
    def get_core_values(self) -> List[Value]:
        """获取核心价值观"""
        return [
            self._values[vid] 
            for vid in self._core_values
            if vid in self._values
        ]
    
    def resolve_value_conflict(
        self,
        value_id1: str,
        value_id2: str,
        context: str,
    ) -> str:
        """
        解决价值观冲突
        
        Args:
            value_id1: 价值观 1
            value_id2: 价值观 2
            context: 上下文
            
        Returns:
            str: 优先选择的价值观 ID
        """
        value1 = self._values.get(value_id1)
        value2 = self._values.get(value_id2)
        
        if not value1 or not value2:
            return ""
        
        # 基于优先级和历史解决
        if value1.priority_score > value2.priority_score:
            winner = value1
            loser = value2
        elif value2.priority_score > value1.priority_score:
            winner = value2
            loser = value1
        else:
            # 平局，检查是否是核心价值观
            if value_id1 in self._core_values:
                winner = value1
                loser = value2
            elif value_id2 in self._core_values:
                winner = value2
                loser = value1
            else:
                # 随机选择（实际中应该有更复杂的逻辑）
                import random
                winner = value1 if random.random() > 0.5 else value2
                loser = value2 if winner == value1 else value1
        
        # 记录解决过程
        self._evolution_history.append({
            "timestamp": datetime.now().isoformat(),
            "event": "conflict_resolution",
            "value1": value_id1,
            "value2": value_id2,
            "winner": winner.value_id,
            "context": context,
        })
        
        return winner.value_id
    
    def get_evolution_history(
        self,
        value_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        获取演化历史
        
        Args:
            value_id: 价值观 ID（可选）
            limit: 返回数量
            
        Returns:
            List[Dict[str, Any]]: 演化记录
        """
        history = self._evolution_history
        
        if value_id:
            history = [
                r for r in history
                if r.get("value_id") == value_id
            ]
        
        return history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_values = len(self._values)
        active_values = sum(1 for v in self._values.values() if v.is_active)
        core_values = len(self._core_values)
        
        avg_priority = sum(
            v.priority_score for v in self._values.values()
        ) / max(total_values, 1)
        
        by_priority: Dict[str, int] = {
            p.name: 0 for p in ValuePriority
        }
        for value in self._values.values():
            by_priority[value.priority.name] += 1
        
        return {
            "total_values": total_values,
            "active_values": active_values,
            "core_values": core_values,
            "average_priority": avg_priority,
            "by_priority": by_priority,
            "evolution_events": len(self._evolution_history),
        }
