"""
使命传播器
"""
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from .mission import Mission


@dataclass
class PropagationEvent:
    """传播事件"""
    event_type: str  # broadcast, targeted, cascade
    mission_snapshot: Dict[str, Any]
    recipients: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


class MissionPropagator:
    """
    使命传播器
    
    负责将使命传递给新智能体和更新现有智能体
    """
    
    def __init__(self, mission: Mission):
        self.mission = mission
        self.propagation_history: List[PropagationEvent] = []
        self.subscribers: Dict[str, Callable] = {}  # agent_id -> callback
    
    def inject_mission(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        向智能体配置注入使命
        
        Args:
            agent_config: 智能体配置
            
        Returns:
            更新后的配置
        """
        updated_config = agent_config.copy()
        updated_config['mission'] = self.mission.core_mission
        updated_config['value_system'] = [v.name for v in self.mission.values]
        updated_config['goals'] = self.mission.goals
        updated_config['principles'] = self.mission.principles
        return updated_config
    
    def subscribe(self, agent_id: str, callback: Callable):
        """订阅使命更新"""
        self.subscribers[agent_id] = callback
    
    def unsubscribe(self, agent_id: str):
        """取消订阅"""
        self.subscribers.pop(agent_id, None)
    
    def broadcast(self, recipients: List[str]) -> PropagationEvent:
        """
        广播使命到多个智能体
        
        Args:
            recipients: 接收者列表
            
        Returns:
            传播事件
        """
        event = PropagationEvent(
            event_type="broadcast",
            mission_snapshot=self.mission.to_dict(),
            recipients=recipients
        )
        self.propagation_history.append(event)
        
        # 触发订阅者回调
        for agent_id in recipients:
            if agent_id in self.subscribers:
                self.subscribers[agent_id](self.mission)
        
        return event
    
    def propagate_to_new_agent(self, agent_id: str) -> Dict[str, Any]:
        """向新智能体传播使命"""
        config = {'agent_id': agent_id}
        return self.inject_mission(config)
    
    def cascade_propagate(self, agent_hierarchy: Dict[str, List[str]]) -> List[PropagationEvent]:
        """
        层级传播（从父到子）
        
        Args:
            agent_hierarchy: 智能体层级关系 {parent_id: [child_ids]}
        """
        events = []
        for parent, children in agent_hierarchy.items():
            event = self.broadcast([parent] + children)
            events.append(event)
        return events
