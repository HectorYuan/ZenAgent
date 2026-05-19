"""
MetaSoul Personality 模块

人格演化系统
"""

from .personality import (
    Personality,
    BigFiveTraits,
    PersonalityState,
)
from .trait_dynamics import (
    TraitDynamics,
    TraitChange,
    EnvironmentalFactor,
)
from .belief_system import (
    BeliefSystem,
    Belief,
    BeliefStrength,
)
from .value_evolution import (
    ValueEvolution,
    Value,
    ValuePriority,
)

__all__ = [
    # Personality
    "Personality",
    "BigFiveTraits",
    "PersonalityState",
    # Trait Dynamics
    "TraitDynamics",
    "TraitChange",
    "EnvironmentalFactor",
    # Belief System
    "BeliefSystem",
    "Belief",
    "BeliefStrength",
    # Value Evolution
    "ValueEvolution",
    "Value",
    "ValuePriority",
]
