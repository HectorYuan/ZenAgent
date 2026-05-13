"""
技能评估器
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class PerformanceMetrics:
    """性能指标"""
    skill_id: str
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_execution_time: float = 0.0
    avg_success_rate: float = 100.0
    user_rating: float = 0.0  # 用户评分
    last_evaluated: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 100.0
        return (self.success_count / self.total_calls) * 100


@dataclass
class EvaluationReport:
    """评估报告"""
    skill_id: str
    overall_score: float  # 综合评分
    performance_score: float
    quality_score: float
    usage_score: float
    recommendations: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def is_healthy(self, threshold: float = 70.0) -> bool:
        return self.overall_score >= threshold


class SkillEvaluator:
    """
    技能评估器
    
    定期评估技能性能和健康度
    """
    
    def __init__(self, registry, caller):
        self.registry = registry
        self.caller = caller
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.evaluation_history: Dict[str, List[EvaluationReport]] = {}
    
    def record_call(self, skill_id: str, success: bool, execution_time: float):
        """记录调用"""
        if skill_id not in self.metrics:
            self.metrics[skill_id] = PerformanceMetrics(skill_id=skill_id)
        
        m = self.metrics[skill_id]
        m.total_calls += 1
        if success:
            m.success_count += 1
        else:
            m.failure_count += 1
        
        # 更新平均执行时间
        m.avg_execution_time = (
            (m.avg_execution_time * (m.total_calls - 1) + execution_time) 
            / m.total_calls
        )
        m.last_evaluated = datetime.now()
    
    def evaluate(self, skill_id: str) -> EvaluationReport:
        """
        评估技能
        
        Args:
            skill_id: 技能ID
            
        Returns:
            EvaluationReport: 评估报告
        """
        skill = self.registry.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")
        
        m = self.metrics.get(skill_id, PerformanceMetrics(skill_id=skill_id))
        recommendations = []
        issues = []
        
        # 性能评分 (0-100)
        if m.avg_execution_time < 1.0:
            perf_score = 100.0
        elif m.avg_execution_time < 5.0:
            perf_score = 80.0
        elif m.avg_execution_time < 30.0:
            perf_score = 60.0
        else:
            perf_score = 40.0
            issues.append("执行时间过长")
            recommendations.append("优化技能实现以提高响应速度")
        
        # 质量评分 (基于成功率)
        quality_score = m.success_rate
        if m.success_rate < 80:
            issues.append("成功率较低")
            recommendations.append("加强错误处理和边界情况处理")
        
        # 使用评分 (基于调用量)
        if m.total_calls == 0:
            usage_score = 50.0
            recommendations.append("技能使用率低，考虑推广或优化")
        elif m.total_calls < 10:
            usage_score = 60.0
        else:
            usage_score = min(100.0, m.total_calls / 10 * 10)
        
        # 综合评分
        overall = (perf_score * 0.3 + quality_score * 0.4 + usage_score * 0.3)
        
        report = EvaluationReport(
            skill_id=skill_id,
            overall_score=overall,
            performance_score=perf_score,
            quality_score=quality_score,
            usage_score=usage_score,
            recommendations=recommendations,
            issues=issues
        )
        
        # 保存历史
        if skill_id not in self.evaluation_history:
            self.evaluation_history[skill_id] = []
        self.evaluation_history[skill_id].append(report)
        
        return report
    
    def evaluate_all(self) -> List[EvaluationReport]:
        """评估所有技能"""
        return [self.evaluate(sid) for sid in self.registry.skills.keys()]
    
    def get_health_report(self) -> Dict[str, Any]:
        """获取整体健康报告"""
        all_reports = self.evaluate_all()
        healthy = len([r for r in all_reports if r.is_healthy()])
        
        return {
            "total_skills": len(all_reports),
            "healthy_count": healthy,
            "unhealthy_count": len(all_reports) - healthy,
            "health_rate": (healthy / len(all_reports) * 100) if all_reports else 100.0,
            "reports": {r.skill_id: r.overall_score for r in all_reports}
        }
