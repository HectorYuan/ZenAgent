"""
反馈处理器

内部反馈和外部反馈的处理
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import threading
import uuid


class FeedbackSource(Enum):
    """反馈来源"""
    INTERNAL = "internal"    # 内部反馈 - 自我评估
    EXTERNAL = "external"    # 外部反馈 - 环境或用户
    PEER = "peer"            # 同伴反馈 - 其他Agent
    SYSTEM = "system"        # 系统反馈 - 自动评估


class FeedbackType(Enum):
    """反馈类型"""
    REINFORCEMENT = "reinforcement"  # 正向强化
    CORRECTION = "correction"        # 纠正
    NOVEL = "novel"                 # 新信息
    WARNING = "warning"             # 警告
    QUESTION = "question"          # 质疑


@dataclass
class Feedback:
    """反馈数据"""
    feedback_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 反馈内容
    source: FeedbackSource = FeedbackSource.INTERNAL
    feedback_type: FeedbackType = FeedbackType.REINFORCEMENT
    content: str = ""
    
    # 关联
    target_id: str = ""  # 关联的目标 ID
    context: str = ""    # 上下文
    
    # 评估
    weight: float = 1.0   # 权重
    reliability: float = 1.0  # 可靠性
    sentiment: float = 0.0    # 情感倾向 (-1 to 1)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedFeedback:
    """处理后的反馈"""
    original: Feedback
    processed_at: datetime = field(default_factory=datetime.now)
    
    # 处理结果
    applicable: bool = True
    adjusted_weight: float = 1.0
    confidence_impact: float = 0.0
    
    # 影响的知识
    affected_knowledge: List[str] = field(default_factory=list)
    insights_generated: List[str] = field(default_factory=list)
    
    # 建议
    suggested_actions: List[str] = field(default_factory=list)


class FeedbackProcessor:
    """
    反馈处理器
    
    处理和整合来自不同来源的反馈
    """
    
    def __init__(self, learner):
        """
        初始化反馈处理器
        
        Args:
            learner: 学习器实例
        """
        self.learner = learner
        
        # 反馈存储
        self._feedback_history: List[Feedback] = []
        self._processed_history: List[ProcessedFeedback] = []
        
        # 统计
        self._feedback_by_source: Dict[FeedbackSource, int] = {}
        self._feedback_by_type: Dict[FeedbackType, int] = {}
        
        # 锁
        self._lock = threading.RLock()
        
        # 回调
        self._on_feedback_processed: List[callable] = []
    
    def process(self, feedback: Feedback) -> Dict[str, Any]:
        """
        处理反馈
        
        Args:
            feedback: 反馈数据
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        with self._lock:
            # 记录原始反馈
            self._feedback_history.append(feedback)
            
            # 更新统计
            self._feedback_by_source[feedback.source] = (
                self._feedback_by_source.get(feedback.source, 0) + 1
            )
            self._feedback_by_type[feedback.feedback_type] = (
                self._feedback_by_type.get(feedback.feedback_type, 0) + 1
            )
            
            # 处理反馈
            processed = self._process_feedback(feedback)
            
            # 记录处理结果
            self._processed_history.append(processed)
            
            # 应用到学习器
            self._apply_to_learner(processed)
            
            # 触发回调
            for callback in self._on_feedback_processed:
                try:
                    callback(processed)
                except Exception:
                    pass
            
            return {
                "feedback_id": feedback.feedback_id,
                "processed": processed.applicable,
                "confidence_delta": processed.confidence_impact,
                "insights": processed.insights_generated,
            }
    
    def _process_feedback(self, feedback: Feedback) -> ProcessedFeedback:
        """处理单个反馈"""
        processed = ProcessedFeedback(
            original=feedback,
        )
        
        # 评估适用性
        processed.applicable = self._evaluate_applicability(feedback)
        
        # 调整权重
        processed.adjusted_weight = self._adjust_weight(feedback)
        
        # 计算置信度影响
        processed.confidence_impact = self._calculate_impact(
            feedback, processed.adjusted_weight
        )
        
        # 生成洞察
        processed.insights_generated = self._generate_insights(feedback)
        
        # 生成建议
        processed.suggested_actions = self._suggest_actions(feedback)
        
        return processed
    
    def _evaluate_applicability(self, feedback: Feedback) -> bool:
        """评估反馈适用性"""
        # 检查可靠性
        if feedback.reliability < 0.3:
            return False
        
        # 检查权重
        if feedback.weight < 0.1:
            return False
        
        # 检查上下文
        if not feedback.context and feedback.source == FeedbackSource.INTERNAL:
            return False
        
        return True
    
    def _adjust_weight(self, feedback: Feedback) -> float:
        """调整权重"""
        weight = feedback.weight
        
        # 基于可靠性调整
        weight *= feedback.reliability
        
        # 基于来源调整
        source_weights = {
            FeedbackSource.SYSTEM: 1.0,
            FeedbackSource.EXTERNAL: 0.9,
            FeedbackSource.PEER: 0.7,
            FeedbackSource.INTERNAL: 0.5,
        }
        weight *= source_weights.get(feedback.source, 0.5)
        
        # 基于类型调整
        type_weights = {
            FeedbackType.CORRECTION: 1.2,  # 纠正更受重视
            FeedbackType.REINFORCEMENT: 1.0,
            FeedbackType.NOVEL: 1.1,
            FeedbackType.WARNING: 0.9,
            FeedbackType.QUESTION: 0.8,
        }
        weight *= type_weights.get(feedback.feedback_type, 1.0)
        
        return max(0.0, min(weight, 2.0))
    
    def _calculate_impact(
        self,
        feedback: Feedback,
        adjusted_weight: float,
    ) -> float:
        """计算置信度影响"""
        impact = 0.0
        
        # 基于类型的影响
        type_impacts = {
            FeedbackType.REINFORCEMENT: 0.1,
            FeedbackType.CORRECTION: -0.1,
            FeedbackType.NOVEL: 0.15,
            FeedbackType.WARNING: -0.05,
            FeedbackType.QUESTION: 0.0,
        }
        impact += type_impacts.get(feedback.feedback_type, 0.0)
        
        # 考虑权重和可靠性
        impact *= adjusted_weight
        
        return impact
    
    def _generate_insights(self, feedback: Feedback) -> List[str]:
        """生成洞察"""
        insights = []
        
        if feedback.feedback_type == FeedbackType.CORRECTION:
            insights.append(f"需要修正: {feedback.content}")
        elif feedback.feedback_type == FeedbackType.NOVEL:
            insights.append(f"新信息: {feedback.content}")
        elif feedback.feedback_type == FeedbackType.WARNING:
            insights.append(f"注意: {feedback.content}")
        
        # 基于情感生成洞察
        if feedback.sentiment > 0.5:
            insights.append("积极反馈 - 继续当前方向")
        elif feedback.sentiment < -0.5:
            insights.append("消极反馈 - 需要调整策略")
        
        return insights
    
    def _suggest_actions(self, feedback: Feedback) -> List[str]:
        """建议行动"""
        suggestions = []
        
        if feedback.feedback_type == FeedbackType.CORRECTION:
            suggestions.append("更新相关知识")
            suggestions.append("调整行为模式")
        elif feedback.feedback_type == FeedbackType.NOVEL:
            suggestions.append("学习新信息")
            suggestions.append("整合到知识库")
        elif feedback.feedback_type == FeedbackType.WARNING:
            suggestions.append("警惕类似情况")
            suggestions.append("制定预防措施")
        
        return suggestions
    
    def _apply_to_learner(self, processed: ProcessedFeedback) -> None:
        """应用到学习器"""
        # 这里可以触发学习器的更新
        pass
    
    def create_internal_feedback(
        self,
        content: str,
        feedback_type: FeedbackType,
        target_id: str = "",
        context: str = "",
    ) -> Feedback:
        """
        创建内部反馈
        
        Args:
            content: 内容
            feedback_type: 反馈类型
            target_id: 目标 ID
            context: 上下文
            
        Returns:
            Feedback: 反馈对象
        """
        return Feedback(
            source=FeedbackSource.INTERNAL,
            feedback_type=feedback_type,
            content=content,
            target_id=target_id,
            context=context,
            reliability=0.7,  # 内部反馈可靠性较低
        )
    
    def create_external_feedback(
        self,
        content: str,
        feedback_type: FeedbackType,
        reliability: float = 1.0,
        **kwargs
    ) -> Feedback:
        """
        创建外部反馈
        
        Args:
            content: 内容
            feedback_type: 反馈类型
            reliability: 可靠性
            **kwargs: 其他参数
            
        Returns:
            Feedback: 反馈对象
        """
        return Feedback(
            source=FeedbackSource.EXTERNAL,
            feedback_type=feedback_type,
            content=content,
            reliability=reliability,
            **kwargs
        )
    
    def get_feedback_history(
        self,
        source: Optional[FeedbackSource] = None,
        feedback_type: Optional[FeedbackType] = None,
        limit: int = 100,
    ) -> List[Feedback]:
        """
        获取反馈历史
        
        Args:
            source: 来源过滤
            feedback_type: 类型过滤
            limit: 数量限制
            
        Returns:
            List[Feedback]: 反馈列表
        """
        results = self._feedback_history
        
        if source:
            results = [f for f in results if f.source == source]
        
        if feedback_type:
            results = [f for f in results if f.feedback_type == feedback_type]
        
        return results[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_feedback": len(self._feedback_history),
            "processed_feedback": len(self._processed_history),
            "by_source": {
                source.value: count 
                for source, count in self._feedback_by_source.items()
            },
            "by_type": {
                ftype.value: count 
                for ftype, count in self._feedback_by_type.items()
            },
        }
    
    def on_feedback_processed(self, callback: callable) -> None:
        """注册反馈处理回调"""
        self._on_feedback_processed.append(callback)
