"""
涌现检测 (Emergent Detection)

检测涌现模式和异常信号。
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EmergenceLevel(Enum):
    """涌现级别"""
    WEAK = "weak"        # 微弱涌现
    MODERATE = "moderate"  # 中度涌现
    STRONG = "strong"    # 强烈涌现
    CRITICAL = "critical"  # 临界涌现


@dataclass
class EmergentPattern:
    """涌现模式"""
    pattern_id: str
    name: str
    description: str
    level: EmergenceLevel
    indicators: List[Dict[str, Any]]  # 触发指标
    intensity: float  # 强度 0-1
    confidence: float  # 置信度
    detected_at: datetime = field(default_factory=datetime.now)
    first_detected: Optional[datetime] = None
    occurrence_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmergenceSignal:
    """涌现信号"""
    signal_id: str
    signal_type: str  # convergence, divergence, acceleration, etc.
    source_indicators: List[str]
    strength: float
    timestamp: datetime = field(default_factory=datetime.now)


class EmergentDetector:
    """
    涌现检测器
    
    检测系统中的涌现模式:
    - 收敛涌现(多源趋同)
    - 加速涌现(变化加速)
    - 相变涌现(状态突变)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 检测配置
        self.convergence_threshold = self.config.get('convergence_threshold', 0.7)
        self.acceleration_threshold = self.config.get('acceleration_threshold', 0.3)
        self.phase_change_threshold = self.config.get('phase_change_threshold', 0.5)
        
        # 检测到的模式
        self.patterns: Dict[str, EmergentPattern] = {}
        
        # 信号历史
        self.signal_history: List[EmergenceSignal] = []
        
        # 历史数据(用于趋势检测)
        self.history_window = self.config.get('history_window', 30)  # 天
        self.historical_data: Dict[str, List[float]] = {}
    
    def detect(
        self,
        current_data: Dict[str, float],
        historical_trends: Optional[Dict[str, List[float]]] = None
    ) -> List[EmergentPattern]:
        """
        检测涌现模式
        
        Args:
            current_data: 当前指标数据
            historical_trends: 历史趋势数据
            
        Returns:
            List[EmergentPattern]: 检测到的涌现模式
        """
        patterns = []
        
        # 更新历史数据
        self._update_historical_data(current_data)
        
        # 检测收敛涌现
        convergence = self._detect_convergence(current_data)
        if convergence:
            patterns.append(convergence)
        
        # 检测加速涌现
        acceleration = self._detect_acceleration()
        if acceleration:
            patterns.append(acceleration)
        
        # 检测相变涌现
        phase_change = self._detect_phase_change()
        if phase_change:
            patterns.append(phase_change)
        
        # 更新存储
        for pattern in patterns:
            self._update_pattern(pattern)
        
        return patterns
    
    def _update_historical_data(self, current_data: Dict[str, float]):
        """更新历史数据"""
        for metric, value in current_data.items():
            if metric not in self.historical_data:
                self.historical_data[metric] = []
            
            self.historical_data[metric].append(value)
            
            # 保持窗口大小
            max_window = self.history_window * 24  # 假设每天一个数据点
            if len(self.historical_data[metric]) > max_window:
                self.historical_data[metric] = self.historical_data[metric][-max_window:]
    
    def _detect_convergence(self, current_data: Dict[str, float]) -> Optional[EmergentPattern]:
        """检测收敛涌现"""
        # 检查多个指标是否向同一方向收敛
        if len(current_data) < 2:
            return None
        
        values = list(current_data.values())
        
        # 计算变异系数(CV)
        mean = sum(values) / len(values)
        if mean == 0:
            return None
        
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5
        cv = std_dev / mean
        
        # 低CV表示收敛
        if cv < (1 - self.convergence_threshold):
            return EmergentPattern(
                pattern_id=f"convergence_{datetime.now().timestamp()}",
                name="Convergence Emergence",
                description=f"Multiple indicators converging (CV: {cv:.3f})",
                level=self._cv_to_level(cv),
                indicators=[
                    {'type': 'convergence', 'cv': cv, 'indicators': list(current_data.keys())}
                ],
                intensity=1 - cv,
                confidence=0.7,
                first_detected=datetime.now()
            )
        
        return None
    
    def _detect_acceleration(self) -> Optional[EmergentPattern]:
        """检测加速涌现"""
        if len(self.historical_data) == 0:
            return None
        
        # 选择第一个有足够数据的指标
        for metric, history in self.historical_data.items():
            if len(history) < 10:
                continue
            
            # 计算最近几个点的加速度
            recent = history[-5:]
            
            # 计算一阶差分(速度)
            velocities = [recent[i] - recent[i-1] for i in range(1, len(recent))]
            
            # 计算二阶差分(加速度)
            accelerations = [velocities[i] - velocities[i-1] for i in range(1, len(velocities))]
            
            if accelerations:
                avg_acceleration = sum(accelerations) / len(accelerations)
                
                # 检查加速度是否超过阈值
                if abs(avg_acceleration) > self.acceleration_threshold:
                    return EmergentPattern(
                        pattern_id=f"acceleration_{metric}_{datetime.now().timestamp()}",
                        name="Acceleration Emergence",
                        description=f"Rapid change in {metric} (acceleration: {avg_acceleration:.3f})",
                        level=EmergenceLevel.MODERATE if avg_acceleration > 0 else EmergenceLevel.STRONG,
                        indicators=[
                            {
                                'type': 'acceleration',
                                'metric': metric,
                                'acceleration': avg_acceleration
                            }
                        ],
                        intensity=min(1.0, abs(avg_acceleration)),
                        confidence=0.6,
                        first_detected=datetime.now(),
                        metadata={'metric': metric}
                    )
        
        return None
    
    def _detect_phase_change(self) -> Optional[EmergentPattern]:
        """检测相变涌现"""
        if len(self.historical_data) == 0:
            return None
        
        for metric, history in self.historical_data.items():
            if len(history) < 10:
                continue
            
            # 比较前半和后半
            mid = len(history) // 2
            first_half = history[:mid]
            second_half = history[mid:]
            
            first_mean = sum(first_half) / len(first_half)
            second_mean = sum(second_half) / len(second_half)
            
            if first_mean == 0:
                continue
            
            # 计算变化率
            change_rate = abs(second_mean - first_mean) / abs(first_mean)
            
            if change_rate > self.phase_change_threshold:
                return EmergentPattern(
                    pattern_id=f"phase_change_{metric}_{datetime.now().timestamp()}",
                    name="Phase Change Emergence",
                    description=f"Significant state change in {metric} (change: {change_rate*100:.1f}%)",
                    level=EmergenceLevel.STRONG if change_rate > 0.5 else EmergenceLevel.MODERATE,
                    indicators=[
                        {
                            'type': 'phase_change',
                            'metric': metric,
                            'before': first_mean,
                            'after': second_mean,
                            'change_rate': change_rate
                        }
                    ],
                    intensity=min(1.0, change_rate),
                    confidence=0.8,
                    first_detected=datetime.now(),
                    metadata={'metric': metric}
                )
        
        return None
    
    def _cv_to_level(self, cv: float) -> EmergenceLevel:
        """将变异系数转换为涌现级别"""
        if cv < 0.1:
            return EmergenceLevel.CRITICAL
        elif cv < 0.2:
            return EmergenceLevel.STRONG
        elif cv < 0.4:
            return EmergenceLevel.MODERATE
        return EmergenceLevel.WEAK
    
    def _update_pattern(self, pattern: EmergentPattern):
        """更新模式记录"""
        # 检查是否已有相似模式
        for existing_id, existing in self.patterns.items():
            if (existing.name == pattern.name and 
                (datetime.now() - existing.detected_at).total_seconds() < 3600):
                # 更新现有模式
                existing.occurrence_count += 1
                existing.intensity = max(existing.intensity, pattern.intensity)
                existing.detected_at = datetime.now()
                return
        
        # 新增模式
        self.patterns[pattern.pattern_id] = pattern
    
    def get_active_patterns(self) -> List[EmergentPattern]:
        """获取活跃模式(最近检测到的)"""
        now = datetime.now()
        return [
            p for p in self.patterns.values()
            if (now - p.detected_at).total_seconds() < 3600  # 1小时内
        ]
    
    def get_emergence_alert(
        self,
        level_threshold: EmergenceLevel = EmergenceLevel.MODERATE
    ) -> Optional[Dict[str, Any]]:
        """获取涌现告警"""
        active = self.get_active_patterns()
        
        critical = [p for p in active if p.level in (
            EmergenceLevel.STRONG, EmergenceLevel.CRITICAL
        )]
        
        if critical:
            return {
                'alert': True,
                'level': 'critical',
                'patterns': [
                    {'id': p.pattern_id, 'name': p.name, 'level': p.level.value}
                    for p in critical
                ],
                'timestamp': datetime.now().isoformat()
            }
        
        moderate = [p for p in active if p.level == EmergenceLevel.MODERATE]
        if moderate:
            return {
                'alert': True,
                'level': 'warning',
                'patterns': [
                    {'id': p.pattern_id, 'name': p.name, 'level': p.level.value}
                    for p in moderate
                ],
                'timestamp': datetime.now().isoformat()
            }
        
        return {'alert': False, 'level': 'normal'}
