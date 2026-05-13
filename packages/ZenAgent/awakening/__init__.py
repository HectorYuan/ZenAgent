"""
Awakening 觉醒适配层
提供 Agent 觉醒能力的统一适配接口
"""

from .adapter import AwakeningAdapter, get_adapter, AwakeningState
from .capabilities import (
    AwakeningCapability,
    CapabilityRegistry,
    get_capability_registry,
)
from .evolution import (
    EvolutionEngine,
    EvolutionStage,
    EvolutionEvent,
    get_evolution_engine,
)

__all__ = [
    # Adapter
    "AwakeningAdapter",
    "get_adapter",
    "AwakeningState",
    # Capabilities
    "AwakeningCapability",
    "CapabilityRegistry",
    "get_capability_registry",
    # Evolution
    "EvolutionEngine",
    "EvolutionStage",
    "EvolutionEvent",
    "get_evolution_engine",
]
