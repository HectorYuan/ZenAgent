"""
SoulTeam 层入口

MetaSoul 记忆系统和 SelfLearning 自学习系统的统一入口
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import threading
import uuid

# MetaSoul Memory 模块
from .memory import (
    MetaSoul,
    MemoryType,
    MemoryEntry,
    MemoryStore,
    MemoryIndex,
    ForgettingMechanism,
)

# SelfLearning 模块
from .learning import (
    SelfLearner,
    FeedbackType,
    Feedback,
    KnowledgeGraph,
    SkillAcquisition,
    LearningOptimizer,
)

# Reflection 模块
from .reflection import (
    Reflector,
    ExperienceAnalyzer,
    InsightExtractor,
    PatternRecognizer,
)

# Personality 模块
from .personality import (
    Personality,
    TraitDynamics,
    BeliefSystem,
    ValueEvolution,
)


@dataclass
class SoulTeamConfig:
    """
    SoulTeam 全局配置
    
    配置 SoulTeam 层的各项参数
    """
    # 灵魂配置
    soul_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    soul_name: str = "SoulTeam"
    
    # Memory 配置
    memory_config: Dict[str, Any] = field(default_factory=lambda: {
        "max_working_memory": 100,
        "max_episodic_memory": 1000,
        "max_semantic_memory": 5000,
        "max_procedural_memory": 500,
        "vector_dim": 128,
    })
    
    # Learning 配置
    learning_config: Dict[str, Any] = field(default_factory=lambda: {
        "learning_rate": 0.01,
        "batch_size": 32,
        "reflection_interval": 10,
        "skill_acquisition_enabled": True,
    })
    
    # Personality 配置
    personality_config: Dict[str, Any] = field(default_factory=lambda: {
        "openness": 0.7,
        "conscientiousness": 0.6,
        "extraversion": 0.5,
        "agreeableness": 0.6,
        "neuroticism": 0.3,
    })
    
    # 功能开关
    enable_memory: bool = True
    enable_learning: bool = True
    enable_reflection: bool = True
    enable_personality: bool = True


class SoulTeam:
    """
    SoulTeam 核心
    
    整合 MetaSoul 记忆系统、SelfLearning 自学习系统、
    反思系统和人格演化的统一入口
    """
    
    def __init__(self, config: Optional[SoulTeamConfig] = None):
        """
        初始化 SoulTeam
        
        Args:
            config: 配置对象
        """
        self.config = config or SoulTeamConfig()
        self._initialized_at = datetime.now()
        
        # 初始化组件
        self._init_memory()
        self._init_learning()
        self._init_reflection()
        self._init_personality()
        
        # 锁
        self._lock = threading.RLock()
        
        # 回调
        self._on_insight_generated: List[callable] = []
        self._on_personality_changed: List[callable] = []
        self._on_learning_completed: List[callable] = []
    
    def _init_memory(self) -> None:
        """初始化 MetaSoul 记忆系统"""
        if self.config.enable_memory:
            self.meta_soul = MetaSoul(
                soul_id=self.config.soul_id,
                name=self.config.soul_name,
            )
            self.memory_store = MemoryStore(
                config=self.config.memory_config
            )
            self.memory_index = MemoryIndex(
                vector_dim=self.config.memory_config.get("vector_dim", 128)
            )
            self.forgetting_mechanism = ForgettingMechanism(
                memory_store=self.memory_store
            )
        else:
            self.meta_soul = None
            self.memory_store = None
            self.memory_index = None
            self.forgetting_mechanism = None
    
    def _init_learning(self) -> None:
        """初始化 SelfLearning 自学习系统"""
        if self.config.enable_learning:
            self.self_learner = SelfLearner(
                soul_id=self.config.soul_id,
                config=self.config.learning_config,
            )
            self.feedback_processor = FeedbackProcessor(
                learner=self.self_learner
            )
            self.knowledge_graph = KnowledgeGraph()
            self.skill_acquisition = SkillAcquisition(
                knowledge_graph=self.knowledge_graph
            )
            self.learning_optimizer = LearningOptimizer(
                config=self.config.learning_config
            )
        else:
            self.self_learner = None
            self.feedback_processor = None
            self.knowledge_graph = None
            self.skill_acquisition = None
            self.learning_optimizer = None
    
    def _init_reflection(self) -> None:
        """初始化反思系统"""
        if self.config.enable_reflection:
            self.reflector = Reflector(
                meta_soul=self.meta_soul,
                knowledge_graph=self.knowledge_graph,
            )
            self.experience_analyzer = ExperienceAnalyzer(
                reflector=self.reflector
            )
            self.insight_extractor = InsightExtractor(
                reflector=self.reflector,
                knowledge_graph=self.knowledge_graph,
            )
            self.pattern_recognizer = PatternRecognizer(
                knowledge_graph=self.knowledge_graph
            )
        else:
            self.reflector = None
            self.experience_analyzer = None
            self.insight_extractor = None
            self.pattern_recognizer = None
    
    def _init_personality(self) -> None:
        """初始化人格演化系统"""
        if self.config.enable_personality:
            self.personality = Personality(
                config=self.config.personality_config
            )
            self.trait_dynamics = TraitDynamics(
                personality=self.personality
            )
            self.belief_system = BeliefSystem()
            self.value_evolution = ValueEvolution(
                belief_system=self.belief_system
            )
        else:
            self.personality = None
            self.trait_dynamics = None
            self.belief_system = None
            self.value_evolution = None
    
    # ==================== Memory 操作 ====================
    
    def store_memory(
        self,
        content: str,
        memory_type: MemoryType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        存储记忆
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型
            metadata: 元数据
            
        Returns:
            Optional[str]: 记忆 ID
        """
        if not self.meta_soul:
            return None
        
        return self.meta_soul.store_memory(
            content=content,
            memory_type=memory_type,
            metadata=metadata,
        )
    
    def retrieve_memory(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """
        检索记忆
        
        Args:
            query: 查询内容
            memory_type: 记忆类型过滤
            limit: 返回数量限制
            
        Returns:
            List[MemoryEntry]: 记忆条目列表
        """
        if not self.meta_soul:
            return []
        
        return self.meta_soul.retrieve(
            query=query,
            memory_type=memory_type,
            limit=limit,
        )
    
    # ==================== Learning 操作 ====================
    
    def learn(
        self,
        experience: Dict[str, Any],
        feedback: Optional[Feedback] = None,
    ) -> Dict[str, Any]:
        """
        学习经验
        
        Args:
            experience: 经验数据
            feedback: 反馈数据
            
        Returns:
            Dict[str, Any]: 学习结果
        """
        if not self.self_learner:
            return {"success": False, "error": "Learning disabled"}
        
        return self.self_learner.learn(experience, feedback)
    
    def process_feedback(
        self,
        feedback: Feedback,
    ) -> Dict[str, Any]:
        """
        处理反馈
        
        Args:
            feedback: 反馈数据
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        if not self.feedback_processor:
            return {"success": False, "error": "Learning disabled"}
        
        return self.feedback_processor.process(feedback)
    
    # ==================== Reflection 操作 ====================
    
    def reflect(
        self,
        experience: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        反思经验
        
        Args:
            experience: 经验数据
            
        Returns:
            Dict[str, Any]: 反思结果
        """
        if not self.reflector:
            return {"success": False, "error": "Reflection disabled"}
        
        return self.reflector.reflect(experience)
    
    def analyze_experience(
        self,
        experience: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        分析经验
        
        Args:
            experience: 经验数据
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        if not self.experience_analyzer:
            return {"success": False, "error": "Reflection disabled"}
        
        return self.experience_analyzer.analyze(experience)
    
    def extract_insights(
        self,
        experiences: List[Dict[str, Any]],
    ) -> List[str]:
        """
        提取洞察
        
        Args:
            experiences: 经验列表
            
        Returns:
            List[str]: 洞察列表
        """
        if not self.insight_extractor:
            return []
        
        return self.insight_extractor.extract(experiences)
    
    # ==================== Personality 操作 ====================
    
    def evolve_personality(
        self,
        experience: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        演化人格
        
        Args:
            experience: 经验数据
            
        Returns:
            Dict[str, float]: 更新后的特质值
        """
        if not self.personality:
            return {}
        
        return self.personality.evolve(experience)
    
    def update_belief(
        self,
        belief: str,
        strength: float,
    ) -> bool:
        """
        更新信念
        
        Args:
            belief: 信念内容
            strength: 信念强度
            
        Returns:
            bool: 是否成功
        """
        if not self.belief_system:
            return False
        
        self.belief_system.update_belief(belief, strength)
        return True
    
    # ==================== 状态和统计 ====================
    
    def get_full_status(self) -> Dict[str, Any]:
        """
        获取完整状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        status = {
            "soul_id": self.config.soul_id,
            "soul_name": self.config.soul_name,
            "timestamp": datetime.now().isoformat(),
            "initialized_at": self._initialized_at.isoformat(),
        }
        
        # Memory 状态
        if self.meta_soul:
            status["memory"] = self.meta_soul.get_stats()
        
        # Learning 状态
        if self.self_learner:
            status["learning"] = self.self_learner.get_stats()
        
        # Knowledge Graph 状态
        if self.knowledge_graph:
            status["knowledge_graph"] = self.knowledge_graph.get_stats()
        
        # Personality 状态
        if self.personality:
            status["personality"] = self.personality.get_traits()
        
        # Belief System 状态
        if self.belief_system:
            status["beliefs"] = self.belief_system.get_beliefs()
        
        return status
    
    def reset(self) -> None:
        """重置 SoulTeam"""
        with self._lock:
            if self.meta_soul:
                self.meta_soul.clear()
            
            if self.knowledge_graph:
                self.knowledge_graph.clear()
            
            if self.personality:
                self.personality.reset()
            
            if self.belief_system:
                self.belief_system.clear()


# 全局 SoulTeam 实例
_default_soulteam: Optional[SoulTeam] = None


def get_soulteam(config: Optional[SoulTeamConfig] = None) -> SoulTeam:
    """
    获取 SoulTeam 实例
    
    Args:
        config: 配置对象
        
    Returns:
        SoulTeam: SoulTeam 实例
    """
    global _default_soulteam
    if _default_soulteam is None:
        _default_soulteam = SoulTeam(config)
    return _default_soulteam


def create_soulteam(**kwargs) -> SoulTeam:
    """
    创建新的 SoulTeam 实例
    
    Args:
        **kwargs: 配置参数
        
    Returns:
        SoulTeam: 新的 SoulTeam 实例
    """
    config = SoulTeamConfig(**kwargs)
    return SoulTeam(config)
