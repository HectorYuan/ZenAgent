"""
经验分析器

深入分析经验模式和趋势
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import threading


class ExperiencePattern(Enum):
    """经验模式"""
    SUCCESS = "success"              # 成功模式
    FAILURE = "failure"              # 失败模式
    REPETITION = "repetition"        # 重复模式
    PROGRESSION = "progression"      # 进步模式
    REGRESSION = "regression"        # 退步模式
    CYCLIC = "cyclic"                # 循环模式


@dataclass
class TrendAnalysis:
    """趋势分析"""
    direction: str  # increasing, decreasing, stable
    slope: float
    volatility: float
    predictions: List[str] = field(default_factory=list)


@dataclass
class PatternMatch:
    """模式匹配"""
    pattern_type: ExperiencePattern
    confidence: float
    instances: List[str] = field(default_factory=list)
    description: str = ""


class ExperienceAnalyzer:
    """
    经验分析器
    
    分析经验数据，识别模式和趋势
    """
    
    def __init__(self, reflector=None):
        """
        初始化经验分析器
        
        Args:
            reflector: 反思引擎实例
        """
        self.reflector = reflector
        
        # 分析缓存
        self._analysis_cache: Dict[str, Any] = {}
        self._last_analysis: Optional[datetime] = None
        
        self._lock = threading.RLock()
    
    def analyze(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析经验
        
        Args:
            experience: 经验数据
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        with self._lock:
            result = {
                "experience_id": experience.get("id", ""),
                "timestamp": datetime.now().isoformat(),
            }
            
            # 基本分析
            result["outcome"] = self._analyze_outcome(experience)
            result["sentiment"] = self._analyze_sentiment(experience)
            
            # 模式识别
            result["patterns"] = self._identify_patterns(experience)
            
            # 关联分析
            result["associations"] = self._analyze_associations(experience)
            
            # 价值评估
            result["value_assessment"] = self._assess_value(experience)
            
            return result
    
    def _analyze_outcome(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        """分析结果"""
        outcome = experience.get("outcome", 0)
        
        if outcome > 0.5:
            label = "positive"
            description = "产生了积极的结果"
        elif outcome < -0.5:
            label = "negative"
            description = "产生了消极的结果"
        else:
            label = "neutral"
            description = "产生了中性的结果"
        
        return {
            "value": outcome,
            "label": label,
            "description": description,
        }
    
    def _analyze_sentiment(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        """分析情感"""
        content = experience.get("content", "")
        result = experience.get("result", "")
        
        # 简单的情感分析
        positive_words = ["success", "good", "great", "excellent", "happy"]
        negative_words = ["fail", "bad", "poor", "sad", "error"]
        
        pos_count = sum(1 for w in positive_words if w in (content + result).lower())
        neg_count = sum(1 for w in negative_words if w in (content + result).lower())
        
        if pos_count > neg_count:
            sentiment = 0.5
            label = "positive"
        elif neg_count > pos_count:
            sentiment = -0.5
            label = "negative"
        else:
            sentiment = 0.0
            label = "neutral"
        
        return {
            "value": sentiment,
            "label": label,
            "positive_signals": pos_count,
            "negative_signals": neg_count,
        }
    
    def _identify_patterns(
        self,
        experience: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """识别模式"""
        patterns = []
        
        outcome = experience.get("outcome", 0)
        tags = experience.get("tags", [])
        
        # 成功/失败模式
        if outcome > 0.3:
            patterns.append({
                "type": ExperiencePattern.SUCCESS.value,
                "confidence": abs(outcome),
                "description": "符合成功模式",
            })
        elif outcome < -0.3:
            patterns.append({
                "type": ExperiencePattern.FAILURE.value,
                "confidence": abs(outcome),
                "description": "符合失败模式",
            })
        
        # 重复模式
        if "repeated" in tags or "again" in tags:
            patterns.append({
                "type": ExperiencePattern.REPETITION.value,
                "confidence": 0.7,
                "description": "涉及重复尝试",
            })
        
        return patterns
    
    def _analyze_associations(
        self,
        experience: Dict[str, Any],
    ) -> List[str]:
        """分析关联"""
        associations = []
        
        # 与其他经验的关联
        related = experience.get("related_experiences", [])
        if related:
            associations.append(f"与 {len(related)} 个相关经验关联")
        
        # 与记忆的关联
        memory_refs = experience.get("memory_references", [])
        if memory_refs:
            associations.append(f"引用了 {len(memory_refs)} 个记忆")
        
        return associations
    
    def _assess_value(
        self,
        experience: Dict[str, Any],
    ) -> Dict[str, Any]:
        """评估价值"""
        outcome = experience.get("outcome", 0)
        novelty = experience.get("novelty", 0.5)
        learning = experience.get("learning", [])
        
        # 计算综合价值
        learning_value = len(learning) * 0.2
        outcome_value = outcome * 0.3
        novelty_value = novelty * 0.2
        
        total_value = (
            learning_value +
            outcome_value +
            novelty_value +
            0.3  # 基础价值
        )
        
        if total_value > 0.7:
            label = "high"
        elif total_value > 0.4:
            label = "medium"
        else:
            label = "low"
        
        return {
            "score": total_value,
            "label": label,
            "breakdown": {
                "learning": learning_value,
                "outcome": outcome_value,
                "novelty": novelty_value,
                "base": 0.3,
            },
        }
    
    def analyze_trends(
        self,
        experiences: List[Dict[str, Any]],
        metric: str = "outcome",
    ) -> TrendAnalysis:
        """
        分析趋势
        
        Args:
            experiences: 经验列表
            metric: 分析指标
            
        Returns:
            TrendAnalysis: 趋势分析结果
        """
        if not experiences:
            return TrendAnalysis(
                direction="stable",
                slope=0.0,
                volatility=0.0,
            )
        
        # 提取指标值
        values = []
        for exp in experiences:
            if metric in exp:
                values.append(float(exp[metric]))
        
        if len(values) < 2:
            return TrendAnalysis(
                direction="stable",
                slope=0.0,
                volatility=0.0,
            )
        
        # 计算斜率（简单线性回归）
        n = len(values)
        x_mean = sum(range(n)) / n
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # 确定方向
        if slope > 0.1:
            direction = "increasing"
        elif slope < -0.1:
            direction = "decreasing"
        else:
            direction = "stable"
        
        # 计算波动性
        mean_val = sum(values) / len(values)
        variance = sum((v - mean_val) ** 2 for v in values) / len(values)
        volatility = variance ** 0.5
        
        # 生成预测
        predictions = []
        if direction == "increasing":
            predictions.append("预计表现将继续改善")
        elif direction == "decreasing":
            predictions.append("需要注意可能的退步")
        else:
            predictions.append("表现趋于稳定")
        
        return TrendAnalysis(
            direction=direction,
            slope=slope,
            volatility=volatility,
            predictions=predictions,
        )
    
    def find_similar_experiences(
        self,
        experience: Dict[str, Any],
        all_experiences: List[Dict[str, Any]],
        limit: int = 5,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        查找相似经验
        
        Args:
            experience: 目标经验
            all_experiences: 所有经验
            limit: 返回数量
            
        Returns:
            List[Tuple[Dict, float]]: (经验, 相似度)
        """
        target_content = experience.get("content", "").lower()
        target_words = set(target_content.split())
        
        similarities = []
        
        for exp in all_experiences:
            if exp.get("id") == experience.get("id"):
                continue
            
            exp_content = exp.get("content", "").lower()
            exp_words = set(exp_content.split())
            
            # 计算 Jaccard 相似度
            if target_words and exp_words:
                intersection = len(target_words & exp_words)
                union = len(target_words | exp_words)
                similarity = intersection / union if union > 0 else 0
            else:
                similarity = 0
            
            similarities.append((exp, similarity))
        
        # 排序并返回
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]
    
    def generate_insights_report(
        self,
        experiences: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        生成洞察报告
        
        Args:
            experiences: 经验列表
            
        Returns:
            Dict[str, Any]: 洞察报告
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "experience_count": len(experiences),
            "trends": {},
            "patterns": [],
            "insights": [],
        }
        
        # 趋势分析
        report["trends"]["outcome"] = self.analyze_trends(
            experiences, "outcome"
        ).__dict__
        
        # 模式统计
        pattern_counts: Dict[str, int] = {}
        for exp in experiences:
            patterns = self._identify_patterns(exp)
            for pattern in patterns:
                ptype = pattern["type"]
                pattern_counts[ptype] = pattern_counts.get(ptype, 0) + 1
        
        report["patterns"] = [
            {"type": k, "count": v}
            for k, v in pattern_counts.items()
        ]
        
        # 生成洞察
        positive_count = sum(
            1 for e in experiences if e.get("outcome", 0) > 0.3
        )
        negative_count = sum(
            1 for e in experiences if e.get("outcome", 0) < -0.3
        )
        
        if positive_count > negative_count:
            report["insights"].append("整体表现偏向积极")
        elif negative_count > positive_count:
            report["insights"].append("存在需要改进的领域")
        
        return report
