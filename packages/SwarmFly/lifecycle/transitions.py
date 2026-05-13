"""
状态转换规则定义和验证器
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Callable, Any


class TransitionType(Enum):
    """转换类型枚举"""
    NORMAL = "normal"       # 正常转换
    FORCE = "force"        # 强制转换
    CONDITIONAL = "conditional"  # 条件转换
    ERROR = "error"        # 错误转换


@dataclass
class TransitionRule:
    """
    状态转换规则
    
    定义状态之间的转换规则和条件
    """
    from_state: 'AgentState'  # 延迟类型注解
    to_state: 'AgentState'    # 延迟类型注解
    transition_type: TransitionType = TransitionType.NORMAL
    condition: Optional[Callable[[], bool]] = None
    priority: int = 0
    description: str = ""
    
    def can_transition(self, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        检查是否可以执行转换
        
        Args:
            context: 转换上下文
            
        Returns:
            bool: 是否可以转换
        """
        if self.condition is None:
            return True
        
        if context is None:
            return self.condition()
        
        # 绑定上下文到条件函数
        try:
            return self.condition()
        except TypeError:
            # 如果条件函数不接受参数
            return self.condition()


class TransitionRules:
    """
    状态转换规则集合
    
    管理一组状态转换规则
    """
    
    def __init__(self, rules: Optional[List[TransitionRule]] = None):
        """
        初始化规则集合
        
        Args:
            rules: 初始规则列表
        """
        self._rules: List[TransitionRule] = rules or []
        self._transition_map: Dict[str, List[str]] = {}
        self._build_transition_map()
    
    def add_rule(self, rule: TransitionRule) -> None:
        """
        添加转换规则
        
        Args:
            rule: 转换规则
        """
        self._rules.append(rule)
        self._build_transition_map()
    
    def remove_rule(self, from_state: str, to_state: str) -> bool:
        """
        移除转换规则
        
        Args:
            from_state: 源状态
            to_state: 目标状态
            
        Returns:
            bool: 是否成功移除
        """
        original_count = len(self._rules)
        self._rules = [
            r for r in self._rules
            if not (str(r.from_state.value) == from_state and str(r.to_state.value) == to_state)
        ]
        if len(self._rules) < original_count:
            self._build_transition_map()
            return True
        return False
    
    def get_rules_for_state(self, from_state: str) -> List[TransitionRule]:
        """
        获取指定状态的所有转换规则
        
        Args:
            from_state: 源状态
            
        Returns:
            List[TransitionRule]: 转换规则列表
        """
        return [
            r for r in self._rules
            if str(r.from_state.value) == from_state
        ]
    
    def get_target_states(self, from_state: str) -> List[str]:
        """
        获取可转换到的目标状态列表
        
        Args:
            from_state: 源状态
            
        Returns:
            List[str]: 目标状态列表
        """
        return self._transition_map.get(from_state, [])
    
    def _build_transition_map(self) -> None:
        """构建状态转换映射"""
        self._transition_map.clear()
        for rule in self._rules:
            from_key = str(rule.from_state.value)
            to_key = str(rule.to_state.value)
            if from_key not in self._transition_map:
                self._transition_map[from_key] = []
            if to_key not in self._transition_map[from_key]:
                self._transition_map[from_key].append(to_key)
    
    @property
    def rules(self) -> List[TransitionRule]:
        """获取所有规则"""
        return self._rules.copy()


class TransitionValidator:
    """
    状态转换验证器
    
    验证状态转换是否符合规则
    """
    
    def __init__(self, rules: List[TransitionRule]):
        """
        初始化验证器
        
        Args:
            rules: 转换规则列表
        """
        self._rules = rules
        self._transition_map = self._build_map(rules)
    
    @staticmethod
    def _build_map(rules: List[TransitionRule]) -> Dict[str, List[str]]:
        """构建转换映射"""
        transition_map: Dict[str, List[str]] = {}
        for rule in rules:
            from_key = str(rule.from_state.value)
            to_key = str(rule.to_state.value)
            if from_key not in transition_map:
                transition_map[from_key] = []
            if to_key not in transition_map[from_key]:
                transition_map[from_key].append(to_key)
        return transition_map
    
    def is_valid_transition(
        self,
        from_state: 'AgentState',
        to_state: 'AgentState',
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        验证状态转换是否合法
        
        Args:
            from_state: 源状态
            to_state: 目标状态
            context: 转换上下文
            
        Returns:
            bool: 是否合法
        """
        from_key = str(from_state.value)
        to_key = str(to_state.value)
        
        # 检查基本转换是否存在
        if from_key not in self._transition_map:
            return False
        
        if to_key not in self._transition_map[from_key]:
            return False
        
        # 检查条件规则
        matching_rules = [
            r for r in self._rules
            if str(r.from_state.value) == from_key and str(r.to_state.value) == to_key
        ]
        
        for rule in matching_rules:
            if not rule.can_transition(context):
                return False
        
        return True
    
    def get_valid_transitions(
        self,
        from_state: 'AgentState',
        context: Optional[Dict[str, Any]] = None,
    ) -> List['AgentState']:
        """
        获取指定状态的所有有效转换目标
        
        Args:
            from_state: 源状态
            context: 转换上下文
            
        Returns:
            List[AgentState]: 有效的目标状态列表
        """
        from_key = str(from_state.value)
        valid_targets = []
        
        for target in self._transition_map.get(from_key, []):
            # 需要重新导入 AgentState 来创建枚举值
            from .agent_lifecycle import AgentState
            try:
                target_state = AgentState(target)
            except ValueError:
                continue
            
            if self.is_valid_transition(from_state, target_state, context):
                valid_targets.append(target_state)
        
        return valid_targets


def get_default_rules() -> List[TransitionRule]:
    """
    获取默认状态转换规则
    
    Returns:
        List[TransitionRule]: 默认规则列表
    """
    from .agent_lifecycle import AgentState
    
    return [
        # Created 状态转换
        TransitionRule(
            from_state=AgentState.CREATED,
            to_state=AgentState.INITIALIZING,
            description="开始初始化",
        ),
        
        # Initializing 状态转换
        TransitionRule(
            from_state=AgentState.INITIALIZING,
            to_state=AgentState.READY,
            description="初始化完成，进入就绪状态",
        ),
        TransitionRule(
            from_state=AgentState.INITIALIZING,
            to_state=AgentState.ERROR,
            transition_type=TransitionType.ERROR,
            description="初始化失败",
        ),
        
        # Ready 状态转换
        TransitionRule(
            from_state=AgentState.READY,
            to_state=AgentState.RUNNING,
            description="启动运行",
        ),
        TransitionRule(
            from_state=AgentState.READY,
            to_state=AgentState.STOPPED,
            description="停止",
        ),
        
        # Running 状态转换
        TransitionRule(
            from_state=AgentState.RUNNING,
            to_state=AgentState.PAUSED,
            description="暂停",
        ),
        TransitionRule(
            from_state=AgentState.RUNNING,
            to_state=AgentState.STOPPED,
            description="停止",
        ),
        TransitionRule(
            from_state=AgentState.RUNNING,
            to_state=AgentState.ERROR,
            transition_type=TransitionType.ERROR,
            description="运行错误",
        ),
        
        # Paused 状态转换
        TransitionRule(
            from_state=AgentState.PAUSED,
            to_state=AgentState.RUNNING,
            description="恢复运行",
        ),
        TransitionRule(
            from_state=AgentState.PAUSED,
            to_state=AgentState.STOPPED,
            description="停止",
        ),
        
        # Stopped 状态转换
        TransitionRule(
            from_state=AgentState.STOPPED,
            to_state=AgentState.READY,
            description="重新就绪",
        ),
        TransitionRule(
            from_state=AgentState.STOPPED,
            to_state=AgentState.DISPOSED,
            description="释放资源",
        ),
        
        # Error 状态转换
        TransitionRule(
            from_state=AgentState.ERROR,
            to_state=AgentState.READY,
            description="错误恢复",
        ),
        TransitionRule(
            from_state=AgentState.ERROR,
            to_state=AgentState.INITIALIZING,
            description="重新初始化",
        ),
        TransitionRule(
            from_state=AgentState.ERROR,
            to_state=AgentState.STOPPED,
            description="停止",
        ),
        
        # Disposed 状态转换（终态，无转换）
        TransitionRule(
            from_state=AgentState.DISPOSED,
            to_state=AgentState.CREATED,
            description="重新创建",
        ),
    ]
