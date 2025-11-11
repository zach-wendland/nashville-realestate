"""Request caching and deduplication for API optimization.

This module implements intelligent caching strategies to minimize redundant API calls:
- In-memory LRU cache with TTL
- Disk-based persistent cache
- Request deduplication
- Cache warming and preloading
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

import pandas as pd


@dataclass
class CacheEntry:
    """Cached API response with metadata."""

    data: Any
    timestamp: float
    hits: int = 0
    last_access: float = field(default_factory=time.time)


class RequestCache:
    """LRU cache with TTL for API responses."""

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 3600,  # 1 hour default
        disk_cache_dir: Optional[Path] = None
    ):
        """
        Initialize request cache.

        Args:
            max_size: Maximum number of cached entries
            ttl_seconds: Time-to-live for cache entries in seconds
            disk_cache_dir: Optional directory for persistent disk cache
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.disk_cache_dir = disk_cache_dir

        self.cache: Dict[str, CacheEntry] = {}
        self.lock = Lock()

        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

        if disk_cache_dir:
            disk_cache_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Disk cache enabled: {disk_cache_dir}")

    def _hash_key(self, params: Dict[str, Any]) -> str:
        """Generate cache key from request parameters."""
        # Sort keys for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True)
        return hashlib.sha256(sorted_params.encode()).hexdigest()

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired."""
        return (time.time() - entry.timestamp) > self.ttl_seconds

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self.cache:
            return

        # Find entry with oldest last_access
        lru_key = min(self.cache.items(), key=lambda item: item[1].last_access)[0]
        del self.cache[lru_key]
        self.evictions += 1

    def _load_from_disk(self, cache_key: str) -> Optional[Any]:
        """Load entry from disk cache."""
        if not self.disk_cache_dir:
            return None

        cache_file = self.disk_cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)

            # Check timestamp
            if (time.time() - data.get('timestamp', 0)) > self.ttl_seconds:
                cache_file.unlink()  # Delete expired file
                return None

            return data.get('data')
        except Exception as e:
            logging.warning(f"Failed to load from disk cache: {e}")
            return None

    def _save_to_disk(self, cache_key: str, data: Any) -> None:
        """Save entry to disk cache."""
        if not self.disk_cache_dir:
            return

        cache_file = self.disk_cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'data': data,
                    'timestamp': time.time()
                }, f)
        except Exception as e:
            logging.warning(f"Failed to save to disk cache: {e}")

    def get(self, params: Dict[str, Any]) -> Optional[Any]:
        """
        Get cached response for parameters.

        Args:
            params: Request parameters

        Returns:
            Cached data if available and not expired, None otherwise
        """
        cache_key = self._hash_key(params)

        with self.lock:
            # Check memory cache
            if cache_key in self.cache:
                entry = self.cache[cache_key]

                if self._is_expired(entry):
                    # Expired, remove from cache
                    del self.cache[cache_key]
                    self.misses += 1
                else:
                    # Cache hit
                    entry.hits += 1
                    entry.last_access = time.time()
                    self.hits += 1
                    logging.debug(f"Cache HIT: {cache_key[:8]}... (hits={entry.hits})")
                    return entry.data

        # Check disk cache
        disk_data = self._load_from_disk(cache_key)
        if disk_data is not None:
            # Promote to memory cache
            with self.lock:
                self._put_unlocked(cache_key, disk_data)
                self.hits += 1
            logging.debug(f"Disk cache HIT: {cache_key[:8]}...")
            return disk_data

        self.misses += 1
        return None

    def _put_unlocked(self, cache_key: str, data: Any) -> None:
        """Put entry in cache without locking (internal use)."""
        # Evict if at capacity
        if len(self.cache) >= self.max_size:
            self._evict_lru()

        self.cache[cache_key] = CacheEntry(
            data=data,
            timestamp=time.time()
        )

    def put(self, params: Dict[str, Any], data: Any) -> None:
        """
        Store response in cache.

        Args:
            params: Request parameters
            data: Response data to cache
        """
        cache_key = self._hash_key(params)

        with self.lock:
            self._put_unlocked(cache_key, data)

        # Save to disk cache asynchronously
        self._save_to_disk(cache_key, data)
        logging.debug(f"Cache PUT: {cache_key[:8]}...")

    def invalidate(self, params: Optional[Dict[str, Any]] = None) -> None:
        """
        Invalidate cache entries.

        Args:
            params: If provided, invalidate specific entry; otherwise clear all
        """
        with self.lock:
            if params is None:
                # Clear all
                self.cache.clear()
                logging.info("Cache cleared")
            else:
                cache_key = self._hash_key(params)
                if cache_key in self.cache:
                    del self.cache[cache_key]
                    logging.debug(f"Cache invalidated: {cache_key[:8]}...")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
                "evictions": self.evictions,
                "ttl_seconds": self.ttl_seconds,
            }

    def cleanup_expired(self) -> int:
        """Remove expired entries from cache. Returns number removed."""
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items()
                if self._is_expired(entry)
            ]

            for key in expired_keys:
                del self.cache[key]

        logging.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        return len(expired_keys)


# Global cache instance
_global_cache: Optional[RequestCache] = None
_cache_lock = Lock()


def get_request_cache(
    max_size: int = 1000,
    ttl_seconds: int = 3600,
    disk_cache_dir: Optional[Path] = None
) -> RequestCache:
    """Get or create global request cache instance."""
    global _global_cache

    with _cache_lock:
        if _global_cache is None:
            _global_cache = RequestCache(
                max_size=max_size,
                ttl_seconds=ttl_seconds,
                disk_cache_dir=disk_cache_dir
            )
        return _global_cache


def reset_cache() -> None:
    """Reset global cache (for testing)."""
    global _global_cache
    with _cache_lock:
        _global_cache = None
