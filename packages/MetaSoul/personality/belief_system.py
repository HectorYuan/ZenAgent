"""
信念系统

管理和演化信念的核心实现
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum
import threading
import uuid


class BeliefStrength(Enum):
    """信念强度"""
    WEAK = 1      # 微弱
    MODERATE = 2  # 中等
    STRONG = 3    # 强烈
    ABSOLUTE = 4  # 绝对


@dataclass
class Belief:
    """信念"""
    belief_id: str
    content: str
    strength: BeliefStrength = BeliefStrength.MODERATE
    confidence: float = 0.5  # 0-1
    
    # 来源
    source: str = ""
    evidence: List[str] = field(default_factory=list)
    
    # 关联
    related_beliefs: List[str] = field(default_factory=list)
    contradicts: List[str] = field(default_factory=list)  # 矛盾的信念
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    times_challenged: int = 0
    times_reinforced: int = 0
    
    def strengthen(self, amount: float = 0.1) -> None:
        """强化信念"""
        self.confidence = min(1.0, self.confidence + amount)
        self.times_reinforced += 1
        self.last_modified = datetime.now()
        
        # 更新强度等级
        if self.confidence > 0.9:
            self.strength = BeliefStrength.ABSOLUTE
        elif self.confidence > 0.7:
            self.strength = BeliefStrength.STRONG
        elif self.confidence > 0.4:
            self.strength = BeliefStrength.MODERATE
        else:
            self.strength = BeliefStrength.WEAK
    
    def weaken(self, amount: float = 0.1) -> None:
        """弱化信念"""
        self.confidence = max(0.0, self.confidence - amount)
        self.times_challenged += 1
        self.last_modified = datetime.now()
        
        # 更新强度等级
        if self.confidence > 0.9:
            self.strength = BeliefStrength.ABSOLUTE
        elif self.confidence > 0.7:
            self.strength = BeliefStrength.STRONG
        elif self.confidence > 0.4:
            self.strength = BeliefStrength.MODERATE
        else:
            self.strength = BeliefStrength.WEAK


class BeliefSystem:
    """
    信念系统
    
    管理信念的创建、更新和演化
    """
    
    def __init__(self):
        """初始化信念系统"""
        self._beliefs: Dict[str, Belief] = {}
        self._belief_index: Dict[str, Set[str]] = {}  # 关键词 -> 信念 ID
        self._contradiction_map: Dict[str, str] = {}  # 信念 ID -> 矛盾信念 ID
        
        self._lock = threading.RLock()
    
    def create_belief(
        self,
        content: str,
        strength: BeliefStrength = BeliefStrength.MODERATE,
        confidence: float = 0.5,
        source: str = "",
        evidence: Optional[List[str]] = None,
    ) -> str:
        """
        创建信念
        
        Args:
            content: 信念内容
            strength: 初始强度
            confidence: 初始置信度
            source: 来源
            evidence: 证据列表
            
        Returns:
            str: 信念 ID
        """
        with self._lock:
            belief_id = str(uuid.uuid4())
            
            belief = Belief(
                belief_id=belief_id,
                content=content,
                strength=strength,
                confidence=confidence,
                source=source,
                evidence=evidence or [],
            )
            
            # 根据置信度更新强度
            if confidence > 0.9:
                belief.strength = BeliefStrength.ABSOLUTE
            elif confidence > 0.7:
                belief.strength = BeliefStrength.STRONG
            elif confidence > 0.4:
                belief.strength = BeliefStrength.MODERATE
            else:
                belief.strength = BeliefStrength.WEAK
            
            self._beliefs[belief_id] = belief
            
            # 更新索引
            self._index_belief(belief)
            
            return belief_id
    
    def _index_belief(self, belief: Belief) -> None:
        """索引信念"""
        content_lower = belief.content.lower()
        
        # 基于关键词索引 - 支持中英文
        words = content_lower.split()
        for word in words:
            if len(word) >= 2:
                if word not in self._belief_index:
                    self._belief_index[word] = set()
                self._belief_index[word].add(belief.belief_id)
        
        # 对于中文内容，按字符级索引（每个汉字作为索引词）
        import re
        # 提取所有连续的汉字/英文单词
        chunks = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', content_lower)
        for chunk in chunks:
            if len(chunk) >= 2:
                if chunk not in self._belief_index:
                    self._belief_index[chunk] = set()
                self._belief_index[chunk].add(belief.belief_id)
            
            # 对于中文词组，进一步拆分
            if re.search(r'[\u4e00-\u9fff]', chunk):
                # 提取所有汉字字符
                chars = re.findall(r'[\u4e00-\u9fff]', chunk)
                for char in chars:
                    if char not in self._belief_index:
                        self._belief_index[char] = set()
                    self._belief_index[char].add(belief.belief_id)
    
    def get_belief(self, belief_id: str) -> Optional[Belief]:
        """获取信念"""
        return self._beliefs.get(belief_id)
    
    def update_belief(
        self,
        belief_id: str,
        confidence: Optional[float] = None,
        new_content: Optional[str] = None,
    ) -> bool:
        """
        更新信念
        
        Args:
            belief_id: 信念 ID
            confidence: 新置信度
            new_content: 新内容
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            belief = self._beliefs.get(belief_id)
            if not belief:
                return False
            
            if confidence is not None:
                if confidence > belief.confidence:
                    belief.strengthen(confidence - belief.confidence)
                else:
                    belief.weaken(belief.confidence - confidence)
            
            if new_content is not None:
                belief.content = new_content
                belief.last_modified = datetime.now()
            
            return True
    
    def reinforce_belief(
        self,
        belief_id: str,
        evidence: Optional[str] = None,
        amount: float = 0.1,
    ) -> bool:
        """
        强化信念
        
        Args:
            belief_id: 信念 ID
            evidence: 新证据
            amount: 强化量
            
        Returns:
            bool: 是否成功
        """
        belief = self._beliefs.get(belief_id)
        if not belief:
            return False
        
        belief.strengthen(amount)
        
        if evidence:
            belief.evidence.append(evidence)
        
        return True
    
    def challenge_belief(
        self,
        belief_id: str,
        counter_evidence: Optional[str] = None,
        amount: float = 0.1,
    ) -> bool:
        """
        挑战信念
        
        Args:
            belief_id: 信念 ID
            counter_evidence: 反证
            amount: 弱化量
            
        Returns:
            bool: 是否成功
        """
        belief = self._beliefs.get(belief_id)
        if not belief:
            return False
        
        belief.weaken(amount)
        
        if counter_evidence:
            belief.evidence.append(f"[挑战] {counter_evidence}")
        
        return True
    
    def create_contradiction(
        self,
        belief_id1: str,
        belief_id2: str,
    ) -> bool:
        """
        创建矛盾关系
        
        Args:
            belief_id1: 信念 ID 1
            belief_id2: 信念 ID 2
            
        Returns:
            bool: 是否成功
        """
        belief1 = self._beliefs.get(belief_id1)
        belief2 = self._beliefs.get(belief_id2)
        
        if not belief1 or not belief2:
            return False
        
        belief1.contradicts.append(belief_id2)
        belief2.contradicts.append(belief_id1)
        
        self._contradiction_map[belief_id1] = belief_id2
        self._contradiction_map[belief_id2] = belief_id1
        
        return True
    
    def resolve_contradiction(
        self,
        belief_id1: str,
        evidence: str,
    ) -> bool:
        """
        解决矛盾
        
        Args:
            belief_id1: 被支持的信念 ID
            evidence: 证据
            
        Returns:
            bool: 是否成功
        """
        belief1 = self._beliefs.get(belief_id1)
        if not belief1:
            return False
        
        # 强化被支持的信念
        belief1.strengthen(0.2)
        belief1.evidence.append(f"[矛盾解决] {evidence}")
        
        # 找到矛盾的信念
        contradicting_id = self._contradiction_map.get(belief_id1)
        if contradicting_id:
            contradicting = self._beliefs.get(contradicting_id)
            if contradicting:
                contradicting.weaken(0.2)
                contradicting.evidence.append(f"[矛盾解决-失败] {evidence}")
        
        return True
    
    def search_beliefs(
        self,
        query: str,
        min_confidence: float = 0.0,
    ) -> List[Belief]:
        """
        搜索信念
        
        Args:
            query: 查询字符串
            min_confidence: 最低置信度
            
        Returns:
            List[Belief]: 匹配的信念
        """
        with self._lock:
            query_lower = query.lower()
            query_words = query_lower.split()
            matching_ids: Set[str] = set()
            
            # 先按空格分词匹配
            for word in query_words:
                if word in self._belief_index:
                    matching_ids.update(self._belief_index[word])
            
            # 对于中文查询，尝试匹配索引中的汉字
            import re
            chinese_chars = re.findall(r'[\u4e00-\u9fff]', query_lower)
            for char in chinese_chars:
                if char in self._belief_index:
                    matching_ids.update(self._belief_index[char])
            
            # 如果没有找到匹配，尝试直接搜索信念内容
            if not matching_ids:
                for belief in self._beliefs.values():
                    if query_lower in belief.content.lower():
                        matching_ids.add(belief.belief_id)
            
            results = []
            for belief_id in matching_ids:
                belief = self._beliefs.get(belief_id)
                if belief and belief.confidence >= min_confidence:
                    results.append(belief)
            
            return sorted(results, key=lambda b: b.confidence, reverse=True)
    
    def get_strong_beliefs(
        self,
        min_strength: BeliefStrength = BeliefStrength.STRONG,
    ) -> List[Belief]:
        """获取强信念"""
        return [
            b for b in self._beliefs.values()
            if b.strength.value >= min_strength.value
        ]
    
    def get_contradictions(self, belief_id: str) -> List[Belief]:
        """获取矛盾的信念"""
        belief = self._beliefs.get(belief_id)
        if not belief:
            return []
        
        contradictions = []
        for cid in belief.contradicts:
            c = self._beliefs.get(cid)
            if c:
                contradictions.append(c)
        
        return contradictions
    
    def get_beliefs(self) -> List[Dict[str, Any]]:
        """获取所有信念"""
        return [
            {
                "belief_id": b.belief_id,
                "content": b.content,
                "strength": b.strength.name,
                "confidence": b.confidence,
                "evidence_count": len(b.evidence),
                "created_at": b.created_at.isoformat(),
            }
            for b in self._beliefs.values()
        ]
    
    def clear(self) -> None:
        """清空信念系统"""
        with self._lock:
            self._beliefs.clear()
            self._belief_index.clear()
            self._contradiction_map.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        by_strength: Dict[str, int] = {
            s.name: 0 for s in BeliefStrength
        }
        
        total_evidence = 0
        total_confidence = 0.0
        
        for belief in self._beliefs.values():
            by_strength[belief.strength.name] += 1
            total_evidence += len(belief.evidence)
            total_confidence += belief.confidence
        
        count = len(self._beliefs)
        
        return {
            "total_beliefs": count,
            "by_strength": by_strength,
            "total_evidence": total_evidence,
            "avg_confidence": total_confidence / count if count > 0 else 0,
            "contradictions": len(self._contradiction_map) // 2,
        }
