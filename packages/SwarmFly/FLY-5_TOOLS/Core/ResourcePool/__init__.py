"""
资源池 (Resource Pool)

提供计算和连接资源的管理。
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import asyncio

logger = logging.getLogger(__name__)


class ResourceState(Enum):
    """资源状态"""
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"


@dataclass
class Resource:
    """资源对象"""
    resource_id: str
    resource_type: str  # cpu, memory, gpu, connection
    capacity: float
    used: float = 0.0
    state: ResourceState = ResourceState.AVAILABLE
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def available(self) -> float:
        """可用量"""
        return max(0, self.capacity - self.used)
    
    @property
    def utilization(self) -> float:
        """利用率"""
        if self.capacity <= 0:
            return 0.0
        return self.used / self.capacity


@dataclass
class Allocation:
    """资源分配"""
    allocation_id: str
    resource_id: str
    requester: str
    amount: float
    allocated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


@dataclass
class ResourceRequest:
    """资源请求"""
    request_id: str
    requester: str
    resource_type: str
    amount: float
    priority: int = 50
    timeout: float = 30.0


@dataclass
class AllocationResult:
    """分配结果"""
    success: bool
    allocation: Optional[Allocation] = None
    error: Optional[str] = None
    wait_time_ms: float = 0.0


class ComputePool:
    """计算资源池"""
    
    def __init__(self, capacity: float = 100.0):
        self.total_capacity = capacity
        self.used_capacity = 0.0
        self.allocations: Dict[str, Allocation] = {}
        self.wait_queue: List[ResourceRequest] = []
    
    @property
    def available(self) -> float:
        return self.total_capacity - self.used_capacity
    
    def can_allocate(self, amount: float) -> bool:
        return self.available >= amount
    
    def allocate(self, allocation: Allocation) -> bool:
        if not self.can_allocate(allocation.amount):
            return False
        
        self.allocations[allocation.allocation_id] = allocation
        self.used_capacity += allocation.amount
        return True
    
    def release(self, allocation_id: str) -> bool:
        if allocation_id in self.allocations:
            amount = self.allocations[allocation_id].amount
            del self.allocations[allocation_id]
            self.used_capacity -= amount
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            'total_capacity': self.total_capacity,
            'used': self.used_capacity,
            'available': self.available,
            'utilization': self.used_capacity / self.total_capacity if self.total_capacity else 0,
            'active_allocations': len(self.allocations)
        }


class ConnectionPool:
    """连接资源池"""
    
    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self.active_connections: Dict[str, Any] = {}
        self.available_connections: List[Any] = []
        self.allocations: Dict[str, Allocation] = {}
    
    @property
    def available_count(self) -> int:
        return self.max_connections - len(self.active_connections)
    
    def acquire(self, allocation: Allocation, factory: callable) -> Optional[Any]:
        if not self.can_acquire():
            return None
        
        # 获取或创建连接
        if self.available_connections:
            conn = self.available_connections.pop()
        else:
            try:
                conn = factory()
            except Exception as e:
                logger.error(f"Connection factory error: {e}")
                return None
        
        self.active_connections[allocation.allocation_id] = conn
        self.allocations[allocation.allocation_id] = allocation
        return conn
    
    def release(self, allocation_id: str) -> bool:
        if allocation_id in self.active_connections:
            conn = self.active_connections.pop(allocation_id)
            if len(self.available_connections) < self.max_connections // 2:
                self.available_connections.append(conn)
            del self.allocations[allocation_id]
            return True
        return False
    
    def can_acquire(self) -> bool:
        return len(self.active_connections) < self.max_connections
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            'max_connections': self.max_connections,
            'active': len(self.active_connections),
            'available': self.available_count,
            'utilization': len(self.active_connections) / self.max_connections
        }


class PoolManager:
    """
    资源池管理器
    
    管理多种类型的资源池:
    - 计算资源池
    - 连接资源池
    - 内存资源池
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 资源池
        self.pools: Dict[str, Any] = {
            'compute': ComputePool(self.config.get('compute_capacity', 100.0)),
            'memory': ComputePool(self.config.get('memory_capacity', 1024.0)),
            'connections': ConnectionPool(self.config.get('max_connections', 100))
        }
        
        # 分配记录
        self.allocation_history: List[Allocation] = []
        
        # 统计
        self.stats = {
            'total_allocations': 0,
            'successful_allocations': 0,
            'failed_allocations': 0,
            'total_releases': 0
        }
    
    async def allocate(
        self,
        requester: str,
        resource_type: str,
        amount: float,
        priority: int = 50,
        timeout: float = 30.0
    ) -> AllocationResult:
        """
        申请资源分配
        
        Args:
            requester: 请求者ID
            resource_type: 资源类型
            amount: 需求量
            priority: 优先级
            timeout: 超时时间
            
        Returns:
            AllocationResult: 分配结果
        """
        import time
        start_time = time.time()
        
        request = ResourceRequest(
            request_id=f"req_{start_time}",
            requester=requester,
            resource_type=resource_type,
            amount=amount,
            priority=priority
        )
        
        pool = self.pools.get(resource_type)
        if not pool:
            return AllocationResult(
                success=False,
                error=f"Unknown resource type: {resource_type}"
            )
        
        # 检查是否可分配
        if hasattr(pool, 'can_allocate'):
            can_allocate = pool.can_allocate(amount)
        else:
            can_allocate = pool.available_count > 0 if hasattr(pool, 'available_count') else True
        
        if not can_allocate:
            # 加入等待队列
            if hasattr(pool, 'wait_queue'):
                pool.wait_queue.append(request)
            
            # 等待
            wait_start = time.time()
            while time.time() - wait_start < timeout:
                await asyncio.sleep(0.1)
                
                if hasattr(pool, 'can_allocate'):
                    can_allocate = pool.can_allocate(amount)
                else:
                    can_allocate = True
                
                if can_allocate:
                    break
            
            if not can_allocate:
                self.stats['failed_allocations'] += 1
                return AllocationResult(
                    success=False,
                    error="Allocation timeout",
                    wait_time_ms=(time.time() - start_time) * 1000
                )
        
        # 执行分配
        import uuid
        allocation = Allocation(
            allocation_id=str(uuid.uuid4())[:12],
            resource_id=f"{resource_type}_{int(time.time())}",
            requester=requester,
            amount=amount
        )
        
        if hasattr(pool, 'allocate'):
            success = pool.allocate(allocation)
        else:
            conn = pool.acquire(allocation, lambda: None)
            success = conn is not None
        
        if success:
            self.allocation_history.append(allocation)
            self.stats['successful_allocations'] += 1
            self.stats['total_allocations'] += 1
            
            return AllocationResult(
                success=True,
                allocation=allocation,
                wait_time_ms=(time.time() - start_time) * 1000
            )
        else:
            self.stats['failed_allocations'] += 1
            return AllocationResult(
                success=False,
                error="Allocation failed"
            )
    
    async def release(self, allocation_id: str, resource_type: str) -> bool:
        """释放资源"""
        pool = self.pools.get(resource_type)
        if not pool:
            return False
        
        if hasattr(pool, 'release'):
            success = pool.release(allocation_id)
        else:
            success = pool.release(allocation_id)
        
        if success:
            self.stats['total_releases'] += 1
            logger.info(f"Resource released: {allocation_id}")
        
        return success
    
    def get_pool_stats(self, resource_type: str) -> Dict[str, Any]:
        """获取池统计"""
        pool = self.pools.get(resource_type)
        if not pool:
            return {}
        
        if hasattr(pool, 'get_stats'):
            return pool.get_stats()
        
        return {
            'active_allocations': len(pool.allocations) if hasattr(pool, 'allocations') else 0
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有池统计"""
        return {
            **self.stats,
            'pools': {
                name: pool.get_stats() if hasattr(pool, 'get_stats') else {}
                for name, pool in self.pools.items()
            }
        }
