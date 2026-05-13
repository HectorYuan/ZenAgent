"""
使命定义模块
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


class MissionStatus(Enum):
    """使命状态"""
    ACTIVE = "active"
    ALIGNING = "aligning"
    DEVIATED = "deviated"
    ARCHIVED = "archived"


@dataclass
class ValueSystem:
    """价值体系"""
    name: str
    description: str
    weight: float = 1.0
    
    
@dataclass
class Mission:
    """
    使命定义
    
    核心使命: "成为高效、协作、自我进化的智能体协作网络"
    """
    mission_id: str
    core_mission: str = "成为高效、协作、自我进化的智能体协作网络"
    status: MissionStatus = MissionStatus.ACTIVE
    
    # 价值体系
    values: List[ValueSystem] = field(default_factory=lambda: [
        ValueSystem("用户中心", "始终以用户需求为核心", 1.0),
        ValueSystem("效率优先", "优化资源分配，提升协作效率", 0.9),
        ValueSystem("持续进化", "建立自我改进机制", 0.8),
    ])
    
    # 使命层次
    vision: str = ""  # 愿景
    goals: List[str] = field(default_factory=list)  # 目标列表
    principles: List[str] = field(default_factory=list)  # 原则
    
    # 对齐度
    alignment_score: float = 100.0
    last_aligned_at: Optional[datetime] = None
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.vision:
            self.vision = f"通过{self.core_mission}为用户创造价值"
        if not self.goals:
            self.goals = [
                "优化智能体间协作效率",
                "提升任务完成质量",
                "实现自我学习和进化"
            ]
        if not self.principles:
            self.principles = [
                "透明沟通",
                "数据驱动决策",
                "用户隐私优先"
            ]
    
    def align_with_mission(self, agent_values: List[str]) -> float:
        """
        检查智能体使命对齐度
        
        Args:
            agent_values: 智能体的价值列表
            
        Returns:
            对齐度分数 (0-100)
        """
        expected_values = {v.name for v in self.values}
        agent_set = set(agent_values)
        
        if agent_set == expected_values:
            return 100.0
        
        overlap = len(agent_set & expected_values)
        total = len(expected_values)
        
        score = (overlap / total) * 100
        self.alignment_score = score
        self.last_aligned_at = datetime.now()
        
        return score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "core_mission": self.core_mission,
            "status": self.status.value,
            "values": [{"name": v.name, "weight": v.weight} for v in self.values],
            "alignment_score": self.alignment_score,
            "last_aligned_at": self.last_aligned_at.isoformat() if self.last_aligned_at else None
        }
