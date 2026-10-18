"""
In-memory 10-minute TTL async cache for public job boards (Remotive, Greenhouse, Lever, Ashby).
Reduces upstream rate limits and accelerates repeated searches.
"""
import asyncio
import time
from typing import Dict, List, Optional, Tuple

from app.section1_foundation_and_providers.schemas.job import JobPosting


class AsyncJobCache:
    """
    In-memory async TTL cache.
    Zero persistence: lives purely in RAM, flushed on server restart.
    """
    def __init__(self, ttl_seconds: float = 600.0):  # 10 minutes default
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[float, List[JobPosting]]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[List[JobPosting]]:
        """Retrieve cached list if not expired."""
        async with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            timestamp, items = entry
            if time.time() - timestamp > self.ttl_seconds:
                # Expired
                self._cache.pop(key, None)
                return None
            return list(items)

    async def set(self, key: str, items: List[JobPosting]) -> None:
        """Store list of postings with current timestamp."""
        async with self._lock:
            self._cache[key] = (time.time(), list(items))

    async def clear(self) -> None:
        """Flush cache."""
        async with self._lock:
            self._cache.clear()

    async def size(self) -> int:
        """Return number of cached keys."""
        async with self._lock:
            return len(self._cache)


# Global singleton instance for public job adapters
job_cache = AsyncJobCache(ttl_seconds=600.0)
