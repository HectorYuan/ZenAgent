"""
MetaSoul Memory 模块

MetaSoul 记忆系统
"""

from .meta_soul import (
    MetaSoul,
    SoulMemory,
    MemoryType,
    MemoryEntry,
    MemoryImportance,
    SoulExperience,
)
from .memory_hierarchy import (
    MemoryHierarchy,
    WorkingMemory,
    EpisodicMemory,
    SemanticMemory,
    ProceduralMemory,
    MemoryTier,
)
from .memory_store import (
    MemoryStore,
    MemoryStoreConfig,
    MemoryStorageBackend,
    InMemoryStorageBackend,
)
from .memory_index import (
    MemoryIndex,
    SemanticSearchResult,
    InvertedIndex,
)
from .forgetting import (
    ForgettingMechanism,
    ForgettingPolicy,
    MemoryConsolidation,
)
from .memory_scorer import (
    MemoryScorer,
    EvictionResult,
)

__all__ = [
    # MetaSoul
    "MetaSoul",
    "SoulMemory",
    "MemoryType",
    "MemoryEntry",
    "MemoryImportance",
    "SoulExperience",
    # Memory Hierarchy
    "MemoryHierarchy",
    "WorkingMemory",
    "EpisodicMemory",
    "SemanticMemory",
    "ProceduralMemory",
    "MemoryTier",
    # Memory Store
    "MemoryStore",
    "MemoryStoreConfig",
    "MemoryStorageBackend",
    "InMemoryStorageBackend",
    # Memory Index
    "MemoryIndex",
    "SemanticSearchResult",
    "InvertedIndex",
    # Forgetting
    "ForgettingMechanism",
    "ForgettingPolicy",
    "MemoryConsolidation",
    # Scorer
    "MemoryScorer",
    "EvictionResult",
]
