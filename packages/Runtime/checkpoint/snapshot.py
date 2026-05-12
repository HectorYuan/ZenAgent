"""
快照管理 - Snapshot Manager

提供状态快照的创建、存储和恢复功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
import uuid


class SnapshotType(Enum):
    """快照类型"""
    FULL = "full"             # 完整快照
    INCREMENTAL = "incremental" # 增量快照
    DELTA = "delta"           # 差异快照


@dataclass
class Snapshot:
    """快照"""
    snapshot_id: str
    aggregate_id: str
    snapshot_type: SnapshotType
    state: Dict[str, Any]
    version: int
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    checksum: Optional[str] = None
    parent_snapshot_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "snapshot_id": self.snapshot_id,
            "aggregate_id": self.aggregate_id,
            "snapshot_type": self.snapshot_type.value,
            "state": self.state,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "checksum": self.checksum,
            "parent_snapshot_id": self.parent_snapshot_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Snapshot":
        """从字典创建"""
        data = data.copy()
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["snapshot_type"] = SnapshotType(data["snapshot_type"])
        return cls(**data)
    
    def verify(self) -> bool:
        """验证快照完整性"""
        if not self.checksum:
            return True
        current_checksum = self._calculate_checksum()
        return current_checksum == self.checksum
    
    def _calculate_checksum(self) -> str:
        """计算校验和"""
        content = json.dumps(self.state, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


class SnapshotManager:
    """
    快照管理器
    
    负责创建、管理和恢复快照。
    支持多种快照策略和版本管理。
    """
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        max_snapshots: int = 10,
        auto_snapshot: bool = True,
        snapshot_interval: int = 100
    ):
        """
        初始化快照管理器
        
        Args:
            storage_path: 存储路径
            max_snapshots: 最大快照数量
            auto_snapshot: 是否自动创建快照
            snapshot_interval: 自动快照间隔（事件数）
        """
        self.storage_path = storage_path
        self.max_snapshots = max_snapshots
        self.auto_snapshot = auto_snapshot
        self.snapshot_interval = snapshot_interval
        
        self._snapshots: Dict[str, List[Snapshot]] = {}
        self._version_counter: Dict[str, int] = {}
        self._snapshots_enabled: Dict[str, bool] = {}
        self._snapshot_hooks: Dict[str, List[Callable]] = {
            "before_snapshot": [],
            "after_snapshot": [],
            "before_restore": [],
            "after_restore": []
        }
    
    def create_snapshot(
        self,
        aggregate_id: str,
        state: Dict[str, Any],
        snapshot_type: SnapshotType = SnapshotType.FULL,
        metadata: Optional[Dict[str, Any]] = None,
        force: bool = False
    ) -> Snapshot:
        """
        创建快照
        
        Args:
            aggregate_id: 聚合 ID
            state: 状态数据
            snapshot_type: 快照类型
            metadata: 快照元数据
            force: 是否强制创建
            
        Returns:
            Snapshot: 创建的快照
        """
        # 检查是否启用快照
        if not force and not self._snapshots_enabled.get(aggregate_id, True):
            raise ValueError(f"Snapshot is disabled for aggregate {aggregate_id}")
        
        # 触发前置钩子
        for hook in self._snapshot_hooks["before_snapshot"]:
            hook(aggregate_id, state)
        
        # 获取版本号
        if aggregate_id not in self._version_counter:
            self._version_counter[aggregate_id] = 0
        self._version_counter[aggregate_id] += 1
        version = self._version_counter[aggregate_id]
        
        # 获取父快照 ID
        parent_id = None
        if self._snapshots.get(aggregate_id):
            parent_id = self._snapshots[aggregate_id][-1].snapshot_id
        
        # 创建快照
        snapshot = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            aggregate_id=aggregate_id,
            snapshot_type=snapshot_type,
            state=state,
            version=version,
            created_at=datetime.now(),
            metadata=metadata or {},
            checksum=self._calculate_checksum(state),
            parent_snapshot_id=parent_id
        )
        
        # 存储快照
        if aggregate_id not in self._snapshots:
            self._snapshots[aggregate_id] = []
        self._snapshots[aggregate_id].append(snapshot)
        
        # 清理旧快照
        self._cleanup_old_snapshots(aggregate_id)
        
        # 持久化
        if self.storage_path:
            self._persist_snapshot(snapshot)
        
        # 触发后置钩子
        for hook in self._snapshot_hooks["after_snapshot"]:
            hook(snapshot)
        
        return snapshot
    
    def get_snapshot(
        self,
        aggregate_id: str,
        version: Optional[int] = None,
        snapshot_id: Optional[str] = None
    ) -> Optional[Snapshot]:
        """
        获取快照
        
        Args:
            aggregate_id: 聚合 ID
            version: 版本号
            snapshot_id: 快照 ID
            
        Returns:
            Optional[Snapshot]: 快照
        """
        snapshots = self._snapshots.get(aggregate_id, [])
        
        if snapshot_id:
            for snap in reversed(snapshots):
                if snap.snapshot_id == snapshot_id:
                    return snap
        elif version is not None:
            for snap in reversed(snapshots):
                if snap.version == version:
                    return snap
        else:
            # 返回最新快照
            return snapshots[-1] if snapshots else None
        
        return None
    
    def get_latest_snapshot(self, aggregate_id: str) -> Optional[Snapshot]:
        """获取最新快照"""
        snapshots = self._snapshots.get(aggregate_id, [])
        return snapshots[-1] if snapshots else None
    
    def get_all_snapshots(self, aggregate_id: str) -> List[Snapshot]:
        """获取所有快照"""
        return self._snapshots.get(aggregate_id, []).copy()
    
    def restore_snapshot(
        self,
        aggregate_id: str,
        version: Optional[int] = None,
        snapshot_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        恢复快照
        
        Args:
            aggregate_id: 聚合 ID
            version: 版本号
            snapshot_id: 快照 ID
            
        Returns:
            Optional[Dict]: 恢复的状态
        """
        snapshot = self.get_snapshot(aggregate_id, version, snapshot_id)
        
        if not snapshot:
            return None
        
        # 验证快照完整性
        if not snapshot.verify():
            raise ValueError(f"Snapshot {snapshot.snapshot_id} failed verification")
        
        # 触发前置钩子
        for hook in self._snapshot_hooks["before_restore"]:
            hook(snapshot)
        
        # 恢复状态
        state = snapshot.state
        
        # 触发后置钩子
        for hook in self._snapshot_hooks["after_restore"]:
            hook(snapshot, state)
        
        return state
    
    def enable_snapshot(self, aggregate_id: str) -> None:
        """启用快照"""
        self._snapshots_enabled[aggregate_id] = True
    
    def disable_snapshot(self, aggregate_id: str) -> None:
        """禁用快照"""
        self._snapshots_enabled[aggregate_id] = False
    
    def should_create_snapshot(self, aggregate_id: str, event_count: int) -> bool:
        """
        检查是否应该创建快照
        
        Args:
            aggregate_id: 聚合 ID
            event_count: 事件数量
            
        Returns:
            bool: 是否应该创建
        """
        if not self.auto_snapshot:
            return False
        
        latest = self.get_latest_snapshot(aggregate_id)
        if not latest:
            return True
        
        return (event_count - latest.version * self.snapshot_interval) >= self.snapshot_interval
    
    def register_hook(self, event: str, callback: Callable) -> None:
        """
        注册钩子
        
        Args:
            event: 事件名称
            callback: 回调函数
        """
        if event in self._snapshot_hooks:
            self._snapshot_hooks[event].append(callback)
    
    def delete_snapshot(
        self,
        aggregate_id: str,
        snapshot_id: Optional[str] = None
    ) -> bool:
        """
        删除快照
        
        Args:
            aggregate_id: 聚合 ID
            snapshot_id: 快照 ID，为空则删除所有
            
        Returns:
            bool: 是否删除成功
        """
        if snapshot_id:
            snapshots = self._snapshots.get(aggregate_id, [])
            for i, snap in enumerate(snapshots):
                if snap.snapshot_id == snapshot_id:
                    del snapshots[i]
                    return True
            return False
        else:
            if aggregate_id in self._snapshots:
                del self._snapshots[aggregate_id]
            return True
    
    def get_snapshot_count(self, aggregate_id: Optional[str] = None) -> int:
        """获取快照数量"""
        if aggregate_id:
            return len(self._snapshots.get(aggregate_id, []))
        return sum(len(snaps) for snaps in self._snapshots.values())
    
    def clear_all(self, aggregate_id: Optional[str] = None) -> None:
        """
        清除快照
        
        Args:
            aggregate_id: 聚合 ID，为空则清除所有
        """
        if aggregate_id:
            if aggregate_id in self._snapshots:
                self._snapshots[aggregate_id].clear()
            if aggregate_id in self._version_counter:
                del self._version_counter[aggregate_id]
        else:
            self._snapshots.clear()
            self._version_counter.clear()
    
    def export_snapshots(self, aggregate_id: str) -> List[Dict[str, Any]]:
        """导出快照"""
        return [s.to_dict() for s in self._snapshots.get(aggregate_id, [])]
    
    def import_snapshots(
        self,
        aggregate_id: str,
        snapshots: List[Dict[str, Any]]
    ) -> None:
        """
        导入快照
        
        Args:
            aggregate_id: 聚合 ID
            snapshots: 快照列表
        """
        self._snapshots[aggregate_id] = [
            Snapshot.from_dict(s) for s in snapshots
        ]
        
        # 更新版本计数器
        if self._snapshots[aggregate_id]:
            max_version = max(s.version for s in self._snapshots[aggregate_id])
            self._version_counter[aggregate_id] = max_version
    
    def _cleanup_old_snapshots(self, aggregate_id: str) -> None:
        """清理旧快照"""
        snapshots = self._snapshots.get(aggregate_id, [])
        if len(snapshots) > self.max_snapshots:
            self._snapshots[aggregate_id] = snapshots[-self.max_snapshots:]
    
    def _persist_snapshot(self, snapshot: Snapshot) -> None:
        """持久化快照"""
        if not self.storage_path:
            return
        
        import os
        os.makedirs(self.storage_path, exist_ok=True)
        
        snapshot_file = os.path.join(
            self.storage_path,
            f"snapshot_{snapshot.aggregate_id}_{snapshot.snapshot_id}.json"
        )
        
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def _calculate_checksum(state: Dict[str, Any]) -> str:
        """计算校验和"""
        content = json.dumps(state, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
