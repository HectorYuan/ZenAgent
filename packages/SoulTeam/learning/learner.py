"""
学习器核心

观察、反思、归纳、验证循环的实现
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import threading
import uuid


class LearningCycle(Enum):
    """学习循环阶段"""
    OBSERVE = "observe"    # 观察 - 收集信息
    REFLECT = "reflect"   # 反思 - 分析理解
    GENERALIZE = "generalize"  # 归纳 - 提取模式
    VERIFY = "verify"     # 验证 - 测试假设
    INTEGRATE = "integrate"  # 整合 - 更新知识


@dataclass
class LearningResult:
    """学习结果"""
    success: bool
    new_knowledge: List[str] = field(default_factory=list)
    modified_beliefs: List[str] = field(default_factory=list)
    skills_acquired: List[str] = field(default_factory=list)
    confidence_delta: float = 0.0
    insights: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Observation:
    """观察记录"""
    observation_id: str
    timestamp: datetime
    content: str
    source: str = ""
    reliability: float = 1.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Reflection:
    """反思记录"""
    reflection_id: str
    timestamp: datetime
    observation_ids: List[str]
    analysis: str
    patterns_identified: List[str] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class Generalization:
    """归纳结果"""
    generalization_id: str
    timestamp: datetime
    source_reflection_ids: List[str]
    statement: str
    conditions: List[str] = field(default_factory=list)
    exceptions: List[str] = field(default_factory=list)
    strength: float = 0.5


class SelfLearner:
    """
    自学习器
    
    实现观察、反思、归纳、验证的学习循环
    """
    
    def __init__(
        self,
        soul_id: str,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化学习器
        
        Args:
            soul_id: 灵魂 ID
            config: 配置
        """
        self.soul_id = soul_id
        self.config = config or {}
        
        # 学习阶段
        self._observations: Dict[str, Observation] = {}
        self._reflections: Dict[str, Reflection] = {}
        self._generalizations: Dict[str, Generalization] = {}
        
        # 学习统计
        self._cycle_count = 0
        self._total_learnings = 0
        self._current_cycle: Optional[LearningCycle] = None
        
        # 锁
        self._lock = threading.RLock()
        
        # 回调
        self._on_learning_complete: List[callable] = []
        self._on_insight: List[callable] = []
    
    def learn(
        self,
        experience: Dict[str, Any],
        feedback: Optional[Dict[str, Any]] = None,
    ) -> LearningResult:
        """
        学习经验
        
        Args:
            experience: 经验数据
            feedback: 反馈数据
            
        Returns:
            LearningResult: 学习结果
        """
        with self._lock:
            result = LearningResult(success=False)
            
            try:
                # 1. 观察阶段
                observation = self._observe(experience)
                result.metadata["observation_id"] = observation.observation_id
                
                # 2. 反思阶段
                reflection = self._reflect([observation])
                result.metadata["reflection_id"] = reflection.reflection_id
                
                # 3. 归纳阶段
                generalization = self._generalize([reflection])
                if generalization:
                    result.metadata["generalization_id"] = generalization.generalization_id
                    result.new_knowledge.append(generalization.statement)
                
                # 4. 整合阶段
                integration = self._integrate(generalization)
                if integration:
                    result.modified_beliefs.extend(integration)
                
                # 处理反馈
                if feedback:
                    feedback_result = self._process_feedback(feedback)
                    result.confidence_delta = feedback_result.get("confidence_delta", 0)
                    result.insights.extend(feedback_result.get("insights", []))
                
                # 验证假设
                if reflection.hypotheses:
                    verification = self._verify(reflection.hypotheses)
                    result.insights.extend(verification)
                
                result.success = True
                self._cycle_count += 1
                self._total_learnings += 1
                
            except Exception as e:
                result.errors.append(str(e))
            
            # 触发回调
            for callback in self._on_learning_complete:
                try:
                    callback(result)
                except Exception:
                    pass
            
            return result
    
    def _observe(self, experience: Dict[str, Any]) -> Observation:
        """
        观察阶段
        
        Args:
            experience: 经验数据
            
        Returns:
            Observation: 观察记录
        """
        self._current_cycle = LearningCycle.OBSERVE
        
        observation = Observation(
            observation_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            content=experience.get("content", str(experience)),
            source=experience.get("source", "direct"),
            reliability=experience.get("reliability", 1.0),
            tags=experience.get("tags", []),
            metadata=experience.get("metadata", {}),
        )
        
        self._observations[observation.observation_id] = observation
        return observation
    
    def _reflect(
        self,
        observations: List[Observation],
    ) -> Reflection:
        """
        反思阶段
        
        Args:
            observations: 观察列表
            
        Returns:
            Reflection: 反思记录
        """
        self._current_cycle = LearningCycle.REFLECT
        
        # 简单分析：识别模式
        patterns = self._identify_patterns(observations)
        
        # 生成假设
        hypotheses = self._generate_hypotheses(patterns)
        
        reflection = Reflection(
            reflection_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            observation_ids=[o.observation_id for o in observations],
            analysis=self._analyze_content(observations),
            patterns_identified=patterns,
            hypotheses=hypotheses,
            confidence=sum(o.reliability for o in observations) / len(observations),
        )
        
        self._reflections[reflection.reflection_id] = reflection
        return reflection
    
    def _generalize(
        self,
        reflections: List[Reflection],
    ) -> Optional[Generalization]:
        """
        归纳阶段
        
        Args:
            reflections: 反思列表
            
        Returns:
            Optional[Generalization]: 归纳结果
        """
        self._current_cycle = LearningCycle.GENERALIZE
        
        if not reflections:
            return None
        
        # 合并所有模式
        all_patterns = []
        for reflection in reflections:
            all_patterns.extend(reflection.patterns_identified)
        
        if not all_patterns:
            return None
        
        # 生成泛化陈述
        statement = f"基于 {len(reflections)} 个反思：{'；'.join(all_patterns[:3])}"
        
        generalization = Generalization(
            generalization_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            source_reflection_ids=[r.reflection_id for r in reflections],
            statement=statement,
            conditions=self._extract_conditions(all_patterns),
            strength=sum(r.confidence for r in reflections) / len(reflections),
        )
        
        self._generalizations[generalization.generalization_id] = generalization
        return generalization
    
    def _verify(
        self,
        hypotheses: List[str],
    ) -> List[str]:
        """
        验证假设
        
        Args:
            hypotheses: 假设列表
            
        Returns:
            List[str]: 验证结果
        """
        self._current_cycle = LearningCycle.VERIFY
        
        verified = []
        for hypothesis in hypotheses:
            # 简单验证：检查是否与已知知识冲突
            if not self._conflicts_with_knowledge(hypothesis):
                verified.append(f"已验证: {hypothesis}")
            else:
                verified.append(f"待检验: {hypothesis}")
        
        return verified
    
    def _integrate(
        self,
        generalization: Optional[Generalization],
    ) -> List[str]:
        """
        整合阶段
        
        Args:
            generalization: 归纳结果
            
        Returns:
            List[str]: 更新的信念列表
        """
        self._current_cycle = LearningCycle.INTEGRATE
        
        modified = []
        
        if generalization:
            # 检查是否需要更新现有泛化
            for existing_id, existing in self._generalizations.items():
                if self._is_contradiction(existing, generalization):
                    modified.append(f"更新: {existing_id} -> {generalization.statement}")
            modified.append(f"新增: {generalization.generalization_id}")
        
        return modified
    
    def _process_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理反馈
        
        Args:
            feedback: 反馈数据
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        feedback_type = feedback.get("type", "correction")
        content = feedback.get("content", "")
        weight = feedback.get("weight", 1.0)
        
        result = {
            "confidence_delta": 0.0,
            "insights": [],
        }
        
        if feedback_type == "correction":
            result["confidence_delta"] = -0.1 * weight
            result["insights"].append(f"纠正: {content}")
        elif feedback_type == "reinforcement":
            result["confidence_delta"] = 0.1 * weight
            result["insights"].append(f"强化: {content}")
        elif feedback_type == "novel":
            result["confidence_delta"] = 0.2 * weight
            result["insights"].append(f"新知: {content}")
        
        return result
    
    def _identify_patterns(
        self,
        observations: List[Observation],
    ) -> List[str]:
        """识别模式"""
        patterns = []
        
        # 简单的模式识别
        for obs in observations:
            tags = obs.tags
            if "success" in tags:
                patterns.append("成功模式")
            if "failure" in tags:
                patterns.append("失败模式")
            if "repeated" in tags:
                patterns.append("重复模式")
        
        return patterns
    
    def _generate_hypotheses(self, patterns: List[str]) -> List[str]:
        """生成假设"""
        hypotheses = []
        
        for pattern in patterns[:2]:  # 最多2个假设
            hypotheses.append(f"假设: {pattern} 可能导致后续结果")
        
        return hypotheses
    
    def _analyze_content(
        self,
        observations: List[Observation],
    ) -> str:
        """分析内容"""
        contents = [o.content for o in observations]
        return f"分析: 观察到 {len(contents)} 个事件"
    
    def _extract_conditions(self, patterns: List[str]) -> List[str]:
        """提取条件"""
        return [f"条件: {p}" for p in patterns[:2]]
    
    def _conflicts_with_knowledge(self, hypothesis: str) -> bool:
        """检查是否与知识冲突"""
        # 简单实现
        return False
    
    def _is_contradiction(
        self,
        gen1: Generalization,
        gen2: Generalization,
    ) -> bool:
        """检查两个泛化是否矛盾"""
        # 简单实现：检查条件是否相反
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "soul_id": self.soul_id,
            "cycle_count": self._cycle_count,
            "total_learnings": self._total_learnings,
            "observations": len(self._observations),
            "reflections": len(self._reflections),
            "generalizations": len(self._generalizations),
            "current_cycle": self._current_cycle.value if self._current_cycle else None,
        }
    
    def on_learning_complete(self, callback: callable) -> None:
        """注册学习完成回调"""
        self._on_learning_complete.append(callback)
    
    def on_insight(self, callback: callable) -> None:
        """注册洞察回调"""
        self._on_insight.append(callback)
