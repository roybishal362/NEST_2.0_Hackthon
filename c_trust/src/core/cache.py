"""
C-TRUST Cache System
====================
Production-grade caching with cache-first pattern.

Design Principles:
1. Cache-first: Always return cached data immediately
2. Background refresh: Compute new data async
3. File persistence: Survive restarts
4. Hash-based invalidation: Detect data changes

Architecture:
    Request → Check Cache
        ↓ (hit)         ↓ (miss)
    Return cached    Compute + Cache
        ↓
    Background check for updates

Usage:
    cache = CacheManager()
    result = cache.get_or_compute("study_01", compute_fn, ttl=1800)
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Callable, Dict, List, Optional
import shutil

from src.core import get_logger

logger = get_logger(__name__)


# ========================================
# CACHE ENTRY
# ========================================

@dataclass
class CacheEntry:
    """Single cache entry with metadata."""
    key: str
    data: Any
    created_at: datetime
    expires_at: datetime
    data_hash: str
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for file storage."""
        return {
            "key": self.key,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "data_hash": self.data_hash,
            "hit_count": self.hit_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Deserialize from file storage."""
        return cls(
            key=data["key"],
            data=data["data"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            data_hash=data["data_hash"],
            hit_count=data.get("hit_count", 0),
        )


# ========================================
# CACHE STATISTICS
# ========================================

@dataclass
class CacheStats:
    """Cache performance statistics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    entries_count: int = 0
    background_refreshes: int = 0
    last_refresh: Optional[datetime] = None
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": f"{self.hit_rate:.1%}",
            "entries_count": self.entries_count,
            "background_refreshes": self.background_refreshes,
            "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None,
        }


# ========================================
# CACHE MANAGER
# ========================================

class CacheManager:
    """
    Production-grade cache manager with cache-first pattern.
    
    Features:
    - In-memory cache with TTL
    - File-based persistence
    - Hash-based change detection
    - Background refresh
    - Thread-safe operations
    """
    
    DEFAULT_TTL = 1800  # 30 minutes
    CACHE_FILE = "analysis_cache.json"
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        default_ttl: int = DEFAULT_TTL,
        enable_persistence: bool = True
    ):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache files
            default_ttl: Default TTL in seconds
            enable_persistence: Enable file persistence
        """
        self.default_ttl = default_ttl
        self.enable_persistence = enable_persistence
        
        # Set cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(__file__).parents[2] / ".cache"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / self.CACHE_FILE
        
        # In-memory cache
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        
        # Statistics
        self.stats = CacheStats()
        
        # Load from file on init
        if enable_persistence:
            self._load_from_file()
        
        logger.info(f"CacheManager initialized: {len(self._cache)} entries loaded")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value by key.
        
        Args:
            key: Cache key
        
        Returns:
            Cached data or None if not found/expired
        """
        with self._lock:
            self.stats.total_requests += 1
            
            entry = self._cache.get(key)
            
            if entry is None:
                self.stats.cache_misses += 1
                return None
            
            if entry.is_expired():
                self.stats.cache_misses += 1
                del self._cache[key]
                return None
            
            # Cache hit!
            self.stats.cache_hits += 1
            entry.hit_count += 1
            return entry.data
    
    def set(
        self,
        key: str,
        data: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set cache value.
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        ttl = ttl or self.default_ttl
        
        with self._lock:
            entry = CacheEntry(
                key=key,
                data=data,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(seconds=ttl),
                data_hash=self._compute_hash(data),
            )
            
            self._cache[key] = entry
            self.stats.entries_count = len(self._cache)
        
        # Persist to file
        if self.enable_persistence:
            self._save_to_file()
    
    def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        ttl: Optional[int] = None,
        force_refresh: bool = False
    ) -> Any:
        """
        Get from cache or compute if missing.
        
        This is the main cache-first method:
        1. Check cache for key
        2. If hit and not expired, return cached
        3. If miss, compute, cache, and return
        
        Args:
            key: Cache key
            compute_fn: Function to compute value if cache miss
            ttl: TTL override
            force_refresh: Force recompute even if cached
        
        Returns:
            Cached or computed data
        """
        if not force_refresh:
            cached = self.get(key)
            if cached is not None:
                logger.debug(f"Cache hit for {key}")
                return cached
        
        # Cache miss - compute
        logger.info(f"Cache miss for {key}, computing...")
        start_time = time.time()
        
        try:
            data = compute_fn()
            compute_time = time.time() - start_time
            
            self.set(key, data, ttl)
            logger.info(f"Computed and cached {key} in {compute_time:.2f}s")
            
            return data
            
        except Exception as e:
            logger.error(f"Compute failed for {key}: {e}")
            raise
    
    def get_or_compute_background(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        ttl: Optional[int] = None
    ) -> Any:
        """
        Get from cache, and refresh in background if stale.
        
        Always returns immediately:
        - If cached (even stale): return cached + trigger background refresh
        - If not cached: compute synchronously
        
        Args:
            key: Cache key
            compute_fn: Function to compute value
            ttl: TTL override
        
        Returns:
            Cached data (potentially stale) or freshly computed
        """
        with self._lock:
            entry = self._cache.get(key)
        
        if entry is not None:
            # Return cached data immediately
            if entry.is_expired():
                # Trigger background refresh
                self._background_refresh(key, compute_fn, ttl)
            
            return entry.data
        
        # No cache - must compute synchronously
        return self.get_or_compute(key, compute_fn, ttl)
    
    def _background_refresh(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        ttl: Optional[int]
    ) -> None:
        """Start background refresh thread."""
        def refresh():
            try:
                logger.info(f"Background refresh for {key}")
                data = compute_fn()
                self.set(key, data, ttl)
                self.stats.background_refreshes += 1
                self.stats.last_refresh = datetime.now()
            except Exception as e:
                logger.error(f"Background refresh failed for {key}: {e}")
        
        thread = Thread(target=refresh, daemon=True)
        thread.start()
    
    def invalidate(self, key: str) -> bool:
        """
        Invalidate a cache entry.
        
        Args:
            key: Cache key to invalidate
        
        Returns:
            True if entry existed and was removed
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self.stats.entries_count = len(self._cache)
                
                if self.enable_persistence:
                    self._save_to_file()
                
                return True
            return False
    
    def invalidate_all(self) -> int:
        """
        Invalidate all cache entries.
        
        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self.stats.entries_count = 0
        
        if self.enable_persistence:
            self._save_to_file()
        
        logger.info(f"Invalidated {count} cache entries")
        return count
    
    def has_changed(self, key: str, new_data: Any) -> bool:
        """
        Check if data has changed from cached version.
        
        Uses hash comparison for efficiency.
        
        Args:
            key: Cache key
            new_data: New data to compare
        
        Returns:
            True if data is different or not cached
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                return True
            
            new_hash = self._compute_hash(new_data)
            return new_hash != entry.data_hash
    
    def _compute_hash(self, data: Any) -> str:
        """Compute hash of data for change detection."""
        try:
            serialized = json.dumps(data, sort_keys=True, default=str)
            return hashlib.md5(serialized.encode()).hexdigest()
        except Exception:
            return hashlib.md5(str(data).encode()).hexdigest()
    
    def _save_to_file(self) -> None:
        """Persist cache to file."""
        try:
            with self._lock:
                cache_data = {
                    key: entry.to_dict()
                    for key, entry in self._cache.items()
                }
            
            # Write to temp file first, then rename (atomic)
            temp_file = self.cache_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            shutil.move(str(temp_file), str(self.cache_file))
            
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _load_from_file(self) -> None:
        """Load cache from file."""
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            loaded = 0
            expired = 0
            
            for key, entry_data in cache_data.items():
                entry = CacheEntry.from_dict(entry_data)
                
                if not entry.is_expired():
                    self._cache[key] = entry
                    loaded += 1
                else:
                    expired += 1
            
            self.stats.entries_count = len(self._cache)
            logger.info(f"Loaded {loaded} entries, discarded {expired} expired")
            
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.stats.to_dict()
    
    def get_all_keys(self) -> List[str]:
        """Get all cache keys."""
        with self._lock:
            return list(self._cache.keys())


# ========================================
# SINGLETON INSTANCE
# ========================================

_cache_instance: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get or create singleton cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance


def reset_cache() -> None:
    """Reset cache instance (for testing)."""
    global _cache_instance
    if _cache_instance:
        _cache_instance.invalidate_all()
    _cache_instance = None


# ========================================
# EXPORTS
# ========================================

__all__ = [
    "CacheManager",
    "CacheEntry", 
    "CacheStats",
    "get_cache",
    "reset_cache",
]
