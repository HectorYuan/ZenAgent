"""
趋势卷积 (Trend Convolv)

将多个维度的趋势进行卷积运算，生成涌现模式。
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConvolvConfig:
    """卷积配置"""
    convolution_window: int = 3  # 卷积窗口大小
    interaction_strength: float = 0.5  # 交互强度
    threshold: float = 0.6  # 涌现阈值
    decay_factor: float = 0.9  # 衰减因子


@dataclass
class ConvolvResult:
    """卷积结果"""
    pattern_id: str
    name: str
    description: str
    source_trends: List[str]  # 源趋势ID
    intensity: float  # 强度 0-1
    confidence: float  # 置信度
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendVector:
    """趋势向量"""
    trend_id: str
    dimension: str  # 维度: tech, market, behavior
    score: float
    velocity: float  # 变化速度
    keywords: List[str] = field(default_factory=list)


class TrendConvolv:
    """
    趋势卷积器
    
    将不同维度的趋势进行卷积，识别潜在的涌现模式。
    
    原理:
    - 将趋势映射为向量
    - 计算向量间的交互作用
    - 生成复合趋势模式
    """
    
    def __init__(self, config: Optional[ConvolvConfig] = None):
        self.config = config or ConvolvConfig()
        
        # 维度权重
        self.dimension_weights = {
            'tech': 0.4,
            'market': 0.3,
            'behavior': 0.3
        }
        
        # 历史结果
        self.patterns: Dict[str, ConvolvResult] = {}
    
    def convolve(
        self,
        tech_trends: List[Any],
        market_trends: List[Any],
        behavior_trends: List[Any]
    ) -> List[ConvolvResult]:
        """
        执行趋势卷积
        
        Args:
            tech_trends: 技术趋势
            market_trends: 市场趋势
            behavior_trends: 行为趋势
            
        Returns:
            List[ConvolvResult]: 涌现模式
        """
        results = []
        
        # 处理全空输入情况
        if not tech_trends and not market_trends and not behavior_trends:
            logger.warning(
                "All trend inputs are empty. No patterns can be generated."
            )
            return results
        
        # 记录单维度为空的情况
        if not tech_trends:
            logger.warning("Tech trends input is empty, skipping tech-related patterns")
        if not market_trends:
            logger.warning("Market trends input is empty, skipping market-related patterns")
        if not behavior_trends:
            logger.warning("Behavior trends input is empty, skipping behavior-related patterns")
        
        # 转换为趋势向量
        tech_vectors = [self._to_vector(t, 'tech') for t in tech_trends]
        market_vectors = [self._to_vector(t, 'market') for t in market_trends]
        behavior_vectors = [self._to_vector(t, 'behavior') for t in behavior_trends]
        
        # 执行跨维度卷积
        cross_patterns = self._cross_dimension_convolution(
            tech_vectors, market_vectors
        )
        results.extend(cross_patterns)
        
        # 三维度卷积
        tri_patterns = self._triple_dimension_convolution(
            tech_vectors, market_vectors, behavior_vectors
        )
        results.extend(tri_patterns)
        
        # 同维度内卷积
        for dim_vectors, dim_name in [
            (tech_vectors, 'tech'),
            (market_vectors, 'market'),
            (behavior_vectors, 'behavior')
        ]:
            intra_patterns = self._intra_dimension_convolution(
                dim_vectors, dim_name
            )
            results.extend(intra_patterns)
        
        # 过滤低强度模式
        results = [r for r in results if r.intensity >= self.config.threshold]
        
        # 存储结果
        for pattern in results:
            self.patterns[pattern.pattern_id] = pattern
        
        return results
    
    def _to_vector(self, trend: Any, dimension: str) -> TrendVector:
        """将趋势转换为向量"""
        return TrendVector(
            trend_id=getattr(trend, 'trend_id', str(id(trend))),
            dimension=dimension,
            score=getattr(trend, 'score', 50) / 100,  # 归一化
            velocity=getattr(trend, 'velocity', 0) / 100,
            keywords=getattr(trend, 'keywords', [])
        )
    
    def _cross_dimension_convolution(
        self,
        vectors1: List[TrendVector],
        vectors2: List[TrendVector]
    ) -> List[ConvolvResult]:
        """跨维度卷积"""
        patterns = []
        
        for v1 in vectors1:
            for v2 in vectors2:
                # 计算交互强度
                interaction = self._calculate_interaction(v1, v2)
                
                if interaction >= self.config.threshold:
                    pattern = ConvolvResult(
                        pattern_id=f"cross_{v1.trend_id}_{v2.trend_id}",
                        name=f"{v1.dimension}-{v2.dimension} Interaction",
                        description=f"Interaction between {v1.dimension} and {v2.dimension} trends",
                        source_trends=[v1.trend_id, v2.trend_id],
                        intensity=interaction,
                        confidence=self._calculate_confidence(interaction),
                        metadata={
                            'dimension1': v1.dimension,
                            'dimension2': v2.dimension,
                            'score1': v1.score,
                            'score2': v2.score
                        }
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _triple_dimension_convolution(
        self,
        tech: List[TrendVector],
        market: List[TrendVector],
        behavior: List[TrendVector]
    ) -> List[ConvolvResult]:
        """三维度卷积"""
        patterns = []
        
        # 选择每个维度的代表性趋势
        top_tech = max(tech, key=lambda v: v.score) if tech else None
        top_market = max(market, key=lambda v: v.score) if market else None
        top_behavior = max(behavior, key=lambda v: v.score) if behavior else None
        
        if all([top_tech, top_market, top_behavior]):
            # 计算三方交互
            interaction = (
                top_tech.score * self.dimension_weights['tech'] +
                top_market.score * self.dimension_weights['market'] +
                top_behavior.score * self.dimension_weights['behavior']
            ) * self.config.interaction_strength
            
            # 检查关键词重叠
            common_keywords = set(top_tech.keywords) & set(top_market.keywords) & set(top_behavior.keywords)
            if common_keywords:
                interaction *= 1.2  # 关键词重叠增加强度
            
            if interaction >= self.config.threshold:
                pattern = ConvolvResult(
                    pattern_id=f"triple_{top_tech.trend_id}_{top_market.trend_id}_{top_behavior.trend_id}",
                    name="Triple Convergence",
                    description=f"Convergence of tech, market, and behavior trends",
                    source_trends=[top_tech.trend_id, top_market.trend_id, top_behavior.trend_id],
                    intensity=min(1.0, interaction),
                    confidence=0.7,
                    metadata={
                        'common_keywords': list(common_keywords)
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _intra_dimension_convolution(
        self,
        vectors: List[TrendVector],
        dimension: str
    ) -> List[ConvolvResult]:
        """同维度内卷积"""
        patterns = []
        
        if len(vectors) < 2:
            return patterns
        
        # 按得分排序
        sorted_vectors = sorted(vectors, key=lambda v: v.score, reverse=True)
        
        # 组合前N个趋势
        top_n = min(self.config.convolution_window, len(sorted_vectors))
        
        for i in range(top_n):
            for j in range(i + 1, top_n):
                v1, v2 = sorted_vectors[i], sorted_vectors[j]
                
                # 计算内积(相似性)
                similarity = self._calculate_similarity(v1, v2)
                
                if similarity >= self.config.threshold:
                    pattern = ConvolvResult(
                        pattern_id=f"{dimension}_intra_{v1.trend_id}_{v2.trend_id}",
                        name=f"{dimension.capitalize()} Synergy",
                        description=f"Synergy within {dimension} dimension",
                        source_trends=[v1.trend_id, v2.trend_id],
                        intensity=similarity * 0.8,  # 同维度折扣
                        confidence=0.6,
                        metadata={
                            'dimension': dimension,
                            'score1': v1.score,
                            'score2': v2.score
                        }
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _calculate_interaction(self, v1: TrendVector, v2: TrendVector) -> float:
        """计算两个向量的交互强度"""
        # 基础强度
        base = (v1.score + v2.score) / 2
        
        # 方向一致性(速度方向)
        direction_bonus = 0
        if v1.velocity * v2.velocity > 0:  # 同向
            direction_bonus = abs(v1.velocity - v2.velocity) * 0.2
        
        # 关键词重叠
        keyword_bonus = 0
        if v1.keywords and v2.keywords:
            overlap = len(set(v1.keywords) & set(v2.keywords))
            keyword_bonus = min(0.2, overlap * 0.05)
        
        # 综合计算
        interaction = (base + direction_bonus + keyword_bonus) * self.config.interaction_strength
        
        return min(1.0, interaction)
    
    def _calculate_similarity(self, v1: TrendVector, v2: TrendVector) -> float:
        """计算向量相似度"""
        # 基于得分的相似度
        score_diff = abs(v1.score - v2.score)
        score_similarity = 1 - score_diff
        
        # 速度相似度
        vel_diff = abs(v1.velocity - v2.velocity)
        vel_similarity = 1 - vel_diff
        
        # 关键词重叠
        if v1.keywords and v2.keywords:
            keyword_similarity = len(set(v1.keywords) & set(v2.keywords)) / max(
                len(set(v1.keywords) | set(v2.keywords)), 1
            )
        else:
            keyword_similarity = 0.5
        
        return (score_similarity * 0.4 + vel_similarity * 0.3 + keyword_similarity * 0.3)
    
    def _calculate_confidence(self, intensity: float) -> float:
        """计算置信度"""
        if intensity >= 0.8:
            return 0.9
        elif intensity >= 0.6:
            return 0.7
        elif intensity >= 0.4:
            return 0.5
        return 0.3
    
    def get_pattern(self, pattern_id: str) -> Optional[ConvolvResult]:
        """获取模式详情"""
        return self.patterns.get(pattern_id)
    
    def get_all_patterns(self) -> List[ConvolvResult]:
        """获取所有模式"""
        return list(self.patterns.values())
    
    def get_strongest_patterns(self, limit: int = 10) -> List[ConvolvResult]:
        """获取最强模式"""
        patterns = sorted(
            self.patterns.values(),
            key=lambda p: p.intensity,
            reverse=True
        )
        return patterns[:limit]
