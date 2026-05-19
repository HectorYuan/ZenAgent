"""
模式识别器

识别和跟踪行为与经验模式
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
import threading
import uuid


class PatternType(Enum):
    """模式类型"""
    SEQUENTIAL = "sequential"      # 序列模式
    CYCLIC = "cyclic"              # 循环模式
    EMERGING = "emerging"           # 新兴模式
    DECLINING = "declining"         # 衰退模式
    ANOMALY = "anomaly"             # 异常模式
    HABIT = "habit"                 # 习惯模式


@dataclass
class Pattern:
    """模式"""
    pattern_id: str
    pattern_type: PatternType
    description: str
    
    # 模式特征
    elements: List[str] = field(default_factory=list)
    frequency: float = 0.0
    regularity: float = 0.0  # 规律性
    
    # 上下文
    context: str = ""
    conditions: List[str] = field(default_factory=list)
    
    # 评估
    confidence: float = 0.5
    strength: float = 0.5  # 模式强度
    
    # 时间信息
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    occurrence_count: int = 0
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


class PatternRecognizer:
    """
    模式识别器
    
    识别和跟踪行为与经验模式
    """
    
    def __init__(self, knowledge_graph=None):
        """
        初始化模式识别器
        
        Args:
            knowledge_graph: 知识图谱
        """
        self.knowledge_graph = knowledge_graph
        
        # 模式存储
        self._patterns: Dict[str, Pattern] = {}
        self._pattern_sequences: Dict[str, List[datetime]] = {}  # 模式 -> 出现时间
        
        # 缓存
        self._element_history: List[Dict[str, Any]] = []
        
        self._lock = threading.RLock()
    
    def register_event(
        self,
        event_type: str,
        elements: List[str],
        context: Optional[str] = None,
    ) -> List[str]:
        """
        注册事件
        
        Args:
            event_type: 事件类型
            elements: 元素列表
            context: 上下文
            
        Returns:
            List[str]: 识别出的模式 ID 列表
        """
        with self._lock:
            # 记录事件
            event = {
                "type": event_type,
                "elements": elements,
                "context": context,
                "timestamp": datetime.now(),
            }
            self._element_history.append(event)
            
            # 限制历史长度
            if len(self._element_history) > 1000:
                self._element_history = self._element_history[-500:]
            
            # 识别模式
            pattern_ids = []
            
            # 序列模式
            sequential = self._detect_sequential_pattern(elements)
            if sequential:
                pattern_ids.append(sequential)
            
            # 循环模式
            cyclic = self._detect_cyclic_pattern(event_type)
            if cyclic:
                pattern_ids.append(cyclic)
            
            # 习惯模式
            habit = self._detect_habit_pattern(elements)
            if habit:
                pattern_ids.append(habit)
            
            return pattern_ids
    
    def _detect_sequential_pattern(
        self,
        elements: List[str],
    ) -> Optional[str]:
        """检测序列模式"""
        if len(elements) < 2:
            return None
        
        # 创建序列键
        sequence_key = " -> ".join(elements)
        
        # 检查是否已存在
        for pattern in self._patterns.values():
            if pattern.pattern_type == PatternType.SEQUENTIAL:
                if pattern.description == sequence_key:
                    # 更新模式
                    pattern.occurrence_count += 1
                    pattern.last_seen = datetime.now()
                    pattern.confidence = min(1.0, pattern.confidence + 0.1)
                    return pattern.pattern_id
        
        # 检查是否符合已知序列模式（至少出现2次）
        if len(self._element_history) >= 2:
            recent_sequences = []
            for event in self._element_history[-5:]:
                seq = " -> ".join(event.get("elements", []))
                if seq:
                    recent_sequences.append(seq)
            
            if sequence_key in recent_sequences:
                count = recent_sequences.count(sequence_key)
                if count >= 2:
                    # 创建新模式
                    pattern_id = str(uuid.uuid4())
                    pattern = Pattern(
                        pattern_id=pattern_id,
                        pattern_type=PatternType.SEQUENTIAL,
                        description=sequence_key,
                        elements=elements,
                        frequency=count / len(self._element_history),
                        confidence=0.6,
                        strength=0.5,
                        occurrence_count=count,
                    )
                    
                    self._patterns[pattern_id] = pattern
                    return pattern_id
        
        return None
    
    def _detect_cyclic_pattern(
        self,
        event_type: str,
    ) -> Optional[str]:
        """检测循环模式"""
        # 检查事件类型出现的时间间隔
        if event_type not in self._pattern_sequences:
            self._pattern_sequences[event_type] = []
        
        self._pattern_sequences[event_type].append(datetime.now())
        
        timestamps = self._pattern_sequences[event_type]
        if len(timestamps) < 3:
            return None
        
        # 计算时间间隔
        intervals = [
            (timestamps[i+1] - timestamps[i]).total_seconds()
            for i in range(len(timestamps)-1)
        ]
        
        # 检查是否近似相等
        if len(intervals) >= 2:
            avg_interval = sum(intervals) / len(intervals)
            variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)
            std_dev = variance ** 0.5
            
            # 如果标准差小于平均值的20%，认为有循环模式
            if std_dev < avg_interval * 0.2:
                # 检查是否已存在
                for pattern in self._patterns.values():
                    if (pattern.pattern_type == PatternType.CYCLIC and
                        event_type in pattern.elements):
                        pattern.occurrence_count += 1
                        pattern.last_seen = datetime.now()
                        return pattern.pattern_id
                
                # 创建新模式
                pattern_id = str(uuid.uuid4())
                pattern = Pattern(
                    pattern_id=pattern_id,
                    pattern_type=PatternType.CYCLIC,
                    description=f"事件 '{event_type}' 呈现周期性",
                    elements=[event_type],
                    frequency=1.0 / avg_interval if avg_interval > 0 else 0,
                    regularity=1.0 - (std_dev / avg_interval if avg_interval > 0 else 1),
                    confidence=0.7,
                    strength=0.6,
                    occurrence_count=len(timestamps),
                )
                
                self._patterns[pattern_id] = pattern
                return pattern_id
        
        return None
    
    def _detect_habit_pattern(
        self,
        elements: List[str],
    ) -> Optional[str]:
        """检测习惯模式"""
        # 统计元素出现频率
        element_counts: Dict[str, int] = {}
        
        for event in self._element_history[-20:]:  # 最近20个事件
            for elem in event.get("elements", []):
                element_counts[elem] = element_counts.get(elem, 0) + 1
        
        # 找出高频元素
        high_freq_elements = [
            elem for elem, count in element_counts.items()
            if count >= 5
        ]
        
        if not high_freq_elements:
            return None
        
        # 检查是否已存在
        for pattern in self._patterns.values():
            if pattern.pattern_type == PatternType.HABIT:
                if set(pattern.elements) == set(high_freq_elements):
                    pattern.last_seen = datetime.now()
                    pattern.confidence = min(1.0, pattern.confidence + 0.05)
                    return pattern.pattern_id
        
        # 创建习惯模式
        pattern_id = str(uuid.uuid4())
        pattern = Pattern(
            pattern_id=pattern_id,
            pattern_type=PatternType.HABIT,
            description=f"习惯性元素: {', '.join(high_freq_elements[:3])}",
            elements=high_freq_elements,
            frequency=len(high_freq_elements) / len(self._element_history),
            confidence=0.6,
            strength=0.7,
            occurrence_count=len(self._element_history),
        )
        
        self._patterns[pattern_id] = pattern
        return pattern_id
    
    def detect_anomalies(
        self,
        current_event: Dict[str, Any],
        threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        检测异常
        
        Args:
            current_event: 当前事件
            threshold: 异常阈值
            
        Returns:
            List[Dict[str, Any]]: 异常描述列表
        """
        anomalies = []
        
        with self._lock:
            # 检查与历史事件的差异
            if len(self._element_history) >= 5:
                # 统计历史元素频率
                history_elements: Set[str] = set()
                for event in self._element_history[-5:]:
                    history_elements.update(event.get("elements", []))
                
                # 检查当前事件的新元素
                current_elements = set(current_event.get("elements", []))
                new_elements = current_elements - history_elements
                
                if len(new_elements) > len(current_elements) * threshold:
                    anomalies.append({
                        "type": "novel_elements",
                        "description": f"发现 {len(new_elements)} 个新元素",
                        "elements": list(new_elements),
                    })
            
            return anomalies
    
    def get_pattern(self, pattern_id: str) -> Optional[Pattern]:
        """获取模式"""
        return self._patterns.get(pattern_id)
    
    def get_patterns_by_type(
        self,
        pattern_type: PatternType,
    ) -> List[Pattern]:
        """按类型获取模式"""
        return [
            p for p in self._patterns.values()
            if p.pattern_type == pattern_type
        ]
    
    def get_active_patterns(
        self,
        max_age_hours: int = 24,
    ) -> List[Pattern]:
        """获取活跃模式"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        return [
            p for p in self._patterns.values()
            if p.last_seen >= cutoff
        ]
    
    def update_pattern_strength(
        self,
        pattern_id: str,
        delta: float,
    ) -> bool:
        """更新模式强度"""
        pattern = self._patterns.get(pattern_id)
        if not pattern:
            return False
        
        pattern.strength = max(0.0, min(1.0, pattern.strength + delta))
        
        # 如果强度过低，标记为衰退
        if pattern.strength < 0.2:
            pattern.pattern_type = PatternType.DECLINING
        
        return True
    
    def merge_patterns(
        self,
        pattern_id1: str,
        pattern_id2: str,
    ) -> Optional[str]:
        """合并模式"""
        pattern1 = self._patterns.get(pattern_id1)
        pattern2 = self._patterns.get(pattern_id2)
        
        if not pattern1 or not pattern2:
            return None
        
        # 创建新模式
        merged_id = str(uuid.uuid4())
        merged = Pattern(
            pattern_id=merged_id,
            pattern_type=pattern1.pattern_type,
            description=f"{pattern1.description} + {pattern2.description}",
            elements=list(set(pattern1.elements + pattern2.elements)),
            frequency=(pattern1.frequency + pattern2.frequency) / 2,
            regularity=(pattern1.regularity + pattern2.regularity) / 2,
            confidence=max(pattern1.confidence, pattern2.confidence),
            strength=max(pattern1.strength, pattern2.strength),
            occurrence_count=pattern1.occurrence_count + pattern2.occurrence_count,
            metadata={
                "merged_from": [pattern_id1, pattern_id2],
            },
        )
        
        self._patterns[merged_id] = merged
        
        # 删除原模式
        del self._patterns[pattern_id1]
        del self._patterns[pattern_id2]
        
        return merged_id
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """获取模式统计"""
        by_type: Dict[str, int] = {}
        total_strength = 0.0
        total_confidence = 0.0
        
        for pattern in self._patterns.values():
            by_type[pattern.pattern_type.value] = (
                by_type.get(pattern.pattern_type.value, 0) + 1
            )
            total_strength += pattern.strength
            total_confidence += pattern.confidence
        
        count = len(self._patterns)
        
        return {
            "total_patterns": count,
            "by_type": by_type,
            "average_strength": total_strength / count if count > 0 else 0,
            "average_confidence": total_confidence / count if count > 0 else 0,
            "recent_events": len(self._element_history),
        }
    
    def clear_old_patterns(
        self,
        max_age_days: int = 30,
        min_strength: float = 0.1,
    ) -> int:
        """清除旧模式"""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        
        to_remove = []
        for pattern_id, pattern in self._patterns.items():
            if pattern.last_seen < cutoff and pattern.strength < min_strength:
                to_remove.append(pattern_id)
        
        for pattern_id in to_remove:
            del self._patterns[pattern_id]
        
        return len(to_remove)
