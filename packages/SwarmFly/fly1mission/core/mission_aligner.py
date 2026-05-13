"""
使命对齐器
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from .mission import Mission, MissionStatus, ValueSystem


@dataclass
class AlignmentReport:
    """对齐报告"""
    agent_id: str
    mission_id: str
    alignment_score: float
    deviations: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def is_aligned(self, threshold: float = 80.0) -> bool:
        return self.alignment_score >= threshold


class MissionAligner:
    """
    使命对齐器
    
    负责检查和管理智能体的使命对齐
    """
    
    def __init__(self, mission: Optional[Mission] = None):
        self.mission = mission or Mission(mission_id="default")
        self.aligned_agents: Dict[str, float] = {}  # agent_id -> alignment_score
        self.deviation_history: Dict[str, List[AlignmentReport]] = {}
    
    def align_agent(self, agent_id: str, agent_values: List[str], 
                    agent_mission: Optional[str] = None) -> AlignmentReport:
        """
        对齐智能体使命
        
        Args:
            agent_id: 智能体ID
            agent_values: 智能体的价值列表
            agent_mission: 智能体使命描述
            
        Returns:
            AlignmentReport: 对齐报告
        """
        deviations = []
        recommendations = []
        
        # 检查使命一致性
        if agent_mission and agent_mission != self.mission.core_mission:
            deviations.append("使命描述偏离核心使命")
            recommendations.append("更新使命描述与核心使命对齐")
        
        # 检查价值体系
        expected_values = {v.name for v in self.mission.values}
        agent_set = set(agent_values)
        
        missing_values = expected_values - agent_set
        if missing_values:
            deviations.append(f"缺少价值: {', '.join(missing_values)}")
            recommendations.append("补充缺失的核心价值")
        
        extra_values = agent_set - expected_values
        if extra_values:
            recommendations.append(f"可考虑移除非核心价值: {', '.join(extra_values)}")
        
        # 计算对齐分数
        overlap = len(agent_set & expected_values)
        score = (overlap / len(expected_values)) * 100 if expected_values else 100.0
        
        # 生成报告
        report = AlignmentReport(
            agent_id=agent_id,
            mission_id=self.mission.mission_id,
            alignment_score=score,
            deviations=deviations,
            recommendations=recommendations
        )
        
        # 记录
        self.aligned_agents[agent_id] = score
        if agent_id not in self.deviation_history:
            self.deviation_history[agent_id] = []
        self.deviation_history[agent_id].append(report)
        
        return report
    
    def check_alignment(self, agent_id: str) -> Optional[float]:
        """检查智能体对齐分数"""
        return self.aligned_agents.get(agent_id)
    
    def get_all_aligned(self, threshold: float = 80.0) -> List[str]:
        """获取所有对齐的智能体"""
        return [aid for aid, score in self.aligned_agents.items() 
                if score >= threshold]
    
    def get_all_deviated(self, threshold: float = 80.0) -> List[str]:
        """获取所有偏离的智能体"""
        return [aid for aid, score in self.aligned_agents.items() 
                if score < threshold]
    
    def get_alignment_rate(self) -> float:
        """获取整体对齐率"""
        if not self.aligned_agents:
            return 100.0
        aligned_count = len([s for s in self.aligned_agents.values() if s >= 80.0])
        return (aligned_count / len(self.aligned_agents)) * 100
