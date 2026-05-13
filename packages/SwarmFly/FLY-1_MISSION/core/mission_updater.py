"""
使命更新器
"""
from typing import List, Callable, Optional, Any, Dict
from datetime import datetime
from dataclasses import dataclass, field
from .mission import Mission, MissionStatus


@dataclass
class MissionUpdateEvent:
    """使命更新事件"""
    update_type: str  # full, partial, emergency
    old_mission: Dict[str, Any]
    new_mission: Dict[str, Any]
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)
    affected_agents: List[str] = field(default_factory=list)


class MissionUpdater:
    """
    使命更新器
    
    负责更新集群使命并通知所有智能体
    """
    
    def __init__(self, mission: Mission):
        self.mission = mission
        self.update_history: List[MissionUpdateEvent] = []
        self.update_listeners: List[Callable] = []
    
    def add_listener(self, callback: Callable[[MissionUpdateEvent], None]):
        """添加更新监听器"""
        self.update_listeners.append(callback)
    
    def notify_listeners(self, event: MissionUpdateEvent):
        """通知所有监听器"""
        for listener in self.update_listeners:
            try:
                listener(event)
            except Exception:
                pass
    
    def update_mission(self, 
                       new_mission_text: Optional[str] = None,
                       new_values: Optional[List[Dict[str, Any]]] = None,
                       reason: str = "定期更新",
                       affected_agents: Optional[List[str]] = None) -> MissionUpdateEvent:
        """
        更新使命
        
        Args:
            new_mission_text: 新使命文本
            new_values: 新价值体系
            reason: 更新原因
            affected_agents: 受影响的智能体列表
        """
        old_dict = self.mission.to_dict()
        
        # 更新使命文本
        if new_mission_text:
            self.mission.core_mission = new_mission_text
        
        # 更新价值体系
        if new_values:
            from .mission import ValueSystem
            self.mission.values = [
                ValueSystem(v['name'], v.get('description', ''), v.get('weight', 1.0))
                for v in new_values
            ]
        
        self.mission.updated_at = datetime.now()
        self.mission.status = MissionStatus.ALIGNING
        
        # 创建事件
        event = MissionUpdateEvent(
            update_type="full" if (new_mission_text and new_values) else "partial",
            old_mission=old_dict,
            new_mission=self.mission.to_dict(),
            reason=reason,
            affected_agents=affected_agents or []
        )
        
        self.update_history.append(event)
        self.notify_listeners(event)
        
        return event
    
    def emergency_update(self, new_mission_text: str, reason: str) -> MissionUpdateEvent:
        """
        紧急更新使命
        
        Args:
            new_mission_text: 新使命文本
            reason: 紧急原因
        """
        self.mission.status = MissionStatus.ACTIVE
        return self.update_mission(
            new_mission_text=new_mission_text,
            reason=f"[紧急] {reason}"
        )
