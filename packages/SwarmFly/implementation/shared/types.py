"""
FLY深度实现 - 类型定义
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


class Priority(Enum):
    """优先级枚举"""
    CRITICAL = 100  # 核心任务
    URGENT = 80    # 紧急任务
    NORMAL = 50    # 普通任务
    LOW = 20      # 低优先级


class MessageType(Enum):
    """消息类型"""
    TEXT = "text"
    JSON = "json"
    BINARY = "binary"
    RPC_REQUEST = "rpc_request"
    RPC_RESPONSE = "rpc_response"
    EVENT = "event"
    COMMAND = "command"


class ResourceType(Enum):
    """资源类型"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    COMPUTE = "compute"
    STORAGE = "storage"
    API = "api"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class AgentState(Enum):
    """智能体状态"""
    IDLE = "idle"
    BUSY = "busy"
    BLOCKED = "blocked"
    OFFLINE = "offline"
    ERROR = "error"
    INITIALIZING = "initializing"


class Realm(Enum):
    """境界等级"""
    R1_PRIMARY = ("初境", 1)   # 基础执行
    R2_AWARENESS = ("明境", 2)  # 规则理解
    R3_WISDOM = ("智境", 3)    # 趋势洞察
    R4_FLUIDITY = ("通境", 4)  # 涌现发现
    R5_TRANSCENDENCE = ("化境", 5)  # 自主进化
    
    @property
    def name_cn(self) -> str:
        return self.value[0]
    
    @property
    def level(self) -> int:
        return self.value[1]


class EnlightenmentLevel(Enum):
    """觉悟等级"""
    E1_BASIC = ("初觉", 1)      # 工具认知
    E2_AWARE = ("觉知", 2)     # 工具选择
    E3_AWAKENED = ("觉醒", 3)  # 工具组合
    E4_ENLIGHTENED = ("觉悟", 4)  # 工具创造
    E5_PERFECTED = ("圆觉", 5)  # 工具无碍
    
    @property
    def name_cn(self) -> str:
        return self.value[0]
    
    @property
    def level(self) -> int:
        return self.value[1]


@dataclass
class ResourceRequest:
    """资源请求"""
    resource_type: ResourceType
    amount: float
    priority: Priority = Priority.NORMAL
    timeout: int = 30  # 秒
    agent_id: Optional[str] = None


@dataclass
class ResourceAllocation:
    """资源分配"""
    allocation_id: str
    resource_type: ResourceType
    amount: float
    agent_id: str
    start_time: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class Conflict:
    """冲突描述"""
    conflict_id: str
    agents: List[str]
    resource: str
    conflict_type: str
    severity: Priority = Priority.NORMAL


@dataclass
class Resolution:
    """解决结果"""
    conflict_id: str
    resolved: bool
    strategy: str
    winner: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
