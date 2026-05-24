"""方案编排流水线 (M10 Phase Q) — A3 决策分离"""
from enum import Enum
from dataclasses import dataclass, field

class ProposalType(str, Enum):
    ARCHITECTURE = "architecture"
    MODULE = "module"
    TOOL = "tool"
    PROCESS = "process"

class DecisionType(str, Enum):
    APPROVE = "approve"
    CONDITIONAL = "conditional_approve"
    REVISE = "needs_revision"
    REJECT = "reject"

@dataclass
class ProposalResult:
    proposal_id: str
    ptype: ProposalType
    decision: DecisionType = DecisionType.APPROVE
    score: float = 0.0
    notes: list[str] = field(default_factory=list)

class ProposalFlowController:
    def evaluate(self, proposal_id: str, ptype: ProposalType,
                 scores: dict[str, float], weights: dict[str, float] = None) -> ProposalResult:
        if not weights:
            weights = {"architecture": 0.4, "risk": 0.3, "effort": 0.3}
        total = sum(scores.get(k, 0) * weights.get(k, 0.1) for k in set(scores) | set(weights))
        decision = (DecisionType.APPROVE if total >= 0.7 else
                    DecisionType.CONDITIONAL if total >= 0.5 else
                    DecisionType.REVISE if total >= 0.3 else DecisionType.REJECT)
        return ProposalResult(proposal_id, ptype, decision, total)
