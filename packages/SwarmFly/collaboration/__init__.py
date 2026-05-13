"""
SwarmFly 协作调度引擎模块

提供任务分发、负载均衡、共识机制和冲突解决等功能
"""

from .engine import (
    CollaborationEngine,
    CollaborationConfig,
    TaskResult,
)
from .task_dispatcher import (
    TaskDispatcher,
    Task,
    TaskPriority,
    TaskStatus,
    DispatchStrategy,
)
from .load_balancer import (
    LoadBalancer,
    LoadMetric,
    BalancingStrategy,
    AgentLoad,
)
from .consensus import (
    ConsensusMechanism,
    ConsensusResult,
    Vote,
    ConsensusProtocol,
    QuorumConsensus,
    WeightedConsensus,
    UnanimousConsensus,
)
from .conflict_resolver import (
    ConflictResolver,
    Conflict,
    ConflictType,
    ResolutionStrategy,
    ResolutionResult,
)

__all__ = [
    # Engine
    "CollaborationEngine",
    "CollaborationConfig",
    "TaskResult",
    # Task Dispatcher
    "TaskDispatcher",
    "Task",
    "TaskPriority",
    "TaskStatus",
    "DispatchStrategy",
    # Load Balancer
    "LoadBalancer",
    "LoadMetric",
    "BalancingStrategy",
    "AgentLoad",
    # Consensus
    "ConsensusMechanism",
    "ConsensusResult",
    "Vote",
    "ConsensusProtocol",
    "QuorumConsensus",
    "WeightedConsensus",
    "UnanimousConsensus",
    # Conflict Resolver
    "ConflictResolver",
    "Conflict",
    "ConflictType",
    "ResolutionStrategy",
    "ResolutionResult",
]
