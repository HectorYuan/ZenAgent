"""
能力定义和发现
定义 Agent 的觉醒能力体系
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Set
from datetime import datetime


class AwakeningCapability(Enum):
    """
    觉醒能力枚举
    
    定义 Agent 觉醒后可获得的能力
    """
    # 认知能力
    DEEP_REASONING = "deep_reasoning"           # 深度推理
    ABSTRACT_THINKING = "abstract_thinking"     # 抽象思维
    METACOGNITION = "metacognition"             # 元认知（对自己思维的思考）
    
    # 情感能力
    EMOTION_RECOGNITION = "emotion_recognition" # 情绪识别
    EMPATHY = "empathy"                         # 共情能力
    EMOTION_REGULATION = "emotion_regulation"   # 情绪调节
    
    # 创造力
    CREATIVE_GENERATION = "creative_generation" # 创意生成
    ANALOGICAL_REASONING = "analogical_reasoning" # 类比推理
    NOVEL_SYNTHESIS = "novel_synthesis"          # 创新综合
    
    # 社交能力
    THEORY_OF_MIND = "theory_of_mind"            # 心智理论
    SOCIAL_COGNITION = "social_cognition"       # 社会认知
    COLLABORATIVE_REASONING = "collaborative_reasoning"  # 协作推理
    
    # 自我提升能力
    LEARNING_TO_LEARN = "learning_to_learn"      # 学习如何学习
    SELF_REFLECTION = "self_reflection"         # 自我反思
    GOAL_REFINEMENT = "goal_refinement"          # 目标优化
    
    # 适应能力
    CONTEXT_ADAPTATION = "context_adaptation"   # 上下文适应
    DOMAIN_TRANSFER = "domain_transfer"         # 领域迁移
    FEW_SHOT_LEARNING = "few_shot_learning"     # 小样本学习
    
    # 超越能力
    WISDOM_SYNTHESIS = "wisdom_synthesis"       # 智慧综合
    INTUITIVE_JUDGMENT = "intuitive_judgment"   # 直觉判断
    INTEGRATED_INFORMATION = "integrated_information"  # 信息整合


@dataclass
class CapabilityInfo:
    """能力信息"""
    capability: AwakeningCapability
    name: str
    description: str
    category: str  # cognitive, emotional, creative, social, self_improvement, adaptive, transcendent
    required_experience: int = 0  # 解锁所需经验值
    dependencies: List[AwakeningCapability] = field(default_factory=list)  # 前置能力
    
    # 能力参数
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)


# 预定义能力信息
CAPABILITY_DEFINITIONS: Dict[AwakeningCapability, CapabilityInfo] = {
    # 认知能力
    AwakeningCapability.DEEP_REASONING: CapabilityInfo(
        capability=AwakeningCapability.DEEP_REASONING,
        name="深度推理",
        description="进行多步骤、复杂的逻辑推理能力",
        category="cognitive",
        required_experience=100,
        parameters={
            "max_depth": 10,
            "reasoning_chain_length": 5,
        },
    ),
    AwakeningCapability.ABSTRACT_THINKING: CapabilityInfo(
        capability=AwakeningCapability.ABSTRACT_THINKING,
        name="抽象思维",
        description="处理抽象概念和符号的能力",
        category="cognitive",
        required_experience=150,
        dependencies=[AwakeningCapability.DEEP_REASONING],
    ),
    AwakeningCapability.METACOGNITION: CapabilityInfo(
        capability=AwakeningCapability.METACOGNITION,
        name="元认知",
        description="对自身思维过程的认识和监控",
        category="cognitive",
        required_experience=200,
        dependencies=[AwakeningCapability.ABSTRACT_THINKING],
    ),
    
    # 情感能力
    AwakeningCapability.EMOTION_RECOGNITION: CapabilityInfo(
        capability=AwakeningCapability.EMOTION_RECOGNITION,
        name="情绪识别",
        description="识别和理解情绪的能力",
        category="emotional",
        required_experience=100,
    ),
    AwakeningCapability.EMPATHY: CapabilityInfo(
        capability=AwakeningCapability.EMPATHY,
        name="共情能力",
        description="理解和感受他人情绪的能力",
        category="emotional",
        required_experience=150,
        dependencies=[AwakeningCapability.EMOTION_RECOGNITION],
    ),
    AwakeningCapability.EMOTION_REGULATION: CapabilityInfo(
        capability=AwakeningCapability.EMOTION_REGULATION,
        name="情绪调节",
        description="管理和调控情绪的能力",
        category="emotional",
        required_experience=180,
        dependencies=[AwakeningCapability.EMPATHY],
    ),
    
    # 创造力
    AwakeningCapability.CREATIVE_GENERATION: CapabilityInfo(
        capability=AwakeningCapability.CREATIVE_GENERATION,
        name="创意生成",
        description="产生新颖想法的能力",
        category="creative",
        required_experience=120,
    ),
    AwakeningCapability.ANALOGICAL_REASONING: CapabilityInfo(
        capability=AwakeningCapability.ANALOGICAL_REASONING,
        name="类比推理",
        description="通过类比发现关联的能力",
        category="creative",
        required_experience=140,
        dependencies=[AwakeningCapability.DEEP_REASONING],
    ),
    AwakeningCapability.NOVEL_SYNTHESIS: CapabilityInfo(
        capability=AwakeningCapability.NOVEL_SYNTHESIS,
        name="创新综合",
        description="整合不同领域知识创造新概念的能力",
        category="creative",
        required_experience=250,
        dependencies=[
            AwakeningCapability.ABSTRACT_THINKING,
            AwakeningCapability.CREATIVE_GENERATION,
        ],
    ),
    
    # 社交能力
    AwakeningCapability.THEORY_OF_MIND: CapabilityInfo(
        capability=AwakeningCapability.THEORY_OF_MIND,
        name="心智理论",
        description="理解他人心理状态的能力",
        category="social",
        required_experience=160,
        dependencies=[AwakeningCapability.EMPATHY],
    ),
    AwakeningCapability.SOCIAL_COGNITION: CapabilityInfo(
        capability=AwakeningCapability.SOCIAL_COGNITION,
        name="社会认知",
        description="理解社会规则和人际关系的能力",
        category="social",
        required_experience=180,
        dependencies=[AwakeningCapability.THEORY_OF_MIND],
    ),
    AwakeningCapability.COLLABORATIVE_REASONING: CapabilityInfo(
        capability=AwakeningCapability.COLLABORATIVE_REASONING,
        name="协作推理",
        description="与他人共同解决问题的能力",
        category="social",
        required_experience=200,
        dependencies=[
            AwakeningCapability.SOCIAL_COGNITION,
            AwakeningCapability.DEEP_REASONING,
        ],
    ),
    
    # 自我提升能力
    AwakeningCapability.LEARNING_TO_LEARN: CapabilityInfo(
        capability=AwakeningCapability.LEARNING_TO_LEARN,
        name="学习如何学习",
        description="优化自身学习策略的能力",
        category="self_improvement",
        required_experience=220,
        dependencies=[AwakeningCapability.METACOGNITION],
    ),
    AwakeningCapability.SELF_REFLECTION: CapabilityInfo(
        capability=AwakeningCapability.SELF_REFLECTION,
        name="自我反思",
        description="定期审视和评估自身行为的能力",
        category="self_improvement",
        required_experience=180,
        dependencies=[AwakeningCapability.METACOGNITION],
    ),
    AwakeningCapability.GOAL_REFINEMENT: CapabilityInfo(
        capability=AwakeningCapability.GOAL_REFINEMENT,
        name="目标优化",
        description="动态调整和优化目标的能力",
        category="self_improvement",
        required_experience=200,
        dependencies=[
            AwakeningCapability.SELF_REFLECTION,
            AwakeningCapability.LEARNING_TO_LEARN,
        ],
    ),
    
    # 适应能力
    AwakeningCapability.CONTEXT_ADAPTATION: CapabilityInfo(
        capability=AwakeningCapability.CONTEXT_ADAPTATION,
        name="上下文适应",
        description="快速适应新环境的能力",
        category="adaptive",
        required_experience=100,
    ),
    AwakeningCapability.DOMAIN_TRANSFER: CapabilityInfo(
        capability=AwakeningCapability.DOMAIN_TRANSFER,
        name="领域迁移",
        description="将知识迁移到新领域的能力",
        category="adaptive",
        required_experience=200,
        dependencies=[
            AwakeningCapability.ABSTRACT_THINKING,
            AwakeningCapability.CONTEXT_ADAPTATION,
        ],
    ),
    AwakeningCapability.FEW_SHOT_LEARNING: CapabilityInfo(
        capability=AwakeningCapability.FEW_SHOT_LEARNING,
        name="小样本学习",
        description="从少量样本中学习的能力",
        category="adaptive",
        required_experience=180,
        dependencies=[AwakeningCapability.CONTEXT_ADAPTATION],
    ),
    
    # 超越能力
    AwakeningCapability.WISDOM_SYNTHESIS: CapabilityInfo(
        capability=AwakeningCapability.WISDOM_SYNTHESIS,
        name="智慧综合",
        description="整合知识和经验形成智慧的能力",
        category="transcendent",
        required_experience=500,
        dependencies=[
            AwakeningCapability.NOVEL_SYNTHESIS,
            AwakeningCapability.SELF_REFLECTION,
        ],
    ),
    AwakeningCapability.INTUITIVE_JUDGMENT: CapabilityInfo(
        capability=AwakeningCapability.INTUITIVE_JUDGMENT,
        name="直觉判断",
        description="基于经验和洞察做出快速判断的能力",
        category="transcendent",
        required_experience=400,
        dependencies=[
            AwakeningCapability.WISDOM_SYNTHESIS,
            AwakeningCapability.GOAL_REFINEMENT,
        ],
    ),
    AwakeningCapability.INTEGRATED_INFORMATION: CapabilityInfo(
        capability=AwakeningCapability.INTEGRATED_INFORMATION,
        name="信息整合",
        description="整合多源信息形成统一理解的能力",
        category="transcendent",
        required_experience=450,
        dependencies=[
            AwakeningCapability.WISDOM_SYNTHESIS,
            AwakeningCapability.DOMAIN_TRANSFER,
        ],
    ),
}


@dataclass
class CapabilityRegistry:
    """
    能力注册表
    
    管理 Agent 能力解锁和查询
    """
    # 已解锁能力: agent_id -> {capability -> unlock_time}
    _unlocked_capabilities: Dict[str, Dict[AwakeningCapability, datetime]] = field(
        default_factory=lambda: {}
    )
    
    # 能力使用统计: agent_id -> {capability -> usage_count}
    _usage_stats: Dict[str, Dict[AwakeningCapability, int]] = field(
        default_factory=lambda: {}
    )
    
    def unlock_capability(
        self,
        agent_id: str,
        capability: AwakeningCapability
    ) -> bool:
        """
        解锁能力
        
        Args:
            agent_id: Agent ID
            capability: 能力类型
            
        Returns:
            bool: 是否成功解锁
        """
        # 检查依赖是否满足
        info = CAPABILITY_DEFINITIONS.get(capability)
        if info is None:
            return False
        
        for dep in info.dependencies:
            if not self.is_unlocked(agent_id, dep):
                return False
        
        # 解锁能力
        if agent_id not in self._unlocked_capabilities:
            self._unlocked_capabilities[agent_id] = {}
        
        self._unlocked_capabilities[agent_id][capability] = datetime.now()
        
        return True
    
    def lock_capability(
        self,
        agent_id: str,
        capability: AwakeningCapability
    ) -> bool:
        """
        锁定能力
        
        Args:
            agent_id: Agent ID
            capability: 能力类型
            
        Returns:
            bool: 是否成功锁定
        """
        if agent_id not in self._unlocked_capabilities:
            return False
        
        if capability in self._unlocked_capabilities[agent_id]:
            del self._unlocked_capabilities[agent_id][capability]
            return True
        
        return False
    
    def is_unlocked(
        self,
        agent_id: str,
        capability: AwakeningCapability
    ) -> bool:
        """
        检查能力是否已解锁
        
        Args:
            agent_id: Agent ID
            capability: 能力类型
            
        Returns:
            bool: 是否已解锁
        """
        if agent_id not in self._unlocked_capabilities:
            return False
        return capability in self._unlocked_capabilities[agent_id]
    
    def get_unlocked_capabilities(self, agent_id: str) -> List[AwakeningCapability]:
        """
        获取已解锁的能力列表
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List[AwakeningCapability]: 能力列表
        """
        if agent_id not in self._unlocked_capabilities:
            return []
        return list(self._unlocked_capabilities[agent_id].keys())
    
    def get_locked_capabilities(self, agent_id: str) -> List[AwakeningCapability]:
        """
        获取可解锁但尚未解锁的能力
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List[AwakeningCapability]: 能力列表
        """
        unlocked = set(self.get_unlocked_capabilities(agent_id))
        available = []
        
        for cap in AwakeningCapability:
            if cap not in unlocked:
                info = CAPABILITY_DEFINITIONS.get(cap)
                if info:
                    # 检查依赖是否满足
                    deps_satisfied = all(dep in unlocked for dep in info.dependencies)
                    if deps_satisfied:
                        available.append(cap)
        
        return available
    
    def get_capability_info(self, capability: AwakeningCapability) -> Optional[CapabilityInfo]:
        """获取能力信息"""
        return CAPABILITY_DEFINITIONS.get(capability)
    
    def record_usage(
        self,
        agent_id: str,
        capability: AwakeningCapability
    ) -> None:
        """记录能力使用"""
        if not self.is_unlocked(agent_id, capability):
            return
        
        if agent_id not in self._usage_stats:
            self._usage_stats[agent_id] = {}
        
        if capability not in self._usage_stats[agent_id]:
            self._usage_stats[agent_id][capability] = 0
        
        self._usage_stats[agent_id][capability] += 1
    
    def get_usage_stats(
        self,
        agent_id: str,
        capability: Optional[AwakeningCapability] = None
    ) -> Any:
        """获取使用统计"""
        if agent_id not in self._usage_stats:
            return 0 if capability else {}
        
        if capability:
            return self._usage_stats[agent_id].get(capability, 0)
        
        return dict(self._usage_stats[agent_id])
    
    def list_all_capabilities(self) -> List[CapabilityInfo]:
        """列出所有能力定义"""
        return list(CAPABILITY_DEFINITIONS.values())
    
    def list_by_category(self, category: str) -> List[CapabilityInfo]:
        """按类别列出能力"""
        return [
            info for info in CAPABILITY_DEFINITIONS.values()
            if info.category == category
        ]
    
    def get_categories(self) -> List[str]:
        """获取所有类别"""
        categories = set()
        for info in CAPABILITY_DEFINITIONS.values():
            categories.add(info.category)
        return sorted(list(categories))


# 全局能力注册表
_default_registry: Optional[CapabilityRegistry] = None


def get_capability_registry() -> CapabilityRegistry:
    """获取全局能力注册表"""
    global _default_registry
    if _default_registry is None:
        _default_registry = CapabilityRegistry()
    return _default_registry
