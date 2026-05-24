"""集群共识机制 (M10 Phase O) — Quorum/Weighted/Unanimous"""
from enum import Enum
from typing import Optional

class ConsensusType(str, Enum):
    QUORUM = "quorum"
    WEIGHTED = "weighted"
    UNANIMOUS = "unanimous"

class ClusterConsensus:
    def __init__(self, quorum_ratio: float = 0.67):
        self._quorum = quorum_ratio

    def decide(self, votes: dict[str, bool], weights: dict[str, float] = None,
               ctype: ConsensusType = ConsensusType.QUORUM) -> Optional[bool]:
        if not votes: return None
        if ctype == ConsensusType.UNANIMOUS:
            return all(votes.values())
        if ctype == ConsensusType.WEIGHTED and weights:
            total_w = sum(weights.get(a, 1.0) for a in votes)
            yes_w = sum(weights.get(a, 1.0) for a, v in votes.items() if v)
            return yes_w / max(total_w, 0.01) >= self._quorum
        yes = sum(1 for v in votes.values() if v)
        return yes / len(votes) >= self._quorum
