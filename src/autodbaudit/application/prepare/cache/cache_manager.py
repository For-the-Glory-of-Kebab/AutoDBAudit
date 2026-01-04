"""
Cache Management Service - Ultra-granular component for connection caching.

This module provides intelligent caching of connection information with
TTL-based expiration and memory-efficient storage.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from autodbaudit.domain.config import ServerConnectionInfo

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """
    Cache entry with TTL support.

    Attributes:
        data: Cached connection information
        timestamp: Creation timestamp
        ttl_seconds: Time-to-live in seconds
    """
    data: ServerConnectionInfo
    timestamp: float
    ttl_seconds: int = 300  # 5 minutes default

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() - self.timestamp > self.ttl_seconds

    def get_age_seconds(self) -> float:
        """Get the age of the cache entry in seconds."""
        return time.time() - self.timestamp

    def get_remaining_ttl(self) -> float:
        """Get remaining TTL in seconds."""
        return max(0, self.ttl_seconds - self.get_age_seconds())


class ConnectionCacheManager:
    """
    Specialized cache manager for connection information.

    Provides TTL-based caching with automatic cleanup and statistics.
    """

    def __init__(self, default_ttl: int = 300) -> None:
        """
        Initialize the cache manager.

        Args:
            default_ttl: Default TTL for cache entries in seconds
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = CacheStats()

    def get(self, key: str) -> Optional[ServerConnectionInfo]:
        """
        Get cached connection information.

        Args:
            key: Cache key (typically server name)

        Returns:
            Cached connection info or None if not found/expired
        """
        entry = self._cache.get(key)
        if entry is None:
            self._stats.record_miss()
            return None

        if entry.is_expired():
            logger.debug("Cache entry expired for key: %s", key)
            self.delete(key)
            self._stats.record_miss()
            return None

        self._stats.record_hit()
        logger.debug("Cache hit for key: %s (age: %.1fs)",
                    key, entry.get_age_seconds())
        return entry.data

    def put(
        self,
        key: str,
        data: ServerConnectionInfo,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Store connection information in cache.

        Args:
            key: Cache key
            data: Connection information to cache
            ttl_seconds: TTL override (uses default if None)
        """
        ttl = ttl_seconds or self.default_ttl
        entry = CacheEntry(
            data=data,
            timestamp=time.time(),
            ttl_seconds=ttl
        )

        self._cache[key] = entry
        self._stats.record_put()
        logger.debug("Cached connection info for key: %s (TTL: %ds)", key, ttl)

    def delete(self, key: str) -> bool:
        """
        Delete a cache entry.

        Args:
            key: Cache key to delete

        Returns:
            True if entry was deleted, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            self._stats.record_delete()
            logger.debug("Deleted cache entry for key: %s", key)
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self._stats.reset()
        logger.info("Cleared %d cache entries", count)

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            del self._cache[key]
            self._stats.record_delete()

        if expired_keys:
            logger.info("Cleaned up %d expired cache entries", len(expired_keys))

        return len(expired_keys)

    def get_stats(self) -> 'CacheStats':
        """
        Get cache statistics.

        Returns:
            Cache statistics object
        """
        return self._stats.copy()

    def get_all_keys(self) -> list[str]:
        """Get all cache keys."""
        return list(self._cache.keys())

    def get_entry_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a cache entry.

        Args:
            key: Cache key

        Returns:
            Entry information or None if not found
        """
        entry = self._cache.get(key)
        if entry is None:
            return None

        return {
            "key": key,
            "age_seconds": entry.get_age_seconds(),
            "remaining_ttl": entry.get_remaining_ttl(),
            "is_expired": entry.is_expired(),
            "server_name": entry.data.server_name,
            "os_type": entry.data.os_type.value,
            "preferred_method": (
                entry.data.preferred_method.value
                if entry.data.preferred_method
                else None
            ),
            "is_available": entry.data.is_available,
        }


@dataclass
class CacheStats:
    """
    Cache statistics tracking.

    Tracks hits, misses, puts, and deletes for performance monitoring.
    """
    hits: int = 0
    misses: int = 0
    puts: int = 0
    deletes: int = 0

    def record_hit(self) -> None:
        """Record a cache hit."""
        self.hits += 1

    def record_miss(self) -> None:
        """Record a cache miss."""
        self.misses += 1

    def record_put(self) -> None:
        """Record a cache put."""
        self.puts += 1

    def record_delete(self) -> None:
        """Record a cache delete."""
        self.deletes += 1

    def get_hit_rate(self) -> float:
        """Get cache hit rate (0.0 to 1.0)."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def reset(self) -> None:
        """Reset all statistics."""
        self.hits = self.misses = self.puts = self.deletes = 0

    def copy(self) -> 'CacheStats':
        """Create a copy of the statistics."""
        return CacheStats(
            hits=self.hits,
            misses=self.misses,
            puts=self.puts,
            deletes=self.deletes
        )
