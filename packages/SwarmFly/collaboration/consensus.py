"""
共识机制

实现多 Agent 决策的共识算法
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime
from abc import ABC, abstractmethod
import threading


class ConsensusProtocol(Enum):
    """共识协议枚举"""
    RAFT = "raft"              # Raft 共识
    PAXOS = "paxos"            # Paxos 共识
    MULTI_PAXOS = "multi_paxos"  # Multi-Paxos
    QUORUM = "quorum"          # 简单多数决
    UNANIMOUS = "unanimous"    # 全员同意
    WEIGHTED = "weighted"      # 加权共识


@dataclass
class Vote:
    """
    投票记录
    
    记录 Agent 的投票信息
    """
    voter_id: str
    value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    weight: float = 1.0
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "voter_id": self.voter_id,
            "value": str(self.value),
            "timestamp": self.timestamp.isoformat(),
            "weight": self.weight,
            "reason": self.reason,
        }


@dataclass
class ConsensusResult:
    """
    共识结果
    
    记录共识决策的结果
    """
    success: bool
    reached_value: Any = None
    protocol: ConsensusProtocol = ConsensusProtocol.QUORUM
    
    # 投票统计
    votes: List[Vote] = field(default_factory=list)
    agree_count: int = 0
    disagree_count: int = 0
    abstain_count: int = 0
    
    # 时间信息
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    
    # 附加信息
    quorum_size: int = 0
    participants: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self, value: Any = None) -> None:
        """结束共识过程"""
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        if value is not None:
            self.reached_value = value
    
    @property
    def total_votes(self) -> int:
        """总投票数"""
        return len(self.votes)
    
    @property
    def agreement_rate(self) -> float:
        """同意率"""
        total = self.total_votes
        if total == 0:
            return 0.0
        return self.agree_count / total
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "reached_value": str(self.reached_value) if self.reached_value else None,
            "protocol": self.protocol.value,
            "votes": [v.to_dict() for v in self.votes],
            "agree_count": self.agree_count,
            "disagree_count": self.disagree_count,
            "abstain_count": self.abstain_count,
            "total_votes": self.total_votes,
            "agreement_rate": self.agreement_rate,
            "duration": self.duration,
            "quorum_size": self.quorum_size,
            "participants": self.participants,
        }


class ConsensusMechanism(ABC):
    """
    共识机制基类
    
    定义共识算法的接口
    """
    
    def __init__(self, protocol: ConsensusProtocol):
        """
        初始化共识机制
        
        Args:
            protocol: 共识协议类型
        """
        self.protocol = protocol
        self._active_rounds: Dict[str, 'ConsensusRound'] = {}
        self._lock = threading.RLock()
    
    @abstractmethod
    def propose(
        self,
        round_id: str,
        value: Any,
        participants: List[str],
        quorum_size: Optional[int] = None,
    ) -> ConsensusResult:
        """
        提出提案
        
        Args:
            round_id: 轮次 ID
            value: 提案值
            participants: 参与者列表
            quorum_size: 法定人数
            
        Returns:
            ConsensusResult: 共识结果
        """
        pass
    
    @abstractmethod
    def vote(
        self,
        round_id: str,
        voter_id: str,
        value: Any,
        weight: float = 1.0,
        reason: str = "",
    ) -> bool:
        """
        投票
        
        Args:
            round_id: 轮次 ID
            voter_id: 投票者 ID
            value: 投票值
            weight: 投票权重
            reason: 投票理由
            
        Returns:
            bool: 投票是否被接受
        """
        pass
    
    @abstractmethod
    def check_decision(self, round_id: str) -> Optional[Any]:
        """
        检查是否达成决策
        
        Args:
            round_id: 轮次 ID
            
        Returns:
            Optional[Any]: 决策值，如果尚未达成则返回 None
        """
        pass
    
    def get_round(self, round_id: str) -> Optional['ConsensusRound']:
        """获取轮次信息"""
        return self._active_rounds.get(round_id)
    
    def cleanup_round(self, round_id: str) -> None:
        """清理轮次"""
        with self._lock:
            self._active_rounds.pop(round_id, None)


@dataclass
class ConsensusRound:
    """共识轮次"""
    round_id: str
    protocol: ConsensusProtocol
    proposed_value: Any
    participants: Set[str]
    votes: Dict[str, Vote] = field(default_factory=dict)
    
    quorum_size: int = 0
    status: str = "pending"  # pending, voting, decided, failed
    
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    decided_value: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class QuorumConsensus(ConsensusMechanism):
    """
    多数决共识
    
    简单多数同意即通过
    """
    
    def __init__(self):
        super().__init__(ConsensusProtocol.QUORUM)
    
    def propose(
        self,
        round_id: str,
        value: Any,
        participants: List[str],
        quorum_size: Optional[int] = None,
    ) -> ConsensusResult:
        """
        提出提案
        
        Args:
            round_id: 轮次 ID
            value: 提案值
            participants: 参与者列表
            quorum_size: 法定人数（默认为参与者数量的多数）
        """
        result = ConsensusResult(
            success=False,
            protocol=self.protocol,
            participants=participants,
            quorum_size=quorum_size or (len(participants) // 2 + 1),
        )
        
        # 创建轮次
        with self._lock:
            self._active_rounds[round_id] = ConsensusRound(
                round_id=round_id,
                protocol=self.protocol,
                proposed_value=value,
                participants=set(participants),
                quorum_size=result.quorum_size,
            )
        
        return result
    
    def vote(
        self,
        round_id: str,
        voter_id: str,
        value: Any,
        weight: float = 1.0,
        reason: str = "",
    ) -> bool:
        """投票"""
        with self._lock:
            round_info = self._active_rounds.get(round_id)
            if not round_info:
                return False
            
            if voter_id not in round_info.participants:
                return False
            
            vote = Vote(
                voter_id=voter_id,
                value=value,
                weight=weight,
                reason=reason,
            )
            
            round_info.votes[voter_id] = vote
            return True
    
    def check_decision(self, round_id: str) -> Optional[Any]:
        """检查决策"""
        with self._lock:
            round_info = self._active_rounds.get(round_id)
            if not round_info:
                return None
            
            # 统计投票
            agree = 0
            disagree = 0
            weighted_agree = 0.0
            weighted_disagree = 0.0
            weighted_total = 0.0
            
            for vote in round_info.votes.values():
                weighted_total += vote.weight
                if vote.value == round_info.proposed_value:
                    agree += 1
                    weighted_agree += vote.weight
                elif vote.value is not None:
                    disagree += 1
                    weighted_disagree += vote.weight
            
            # 检查是否达到多数
            total_votes = len(round_info.votes)
            required = round_info.quorum_size
            
            if total_votes >= required:
                if weighted_agree > weighted_total / 2:
                    round_info.status = "decided"
                    round_info.decided_value = round_info.proposed_value
                    return round_info.proposed_value
                elif weighted_disagree > weighted_total / 2:
                    round_info.status = "decided"
                    round_info.decided_value = None
                    return None
            
            return None


class WeightedConsensus(ConsensusMechanism):
    """
    加权共识
    
    根据 Agent 权重计算共识
    """
    
    def __init__(self):
        super().__init__(ConsensusProtocol.WEIGHTED)
        self._weights: Dict[str, float] = {}
    
    def set_weight(self, agent_id: str, weight: float) -> None:
        """设置 Agent 权重"""
        self._weights[agent_id] = weight
    
    def get_weight(self, agent_id: str) -> float:
        """获取 Agent 权重"""
        return self._weights.get(agent_id, 1.0)
    
    def propose(
        self,
        round_id: str,
        value: Any,
        participants: List[str],
        quorum_size: Optional[int] = None,
    ) -> ConsensusResult:
        """提出提案"""
        total_weight = sum(self.get_weight(p) for p in participants)
        
        result = ConsensusResult(
            success=False,
            protocol=self.protocol,
            participants=participants,
            quorum_size=quorum_size or int(total_weight / 2) + 1,
            metadata={"total_weight": total_weight},
        )
        
        with self._lock:
            self._active_rounds[round_id] = ConsensusRound(
                round_id=round_id,
                protocol=self.protocol,
                proposed_value=value,
                participants=set(participants),
                quorum_size=result.quorum_size,
            )
        
        return result
    
    def vote(
        self,
        round_id: str,
        voter_id: str,
        value: Any,
        weight: float = 1.0,
        reason: str = "",
    ) -> bool:
        """投票"""
        with self._lock:
            round_info = self._active_rounds.get(round_id)
            if not round_info:
                return False
            
            if voter_id not in round_info.participants:
                return False
            
            # 使用设置的权重或默认权重
            effective_weight = weight if weight != 1.0 else self.get_weight(voter_id)
            
            vote = Vote(
                voter_id=voter_id,
                value=value,
                weight=effective_weight,
                reason=reason,
            )
            
            round_info.votes[voter_id] = vote
            return True
    
    def check_decision(self, round_id: str) -> Optional[Any]:
        """检查决策"""
        with self._lock:
            round_info = self._active_rounds.get(round_id)
            if not round_info:
                return None
            
            total_weight = sum(self.get_weight(p) for p in round_info.participants)
            weighted_agree = 0.0
            weighted_disagree = 0.0
            
            for vote in round_info.votes.values():
                if vote.value == round_info.proposed_value:
                    weighted_agree += vote.weight
                elif vote.value is not None:
                    weighted_disagree += vote.weight
            
            # 检查是否达到加权多数
            if weighted_agree > total_weight / 2:
                round_info.status = "decided"
                round_info.decided_value = round_info.proposed_value
                return round_info.proposed_value
            elif weighted_disagree > total_weight / 2:
                round_info.status = "decided"
                round_info.decided_value = None
                return None
            
            return None


class UnanimousConsensus(ConsensusMechanism):
    """
    全员同意共识
    
    所有参与者都必须同意
    """
    
    def __init__(self):
        super().__init__(ConsensusProtocol.UNANIMOUS)
    
    def propose(
        self,
        round_id: str,
        value: Any,
        participants: List[str],
        quorum_size: Optional[int] = None,
    ) -> ConsensusResult:
        """提出提案"""
        result = ConsensusResult(
            success=False,
            protocol=self.protocol,
            participants=participants,
            quorum_size=len(participants),  # 全员
        )
        
        with self._lock:
            self._active_rounds[round_id] = ConsensusRound(
                round_id=round_id,
                protocol=self.protocol,
                proposed_value=value,
                participants=set(participants),
                quorum_size=result.quorum_size,
            )
        
        return result
    
    def vote(
        self,
        round_id: str,
        voter_id: str,
        value: Any,
        weight: float = 1.0,
        reason: str = "",
    ) -> bool:
        """投票"""
        with self._lock:
            round_info = self._active_rounds.get(round_id)
            if not round_info:
                return False
            
            if voter_id not in round_info.participants:
                return False
            
            vote = Vote(
                voter_id=voter_id,
                value=value,
                weight=weight,
                reason=reason,
            )
            
            round_info.votes[voter_id] = vote
            return True
    
    def check_decision(self, round_id: str) -> Optional[Any]:
        """检查决策"""
        with self._lock:
            round_info = self._active_rounds.get(round_id)
            if not round_info:
                return None
            
            # 检查是否所有人都已投票
            if len(round_info.votes) < len(round_info.participants):
                return None
            
            # 检查是否所有人都同意
            all_agree = all(
                vote.value == round_info.proposed_value
                for vote in round_info.votes.values()
            )
            
            if all_agree:
                round_info.status = "decided"
                round_info.decided_value = round_info.proposed_value
                return round_info.proposed_value
            
            # 有人不同意
            round_info.status = "failed"
            round_info.decided_value = None
            return None
