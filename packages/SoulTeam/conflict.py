"""集群冲突解决 (M10 Phase P)"""
from enum import Enum

class ConflictStrategy(str, Enum):
    PRIORITY = "priority"
    VOTE = "vote"
    ARBITRATION = "arbitration"

class ClusterConflictResolver:
    def resolve(self, conflicts: list[dict], strategy: ConflictStrategy =
                ConflictStrategy.PRIORITY) -> dict:
        if not conflicts: return {}
        if strategy == ConflictStrategy.PRIORITY:
            return min(conflicts, key=lambda c: c.get("priority", 99))
        return conflicts[0]  # fallback
