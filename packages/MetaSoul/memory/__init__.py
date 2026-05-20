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
from .hierarchical_store import (
    HierarchicalStore,
    MemoryEntry as HierarchicalMemoryEntry,
    MemoryTier as HierarchicalMemoryTier,
    MemoryBackend,
    BackendProtocol,
    StoreStats,
)
from .memory_retriever import (
    MemoryRetriever,
    RetrieveIntent,
)
from .semantic_kb import (
    SemanticKnowledgeBase,
    KnowledgeTriple,
)
from .knowledge_extractor import (
    KnowledgeExtractor,
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
    # Hierarchical Store (M8 P3)
    "HierarchicalStore",
    "HierarchicalMemoryEntry",
    "HierarchicalMemoryTier",
    "MemoryBackend",
    "BackendProtocol",
    "StoreStats",
    # Memory Retriever
    "MemoryRetriever",
    "RetrieveIntent",
    # Semantic KB
    "SemanticKnowledgeBase",
    "KnowledgeTriple",
    # Knowledge Extractor
    "KnowledgeExtractor",
]
