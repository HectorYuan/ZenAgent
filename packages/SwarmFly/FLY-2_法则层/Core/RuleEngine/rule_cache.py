"""
规则缓存 (Rule Cache)

提供LRU缓存 + 版本控制的规则缓存实现。
支持规则版本管理、回滚和一致性验证。
"""

import time
import hashlib
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
from threading import Lock
import logging

from .rule_parser import Rule

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    version: str = "1.0"
    checksum: str = ""
    
    def touch(self):
        """更新访问时间"""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """检查是否过期"""
        return (datetime.now() - self.created_at).total_seconds() > ttl_seconds


@dataclass
class VersionSnapshot:
    """版本快照"""
    version_id: str
    version_name: str
    rules: Dict[str, Rule]
    checksum: str
    created_at: datetime
    created_by: str
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_stable: bool = True
    rollback_from: Optional[str] = None  # 可回滚的版本ID


class RuleCache:
    """
    规则缓存管理器
    
    提供多层缓存策略:
    - L1: 内存LRU缓存(高频访问)
    - L2: 版本快照缓存(状态一致性)
    
    特性:
    - LRU驱逐策略
    - 版本控制与回滚
    - 一致性校验
    - 统计监控
    """
    
    def __init__(
        self,
        max_size: int = 10000,
        l1_ttl_seconds: int = 3600,
        l2_ttl_seconds: int = 86400,
        enable_versioning: bool = True
    ):
        # L1缓存配置
        self.max_size = max_size
        self.l1_ttl = l1_ttl_seconds
        self.l2_ttl = l2_ttl_seconds
        
        # L1缓存(内存LRU)
        self.l1_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.l1_lock = Lock()
        
        # L2缓存(版本快照)
        self.l2_cache: Dict[str, VersionSnapshot] = {}
        self.l2_lock = Lock()
        
        # 版本管理
        self.enable_versioning = enable_versioning
        self.current_version: Optional[str] = None
        self.version_history: List[str] = []  # 版本ID列表
        
        # 统计信息
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'versions_created': 0,
            'rollbacks': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，不存在则返回None
        """
        # L1查找
        entry = self._l1_get(key)
        if entry is not None:
            self.stats['hits'] += 1
            return entry.value
        
        # L2查找
        entry = self._l2_get(key)
        if entry is not None:
            self.stats['hits'] += 1
            # 提升到L1
            self._l1_set(key, entry.value)
            return entry.value
        
        self.stats['misses'] += 1
        return None
    
    def _l1_get(self, key: str) -> Optional[CacheEntry]:
        """L1缓存获取"""
        with self.l1_lock:
            if key in self.l1_cache:
                entry = self.l1_cache[key]
                
                # 检查过期
                if entry.is_expired(self.l1_ttl):
                    del self.l1_cache[key]
                    return None
                
                # 更新访问顺序(LRU)
                self.l1_cache.move_to_end(key)
                entry.touch()
                return entry
            
            return None
    
    def _l2_get(self, key: str) -> Optional[CacheEntry]:
        """L2缓存获取"""
        with self.l2_lock:
            # 在所有版本中查找
            for version_id, snapshot in self.l2_cache.items():
                if key in snapshot.rules:
                    return CacheEntry(
                        key=key,
                        value=snapshot.rules[key],
                        checksum=snapshot.checksum
                    )
            return None
    
    def set(self, key: str, value: Any, version: Optional[str] = None):
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            version: 版本号(可选)
        """
        checksum = self._calculate_checksum(value)
        
        with self.l1_lock:
            # LRU驱逐
            while len(self.l1_cache) >= self.max_size:
                evicted_key, evicted_entry = self.l1_cache.popitem(last=False)
                self.stats['evictions'] += 1
                logger.debug(f"Evicted: {evicted_key}")
            
            # 创建新条目
            entry = CacheEntry(
                key=key,
                value=value,
                checksum=checksum,
                version=version or self.current_version or "1.0"
            )
            
            self.l1_cache[key] = entry
            self.l1_cache.move_to_end(key)
    
    def _l1_set(self, key: str, value: Any):
        """提升到L1缓存"""
        with self.l1_lock:
            if key in self.l1_cache:
                self.l1_cache[key].touch()
            else:
                checksum = self._calculate_checksum(value)
                self.l1_cache[key] = CacheEntry(
                    key=key,
                    value=value,
                    checksum=checksum
                )
    
    def invalidate(self, key: str):
        """使缓存失效"""
        with self.l1_lock:
            if key in self.l1_cache:
                del self.l1_cache[key]
    
    def invalidate_pattern(self, pattern: str):
        """使匹配模式的缓存失效"""
        import re
        compiled_pattern = re.compile(pattern)
        
        with self.l1_lock:
            keys_to_delete = [
                k for k in self.l1_cache.keys()
                if compiled_pattern.match(k)
            ]
            for key in keys_to_delete:
                del self.l1_cache[key]
    
    def clear(self):
        """清空所有缓存"""
        with self.l1_lock:
            self.l1_cache.clear()
        
        with self.l2_lock:
            self.l2_cache.clear()
        
        logger.info("Cache cleared")
    
    def _calculate_checksum(self, value: Any) -> str:
        """计算校验和"""
        if isinstance(value, Rule):
            return value.get_checksum()
        elif isinstance(value, dict):
            content = json.dumps(value, sort_keys=True, default=str)
            return hashlib.sha256(content.encode()).hexdigest()
        else:
            content = json.dumps(value, sort_keys=True, default=str)
            return hashlib.sha256(content.encode()).hexdigest()
    
    # ==================== 版本管理 ====================
    
    def create_version(
        self,
        rules: Dict[str, Rule],
        version_name: str,
        created_by: str = "system",
        description: str = ""
    ) -> str:
        """
        创建版本快照
        
        Args:
            rules: 规则字典
            version_name: 版本名称
            created_by: 创建者
            description: 版本描述
            
        Returns:
            版本ID
        """
        if not self.enable_versioning:
            raise ValueError("Versioning is disabled")
        
        # 生成版本ID
        version_id = self._generate_version_id(rules, version_name)
        
        # 计算快照校验和
        all_rules_content = []
        for rule_id, rule in sorted(rules.items()):
            all_rules_content.append(rule.get_checksum())
        combined_checksum = hashlib.sha256(
            ''.join(all_rules_content).encode()
        ).hexdigest()
        
        # 创建快照
        snapshot = VersionSnapshot(
            version_id=version_id,
            version_name=version_name,
            rules=rules.copy(),
            checksum=combined_checksum,
            created_at=datetime.now(),
            created_by=created_by,
            description=description,
            rollback_from=self.current_version
        )
        
        with self.l2_lock:
            self.l2_cache[version_id] = snapshot
            self.version_history.append(version_id)
            self.current_version = version_id
        
        self.stats['versions_created'] += 1
        logger.info(f"Version created: {version_id} - {version_name}")
        
        return version_id
    
    def _generate_version_id(self, rules: Dict[str, Rule], version_name: str) -> str:
        """生成版本ID"""
        content = f"{version_name}:{len(rules)}:{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get_version(self, version_id: str) -> Optional[VersionSnapshot]:
        """获取指定版本"""
        with self.l2_lock:
            return self.l2_cache.get(version_id)
    
    def get_current_version(self) -> Optional[VersionSnapshot]:
        """获取当前版本"""
        if not self.current_version:
            return None
        return self.get_version(self.current_version)
    
    def list_versions(self, limit: int = 100) -> List[VersionSnapshot]:
        """列出所有版本(按时间倒序)"""
        with self.l2_lock:
            versions = sorted(
                self.l2_cache.values(),
                key=lambda v: v.created_at,
                reverse=True
            )
            return versions[:limit]
    
    def rollback_to_version(self, version_id: str) -> Tuple[bool, str]:
        """
        回滚到指定版本
        
        Returns:
            (成功标志, 消息)
        """
        snapshot = self.get_version(version_id)
        if not snapshot:
            return False, f"Version not found: {version_id}"
        
        # 更新当前版本
        with self.l2_lock:
            self.current_version = version_id
        
        # 清空L1缓存(强制重新加载)
        with self.l1_lock:
            self.l1_cache.clear()
            
            # 预热缓存
            for rule_id, rule in snapshot.rules.items():
                self.l1_cache[rule_id] = CacheEntry(
                    key=rule_id,
                    value=rule,
                    version=version_id,
                    checksum=rule.get_checksum()
                )
        
        self.stats['rollbacks'] += 1
        logger.info(f"Rolled back to version: {version_id}")
        
        return True, f"Successfully rolled back to {snapshot.version_name}"
    
    def find_stable_version(self) -> Optional[VersionSnapshot]:
        """查找最近的稳定版本"""
        with self.l2_lock:
            stable_versions = [
                v for v in self.l2_cache.values()
                if v.is_stable
            ]
            
            if not stable_versions:
                return None
            
            return max(stable_versions, key=lambda v: v.created_at)
    
    def mark_version_unstable(self, version_id: str):
        """标记版本为不稳定"""
        with self.l2_lock:
            if version_id in self.l2_cache:
                self.l2_cache[version_id].is_stable = False
    
    # ==================== 统计与监控 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        hit_rate = 0.0
        total_requests = self.stats['hits'] + self.stats['misses']
        if total_requests > 0:
            hit_rate = self.stats['hits'] / total_requests
        
        with self.l1_lock:
            l1_size = len(self.l1_cache)
        
        with self.l2_lock:
            l2_size = len(self.l2_cache)
        
        return {
            'l1': {
                'size': l1_size,
                'max_size': self.max_size,
                'utilization': l1_size / self.max_size if self.max_size > 0 else 0
            },
            'l2': {
                'size': l2_size,
                'versions': len(self.version_history)
            },
            'hit_rate': hit_rate,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'evictions': self.stats['evictions'],
            'versions_created': self.stats['versions_created'],
            'rollbacks': self.stats['rollbacks']
        }
    
    def cleanup_expired(self):
        """清理过期条目"""
        with self.l1_lock:
            expired_keys = [
                k for k, v in self.l1_cache.items()
                if v.is_expired(self.l1_ttl)
            ]
            for key in expired_keys:
                del self.l1_cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired entries")


class RuleCacheManager:
    """
    规则缓存管理器
    
    提供统一的缓存管理接口，支持:
    - 多缓存实例
    - 分布式缓存同步(预留接口)
    - 缓存策略配置
    - 智能预热
    - 访问模式学习
    
    增强特性:
    - LFU频率统计: 基于访问频率的缓存优化
    - 预热策略: 系统启动时自动预加载高频规则
    - 智能TTL: 基于访问模式的动态TTL调整
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.caches: Dict[str, RuleCache] = {}
        self.default_cache = RuleCache(
            max_size=self.config.get('max_size', 10000),
            l1_ttl_seconds=self.config.get('l1_ttl', 3600),
            l2_ttl_seconds=self.config.get('l2_ttl', 86400)
        )
        self.caches['default'] = self.default_cache
        
        # 增强：访问频率统计
        self.access_frequency: Dict[str, int] = {}  # key -> access count
        self.hot_keys: List[str] = []  # 高频访问的key列表
        self.hot_threshold = self.config.get('hot_threshold', 100)  # 进入hot列表的阈值
        
        # 增强：预热配置
        self.prewarm_enabled = self.config.get('prewarm_enabled', True)
        self.prewarm_size = self.config.get('prewarm_size', 100)  # 预热时加载的规则数
    
    def get_cache(self, name: str = 'default') -> RuleCache:
        """获取命名缓存"""
        if name not in self.caches:
            self.caches[name] = RuleCache()
        return self.caches[name]
    
    def create_cache(
        self,
        name: str,
        max_size: int = 10000,
        l1_ttl: int = 3600,
        l2_ttl: int = 86400
    ) -> RuleCache:
        """创建新缓存"""
        cache = RuleCache(
            max_size=max_size,
            l1_ttl_seconds=l1_ttl,
            l2_ttl_seconds=l2_ttl
        )
        self.caches[name] = cache
        return cache
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """获取所有缓存统计"""
        return {
            name: cache.get_stats()
            for name, cache in self.caches.items()
        }
    
    # ==================== 增强功能 ====================
    
    def record_access(self, key: str):
        """记录缓存访问，更新频率统计"""
        self.access_frequency[key] = self.access_frequency.get(key, 0) + 1
        
        # 更新hot keys列表
        if self.access_frequency[key] >= self.hot_threshold:
            if key not in self.hot_keys:
                self.hot_keys.append(key)
                self._sort_hot_keys()
    
    def _sort_hot_keys(self):
        """按频率排序hot keys"""
        self.hot_keys.sort(key=lambda k: self.access_frequency.get(k, 0), reverse=True)
    
    def get_hot_keys(self, top_n: int = 100) -> List[str]:
        """获取最热门的N个key"""
        return self.hot_keys[:top_n]
    
    def get_access_stats(self) -> Dict[str, Any]:
        """获取访问统计"""
        total_access = sum(self.access_frequency.values())
        unique_keys = len(self.access_frequency)
        avg_access = total_access / unique_keys if unique_keys > 0 else 0
        
        return {
            'total_access': total_access,
            'unique_keys': unique_keys,
            'avg_access_per_key': avg_access,
            'hot_keys_count': len(self.hot_keys),
            'top_10_keys': self.get_hot_keys(10)
        }
    
    def prewarm_cache(self, rules: Dict[str, Any]):
        """
        预热缓存
        
        策略:
        1. 按频率排序，选择最热门的规则
        2. 优先加载到L1缓存
        3. 保留版本快照在L2
        """
        if not self.prewarm_enabled:
            logger.info("Prewarm disabled, skipping")
            return
        
        logger.info(f"Starting cache prewarm with {len(rules)} rules")
        
        # 按访问频率排序
        sorted_rules = sorted(
            rules.items(),
            key=lambda x: self.access_frequency.get(x[0], 0),
            reverse=True
        )
        
        # 加载top N规则
        count = 0
        for rule_id, rule in sorted_rules[:self.prewarm_size]:
            self.default_cache.set(rule_id, rule)
            count += 1
        
        logger.info(f"Cache prewarmed with {count} rules")
    
    def warm_hot_keys(self):
        """
        专门预热hot keys
        
        用于系统恢复或新节点启动时
        """
        logger.info(f"Warming {len(self.hot_keys)} hot keys")
        
        for key in self.hot_keys:
            if key not in self.default_cache.l1_cache:
                # 尝试从L2恢复
                value = self.default_cache.get(key)
                if value is not None:
                    logger.debug(f"Warmed key: {key}")
    
    def get_cache_efficiency_score(self) -> float:
        """
        计算缓存效率评分
        
        考虑因素:
        - 命中率
        - 热键占比
        - 驱逐率
        """
        if not self.default_cache:
            return 0.0
        
        stats = self.default_cache.get_stats()
        hit_rate = stats.get('hit_rate', 0)
        hot_ratio = len(self.hot_keys) / max(1, stats.get('l1', {}).get('size', 1))
        eviction_rate = stats.get('evictions', 0) / max(1, stats.get('hits', 1))
        
        # 综合评分
        score = (hit_rate * 0.6) + (hot_ratio * 0.2) + (1 - min(eviction_rate, 1)) * 0.2
        return round(score, 4)
    
    def suggest_optimization(self) -> Dict[str, Any]:
        """建议缓存优化"""
        suggestions = []
        score = self.get_cache_efficiency_score()
        
        if score < 0.7:
            suggestions.append("Cache efficiency is low, consider increasing cache size")
        
        stats = self.default_cache.get_stats()
        l1_util = stats.get('l1', {}).get('utilization', 0)
        
        if l1_util > 0.9:
            suggestions.append("L1 cache nearly full, consider increasing max_size")
        
        if stats.get('evictions', 0) > 1000:
            suggestions.append("High eviction rate, consider adjusting TTL or size")
        
        hot_count = len([k for k in self.hot_keys if k not in self.default_cache.l1_cache])
        if hot_count > 0:
            suggestions.append(f"{hot_count} hot keys are not in cache, consider prewarming")
        
        return {
            'efficiency_score': score,
            'suggestions': suggestions,
            'recommendations': self._get_size_recommendations(stats)
        }
    
    def _get_size_recommendations(self, stats: Dict[str, Any]) -> Dict[str, int]:
        """根据使用情况推荐缓存大小"""
        current_size = stats.get('l1', {}).get('max_size', 10000)
        utilization = stats.get('l1', {}).get('utilization', 0)
        
        if utilization > 0.85:
            return {'recommended_l1_size': int(current_size * 1.5)}
        elif utilization < 0.3:
            return {'recommended_l1_size': int(current_size * 0.7)}
        else:
            return {'recommended_l1_size': current_size}
