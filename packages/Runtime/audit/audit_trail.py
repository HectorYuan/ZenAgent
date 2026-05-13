"""
审计轨迹管理

提供审计记录的存储、查询、分析和追踪功能
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Set, Iterator
from collections import defaultdict, deque
import json
import threading
import uuid
import bisect


class AuditRecordType(Enum):
    """审计记录类型"""
    EVENT = "event"              # 普通事件
    TRANSACTION = "transaction"  # 事务
    SESSION = "session"          # 会话
    RELATIONSHIP = "relationship"  # 关系


class RecordStatus(Enum):
    """记录状态"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    COMPROMISED = "compromised"


@dataclass
class AuditRecord:
    """
    审计记录
    
    代表一个完整的审计轨迹条目
    """
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    record_type: AuditRecordType = AuditRecordType.EVENT
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 标识信息
    actor_id: str = ""
    actor_type: str = "system"
    session_id: Optional[str] = None
    
    # 资源信息
    resource_type: str = ""
    resource_id: str = ""
    
    # 操作信息
    operation: str = ""
    action: str = ""
    status: str = "success"
    
    # 数据
    details: Dict[str, Any] = field(default_factory=dict)
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    
    # 追踪
    correlation_id: Optional[str] = None
    parent_record_id: Optional[str] = None
    child_record_ids: List[str] = field(default_factory=list)
    
    # 元数据
    status_flag: RecordStatus = RecordStatus.ACTIVE
    tags: Set[str] = field(default_factory=set)
    retention_days: int = 365  # 默认保留一年
    checksum: Optional[str] = None
    
    # 位置信息
    source_ip: Optional[str] = None
    source_location: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "record_id": self.record_id,
            "record_type": self.record_type.value,
            "timestamp": self.timestamp.isoformat(),
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "session_id": self.session_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "operation": self.operation,
            "action": self.action,
            "status": self.status,
            "details": self.details,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "correlation_id": self.correlation_id,
            "parent_record_id": self.parent_record_id,
            "child_record_ids": self.child_record_ids,
            "status_flag": self.status_flag.value,
            "tags": list(self.tags),
            "retention_days": self.retention_days,
            "checksum": self.checksum,
            "source_ip": self.source_ip,
            "source_location": self.source_location,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditRecord":
        """从字典创建"""
        data = data.copy()
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if "record_type" in data:
            data["record_type"] = AuditRecordType(data["record_type"])
        if "status_flag" in data:
            data["status_flag"] = RecordStatus(data["status_flag"])
        if "tags" in data and isinstance(data["tags"], list):
            data["tags"] = set(data["tags"])
        return cls(**data)
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        expiry_date = self.timestamp + timedelta(days=self.retention_days)
        return datetime.now() > expiry_date


@dataclass
class AuditQuery:
    """审计查询条件"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # 标识过滤
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None
    session_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    
    # 操作过滤
    operation: Optional[str] = None
    action: Optional[str] = None
    status: Optional[str] = None
    
    # 追踪过滤
    correlation_id: Optional[str] = None
    record_id: Optional[str] = None
    parent_record_id: Optional[str] = None
    
    # 标签过滤
    tags: Optional[Set[str]] = None
    any_tags: bool = False  # True: 匹配任一标签, False: 匹配所有标签
    
    # 状态过滤
    status_flags: Optional[Set[RecordStatus]] = None
    
    # 分页
    limit: int = 100
    offset: int = 0
    
    # 排序
    order_by: str = "timestamp"  # timestamp, record_id
    order_desc: bool = True  # 降序


class AuditTrail:
    """
    审计轨迹管理器
    
    提供审计记录的存储、索引、查询和分析功能
    """
    
    def __init__(
        self,
        max_records: int = 100000,
        enable_indexing: bool = True,
        enable_compression: bool = False,
    ):
        self.max_records = max_records
        self.enable_indexing = enable_indexing
        self.enable_compression = enable_compression
        
        # 存储
        self._records: List[AuditRecord] = []
        self._record_map: Dict[str, AuditRecord] = {}
        self._lock = threading.RLock()
        
        # 索引
        self._indexes: Dict[str, Dict[str, List[int]]] = defaultdict(dict)
        
        # 时间索引（用于高效时间范围查询）
        self._timestamps: List[datetime] = []
        
        # 统计
        self._stats = {
            "total_records": 0,
            "by_type": defaultdict(int),
            "by_status": defaultdict(int),
            "by_actor": defaultdict(int),
        }
        self._stats_lock = threading.Lock()
    
    def add(
        self,
        record: AuditRecord,
        compute_checksum: bool = True,
    ) -> str:
        """
        添加审计记录
        
        Args:
            record: 审计记录
            compute_checksum: 是否计算校验和
            
        Returns:
            记录 ID
        """
        with self._lock:
            # 计算校验和
            if compute_checksum and record.checksum is None:
                record.checksum = self._compute_checksum(record)
            
            # 检查重复
            if record.record_id in self._record_map:
                return record.record_id
            
            # 添加记录
            idx = len(self._records)
            self._records.append(record)
            self._record_map[record.record_id] = record
            
            # 更新时间索引
            bisect.insort(self._timestamps, record.timestamp)
            
            # 更新倒排索引
            if self.enable_indexing:
                self._update_indexes(record, idx)
            
            # 更新统计
            with self._stats_lock:
                self._stats["total_records"] += 1
                self._stats["by_type"][record.record_type.value] += 1
                self._stats["by_status"][record.status_flag.value] += 1
                if record.actor_id:
                    self._stats["by_actor"][record.actor_id] += 1
            
            # 清理过期记录
            self._cleanup_old_records()
            
            return record.record_id
    
    def _compute_checksum(self, record: AuditRecord) -> str:
        """计算记录校验和"""
        import hashlib
        data = json.dumps(record.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _update_indexes(self, record: AuditRecord, idx: int) -> None:
        """更新索引"""
        # 按 actor_id 索引
        if record.actor_id:
            self._add_to_index("actor_id", record.actor_id, idx)
        
        # 按 session_id 索引
        if record.session_id:
            self._add_to_index("session_id", record.session_id, idx)
        
        # 按 resource_type 索引
        if record.resource_type:
            self._add_to_index("resource_type", record.resource_type, idx)
        
        # 按 resource_id 索引
        if record.resource_id:
            self._add_to_index("resource_id", record.resource_id, idx)
        
        # 按 operation 索引
        if record.operation:
            self._add_to_index("operation", record.operation, idx)
        
        # 按 correlation_id 索引
        if record.correlation_id:
            self._add_to_index("correlation_id", record.correlation_id, idx)
        
        # 按 status 索引
        self._add_to_index("status", record.status, idx)
        
        # 按 tags 索引
        for tag in record.tags:
            self._add_to_index("tags", tag, idx)
    
    def _add_to_index(
        self,
        index_name: str,
        key: str,
        idx: int,
    ) -> None:
        """添加到索引"""
        if key not in self._indexes[index_name]:
            self._indexes[index_name][key] = []
        if idx not in self._indexes[index_name][key]:
            bisect.insort(self._indexes[index_name][key], idx)
    
    def _cleanup_old_records(self) -> None:
        """清理过期记录"""
        while len(self._records) > self.max_records:
            old_record = self._records.pop(0)
            self._timestamps.pop(0)
            self._record_map.pop(old_record.record_id, None)
            
            # 更新统计
            with self._stats_lock:
                self._stats["total_records"] -= 1
                self._stats["by_type"][old_record.record_type.value] -= 1
                self._stats["by_status"][old_record.status_flag.value] -= 1
    
    def get(self, record_id: str) -> Optional[AuditRecord]:
        """获取指定记录"""
        return self._record_map.get(record_id)
    
    def query(self, query: AuditQuery) -> List[AuditRecord]:
        """
        查询审计记录
        
        Args:
            query: 查询条件
            
        Returns:
            匹配的记录列表
        """
        with self._lock:
            # 使用索引加速查询
            candidate_indices: Optional[Set[int]] = None
            
            if self.enable_indexing:
                # 基于 actor_id 过滤
                if query.actor_id and "actor_id" in self._indexes:
                    indices = set(self._indexes["actor_id"].get(query.actor_id, []))
                    candidate_indices = indices if candidate_indices is None else candidate_indices & indices
                
                # 基于 session_id 过滤
                if query.session_id and "session_id" in self._indexes:
                    indices = set(self._indexes["session_id"].get(query.session_id, []))
                    candidate_indices = indices if candidate_indices is None else candidate_indices & indices
                
                # 基于 resource_type 过滤
                if query.resource_type and "resource_type" in self._indexes:
                    indices = set(self._indexes["resource_type"].get(query.resource_type, []))
                    candidate_indices = indices if candidate_indices is None else candidate_indices & indices
                
                # 基于 resource_id 过滤
                if query.resource_id and "resource_id" in self._indexes:
                    indices = set(self._indexes["resource_id"].get(query.resource_id, []))
                    candidate_indices = indices if candidate_indices is None else candidate_indices & indices
                
                # 基于 operation 过滤
                if query.operation and "operation" in self._indexes:
                    indices = set(self._indexes["operation"].get(query.operation, []))
                    candidate_indices = indices if candidate_indices is None else candidate_indices & indices
                
                # 基于 correlation_id 过滤
                if query.correlation_id and "correlation_id" in self._indexes:
                    indices = set(self._indexes["correlation_id"].get(query.correlation_id, []))
                    candidate_indices = indices if candidate_indices is None else candidate_indices & indices
                
                # 基于 tags 过滤
                if query.tags and "tags" in self._indexes:
                    tag_indices_sets = [set(self._indexes["tags"].get(tag, [])) for tag in query.tags]
                    if query.any_tags:
                        combined = set()
                        for s in tag_indices_sets:
                            combined |= s
                    else:
                        combined = tag_indices_sets[0]
                        for s in tag_indices_sets[1:]:
                            combined &= s
                    candidate_indices = combined if candidate_indices is None else candidate_indices & combined
                
                # 基于 status 过滤
                if query.status and "status" in self._indexes:
                    indices = set(self._indexes["status"].get(query.status, []))
                    candidate_indices = indices if candidate_indices is None else candidate_indices & indices
            
            # 时间范围过滤（使用二分查找）
            start_idx, end_idx = 0, len(self._records)
            if query.start_time:
                start_idx = bisect.bisect_left(self._timestamps, query.start_time)
            if query.end_time:
                end_idx = bisect.bisect_right(self._timestamps, query.end_time)
            
            # 合并时间和候选索引
            if candidate_indices is not None:
                time_indices = set(range(start_idx, end_idx))
                candidate_indices = candidate_indices & time_indices
            else:
                candidate_indices = set(range(start_idx, end_idx))
            
            # 获取候选记录
            results = [self._records[i] for i in sorted(candidate_indices)]
            
            # 过滤其他条件
            if query.actor_type:
                results = [r for r in results if r.actor_type == query.actor_type]
            if query.action:
                results = [r for r in results if r.action == query.action]
            if query.record_id:
                results = [r for r in results if r.record_id == query.record_id]
            if query.parent_record_id:
                results = [r for r in results if r.parent_record_id == query.parent_record_id]
            if query.status_flags:
                results = [r for r in results if r.status_flag in query.status_flags]
            
            # 排序
            if query.order_by == "timestamp":
                results.sort(key=lambda r: r.timestamp, reverse=query.order_desc)
            elif query.order_by == "record_id":
                results.sort(key=lambda r: r.record_id, reverse=query.order_desc)
            
            # 分页
            return results[query.offset:query.offset + query.limit]
    
    def get_trace(self, correlation_id: str) -> List[AuditRecord]:
        """获取完整追踪链"""
        return self.query(AuditQuery(correlation_id=correlation_id, limit=1000))
    
    def get_session_records(self, session_id: str) -> List[AuditRecord]:
        """获取会话所有记录"""
        return self.query(AuditQuery(session_id=session_id, limit=1000))
    
    def get_actor_activity(self, actor_id: str) -> List[AuditRecord]:
        """获取操作者活动记录"""
        return self.query(AuditQuery(actor_id=actor_id, limit=1000))
    
    def get_failed_operations(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[AuditRecord]:
        """获取失败操作"""
        return self.query(AuditQuery(
            start_time=start_time,
            end_time=end_time,
            status="failure",
            limit=1000,
        ))
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._stats_lock:
            stats = dict(self._stats)
            stats["by_type"] = dict(stats["by_type"])
            stats["by_status"] = dict(stats["by_status"])
            stats["by_actor"] = dict(stats["by_actor"])
            return stats
    
    def get_active_sessions(self) -> Set[str]:
        """获取活跃会话"""
        with self._lock:
            return set(r.session_id for r in self._records if r.session_id)
    
    def mark_compromised(self, record_id: str) -> bool:
        """标记记录为已泄露"""
        record = self.get(record_id)
        if record:
            record.status_flag = RecordStatus.COMPROMISED
            return True
        return False
    
    def archive(self, record_id: str) -> bool:
        """归档记录"""
        record = self.get(record_id)
        if record:
            record.status_flag = RecordStatus.ARCHIVED
            return True
        return False
    
    def __len__(self) -> int:
        """获取记录总数"""
        return len(self._records)
    
    def __iter__(self) -> Iterator[AuditRecord]:
        """迭代器"""
        return iter(self._records)
    
    def __getitem__(self, record_id: str) -> Optional[AuditRecord]:
        """获取指定记录"""
        return self.get(record_id)


# 全局审计轨迹实例
_default_trail: Optional[AuditTrail] = None
_trail_lock = threading.Lock()


def get_default_trail() -> AuditTrail:
    """获取默认审计轨迹实例"""
    global _default_trail
    with _trail_lock:
        if _default_trail is None:
            _default_trail = AuditTrail()
        return _default_trail


def set_default_trail(trail: AuditTrail) -> None:
    """设置默认审计轨迹实例"""
    global _default_trail
    with _trail_lock:
        _default_trail = trail
