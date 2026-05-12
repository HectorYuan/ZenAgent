"""
自适应控制器 (Adaptive Controller)

实现自适应调整机制:
- 策略优化
- 资源伸缩
- 技能激活
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AdjustmentType(Enum):
    """调整类型"""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    STRATEGY_CHANGE = "strategy_change"
    SKILL_ACTIVATE = "skill_activate"
    SKILL_DEACTIVATE = "skill_deactivate"


@dataclass
class Adjustment:
    """调整操作"""
    adjustment_id: str
    adjustment_type: AdjustmentType
    target: str  # 目标资源/技能ID
    current_value: Any
    target_value: Any
    reason: str
    priority: int = 50
    timestamp: datetime = field(default_factory=datetime.now)
    estimated_impact: float = 0.0  # 预估影响


@dataclass
class StrategyChange:
    """策略变更"""
    change_id: str
    strategy_name: str
    from_params: Dict[str, Any]
    to_params: Dict[str, Any]
    trigger_reason: str
    confidence: float  # 调整置信度
    expected_improvement: float = 0.0  # 预期改善百分比


class StrategyOptimizer:
    """策略优化器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.strategies: Dict[str, Dict[str, Any]] = {}
    
    def optimize(
        self,
        current_performance: Dict[str, float],
        target_metrics: Dict[str, float]
    ) -> List[StrategyChange]:
        """优化策略"""
        changes = []
        
        for metric, current_value in current_performance.items():
            target = target_metrics.get(metric)
            if target is None:
                continue
            
            # 计算差距
            gap = target - current_value
            gap_pct = gap / target if target != 0 else 0
            
            if abs(gap_pct) > 0.1:  # 超过10%差距需要调整
                change = StrategyChange(
                    change_id=f"change_{metric}_{datetime.now().timestamp()}",
                    strategy_name=metric,
                    from_params={'value': current_value},
                    to_params={'value': target},
                    trigger_reason=f"Performance gap: {gap_pct*100:.1f}%",
                    confidence=min(0.9, 0.5 + abs(gap_pct)),
                    expected_improvement=gap_pct * 100
                )
                changes.append(change)
        
        return changes


class ResourceScaler:
    """资源伸缩器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 伸缩配置 - 添加范围校验
        raw_scale_up = self.config.get('scale_up_threshold', 0.8)
        raw_scale_down = self.config.get('scale_down_threshold', 0.3)
        raw_min = self.config.get('min_capacity', 1)
        raw_max = self.config.get('max_capacity', 100)
        raw_step = self.config.get('scale_step', 0.2)
        
        # 校验并修正配置值
        self.scale_up_threshold = max(0.0, min(1.0, raw_scale_up))
        self.scale_down_threshold = max(0.0, min(1.0, raw_scale_down))
        self.scale_step = max(0.01, min(1.0, raw_step))
        self.min_capacity = max(1, int(raw_min))
        self.max_capacity = max(self.min_capacity, int(raw_max))
        
        # 确保 scale_up_threshold > scale_down_threshold
        if self.scale_up_threshold <= self.scale_down_threshold:
            logger.warning(
                f"Invalid threshold config: scale_up_threshold ({self.scale_up_threshold}) "
                f"should be greater than scale_down_threshold ({self.scale_down_threshold}). "
                f"Auto-correcting to ensure valid range."
            )
            self.scale_up_threshold = self.scale_down_threshold + 0.2
        
        logger.info(
            f"ResourceScaler initialized with: "
            f"scale_up_threshold={self.scale_up_threshold}, "
            f"scale_down_threshold={self.scale_down_threshold}, "
            f"min_capacity={self.min_capacity}, "
            f"max_capacity={self.max_capacity}, "
            f"scale_step={self.scale_step}"
        )
    
    def evaluate(
        self,
        current_utilization: float,
        demand_trend: float,  # 需求趋势 -1到1
        queue_length: int = 0
    ) -> Adjustment:
        """评估资源伸缩需求"""
        # 综合评分
        score = current_utilization * 0.6 + abs(demand_trend) * 0.4
        
        # 根据队列长度调整
        if queue_length > 100:
            score += 0.2
        elif queue_length > 50:
            score += 0.1
        
        adjustment_type = None
        target_value = None
        
        if score > self.scale_up_threshold:
            adjustment_type = AdjustmentType.SCALE_UP
            # 扩容
            current = self.min_capacity  # 简化
            target_value = int(current * (1 + self.scale_step))
            target_value = min(target_value, self.max_capacity)
        elif score < self.scale_down_threshold:
            adjustment_type = AdjustmentType.SCALE_DOWN
            # 缩容
            current = self.min_capacity  # 简化
            target_value = int(current * (1 - self.scale_step))
            target_value = max(target_value, self.min_capacity)
        
        if adjustment_type:
            return Adjustment(
                adjustment_id=f"scale_{datetime.now().timestamp()}",
                adjustment_type=adjustment_type,
                target="resources",
                current_value=current_utilization,
                target_value=target_value,
                reason=f"Utilization: {current_utilization:.1%}, Trend: {demand_trend:.2f}",
                estimated_impact=abs(target_value - current_utilization) if target_value else 0
            )
        
        return None


class SkillActivator:
    """技能激活器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 技能注册
        self.skills: Dict[str, Dict[str, Any]] = {}
        self.active_skills: set = set()
        
        # 初始化默认技能
        self._init_default_skills()
    
    def _init_default_skills(self):
        """初始化默认技能"""
        default_skills = [
            {'id': 'text_analysis', 'name': '文本分析', 'category': 'cognitive'},
            {'id': 'image_recognition', 'name': '图像识别', 'category': 'perception'},
            {'id': 'code_generation', 'name': '代码生成', 'category': 'creative'},
            {'id': 'data_processing', 'name': '数据处理', 'category': 'technical'},
            {'id': 'communication', 'name': '沟通协作', 'category': 'social'}
        ]
        
        for skill in default_skills:
            self.skills[skill['id']] = skill
            self.active_skills.add(skill['id'])
    
    def get_recommended_skills(
        self,
        task_requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """获取推荐技能"""
        recommended = []
        required_categories = task_requirements.get('categories', [])
        
        for skill_id, skill in self.skills.items():
            if skill['category'] in required_categories:
                recommended.append(skill)
        
        return recommended
    
    def should_activate(
        self,
        skill_id: str,
        trend_score: float
    ) -> bool:
        """判断是否应激活技能"""
        if skill_id not in self.skills:
            return False
        
        # 阈值
        activation_threshold = self.config.get('activation_threshold', 60.0)
        
        return trend_score >= activation_threshold
    
    def activate(self, skill_id: str) -> bool:
        """激活技能"""
        if skill_id in self.skills:
            self.active_skills.add(skill_id)
            logger.info(f"Skill activated: {skill_id}")
            return True
        return False
    
    def deactivate(self, skill_id: str) -> bool:
        """停用技能"""
        if skill_id in self.active_skills:
            self.active_skills.remove(skill_id)
            logger.info(f"Skill deactivated: {skill_id}")
            return True
        return False
    
    def get_active_skills(self) -> List[Dict[str, Any]]:
        """获取活跃技能列表"""
        return [
            self.skills[sid]
            for sid in self.active_skills
            if sid in self.skills
        ]


class AdaptiveController:
    """
    自适应调整控制器
    
    根据趋势自动调整:
    - 策略参数
    - 资源配置
    - 技能激活
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 子组件
        self.strategy_optimizer = StrategyOptimizer(config.get('strategy'))
        self.resource_scaler = ResourceScaler(config.get('resource'))
        self.skill_activator = SkillActivator(config.get('skill'))
        
        # 调整历史
        self.adjustment_history: List[Adjustment] = []
        
        # 回调
        self.on_adjustment: List[Callable] = []
        
        # 配置
        self.auto_adjust = self.config.get('auto_adjust', True)
        self.adjustment_interval = self.config.get('adjustment_interval', 300)  # 5分钟
    
    def adjust_strategy(
        self,
        trends: List[Any],
        current_metrics: Dict[str, float]
    ) -> List[StrategyChange]:
        """根据趋势调整策略"""
        # 简化: 从趋势中提取目标指标
        target_metrics = {}
        for trend in trends:
            if hasattr(trend, 'score'):
                # 将趋势得分映射到指标
                target_metrics['performance'] = trend.score / 100
        
        changes = self.strategy_optimizer.optimize(current_metrics, target_metrics)
        
        # 记录调整
        for change in changes:
            logger.info(f"Strategy change: {change.strategy_name} - {change.trigger_reason}")
        
        return changes
    
    def adjust_resources(
        self,
        utilization: float,
        demand_trend: float,
        queue_length: int = 0
    ) -> Optional[Adjustment]:
        """调整资源配置"""
        adjustment = self.resource_scaler.evaluate(
            utilization, demand_trend, queue_length
        )
        
        if adjustment:
            self.adjustment_history.append(adjustment)
            
            # 触发回调
            for callback in self.on_adjustment:
                try:
                    callback(adjustment)
                except Exception as e:
                    logger.error(f"Adjustment callback error: {e}")
            
            logger.info(
                f"Resource adjustment: {adjustment.adjustment_type.value} "
                f"- {adjustment.reason}"
            )
        
        return adjustment
    
    def adjust_skills(
        self,
        emerging_trends: List[Any]
    ) -> List[Adjustment]:
        """根据趋势调整技能"""
        adjustments = []
        
        for trend in emerging_trends:
            # 获取相关技能建议
            skill_recommendations = self.skill_activator.get_recommended_skills({
                'categories': trend.keywords if hasattr(trend, 'keywords') else []
            })
            
            for skill in skill_recommendations:
                if self.skill_activator.should_activate(skill['id'], trend.score):
                    self.skill_activator.activate(skill['id'])
                    
                    adjustment = Adjustment(
                        adjustment_id=f"skill_{skill['id']}_{datetime.now().timestamp()}",
                        adjustment_type=AdjustmentType.SKILL_ACTIVATE,
                        target=skill['id'],
                        current_value=False,
                        target_value=True,
                        reason=f"Emerging trend: {trend.name}",
                        priority=50
                    )
                    adjustments.append(adjustment)
        
        self.adjustment_history.extend(adjustments)
        return adjustments
    
    def execute_adjustments(
        self,
        adjustments: List[Adjustment]
    ) -> Dict[str, bool]:
        """执行调整"""
        results = {}
        
        for adj in adjustments:
            try:
                if adj.adjustment_type == AdjustmentType.SCALE_UP:
                    # 执行扩容
                    results[adj.adjustment_id] = True
                    
                elif adj.adjustment_type == AdjustmentType.SCALE_DOWN:
                    # 执行缩容
                    results[adj.adjustment_id] = True
                    
                elif adj.adjustment_type == AdjustmentType.SKILL_ACTIVATE:
                    results[adj.adjustment_id] = self.skill_activator.activate(adj.target)
                    
                elif adj.adjustment_type == AdjustmentType.SKILL_DEACTIVATE:
                    results[adj.adjustment_id] = self.skill_activator.deactivate(adj.target)
                    
            except Exception as e:
                logger.error(f"Adjustment execution failed: {adj.adjustment_id} - {e}")
                results[adj.adjustment_id] = False
        
        return results
    
    def get_adjustment_summary(self) -> Dict[str, Any]:
        """获取调整摘要"""
        return {
            'total_adjustments': len(self.adjustment_history),
            'by_type': {
                at.value: sum(1 for a in self.adjustment_history if a.adjustment_type == at)
                for at in AdjustmentType
            },
            'active_skills': len(self.skill_activator.active_skills),
            'recent_adjustments': [
                {
                    'id': a.adjustment_id,
                    'type': a.adjustment_type.value,
                    'target': a.target,
                    'reason': a.reason
                }
                for a in self.adjustment_history[-10:]
            ]
        }
