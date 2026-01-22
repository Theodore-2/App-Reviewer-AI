"""
App Reviewer AI - Redis Cache Layer

Handles Redis connections and caching operations.
"""

import redis.asyncio as redis
from typing import Optional, Any
import json
import logging
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger(__name__)

# Global Redis client
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client."""
    global _redis_client
    
    if _redis_client is not None:
        try:
            await _redis_client.ping()
            return _redis_client
        except Exception:
            _redis_client = None
    
    settings = get_settings()
    
    try:
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        await _redis_client.ping()
        logger.info("Connected to Redis")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
        return None


class InMemoryCache:
    """Fallback in-memory cache when Redis is unavailable."""
    
    def __init__(self):
        self._data: dict = {}
    
    async def get(self, key: str) -> Optional[str]:
        return self._data.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        self._data[key] = value
    
    async def delete(self, key: str) -> None:
        self._data.pop(key, None)
    
    async def keys(self, pattern: str) -> list:
        import fnmatch
        return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]


# Fallback in-memory cache
_memory_cache = InMemoryCache()


class CacheManager:
    """Unified cache manager supporting Redis with in-memory fallback."""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def _get_backend(self):
        """Get cache backend (Redis or in-memory)."""
        redis_client = await get_redis_client()
        return redis_client if redis_client else _memory_cache
    
    async def get_json(self, key: str) -> Optional[dict]:
        """Get JSON value from cache."""
        backend = await self._get_backend()
        value = await backend.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    async def set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> None:
        """Set JSON value in cache."""
        backend = await self._get_backend()
        json_str = json.dumps(value, default=str)
        await backend.set(key, json_str, ex=ttl)
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        backend = await self._get_backend()
        await backend.delete(key)
    
    async def find_keys(self, pattern: str) -> list:
        """Find keys matching pattern."""
        backend = await self._get_backend()
        return await backend.keys(pattern)


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get cache manager singleton."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
