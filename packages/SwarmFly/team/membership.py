"""
成员管理

管理团队成员和成员关系
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
import threading
import uuid


class MembershipStatus(Enum):
    """成员状态枚举"""
    PENDING = "pending"         # 待审核
    ACTIVE = "active"           # 活跃
    INACTIVE = "inactive"       # 非活跃
    SUSPENDED = "suspended"      # 暂停
    REMOVED = "removed"         # 已移除


@dataclass
class Member:
    """
    成员
    
    表示团队中的一个成员
    """
    member_id: str
    agent_id: str
    team_id: str
    
    # 角色
    role: str = "worker"
    
    # 状态
    status: MembershipStatus = MembershipStatus.PENDING
    
    # 能力评分
    capability_scores: Dict[str, float] = field(default_factory=dict)
    
    # 统计
    tasks_completed: int = 0
    tasks_failed: int = 0
    
    # 时间
    joined_at: datetime = field(default_factory=datetime.now)
    last_active_at: datetime = field(default_factory=datetime.now)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_active(self) -> bool:
        """是否活跃"""
        return self.status == MembershipStatus.ACTIVE
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 0.0
        return self.tasks_completed / total
    
    @property
    def performance_score(self) -> float:
        """性能评分"""
        return self.success_rate * 0.7 + (1 / (1 + self.tasks_failed)) * 0.3
    
    def update_activity(self) -> None:
        """更新活动时间"""
        self.last_active_at = datetime.now()
    
    def record_task_completion(self, success: bool) -> None:
        """记录任务完成"""
        self.update_activity()
        if success:
            self.tasks_completed += 1
        else:
            self.tasks_failed += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "member_id": self.member_id,
            "agent_id": self.agent_id,
            "team_id": self.team_id,
            "role": self.role,
            "status": self.status.value,
            "capability_scores": self.capability_scores,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "success_rate": self.success_rate,
            "performance_score": self.performance_score,
            "joined_at": self.joined_at.isoformat(),
            "last_active_at": self.last_active_at.isoformat(),
        }


@dataclass
class MembershipRequest:
    """
    成员请求
    
    表示加入团队的请求
    """
    request_id: str
    agent_id: str
    team_id: str
    
    # 请求信息
    requested_role: str = "worker"
    reason: str = ""
    
    # 能力
    capabilities: Dict[str, float] = field(default_factory=dict)
    
    # 状态
    status: MembershipStatus = MembershipStatus.PENDING
    
    # 时间
    requested_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    processed_by: Optional[str] = None
    
    # 结果
    approved: bool = False
    rejection_reason: str = ""
    
    def approve(self, processed_by: Optional[str] = None) -> None:
        """批准请求"""
        self.status = MembershipStatus.ACTIVE
        self.processed_at = datetime.now()
        self.processed_by = processed_by
        self.approved = True
    
    def reject(self, reason: str, processed_by: Optional[str] = None) -> None:
        """拒绝请求"""
        self.status = MembershipStatus.REMOVED
        self.processed_at = datetime.now()
        self.processed_by = processed_by
        self.approved = False
        self.rejection_reason = reason
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "team_id": self.team_id,
            "requested_role": self.requested_role,
            "reason": self.reason,
            "status": self.status.value,
            "requested_at": self.requested_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "approved": self.approved,
            "rejection_reason": self.rejection_reason,
        }


class MembershipManager:
    """
    成员管理器
    
    管理团队成员和成员请求
    """
    
    def __init__(self, team_id: str):
        """
        初始化成员管理器
        
        Args:
            team_id: 团队 ID
        """
        self.team_id = team_id
        
        # 成员
        self._members: Dict[str, Member] = {}  # member_id -> Member
        self._agents: Dict[str, str] = {}  # agent_id -> member_id
        
        # 请求
        self._requests: Dict[str, MembershipRequest] = {}  # request_id -> Request
        
        # 角色分布
        self._role_counts: Dict[str, int] = {}
        
        # 锁
        self._lock = threading.RLock()
        
        # 回调
        self._on_member_added: List[callable] = []
        self._on_member_removed: List[callable] = []
        self._on_request_received: List[callable] = []
        self._on_request_processed: List[callable] = []
    
    @property
    def member_count(self) -> int:
        """成员数量"""
        return len(self._members)
    
    @property
    def active_member_count(self) -> int:
        """活跃成员数量"""
        return sum(1 for m in self._members.values() if m.is_active)
    
    def add_member(
        self,
        agent_id: str,
        role: str = "worker",
        capabilities: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Member:
        """
        添加成员
        
        Args:
            agent_id: Agent ID
            role: 角色
            capabilities: 能力评分
            metadata: 元数据
            
        Returns:
            Member: 创建的成员对象
        """
        with self._lock:
            # 检查是否已存在
            if agent_id in self._agents:
                return self._members[self._agents[agent_id]]
            
            member = Member(
                member_id=str(uuid.uuid4()),
                agent_id=agent_id,
                team_id=self.team_id,
                role=role,
                capability_scores=capabilities or {},
                metadata=metadata or {},
            )
            
            self._members[member.member_id] = member
            self._agents[agent_id] = member.member_id
            
            # 更新角色计数
            self._role_counts[role] = self._role_counts.get(role, 0) + 1
            
            # 触发回调
            for callback in self._on_member_added:
                try:
                    callback(member)
                except Exception:
                    pass
            
            return member
    
    def remove_member(self, agent_id: str) -> bool:
        """
        移除成员
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            if agent_id not in self._agents:
                return False
            
            member_id = self._agents[agent_id]
            member = self._members[member_id]
            
            # 更新状态
            member.status = MembershipStatus.REMOVED
            
            # 更新角色计数
            if member.role in self._role_counts:
                self._role_counts[member.role] = max(0, self._role_counts[member.role] - 1)
            
            # 移除
            self._agents.pop(agent_id)
            self._members.pop(member_id)
            
            # 触发回调
            for callback in self._on_member_removed:
                try:
                    callback(member)
                except Exception:
                    pass
            
            return True
    
    def get_member(self, agent_id: str) -> Optional[Member]:
        """获取成员"""
        member_id = self._agents.get(agent_id)
        return self._members.get(member_id) if member_id else None
    
    def get_all_members(self) -> List[Member]:
        """获取所有成员"""
        return list(self._members.values())
    
    def get_active_members(self) -> List[Member]:
        """获取活跃成员"""
        return [m for m in self._members.values() if m.is_active]
    
    def get_members_by_role(self, role: str) -> List[Member]:
        """获取指定角色的成员"""
        return [m for m in self._members.values() if m.role == role]
    
    def update_member_status(self, agent_id: str, status: MembershipStatus) -> bool:
        """
        更新成员状态
        
        Args:
            agent_id: Agent ID
            status: 新状态
            
        Returns:
            bool: 是否成功
        """
        member = self.get_member(agent_id)
        if not member:
            return False
        
        member.status = status
        if status == MembershipStatus.ACTIVE:
            member.update_activity()
        
        return True
    
    # ==================== 加入请求 ====================
    
    def create_request(
        self,
        agent_id: str,
        requested_role: str = "worker",
        reason: str = "",
        capabilities: Optional[Dict[str, float]] = None,
    ) -> MembershipRequest:
        """
        创建加入请求
        
        Args:
            agent_id: Agent ID
            requested_role: 请求的角色
            reason: 申请理由
            capabilities: 能力评分
            
        Returns:
            MembershipRequest: 创建的请求
        """
        with self._lock:
            request = MembershipRequest(
                request_id=str(uuid.uuid4()),
                agent_id=agent_id,
                team_id=self.team_id,
                requested_role=requested_role,
                reason=reason,
                capabilities=capabilities or {},
            )
            
            self._requests[request.request_id] = request
            
            # 触发回调
            for callback in self._on_request_received:
                try:
                    callback(request)
                except Exception:
                    pass
            
            return request
    
    def process_request(
        self,
        request_id: str,
        approved: bool,
        processed_by: Optional[str] = None,
        rejection_reason: str = "",
    ) -> bool:
        """
        处理加入请求
        
        Args:
            request_id: 请求 ID
            approved: 是否批准
            processed_by: 处理者 ID
            rejection_reason: 拒绝原因
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            request = self._requests.get(request_id)
            if not request:
                return False
            
            if approved:
                request.approve(processed_by)
                # 自动添加为成员
                self.add_member(
                    agent_id=request.agent_id,
                    role=request.requested_role,
                    capabilities=request.capabilities,
                )
            else:
                request.reject(rejection_reason, processed_by)
            
            # 触发回调
            for callback in self._on_request_processed:
                try:
                    callback(request)
                except Exception:
                    pass
            
            return True
    
    def get_pending_requests(self) -> List[MembershipRequest]:
        """获取待处理的请求"""
        return [
            r for r in self._requests.values()
            if r.status == MembershipStatus.PENDING
        ]
    
    def get_request(self, request_id: str) -> Optional[MembershipRequest]:
        """获取请求"""
        return self._requests.get(request_id)
    
    # ==================== 统计 ====================
    
    def get_role_distribution(self) -> Dict[str, int]:
        """获取角色分布"""
        return self._role_counts.copy()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        members = self.get_all_members()
        
        if not members:
            return {
                "total_members": 0,
                "active_members": 0,
                "avg_success_rate": 0.0,
                "avg_performance": 0.0,
            }
        
        return {
            "total_members": len(members),
            "active_members": self.active_member_count,
            "avg_success_rate": sum(m.success_rate for m in members) / len(members),
            "avg_performance": sum(m.performance_score for m in members) / len(members),
            "role_distribution": self.get_role_distribution(),
        }
    
    # ==================== 回调 ====================
    
    def register_callback(
        self,
        event: str,
        callback: callable,
    ) -> None:
        """注册回调"""
        if event == "member_added":
            self._on_member_added.append(callback)
        elif event == "member_removed":
            self._on_member_removed.append(callback)
        elif event == "request_received":
            self._on_request_received.append(callback)
        elif event == "request_processed":
            self._on_request_processed.append(callback)
