"""
记忆存储

可插拔后端的记忆存储实现
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Type, Protocol
from datetime import datetime
from abc import ABC, abstractmethod
import threading
import json
import uuid


class MemoryStorageBackend(Protocol):
    """记忆存储后端协议"""
    
    def save(self, memory_id: str, data: Dict[str, Any]) -> bool:
        """保存记忆"""
        ...
    
    def load(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """加载记忆"""
        ...
    
    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        ...
    
    def query(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """查询记忆"""
        ...
    
    def exists(self, memory_id: str) -> bool:
        """检查记忆是否存在"""
        ...


@dataclass
class MemoryStoreConfig:
    """记忆存储配置"""
    max_memories: int = 10000
    default_ttl: Optional[int] = None  # 默认生存时间（秒）
    enable_persistence: bool = False
    persist_path: str = "./memory_store.json"
    enable_compression: bool = False
    index_on_save: bool = True


class InMemoryStorageBackend:
    """
    内存存储后端
    
    简单的内存存储实现，用于开发和测试
    """
    
    def __init__(self):
        """初始化内存存储后端"""
        self._storage: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    def save(self, memory_id: str, data: Dict[str, Any]) -> bool:
        """
        保存记忆
        
        Args:
            memory_id: 记忆 ID
            data: 记忆数据
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            self._storage[memory_id] = data.copy()
            return True
    
    def load(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        加载记忆
        
        Args:
            memory_id: 记忆 ID
            
        Returns:
            Optional[Dict[str, Any]]: 记忆数据
        """
        with self._lock:
            return self._storage.get(memory_id, {}).copy()
    
    def delete(self, memory_id: str) -> bool:
        """
        删除记忆
        
        Args:
            memory_id: 记忆 ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            if memory_id in self._storage:
                del self._storage[memory_id]
                return True
            return False
    
    def query(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        查询记忆
        
        Args:
            filters: 过滤条件
            
        Returns:
            List[Dict[str, Any]]: 匹配的记忆列表
        """
        with self._lock:
            results = []
            for memory in self._storage.values():
                if self._matches_filters(memory, filters):
                    results.append(memory.copy())
            return results
    
    def exists(self, memory_id: str) -> bool:
        """
        检查记忆是否存在
        
        Args:
            memory_id: 记忆 ID
            
        Returns:
            bool: 是否存在
        """
        with self._lock:
            return memory_id in self._storage
    
    def get_all(self) -> List[Dict[str, Any]]:
        """获取所有记忆"""
        with self._lock:
            return [m.copy() for m in self._storage.values()]
    
    def clear(self) -> None:
        """清空存储"""
        with self._lock:
            self._storage.clear()
    
    def _matches_filters(
        self,
        memory: Dict[str, Any],
        filters: Dict[str, Any],
    ) -> bool:
        """检查记忆是否匹配过滤器"""
        for key, value in filters.items():
            if key not in memory:
                return False
            if isinstance(value, (list, tuple)):
                if memory[key] not in value:
                    return False
            elif memory[key] != value:
                return False
        return True


class FileStorageBackend:
    """
    文件存储后端
    
    基于 JSON 文件的持久化存储
    """
    
    def __init__(self, filepath: str = "./memory_store.json"):
        """
        初始化文件存储后端
        
        Args:
            filepath: 文件路径
        """
        self._filepath = filepath
        self._memory_backend = InMemoryStorageBackend()
        self._lock = threading.RLock()
        self._load_from_file()
    
    def save(self, memory_id: str, data: Dict[str, Any]) -> bool:
        """保存记忆"""
        with self._lock:
            result = self._memory_backend.save(memory_id, data)
            if result:
                self._save_to_file()
            return result
    
    def load(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """加载记忆"""
        with self._lock:
            return self._memory_backend.load(memory_id)
    
    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        with self._lock:
            result = self._memory_backend.delete(memory_id)
            if result:
                self._save_to_file()
            return result
    
    def query(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """查询记忆"""
        return self._memory_backend.query(filters)
    
    def exists(self, memory_id: str) -> bool:
        """检查记忆是否存在"""
        return self._memory_backend.exists(memory_id)
    
    def _save_to_file(self) -> None:
        """保存到文件"""
        try:
            with open(self._filepath, 'w', encoding='utf-8') as f:
                json.dump(
                    self._memory_backend.get_all(),
                    f,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
        except Exception:
            pass
    
    def _load_from_file(self) -> None:
        """从文件加载"""
        try:
            with open(self._filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for memory in data:
                    memory_id = memory.get("memory_id")
                    if memory_id:
                        self._memory_backend.save(memory_id, memory)
        except Exception:
            pass


class MemoryStore:
    """
    记忆存储管理器
    
    统一的记忆存储接口，支持可插拔后端
    """
    
    def __init__(self, config: Optional[MemoryStoreConfig] = None):
        """
        初始化记忆存储
        
        Args:
            config: 存储配置
        """
        self.config = config or MemoryStoreConfig()
        
        # 选择后端
        if self.config.enable_persistence:
            self._backend: MemoryStorageBackend = FileStorageBackend(
                filepath=self.config.persist_path
            )
        else:
            self._backend = InMemoryStorageBackend()
        
        self._lock = threading.RLock()
    
    def store(
        self,
        memory_id: str,
        content: str,
        memory_type: str = "general",
        importance: int = 3,
        metadata: Optional[Dict[str, Any]] = None,
        emotional_valence: float = 0.0,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        存储记忆
        
        Args:
            memory_id: 记忆 ID
            content: 记忆内容
            memory_type: 记忆类型
            importance: 重要性 (1-5)
            metadata: 元数据
            emotional_valence: 情感效价
            tags: 标签
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            data = {
                "memory_id": memory_id,
                "content": content,
                "memory_type": memory_type,
                "importance": importance,
                "metadata": metadata or {},
                "emotional_valence": emotional_valence,
                "tags": tags or [],
                "created_at": datetime.now().isoformat(),
                "access_count": 0,
                "last_accessed": datetime.now().isoformat(),
            }
            
            return self._backend.save(memory_id, data)
    
    def retrieve(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        检索记忆
        
        Args:
            memory_id: 记忆 ID
            
        Returns:
            Optional[Dict[str, Any]]: 记忆数据
        """
        with self._lock:
            data = self._backend.load(memory_id)
            
            if data:
                # 更新访问统计
                data["access_count"] = data.get("access_count", 0) + 1
                data["last_accessed"] = datetime.now().isoformat()
                self._backend.save(memory_id, data)
            
            return data
    
    def delete(self, memory_id: str) -> bool:
        """
        删除记忆
        
        Args:
            memory_id: 记忆 ID
            
        Returns:
            bool: 是否成功
        """
        return self._backend.delete(memory_id)
    
    def query_by_type(self, memory_type: str) -> List[Dict[str, Any]]:
        """
        按类型查询
        
        Args:
            memory_type: 记忆类型
            
        Returns:
            List[Dict[str, Any]]: 记忆列表
        """
        return self._backend.query({"memory_type": memory_type})
    
    def query_by_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        """
        按标签查询
        
        Args:
            tags: 标签列表
            
        Returns:
            List[Dict[str, Any]]: 记忆列表
        """
        results = []
        for memory in self._backend.query({}):
            memory_tags = memory.get("tags", [])
            if any(tag in memory_tags for tag in tags):
                results.append(memory)
        return results
    
    def query_by_importance(
        self,
        min_importance: int = 1,
        max_importance: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        按重要性查询
        
        Args:
            min_importance: 最低重要性
            max_importance: 最高重要性
            
        Returns:
            List[Dict[str, Any]]: 记忆列表
        """
        results = []
        for memory in self._backend.query({}):
            importance = memory.get("importance", 0)
            if min_importance <= importance <= max_importance:
                results.append(memory)
        return results
    
    def query_by_time_range(
        self,
        start: datetime,
        end: datetime,
    ) -> List[Dict[str, Any]]:
        """
        按时间范围查询
        
        Args:
            start: 开始时间
            end: 结束时间
            
        Returns:
            List[Dict[str, Any]]: 记忆列表
        """
        results = []
        for memory in self._backend.query({}):
            created_at_str = memory.get("created_at", "")
            try:
                created_at = datetime.fromisoformat(created_at_str)
                if start <= created_at <= end:
                    results.append(memory)
            except Exception:
                pass
        return results
    
    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的记忆
        
        Args:
            limit: 数量限制
            
        Returns:
            List[Dict[str, Any]]: 记忆列表
        """
        all_memories = self._backend.query({})
        sorted_memories = sorted(
            all_memories,
            key=lambda m: m.get("created_at", ""),
            reverse=True
        )
        return sorted_memories[:limit]
    
    def get_most_accessed(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取访问最多的记忆
        
        Args:
            limit: 数量限制
            
        Returns:
            List[Dict[str, Any]]: 记忆列表
        """
        all_memories = self._backend.query({})
        sorted_memories = sorted(
            all_memories,
            key=lambda m: m.get("access_count", 0),
            reverse=True
        )
        return sorted_memories[:limit]
    
    def count(self) -> int:
        """获取记忆总数"""
        return len(self._backend.query({}))
    
    def clear(self) -> None:
        """清空存储"""
        self._backend.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        all_memories = self._backend.query({})
        
        by_type: Dict[str, int] = {}
        by_importance: Dict[int, int] = {}
        total_access = 0
        
        for memory in all_memories:
            memory_type = memory.get("memory_type", "unknown")
            importance = memory.get("importance", 0)
            
            by_type[memory_type] = by_type.get(memory_type, 0) + 1
            by_importance[importance] = by_importance.get(importance, 0) + 1
            total_access += memory.get("access_count", 0)
        
        return {
            "total_memories": len(all_memories),
            "by_type": by_type,
            "by_importance": by_importance,
            "total_accesses": total_access,
            "avg_access": total_access / len(all_memories) if all_memories else 0,
        }
