"""
MetaSoul Learning 模块

SelfLearning 自学习系统
"""

from .learner import (
    SelfLearner,
    LearningCycle,
    LearningResult,
)
from .feedback_processor import (
    FeedbackProcessor,
    FeedbackType,
    Feedback,
    FeedbackSource,
)
from .knowledge_graph import (
    KnowledgeGraph,
    Entity,
    Relation,
    KnowledgeQuery,
    EntityType,
    RelationType,
)
from .skill_acquisition import (
    SkillAcquisition,
    SkillLevel,
    SkillRecord,
)
from .learning_optimizer import (
    LearningOptimizer,
    CurriculumStage,
    TransferLearningResult,
)

__all__ = [
    # Learner
    "SelfLearner",
    "LearningCycle",
    "LearningResult",
    # Feedback
    "FeedbackProcessor",
    "FeedbackType",
    "Feedback",
    "FeedbackSource",
    # Knowledge Graph
    "KnowledgeGraph",
    "Entity",
    "Relation",
    "KnowledgeQuery",
    "EntityType",
    "RelationType",
    # Skill Acquisition
    "SkillAcquisition",
    "SkillLevel",
    "SkillRecord",
    # Learning Optimizer
    "LearningOptimizer",
    "CurriculumStage",
    "TransferLearningResult",
]
