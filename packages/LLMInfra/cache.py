"""
缓存模块
"""

from typing import Optional, Any, Dict
import hashlib
import json
import logging
import time
from datetime import datetime

from .core import ChatRequest, Message

logger = logging.getLogger(__name__)


class CacheBackend:
    """缓存后端基类"""
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        raise NotImplementedError
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """设置缓存"""
        raise NotImplementedError
    
    async def delete(self, key: str) -> None:
        """删除缓存"""
        raise NotImplementedError
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        raise NotImplementedError


class MemoryCache(CacheBackend):
    """内存缓存"""
    
    def __init__(self):
        self._cache: Dict[str, tuple[Any, float]] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self._cache:
            return None
        
        value, expire_at = self._cache[key]
        if time.time() > expire_at:
            del self._cache[key]
            return None
        
        return value
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """设置缓存"""
        self._cache[key] = (value, time.time() + ttl)
    
    async def delete(self, key: str) -> None:
        """删除缓存"""
        if key in self._cache:
            del self._cache[key]
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        if key not in self._cache:
            return False
        
        _, expire_at = self._cache[key]
        if time.time() > expire_at:
            del self._cache[key]
            return False
        
        return True
    
    def clear_expired(self):
        """清除过期缓存"""
        now = time.time()
        keys_to_delete = [
            key for key, (_, expire_at) in self._cache.items()
            if now > expire_at
        ]
        for key in keys_to_delete:
            del self._cache[key]


class RedisCache(CacheBackend):
    """Redis 缓存"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._redis = None
        self._redis_url = redis_url
    
    async def _get_redis(self):
        """获取 Redis 连接"""
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = await aioredis.from_url(self._redis_url)
            except ImportError:
                logger.warning("Redis not available, using memory cache")
                raise
        return self._redis
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            redis = await self._get_redis()
            data = await redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """设置缓存"""
        try:
            redis = await self._get_redis()
            await redis.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")
    
    async def delete(self, key: str) -> None:
        """删除缓存"""
        try:
            redis = await self._get_redis()
            await redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            redis = await self._get_redis()
            return bool(await redis.exists(key))
        except Exception as e:
            logger.warning(f"Redis exists failed: {e}")
            return False


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, config):
        self.config = config
        self.enabled = config.enabled
        self.ttl = config.ttl
        
        if config.type == "redis":
            try:
                self.backend = RedisCache(config.redis_url)
                logger.info("Using Redis cache backend")
            except Exception:
                self.backend = MemoryCache()
                logger.info("Falling back to memory cache")
        else:
            self.backend = MemoryCache()
            logger.info("Using memory cache backend")
    
    def _generate_cache_key(self, request: ChatRequest) -> str:
        """生成缓存键"""
        key_data = {
            "model": request.model,
            "messages": [msg.model_dump(exclude_none=True) for msg in request.messages],
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
        
        key_json = json.dumps(key_data, sort_keys=True)
        return f"llm:cache:{hashlib.md5(key_json.encode()).hexdigest()}"
    
    async def get(self, request: ChatRequest) -> Optional[dict]:
        """获取缓存"""
        if not self.enabled:
            return None
        
        key = self._generate_cache_key(request)
        cached = await self.backend.get(key)
        if cached:
            logger.debug(f"Cache hit: {key[:20]}...")
            return cached
        
        return None
    
    async def set(self, request: ChatRequest, response: dict) -> None:
        """设置缓存"""
        if not self.enabled:
            return
        
        key = self._generate_cache_key(request)
        await self.backend.set(key, response, self.ttl)
        logger.debug(f"Cache set: {key[:20]}...")
    
    async def invalidate(self, request: ChatRequest) -> None:
        """使缓存失效"""
        if not self.enabled:
            return
        
        key = self._generate_cache_key(request)
        await self.backend.delete(key)
