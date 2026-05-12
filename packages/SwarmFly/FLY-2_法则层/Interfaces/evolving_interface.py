"""
Evolving引擎接口

提供与Evolving引擎的双向通信:
- 能力上报
- 进化请求
- 境界跃迁
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import asyncio
import hashlib

logger = logging.getLogger(__name__)


class EvolutionStatus(Enum):
    """进化状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CapabilityType(Enum):
    """能力类型"""
    COGNITIVE = "cognitive"       # 认知能力
    EXECUTIVE = "executive"       # 执行能力
    COLLABORATIVE = "collaborative"  # 协作能力
    ADAPTIVE = "adaptive"          # 适应能力
    CREATIVE = "creative"          # 创造能力


@dataclass
class CapabilityMetrics:
    """能力指标"""
    capability_type: CapabilityType
    score: float  # 0-100
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    trend: str = "stable"  # improving, stable, declining


@dataclass
class ExecutionResult:
    """执行结果"""
    execution_id: str
    agent_id: str
    task_id: str
    success: bool
    output: Optional[Any] = None
    error: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvolutionRequest:
    """进化请求"""
    request_id: str
    agent_id: str
    target_capability: CapabilityType
    current_score: float
    target_score: float
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    priority: int = 50
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvolutionResult:
    """进化结果"""
    request_id: str
    agent_id: str
    status: EvolutionStatus
    capability_type: CapabilityType
    before_score: float
    after_score: float
    improvement: float
    recommendations: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class RealmTransition:
    """境界跃迁"""
    transition_id: str
    agent_id: str
    from_realm: str
    to_realm: str
    trigger_reason: str
    assessment_result: Dict[str, Any] = field(default_factory=dict)
    status: EvolutionStatus = EvolutionStatus.PENDING
    approved: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class EvolvingInterface:
    """
    Evolving引擎接口
    
    负责与Evolving引擎的通信和协调:
    - 执行结果上报
    - 能力进化请求
    - 境界跃迁
    """
    
    # 境界等级
    REALM_LEVELS = {
        'R1': 1,  # 初境
        'R2': 2,  # 明境
        'R3': 3,  # 智境
        'R4': 4,  # 通境
        'R5': 5   # 化境
    }
    
    # 境界跃迁阈值
    REALM_TRANSITION_THRESHOLD = 85.0
    REALM_COOLDOWN_DAYS = 7
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Evolving引擎连接配置
        self.evolving_url = self.config.get('evolving_url', 'http://localhost:8082')
        self.connection_timeout = self.config.get('connection_timeout', 30)
        
        # 进化配置
        self.auto_evolve = self.config.get('auto_evolve', True)
        self.min_improvement = self.config.get('min_improvement', 5.0)
        
        # 能力历史
        self.capability_history: Dict[str, List[CapabilityMetrics]] = {}
        
        # 进化请求历史
        self.evolution_requests: Dict[str, EvolutionRequest] = {}
        self.evolution_results: Dict[str, EvolutionResult] = {}
        
        # 境界跃迁历史
        self.realm_transitions: Dict[str, RealmTransition] = {}
        self.last_transition_time: Dict[str, datetime] = {}
        
        # 回调
        self.on_evolution_complete: List[Callable] = []
        self.on_realm_transition: List[Callable] = []
        
        # 连接状态
        self.is_connected = False
        
        # 统计
        self.stats = {
            'total_reports': 0,
            'successful_evolutions': 0,
            'failed_evolutions': 0,
            'total_transitions': 0,
            'approved_transitions': 0
        }
    
    async def connect(self) -> bool:
        """连接到Evolving引擎"""
        try:
            logger.info(f"Connecting to Evolving engine at {self.evolving_url}")
            await asyncio.sleep(0.1)
            
            self.is_connected = True
            logger.info("Connected to Evolving engine")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Evolving: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """断开连接"""
        self.is_connected = False
        logger.info("Disconnected from Evolving engine")
    
    # ==================== 执行结果上报 ====================
    
    async def report_execution_result(self, result: ExecutionResult) -> bool:
        """
        上报执行结果用于进化分析
        
        Args:
            result: 执行结果
            
        Returns:
            bool: 是否成功
        """
        if not self.is_connected:
            if not await self.connect():
                return False
        
        try:
            # 分析执行结果并更新能力评分
            capability_metrics = self._analyze_execution(result)
            
            # 存储历史
            self._update_capability_history(result.agent_id, capability_metrics)
            
            # 检查是否需要进化请求
            if self.auto_evolve and result.success:
                await self._check_evolution_need(result.agent_id, capability_metrics)
            
            self.stats['total_reports'] += 1
            
            logger.debug(f"Execution result reported: {result.execution_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to report execution result: {e}")
            return False
    
    def _analyze_execution(self, result: ExecutionResult) -> Dict[CapabilityType, CapabilityMetrics]:
        """分析执行结果，生成能力指标"""
        metrics = {}
        
        # 基于执行指标评估能力
        if result.metrics:
            # 认知能力 - 基于任务完成度
            cognitive_score = result.metrics.get('accuracy', 0.5) * 100
            metrics[CapabilityType.COGNITIVE] = CapabilityMetrics(
                capability_type=CapabilityType.COGNITIVE,
                score=cognitive_score,
                evidence=[{'execution_id': result.execution_id, 'accuracy': result.metrics.get('accuracy')}]
            )
            
            # 执行能力 - 基于速度和成功率
            executive_score = (result.metrics.get('success_rate', 0.5) * 50 + 
                            max(0, 100 - result.duration_ms / 10))
            metrics[CapabilityType.EXECUTIVE] = CapabilityMetrics(
                capability_type=CapabilityType.EXECUTIVE,
                score=min(100, executive_score),
                evidence=[{'execution_id': result.execution_id, 'duration_ms': result.duration_ms}]
            )
            
            # 协作能力
            if 'collaboration_score' in result.metrics:
                metrics[CapabilityType.COLLABORATIVE] = CapabilityMetrics(
                    capability_type=CapabilityType.COLLABORATIVE,
                    score=result.metrics['collaboration_score'] * 100,
                    evidence=[{'execution_id': result.execution_id}]
                )
        
        return metrics
    
    def _update_capability_history(
        self,
        agent_id: str,
        metrics: Dict[CapabilityType, CapabilityMetrics]
    ):
        """更新能力历史"""
        if agent_id not in self.capability_history:
            self.capability_history[agent_id] = []
        
        for cap_type, metric in metrics.items():
            self.capability_history[agent_id].append(metric)
            
            # 保留最近100条记录
            if len(self.capability_history[agent_id]) > 100:
                self.capability_history[agent_id] = self.capability_history[agent_id][-100:]
    
    async def _check_evolution_need(
        self,
        agent_id: str,
        metrics: Dict[CapabilityType, CapabilityMetrics]
    ):
        """检查是否需要进化"""
        for cap_type, metric in metrics.items():
            # 计算平均分数
            history = self.capability_history.get(agent_id, [])
            recent_scores = [
                m.score for m in history
                if m.capability_type == cap_type
            ][-10:]  # 最近10条
            
            if len(recent_scores) >= 5:
                avg_score = sum(recent_scores) / len(recent_scores)
                
                # 如果连续提升，考虑请求进化
                if all(recent_scores[i] <= recent_scores[i+1] 
                       for i in range(len(recent_scores)-1)):
                    if metric.score - avg_score >= self.min_improvement:
                        await self.request_evolution(
                            agent_id=agent_id,
                            capability_type=cap_type,
                            current_score=avg_score,
                            target_score=metric.score
                        )
    
    # ==================== 能力进化 ====================
    
    async def request_evolution(
        self,
        agent_id: str,
        capability_type: CapabilityType,
        current_score: float,
        target_score: float,
        evidence: Optional[List[Dict[str, Any]]] = None
    ) -> EvolutionResult:
        """
        请求能力进化
        
        Args:
            agent_id: 智能体ID
            capability_type: 能力类型
            current_score: 当前评分
            target_score: 目标评分
            evidence: 证据
            
        Returns:
            EvolutionResult: 进化结果
        """
        request = EvolutionRequest(
            request_id=self._generate_request_id(),
            agent_id=agent_id,
            target_capability=capability_type,
            current_score=current_score,
            target_score=target_score,
            evidence=evidence or []
        )
        
        self.evolution_requests[request.request_id] = request
        
        # 模拟进化处理
        result = EvolutionResult(
            request_id=request.request_id,
            agent_id=agent_id,
            status=EvolutionStatus.IN_PROGRESS,
            capability_type=capability_type,
            before_score=current_score,
            after_score=current_score,
            improvement=0.0,
            started_at=datetime.now()
        )
        
        try:
            # 模拟进化过程
            await asyncio.sleep(0.1)
            
            # 生成进化结果
            result.status = EvolutionStatus.SUCCESS
            result.after_score = target_score
            result.improvement = target_score - current_score
            result.completed_at = datetime.now()
            result.recommendations = self._generate_recommendations(result)
            
            self.stats['successful_evolutions'] += 1
            
        except Exception as e:
            result.status = EvolutionStatus.FAILED
            result.error_message = str(e)
            self.stats['failed_evolutions'] += 1
            logger.error(f"Evolution failed: {e}")
        
        self.evolution_results[request.request_id] = result
        
        # 触发回调
        for callback in self.on_evolution_complete:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Evolution complete callback error: {e}")
        
        return result
    
    def _generate_recommendations(self, result: EvolutionResult) -> List[str]:
        """生成进化建议"""
        recommendations = []
        
        if result.improvement < 5:
            recommendations.append("继续当前训练，积累更多经验")
        elif result.improvement < 10:
            recommendations.append("可以尝试更具挑战性的任务")
        else:
            recommendations.append("能力提升显著，考虑探索新领域")
        
        return recommendations
    
    async def get_capability_report(self, agent_id: str) -> Dict[str, Any]:
        """获取能力报告"""
        history = self.capability_history.get(agent_id, [])
        
        # 按能力类型聚合
        by_type = {}
        for metric in history:
            cap_type = metric.capability_type.value
            if cap_type not in by_type:
                by_type[cap_type] = []
            by_type[cap_type].append(metric)
        
        # 计算统计
        stats = {}
        for cap_type, metrics in by_type.items():
            scores = [m.score for m in metrics]
            stats[cap_type] = {
                'current': scores[-1] if scores else 0,
                'average': sum(scores) / len(scores) if scores else 0,
                'max': max(scores) if scores else 0,
                'min': min(scores) if scores else 0,
                'count': len(scores)
            }
        
        return {
            'agent_id': agent_id,
            'capabilities': stats,
            'history_count': len(history)
        }
    
    # ==================== 境界跃迁 ====================
    
    async def check_realm_transition(
        self,
        agent_id: str,
        current_realm: str,
        capability_scores: Dict[str, float]
    ) -> Optional[RealmTransition]:
        """
        检查是否可以进行境界跃迁
        
        Args:
            agent_id: 智能体ID
            current_realm: 当前境界
            capability_scores: 各项能力评分
            
        Returns:
            RealmTransition: 跃迁信息，如果有资格的话
        """
        # 检查冷却期
        if agent_id in self.last_transition_time:
            days_since = (datetime.now() - self.last_transition_time[agent_id]).days
            if days_since < self.REALM_COOLDOWN_DAYS:
                return None
        
        # 计算综合评分
        avg_score = sum(capability_scores.values()) / len(capability_scores) if capability_scores else 0
        
        # 检查是否达到跃迁条件
        if avg_score < self.REALM_TRANSITION_THRESHOLD:
            return None
        
        # 获取目标境界
        current_level = self.REALM_LEVELS.get(current_realm, 1)
        if current_level >= 5:
            return None  # 已达最高境界
        
        target_realm = f'R{current_level + 1}'
        
        transition = RealmTransition(
            transition_id=self._generate_request_id(),
            agent_id=agent_id,
            from_realm=current_realm,
            to_realm=target_realm,
            trigger_reason=f"综合评分达到{avg_score:.1f}，超过阈值{self.REALM_TRANSITION_THRESHOLD}",
            assessment_result={
                'average_score': avg_score,
                'capability_scores': capability_scores
            }
        )
        
        return transition
    
    async def request_realm_transition(
        self,
        transition: RealmTransition
    ) -> RealmTransition:
        """
        请求境界跃迁
        
        Args:
            transition: 跃迁请求
            
        Returns:
            RealmTransition: 更新后的跃迁信息
        """
        transition.status = EvolutionStatus.IN_PROGRESS
        self.realm_transitions[transition.transition_id] = transition
        
        # 模拟评估过程
        await asyncio.sleep(0.1)
        
        # 简化评估：平均分>85即可通过
        avg_score = transition.assessment_result.get('average_score', 0)
        transition.approved = avg_score >= self.REALM_TRANSITION_THRESHOLD
        transition.status = EvolutionStatus.SUCCESS if transition.approved else EvolutionStatus.FAILED
        transition.completed_at = datetime.now()
        
        if transition.approved:
            self.last_transition_time[transition.agent_id] = datetime.now()
            self.stats['approved_transitions'] += 1
            
            logger.info(
                f"Realm transition approved: {transition.agent_id} "
                f"{transition.from_realm} -> {transition.to_realm}"
            )
        else:
            logger.warning(
                f"Realm transition denied: {transition.agent_id} "
                f"(score: {avg_score:.1f})"
            )
        
        self.stats['total_transitions'] += 1
        
        # 触发回调
        for callback in self.on_realm_transition:
            try:
                callback(transition)
            except Exception as e:
                logger.error(f"Realm transition callback error: {e}")
        
        return transition
    
    # ==================== 工具方法 ====================
    
    def _generate_request_id(self) -> str:
        """生成请求ID"""
        import time
        content = f"{time.time()}:{datetime.now().microsecond}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'total_requests': len(self.evolution_requests),
            'total_results': len(self.evolution_results),
            'total_transitions': len(self.realm_transitions),
            'agents_tracked': len(self.capability_history)
        }
