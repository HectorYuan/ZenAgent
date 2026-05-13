"""
洞察提取器

从经验中提取深层次洞察
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum
import threading
import uuid


class InsightType(Enum):
    """洞察类型"""
    CAUSAL = "causal"          # 因果洞察
    CORRELATIONAL = "correlational"  # 相关洞察
    TEMPORAL = "temporal"      # 时间洞察
    PROCEDURAL = "procedural"  # 过程洞察
    CONTRADICTORY = "contradictory"  # 矛盾洞察
    CREATIVE = "creative"      # 创造性洞察


@dataclass
class Insight:
    """洞察"""
    insight_id: str
    insight_type: InsightType
    content: str
    
    # 来源
    source_experiences: List[str] = field(default_factory=list)
    
    # 评估
    confidence: float = 0.5
    novelty: float = 0.5
    utility: float = 0.5
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_score(self) -> float:
        """获取综合评分"""
        return (self.confidence + self.novelty + self.utility) / 3


class InsightExtractor:
    """
    洞察提取器
    
    从多个经验中提取深层次洞察
    """
    
    def __init__(
        self,
        reflector=None,
        knowledge_graph=None,
    ):
        """
        初始化洞察提取器
        
        Args:
            reflector: 反思引擎
            knowledge_graph: 知识图谱
        """
        self.reflector = reflector
        self.knowledge_graph = knowledge_graph
        
        # 洞察存储
        self._insights: Dict[str, Insight] = {}
        self._insight_index: Dict[str, Set[str]] = {}  # 标签 -> 洞察 ID
        
        self._lock = threading.RLock()
    
    def extract(
        self,
        experiences: List[Dict[str, Any]],
    ) -> List[str]:
        """
        提取洞察
        
        Args:
            experiences: 经验列表
            
        Returns:
            List[str]: 洞察 ID 列表
        """
        with self._lock:
            insight_ids = []
            
            # 因果洞察
            causal_insights = self._extract_causal_insights(experiences)
            insight_ids.extend(causal_insights)
            
            # 相关洞察
            correlational_insights = self._extract_correlational_insights(
                experiences
            )
            insight_ids.extend(correlational_insights)
            
            # 时间洞察
            temporal_insights = self._extract_temporal_insights(experiences)
            insight_ids.extend(temporal_insights)
            
            # 过程洞察
            procedural_insights = self._extract_procedural_insights(experiences)
            insight_ids.extend(procedural_insights)
            
            return insight_ids
    
    def _extract_causal_insights(
        self,
        experiences: List[Dict[str, Any]],
    ) -> List[str]:
        """提取因果洞察"""
        insight_ids = []
        
        # 分析导致成功的因素
        success_experiences = [
            e for e in experiences
            if e.get("outcome", 0) > 0.3
        ]
        
        failure_experiences = [
            e for e in experiences
            if e.get("outcome", 0) < -0.3
        ]
        
        if success_experiences:
            # 提取成功因素
            common_success_factors = self._find_common_factors(
                success_experiences
            )
            
            if common_success_factors:
                insight = Insight(
                    insight_id=str(uuid.uuid4()),
                    insight_type=InsightType.CAUSAL,
                    content=f"这些因素可能导致成功: {', '.join(common_success_factors[:3])}",
                    source_experiences=[
                        e.get("id", "") for e in success_experiences
                    ],
                    confidence=0.7,
                    novelty=0.5,
                    utility=0.8,
                    tags=["success", "causal"],
                )
                
                insight_ids.append(insight.insight_id)
                self._store_insight(insight)
        
        if failure_experiences:
            # 提取失败因素
            common_failure_factors = self._find_common_factors(
                failure_experiences
            )
            
            if common_failure_factors:
                insight = Insight(
                    insight_id=str(uuid.uuid4()),
                    insight_type=InsightType.CAUSAL,
                    content=f"这些因素可能导致失败: {', '.join(common_failure_factors[:3])}",
                    source_experiences=[
                        e.get("id", "") for e in failure_experiences
                    ],
                    confidence=0.6,
                    novelty=0.5,
                    utility=0.7,
                    tags=["failure", "causal"],
                )
                
                insight_ids.append(insight.insight_id)
                self._store_insight(insight)
        
        return insight_ids
    
    def _extract_correlational_insights(
        self,
        experiences: List[Dict[str, Any]],
    ) -> List[str]:
        """提取相关洞察"""
        insight_ids = []
        
        # 简单实现：查找共同出现的元素
        if len(experiences) < 2:
            return insight_ids
        
        # 统计元素共现
        element_pairs: Dict[Tuple[str, str], int] = {}
        
        for exp in experiences:
            elements = self._extract_elements(exp)
            for i, e1 in enumerate(elements):
                for e2 in elements[i+1:]:
                    pair = tuple(sorted([e1, e2]))
                    element_pairs[pair] = element_pairs.get(pair, 0) + 1
        
        # 找出高共现的元素对
        for (e1, e2), count in element_pairs.items():
            if count >= len(experiences) * 0.5:
                insight = Insight(
                    insight_id=str(uuid.uuid4()),
                    insight_type=InsightType.CORRELATIONAL,
                    content=f"'{e1}' 和 '{e2}' 经常同时出现",
                    confidence=0.6,
                    novelty=0.4,
                    utility=0.5,
                    tags=["correlation"],
                )
                
                insight_ids.append(insight.insight_id)
                self._store_insight(insight)
        
        return insight_ids
    
    def _extract_temporal_insights(
        self,
        experiences: List[Dict[str, Any]],
    ) -> List[str]:
        """提取时间洞察"""
        insight_ids = []
        
        if len(experiences) < 3:
            return insight_ids
        
        # 检查是否有进步趋势
        outcomes = [e.get("outcome", 0) for e in experiences]
        
        improving = all(
            outcomes[i] <= outcomes[i+1]
            for i in range(len(outcomes)-1)
        )
        
        declining = all(
            outcomes[i] >= outcomes[i+1]
            for i in range(len(outcomes)-1)
        )
        
        if improving:
            insight = Insight(
                insight_id=str(uuid.uuid4()),
                insight_type=InsightType.TEMPORAL,
                content="表现呈现持续改善趋势",
                confidence=0.7,
                novelty=0.3,
                utility=0.8,
                tags=["progression", "temporal"],
            )
            insight_ids.append(insight.insight_id)
            self._store_insight(insight)
        
        elif declining:
            insight = Insight(
                insight_id=str(uuid.uuid4()),
                insight_type=InsightType.TEMPORAL,
                content="表现呈现下降趋势，需要警惕",
                confidence=0.7,
                novelty=0.3,
                utility=0.8,
                tags=["regression", "temporal"],
            )
            insight_ids.append(insight.insight_id)
            self._store_insight(insight)
        
        return insight_ids
    
    def _extract_procedural_insights(
        self,
        experiences: List[Dict[str, Any]],
    ) -> List[str]:
        """提取过程洞察"""
        insight_ids = []
        
        # 分析成功经验的步骤
        success_experiences = [
            e for e in experiences
            if e.get("outcome", 0) > 0.3
        ]
        
        if success_experiences:
            # 提取共同步骤
            all_steps = []
            for exp in success_experiences:
                steps = exp.get("steps", [])
                all_steps.extend(steps)
            
            # 统计步骤出现频率
            step_counts: Dict[str, int] = {}
            for step in all_steps:
                step_counts[step] = step_counts.get(step, 0) + 1
            
            # 找出高频步骤
            common_steps = [
                step for step, count in step_counts.items()
                if count >= len(success_experiences) * 0.5
            ]
            
            if common_steps:
                insight = Insight(
                    insight_id=str(uuid.uuid4()),
                    insight_type=InsightType.PROCEDURAL,
                    content=f"成功经验通常包含: {', '.join(common_steps[:3])}",
                    source_experiences=[
                        e.get("id", "") for e in success_experiences
                    ],
                    confidence=0.7,
                    novelty=0.4,
                    utility=0.9,
                    tags=["procedure", "success"],
                )
                
                insight_ids.append(insight.insight_id)
                self._store_insight(insight)
        
        return insight_ids
    
    def _find_common_factors(
        self,
        experiences: List[Dict[str, Any]],
    ) -> List[str]:
        """找出共同因素"""
        if not experiences:
            return []
        
        # 简单实现：统计各因素出现次数
        factor_counts: Dict[str, int] = {}
        
        for exp in experiences:
            factors = exp.get("factors", [])
            for factor in factors:
                factor_counts[factor] = factor_counts.get(factor, 0) + 1
        
        # 返回出现次数较多的因素
        threshold = len(experiences) * 0.5
        return [
            factor for factor, count in factor_counts.items()
            if count >= threshold
        ]
    
    def _extract_elements(self, experience: Dict[str, Any]) -> List[str]:
        """提取元素"""
        elements = []
        
        # 从内容中提取
        content = experience.get("content", "")
        elements.extend(content.split())
        
        # 从标签中提取
        elements.extend(experience.get("tags", []))
        
        # 从上下文中提取
        context = experience.get("context", "")
        elements.extend(context.split())
        
        return elements
    
    def _store_insight(self, insight: Insight) -> None:
        """存储洞察"""
        self._insights[insight.insight_id] = insight
        
        # 更新索引
        for tag in insight.tags:
            if tag not in self._insight_index:
                self._insight_index[tag] = set()
            self._insight_index[tag].add(insight.insight_id)
    
    def get_insight(self, insight_id: str) -> Optional[Insight]:
        """获取洞察"""
        return self._insights.get(insight_id)
    
    def get_insights_by_tag(
        self,
        tag: str,
        min_score: float = 0.0,
    ) -> List[Insight]:
        """按标签获取洞察"""
        insight_ids = self._insight_index.get(tag, set())
        
        insights = []
        for insight_id in insight_ids:
            insight = self._insights.get(insight_id)
            if insight and insight.get_score() >= min_score:
                insights.append(insight)
        
        return sorted(insights, key=lambda i: i.get_score(), reverse=True)
    
    def get_top_insights(
        self,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> List[Insight]:
        """获取评分最高的洞察"""
        filtered = [
            i for i in self._insights.values()
            if i.get_score() >= min_score
        ]
        
        return sorted(
            filtered,
            key=lambda i: i.get_score(),
            reverse=True
        )[:limit]
    
    def update_insight_evaluation(
        self,
        insight_id: str,
        novelty: Optional[float] = None,
        utility: Optional[float] = None,
    ) -> bool:
        """更新洞察评估"""
        insight = self._insights.get(insight_id)
        if not insight:
            return False
        
        if novelty is not None:
            insight.novelty = novelty
        if utility is not None:
            insight.utility = utility
        
        return True
