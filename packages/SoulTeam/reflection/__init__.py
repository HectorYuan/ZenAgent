"""
SoulTeam Reflection 模块

反思系统
"""

from .reflector import (
    Reflector,
    ReflectionResult,
    ReflectionDepth,
)
from .experience_analyzer import (
    ExperienceAnalyzer,
    ExperiencePattern,
)
from .insight_extractor import (
    InsightExtractor,
    Insight,
    InsightType,
)
from .pattern_recognizer import (
    PatternRecognizer,
    Pattern,
    PatternType,
)

__all__ = [
    # Reflector
    "Reflector",
    "ReflectionResult",
    "ReflectionDepth",
    # Experience Analyzer
    "ExperienceAnalyzer",
    "ExperiencePattern",
    # Insight Extractor
    "InsightExtractor",
    "Insight",
    "InsightType",
    # Pattern Recognizer
    "PatternRecognizer",
    "Pattern",
    "PatternType",
]
