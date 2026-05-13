"""
技能缓存
"""
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import hashlib
import json


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


class SkillCache:
    """
    技能结果缓存
    
    缓存技能调用结果以提高响应速度
    """
    
    def __init__(self, default_ttl: int = 3600):
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.stats = {"hits": 0, "misses": 0}
    
    def _make_key(self, skill_id: str, params: Dict[str, Any]) -> str:
        """生成缓存键"""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(f"{skill_id}:{param_str}".encode()).hexdigest()
    
    def get(self, skill_id: str, params: Dict[str, Any]) -> Optional[Any]:
        """获取缓存"""
        key = self._make_key(skill_id, params)
        entry = self.cache.get(key)
        
        if entry is None:
            self.stats["misses"] += 1
            return None
        
        if entry.is_expired():
            del self.cache[key]
            self.stats["misses"] += 1
            return None
        
        entry.hit_count += 1
        self.stats["hits"] += 1
        return entry.value
    
    def set(self, skill_id: str, params: Dict[str, Any], 
            value: Any, ttl: Optional[int] = None) -> str:
        """设置缓存"""
        key = self._make_key(skill_id, params)
        expires_at = None
        if ttl is None:
            ttl = self.default_ttl
        if ttl > 0:
            expires_at = datetime.now() + timedelta(seconds=ttl)
        
        self.cache[key] = CacheEntry(
            key=key,
            value=value,
            expires_at=expires_at
        )
        return key
    
    def invalidate(self, skill_id: Optional[str] = None):
        """清除缓存"""
        if skill_id is None:
            self.cache.clear()
        else:
            keys_to_remove = [
                k for k, v in self.cache.items() 
                if k.startswith(skill_id)
            ]
            for k in keys_to_remove:
                del self.cache[k]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "size": len(self.cache),
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": hit_rate
        }
