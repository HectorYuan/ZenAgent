"""
SoulTeam 集群协议 — 统一消息格式 (M10 Phase A)

设计依据: 智能体集群运行机制 v1.2

7 种消息类型 + JSON 载荷 + correlation_id + 6 状态任务机
"""

import uuid
import time
import json
from enum import Enum
from typing import Optional, Any
from dataclasses import dataclass, field


class MessageType(str, Enum):
    TASK_REQUEST = "TASK_REQUEST"
    TASK_RESULT = "TASK_RESULT"
    STATUS_UPDATE = "STATUS_UPDATE"
    HEARTBEAT = "HEARTBEAT"
    QUERY_STATE = "QUERY_STATE"
    ABORT_TASK = "ABORT_TASK"
    ESCALATE = "ESCALATE"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"


class Priority(int, Enum):
    P0_CRITICAL = 0
    P1_URGENT = 1
    P2_HIGH = 2
    P3_NORMAL = 3
    P4_LOW = 4
    P5_BACKGROUND = 5


class ExecutionMode(str, Enum):
    SINGLE = "single"
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    FAN_OUT_FAN_IN = "fan_out_fan_in"
    CONDITIONAL = "conditional"


class CollaborationProtocol(str, Enum):
    MASTER_SLAVE = "MASTER_SLAVE"
    PEER_TO_PEER = "PEER_TO_PEER"
    HIERARCHICAL = "HIERARCHICAL"
    HYBRID = "HYBRID"


# ---- Message ----

@dataclass
class ClusterMessage:
    """统一集群消息"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    msg_type: MessageType = MessageType.TASK_REQUEST
    sender_id: str = ""
    receiver_id: str = ""
    correlation_id: str = ""
    payload: dict = field(default_factory=dict)
    priority: Priority = Priority.P3_NORMAL
    timestamp: float = field(default_factory=time.time)
    ttl: int = 300

    @classmethod
    def task_request(cls, sender: str, receiver: str, task_data: dict,
                     priority: Priority = Priority.P3_NORMAL) -> "ClusterMessage":
        cid = str(uuid.uuid4())[:8]
        return cls(
            msg_type=MessageType.TASK_REQUEST, sender_id=sender,
            receiver_id=receiver, correlation_id=cid,
            payload={"task": task_data, "status": TaskStatus.PENDING.value},
            priority=priority,
        )

    @classmethod
    def task_result(cls, sender: str, receiver: str, correlation_id: str,
                    result: Any, status: TaskStatus) -> "ClusterMessage":
        return cls(
            msg_type=MessageType.TASK_RESULT, sender_id=sender,
            receiver_id=receiver, correlation_id=correlation_id,
            payload={"result": result, "status": status.value},
        )

    @classmethod
    def heartbeat(cls, sender: str, zone: str = "A") -> "ClusterMessage":
        return cls(
            msg_type=MessageType.HEARTBEAT, sender_id=sender,
            payload={"zone": zone, "alive": True},
        )

    @classmethod
    def status_update(cls, sender: str, receiver: str, correlation_id: str,
                      status: TaskStatus) -> "ClusterMessage":
        return cls(
            msg_type=MessageType.STATUS_UPDATE, sender_id=sender,
            receiver_id=receiver, correlation_id=correlation_id,
            payload={"status": status.value},
        )

    @classmethod
    def abort(cls, sender: str, receiver: str, correlation_id: str,
              reason: str = "") -> "ClusterMessage":
        return cls(
            msg_type=MessageType.ABORT_TASK, sender_id=sender,
            receiver_id=receiver, correlation_id=correlation_id,
            payload={"reason": reason}, priority=Priority.P0_CRITICAL,
        )

    @classmethod
    def escalate(cls, sender: str, receiver: str, correlation_id: str,
                 reason: str) -> "ClusterMessage":
        return cls(
            msg_type=MessageType.ESCALATE, sender_id=sender,
            receiver_id=receiver, correlation_id=correlation_id,
            payload={"reason": reason}, priority=Priority.P1_URGENT,
        )

    def to_json(self) -> str:
        return json.dumps({
            "message_id": self.message_id,
            "msg_type": self.msg_type.value,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "correlation_id": self.correlation_id,
            "payload": self.payload,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
        }, ensure_ascii=False)

    @classmethod
    def from_json(cls, data: str) -> "ClusterMessage":
        d = json.loads(data)
        return cls(
            message_id=d.get("message_id", ""),
            msg_type=MessageType(d.get("msg_type", "TASK_REQUEST")),
            sender_id=d.get("sender_id", ""),
            receiver_id=d.get("receiver_id", ""),
            correlation_id=d.get("correlation_id", ""),
            payload=d.get("payload", {}),
            priority=Priority(d.get("priority", 3)),
            timestamp=d.get("timestamp", time.time()),
            ttl=d.get("ttl", 300),
        )


# ---- Baton (Zone heartbeat relay) ----

@dataclass
class Baton:
    """Zone 心跳接力棒"""
    zone: str = "A"
    holder_id: str = ""
    passed_at: float = field(default_factory=time.time)
    round_count: int = 0
    active_agents: list[str] = field(default_factory=list)

    def pass_to(self, zone: str, holder_id: str):
        self.zone = zone
        self.holder_id = holder_id
        self.passed_at = time.time()
        self.round_count += 1

    def to_json(self) -> str:
        return json.dumps({
            "zone": self.zone, "holder_id": self.holder_id,
            "passed_at": self.passed_at, "round_count": self.round_count,
            "active_agents": self.active_agents,
        })
