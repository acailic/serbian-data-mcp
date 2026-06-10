"""File-based response caching for API requests."""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ResponseCache:
    """Simple file-based cache for API responses."""

    def __init__(self, cache_dir: Path, default_ttl: int = 300):
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Response cache initialized at {self.cache_dir} (default TTL={default_ttl}s)")

    def _cache_key(self, method: str, url: str, params: Optional[dict] = None) -> str:
        """Generate a deterministic cache key from request parameters."""
        raw = f"{method}:{url}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, method: str, url: str, params: Optional[dict] = None, ttl: Optional[int] = None) -> Optional[dict]:
        """Retrieve a cached response if it exists and hasn't expired.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full request URL
            params: Query parameters used in the request
            ttl: Time-to-live in seconds (overrides default_ttl)

        Returns:
            Cached response data dict, or None if not found/expired
        """
        key = self._cache_key(method, url, params)
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    entry = json.load(f)
                if time.time() - entry.get("timestamp", 0) < (ttl or self.default_ttl):
                    logger.debug(f"Cache hit for {method} {url}")
                    return entry.get("data")
                else:
                    cache_file.unlink(missing_ok=True)
                    logger.debug(f"Cache expired for {method} {url}")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Corrupted cache entry {key}: {e}")
                cache_file.unlink(missing_ok=True)
        else:
            logger.debug(f"Cache miss for {method} {url}")
        return None

    def set(self, method: str, url: str, params: Optional[dict] = None, data: Any = None) -> None:
        """Store a response in the cache.

        Args:
            method: HTTP method
            url: Full request URL
            params: Query parameters used in the request
            data: Response data to cache
        """
        key = self._cache_key(method, url, params)
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, "w") as f:
                json.dump({"timestamp": time.time(), "data": data}, f, default=str)
            logger.debug(f"Cached {method} {url}")
        except IOError as e:
            logger.warning(f"Failed to cache {method} {url}: {e}")

    def clear(self) -> None:
        """Remove all cached entries."""
        for f in self.cache_dir.glob("*.json"):
            f.unlink(missing_ok=True)
        logger.info("Cache cleared")
