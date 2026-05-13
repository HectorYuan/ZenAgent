"""
资源仲裁器 (Resource Arbiter)

提供资源分配决策和冲突仲裁功能。
支持多种分配策略: 优先级、公平、轮询等。
"""

import time
import hashlib
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """资源类型"""
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    GPU = "gpu"
    CUSTOM = "custom"


class AllocationStrategy(Enum):
    """分配策略"""
    PRIORITY = "priority"           # 优先级分配
    FAIR_SHARE = "fair_share"      # 公平分配
    ROUND_ROBIN = "round_robin"    # 轮询分配
    FIRST_COME = "first_come"      # 先到先得
    LOAD_BALANCED = "load_balanced" # 负载均衡


@dataclass
class ResourceRequest:
    """资源请求"""
    request_id: str
    agent_id: str
    resource_type: ResourceType
    amount: float
    priority: int = 50
    timeout: float = 30.0  # 请求超时(秒)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        return (datetime.now() - self.created_at).total_seconds() > self.timeout


@dataclass
class ResourceAllocation:
    """资源分配"""
    allocation_id: str
    request_id: str
    agent_id: str
    resource_type: ResourceType
    amount: float
    granted_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    released: bool = False
    
    def is_valid(self) -> bool:
        """检查分配是否有效"""
        if self.released:
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True


@dataclass
class ArbitrationResult:
    """仲裁结果"""
    granted: bool
    allocation: Optional[ResourceAllocation] = None
    denied_reason: Optional[str] = None
    alternative_agent: Optional[str] = None
    queue_position: Optional[int] = None
    estimated_wait_time: float = 0.0


class ResourcePool:
    """资源池"""
    
    def __init__(self, resource_type: ResourceType, total_capacity: float):
        self.resource_type = resource_type
        self.total_capacity = total_capacity
        self.used_capacity: float = 0.0
        self.allocations: Dict[str, ResourceAllocation] = {}
        self.reserved_capacity: float = 0.0
    
    @property
    def available_capacity(self) -> float:
        """可用容量"""
        return self.total_capacity - self.used_capacity - self.reserved_capacity
    
    @property
    def utilization(self) -> float:
        """利用率"""
        if self.total_capacity <= 0:
            return 0.0
        return self.used_capacity / self.total_capacity
    
    def can_allocate(self, amount: float) -> bool:
        """检查是否可以分配"""
        return self.available_capacity >= amount
    
    def allocate(self, allocation: ResourceAllocation) -> bool:
        """执行分配"""
        if not self.can_allocate(allocation.amount):
            return False
        
        self.allocations[allocation.allocation_id] = allocation
        self.used_capacity += allocation.amount
        return True
    
    def release(self, allocation_id: str) -> bool:
        """释放分配"""
        if allocation_id in self.allocations:
            allocation = self.allocations[allocation_id]
            self.used_capacity -= allocation.amount
            del self.allocations[allocation_id]
            return True
        return False
    
    def reserve(self, amount: float):
        """预留容量"""
        self.reserved_capacity += amount
    
    def release_reservation(self, amount: float):
        """释放预留"""
        self.reserved_capacity = max(0, self.reserved_capacity - amount)


class ResourceArbiter:
    """
    资源仲裁器
    
    管理和分配资源，解决资源竞争:
    - 多资源类型管理
    - 多种分配策略
    - 资源预留
    - 抢占式分配
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 资源池
        self.pools: Dict[ResourceType, ResourcePool] = {}
        
        # 待处理请求队列
        self.pending_requests: Dict[ResourceType, List[ResourceRequest]] = defaultdict(list)
        
        # 分配历史
        self.allocation_history: List[ResourceAllocation] = []
        
        # 轮询计数器
        self.round_robin_counters: Dict[ResourceType, int] = defaultdict(int)
        
        # 默认策略
        self.default_strategy = AllocationStrategy(
            self.config.get('default_strategy', 'priority')
        )
        
        # 配置资源池
        self._init_resource_pools()
    
    def _init_resource_pools(self):
        """初始化资源池"""
        capacities = self.config.get('capacities', {})
        
        default_capacities = {
            ResourceType.CPU: 100.0,
            ResourceType.MEMORY: 1024.0,  # GB
            ResourceType.STORAGE: 10000.0,  # GB
            ResourceType.NETWORK: 1000.0,  # Mbps
            ResourceType.GPU: 8.0,
        }
        
        for res_type in ResourceType:
            capacity = capacities.get(res_type.value, default_capacities.get(res_type, 100.0))
            self.pools[res_type] = ResourcePool(res_type, capacity)
    
    def add_request(self, request: ResourceRequest) -> bool:
        """添加资源请求"""
        # 验证资源类型
        if isinstance(request.resource_type, str):
            try:
                request.resource_type = ResourceType(request.resource_type)
            except ValueError:
                logger.error(f"Invalid resource type: {request.resource_type}")
                return False
        
        # 添加到等待队列
        self.pending_requests[request.resource_type].append(request)
        
        # 按优先级排序
        self.pending_requests[request.resource_type].sort(
            key=lambda r: (r.priority, r.created_at),
            reverse=True
        )
        
        logger.debug(f"Request added: {request.request_id} for {request.resource_type.value}")
        return True
    
    def request_allocation(
        self,
        agent_id: str,
        resource_type: ResourceType,
        amount: float,
        priority: int = 50,
        timeout: float = 30.0,
        strategy: Optional[AllocationStrategy] = None
    ) -> ArbitrationResult:
        """
        请求资源分配
        
        Args:
            agent_id: 智能体ID
            resource_type: 资源类型
            amount: 请求数量
            priority: 优先级(0-100)
            timeout: 超时时间
            strategy: 分配策略
            
        Returns:
            ArbitrationResult: 仲裁结果
        """
        # 创建请求
        request = ResourceRequest(
            request_id=self._generate_request_id(agent_id, resource_type),
            agent_id=agent_id,
            resource_type=resource_type,
            amount=amount,
            priority=priority,
            timeout=timeout
        )
        
        # 检查资源池
        pool = self.pools.get(resource_type)
        if not pool:
            return ArbitrationResult(
                granted=False,
                denied_reason=f"Unknown resource type: {resource_type}"
            )
        
        # 尝试直接分配
        if pool.can_allocate(amount):
            allocation = self._create_allocation(request)
            if pool.allocate(allocation):
                self.allocation_history.append(allocation)
                return ArbitrationResult(granted=True, allocation=allocation)
        
        # 加入等待队列
        self.add_request(request)
        
        # 返回等待信息
        queue_position = len(self.pending_requests[resource_type])
        
        return ArbitrationResult(
            granted=False,
            queue_position=queue_position,
            estimated_wait_time=self._estimate_wait_time(resource_type, amount),
            denied_reason="Insufficient resources, request queued"
        )
    
    def _create_allocation(self, request: ResourceRequest) -> ResourceAllocation:
        """创建分配"""
        return ResourceAllocation(
            allocation_id=self._generate_allocation_id(request),
            request_id=request.request_id,
            agent_id=request.agent_id,
            resource_type=request.resource_type,
            amount=request.amount,
            expires_at=datetime.now() + timedelta(seconds=request.timeout)
        )
    
    def release_allocation(self, allocation_id: str) -> bool:
        """释放分配"""
        for pool in self.pools.values():
            if pool.release(allocation_id):
                # 尝试处理等待队列
                self._process_pending_requests(pool.resource_type)
                return True
        return False
    
    def release_agent_resources(self, agent_id: str) -> List[str]:
        """释放智能体的所有资源"""
        released = []
        
        for pool in self.pools.values():
            to_release = [
                alloc_id for alloc_id, alloc in pool.allocations.items()
                if alloc.agent_id == agent_id and not alloc.released
            ]
            
            for alloc_id in to_release:
                if pool.release(alloc_id):
                    released.append(alloc_id)
        
        return released
    
    def preempt_allocation(
        self,
        allocation_id: str,
        preemptor_id: str,
        reason: str = ""
    ) -> bool:
        """
        抢占式分配
        
        强制释放低优先级分配给高优先级请求
        """
        # 查找分配
        allocation = None
        pool = None
        
        for p in self.pools.values():
            if allocation_id in p.allocations:
                allocation = p.allocations[allocation_id]
                pool = p
                break
        
        if not allocation or not pool:
            return False
        
        # 检查是否可以抢占
        # (这里简化处理，实际应该比较优先级)
        pool.release(allocation_id)
        
        logger.warning(
            f"Allocation {allocation_id} preempted by {preemptor_id}: {reason}"
        )
        
        return True
    
    def _process_pending_requests(self, resource_type: ResourceType):
        """处理等待队列"""
        pool = self.pools.get(resource_type)
        if not pool:
            return
        
        queue = self.pending_requests[resource_type]
        processed = []
        
        for request in queue:
            # 跳过过期请求
            if request.is_expired:
                processed.append(request)
                continue
            
            # 尝试分配
            if pool.can_allocate(request.amount):
                allocation = self._create_allocation(request)
                if pool.allocate(allocation):
                    self.allocation_history.append(allocation)
                    processed.append(request)
                    logger.debug(f"Queued request granted: {request.request_id}")
        
        # 移除已处理请求
        for request in processed:
            if request in queue:
                queue.remove(request)
    
    def _estimate_wait_time(self, resource_type: ResourceType, amount: float) -> float:
        """估算等待时间"""
        pool = self.pools.get(resource_type)
        if not pool:
            return float('inf')
        
        queue = self.pending_requests[resource_type]
        if not queue:
            return 0.0
        
        # 简化估算: 假设平均每个请求使用5秒
        avg_request_time = 5.0
        position = len(queue)
        
        return position * avg_request_time
    
    def get_allocation(self, allocation_id: str) -> Optional[ResourceAllocation]:
        """获取分配信息"""
        for pool in self.pools.values():
            if allocation_id in pool.allocations:
                return pool.allocations[allocation_id]
        return None
    
    def get_agent_allocations(self, agent_id: str) -> List[ResourceAllocation]:
        """获取智能体的所有分配"""
        allocations = []
        for pool in self.pools.values():
            for alloc in pool.allocations.values():
                if alloc.agent_id == agent_id and not alloc.released:
                    allocations.append(alloc)
        return allocations
    
    def get_resource_status(self, resource_type: ResourceType) -> Dict[str, Any]:
        """获取资源状态"""
        pool = self.pools.get(resource_type)
        if not pool:
            return {}
        
        return {
            'type': pool.resource_type.value,
            'total': pool.total_capacity,
            'used': pool.used_capacity,
            'available': pool.available_capacity,
            'reserved': pool.reserved_capacity,
            'utilization': pool.utilization,
            'pending_requests': len(self.pending_requests[resource_type])
        }
    
    def _generate_request_id(self, agent_id: str, resource_type: ResourceType) -> str:
        """生成请求ID"""
        content = f"{agent_id}:{resource_type.value}:{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _generate_allocation_id(self, request: ResourceRequest) -> str:
        """生成分配ID"""
        content = f"{request.request_id}:{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_allocations': len(self.allocation_history),
            'active_allocations': sum(
                len(p.allocations) for p in self.pools.values()
            ),
            'pending_requests': sum(
                len(q) for q in self.pending_requests.values()
            ),
            'resource_status': {
                rt.value: self.get_resource_status(rt)
                for rt in self.pools.keys()
            }
        }
