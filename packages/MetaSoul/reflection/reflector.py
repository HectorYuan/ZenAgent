"""
反思引擎

反思和经验分析的核心实现
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import threading
import uuid


class ReflectionDepth(Enum):
    """反思深度"""
    SURFACE = "surface"      # 表面反思 - 发生了什么
    CAUSAL = "causal"        # 因果反思 - 为什么发生
    MEANING = "meaning"      # 意义反思 - 意味着什么
    TRANSFORMATIVE = "transformative"  # 变革反思 - 如何改变


@dataclass
class ReflectionResult:
    """反思结果"""
    reflection_id: str
    timestamp: datetime
    depth: ReflectionDepth
    
    # 反思内容
    experience_summary: str
    causes_identified: List[str] = field(default_factory=list)
    effects_observed: List[str] = field(default_factory=list)
    
    # 洞察
    insights: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    
    # 行动建议
    suggested_actions: List[str] = field(default_factory=list)
    
    # 元数据
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


class Reflector:
    """
    反思引擎
    
    实现深度反思功能
    """
    
    def __init__(
        self,
        meta_soul=None,
        knowledge_graph=None,
    ):
        """
        初始化反思引擎
        
        Args:
            meta_soul: MetaSoul 实例
            knowledge_graph: 知识图谱
        """
        self.meta_soul = meta_soul
        self.knowledge_graph = knowledge_graph
        
        # 反思历史
        self._reflections: Dict[str, ReflectionResult] = {}
        
        # 回调
        self._on_reflection_complete: List[callable] = []
        
        self._lock = threading.RLock()
    
    def reflect(
        self,
        experience: Dict[str, Any],
        depth: ReflectionDepth = ReflectionDepth.SURFACE,
    ) -> Dict[str, Any]:
        """
        反思经验
        
        Args:
            experience: 经验数据
            depth: 反思深度
            
        Returns:
            Dict[str, Any]: 反思结果
        """
        with self._lock:
            # 执行反思
            result = self._perform_reflection(experience, depth)
            
            # 存储结果
            self._reflections[result.reflection_id] = result
            
            # 整合到 MetaSoul
            if self.meta_soul:
                self._integrate_reflection(result)
            
            # 触发回调
            for callback in self._on_reflection_complete:
                try:
                    callback(result)
                except Exception:
                    pass
            
            return {
                "reflection_id": result.reflection_id,
                "depth": result.depth.value,
                "insights": result.insights,
                "lessons_learned": result.lessons_learned,
                "suggested_actions": result.suggested_actions,
                "causes_identified": result.causes_identified,
                "effects_observed": result.effects_observed,
            }
    
    def _perform_reflection(
        self,
        experience: Dict[str, Any],
        depth: ReflectionDepth,
    ) -> ReflectionResult:
        """执行反思"""
        reflection_id = str(uuid.uuid4())
        
        # 经验摘要
        experience_summary = self._summarize_experience(experience)
        
        # 根据深度执行不同的反思
        if depth == ReflectionDepth.SURFACE:
            causes = []
            effects = []
            insights = []
        elif depth == ReflectionDepth.CAUSAL:
            causes = self._analyze_causes(experience)
            effects = self._analyze_effects(experience)
            insights = []
        elif depth == ReflectionDepth.MEANING:
            causes = self._analyze_causes(experience)
            effects = self._analyze_effects(experience)
            insights = self._extract_meaning(experience)
        else:  # TRANSFORMATIVE
            causes = self._analyze_causes(experience)
            effects = self._analyze_effects(experience)
            insights = self._extract_meaning(experience)
        
        # 提取教训
        lessons = self._extract_lessons(experience, causes, effects)
        
        # 生成行动建议
        actions = self._generate_actions(experience, lessons)
        
        return ReflectionResult(
            reflection_id=reflection_id,
            timestamp=datetime.now(),
            depth=depth,
            experience_summary=experience_summary,
            causes_identified=causes,
            effects_observed=effects,
            insights=insights,
            lessons_learned=lessons,
            suggested_actions=actions,
            confidence=0.6,
        )
    
    def _summarize_experience(self, experience: Dict[str, Any]) -> str:
        """总结经验"""
        context = experience.get("context", "")
        action = experience.get("action", "")
        result = experience.get("result", "")
        
        return f"{context} -> {action} -> {result}"
    
    def _analyze_causes(self, experience: Dict[str, Any]) -> List[str]:
        """分析原因"""
        causes = []
        
        # 简单分析：基于经验中的关键词
        context = experience.get("context", "").lower()
        action = experience.get("action", "").lower()
        result = experience.get("result", "").lower()
        
        if "because" in context or "due to" in context:
            causes.append("存在明确的因果说明")
        
        if "failed" in result or "error" in result:
            causes.append("可能存在执行问题")
        
        # 检查 MetaSoul 中的相关记忆
        if self.meta_soul:
            related = self.meta_soul.retrieve(
                query=context,
                limit=3,
            )
            if related:
                causes.append(f"与 {len(related)} 个相关记忆关联")
        
        return causes
    
    def _analyze_effects(self, experience: Dict[str, Any]) -> List[str]:
        """分析影响"""
        effects = []
        
        result = experience.get("result", "")
        outcome = experience.get("outcome", 0)
        
        if outcome > 0:
            effects.append("产生了正面影响")
        elif outcome < 0:
            effects.append("产生了负面影响")
        
        # 检查是否创建了新知识
        learning = experience.get("learning", [])
        if learning:
            effects.append(f"产生了 {len(learning)} 个新学习点")
        
        return effects
    
    def _extract_meaning(self, experience: Dict[str, Any]) -> List[str]:
        """提取意义"""
        meanings = []
        
        outcome = experience.get("outcome", 0)
        context = experience.get("context", "")
        
        if outcome > 0.5:
            meanings.append("这是一个成功的经验，验证了当前方法的有效性")
        elif outcome < -0.5:
            meanings.append("这是一个重要的失败经验，提供了改进的机会")
        
        # 基于上下文提取更深层的意义
        if "first" in context.lower() or "new" in context.lower():
            meanings.append("这是一个探索性经验，拓展了认知边界")
        
        return meanings
    
    def _extract_lessons(
        self,
        experience: Dict[str, Any],
        causes: List[str],
        effects: List[str],
    ) -> List[str]:
        """提取教训"""
        lessons = []
        
        outcome = experience.get("outcome", 0)
        
        if outcome > 0:
            lessons.append("当前方法有效，应继续使用")
        elif outcome < 0:
            lessons.append("需要调整方法或策略")
        
        # 从原因中提取教训
        for cause in causes:
            if "执行问题" in cause:
                lessons.append("需要提高执行准确性")
        
        # 从效果中提取教训
        for effect in effects:
            if "新学习点" in effect:
                lessons.append("每次经验都是学习的机会")
        
        return lessons
    
    def _generate_actions(
        self,
        experience: Dict[str, Any],
        lessons: List[str],
    ) -> List[str]:
        """生成行动建议"""
        actions = []
        
        outcome = experience.get("outcome", 0)
        
        if outcome > 0:
            actions.append("巩固当前方法")
            actions.append("尝试在其他场景应用")
        elif outcome < 0:
            actions.append("分析失败原因")
            actions.append("制定改进计划")
        
        # 基于教训生成行动
        for lesson in lessons:
            if "调整" in lesson:
                actions.append("实践新的调整方案")
            if "学习" in lesson:
                actions.append("记录并分享经验")
        
        return actions[:3]  # 最多3个行动
    
    def _integrate_reflection(self, result: ReflectionResult) -> None:
        """整合反思到 MetaSoul"""
        if not self.meta_soul:
            return
        
        # 存储反思记忆
        content = f"反思: {result.experience_summary}"
        if result.insights:
            content += f"\n洞察: {'; '.join(result.insights)}"
        if result.lessons_learned:
            content += f"\n教训: {'; '.join(result.lessons_learned)}"
        
        # 存储为语义记忆
        from ..memory.meta_soul import MemoryType, MemoryImportance
        self.meta_soul.store_memory(
            content=content,
            memory_type=MemoryType.SEMANTIC,
            importance=MemoryImportance.HIGH,
        )
    
    def get_recent_reflections(
        self,
        limit: int = 10,
    ) -> List[ReflectionResult]:
        """获取最近的反思"""
        reflections = sorted(
            self._reflections.values(),
            key=lambda r: r.timestamp,
            reverse=True
        )
        return reflections[:limit]
    
    def get_insights_from_reflections(
        self,
        min_confidence: float = 0.5,
    ) -> List[str]:
        """从反思中获取洞察"""
        insights = []
        
        for reflection in self._reflections.values():
            if reflection.confidence >= min_confidence:
                insights.extend(reflection.insights)
        
        return insights
    
    def on_reflection_complete(self, callback: callable) -> None:
        """注册反思完成回调"""
        self._on_reflection_complete.append(callback)
