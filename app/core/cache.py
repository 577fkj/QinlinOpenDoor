import asyncio
from time import time
from typing import Any, Optional, Dict
from dataclasses import dataclass


@dataclass
class CacheEntry:
    timestamp: float
    data: Any


class CacheManager:
    def __init__(self):
        self._store: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str, max_age: float) -> Optional[Any]:
        async with self._lock:
            if key in self._store:
                entry = self._store[key]
                if time() - entry.timestamp < max_age:
                    return entry.data
                else:
                    del self._store[key]
        return None

    async def set(self, key: str, data: Any):
        async with self._lock:
            self._store[key] = CacheEntry(timestamp=time(), data=data)

    async def clear(self):
        async with self._lock:
            self._store.clear()

    async def cleanup(self, max_age: float):
        async with self._lock:
            current_time = time()
            expired_keys = [
                k for k, v in self._store.items()
                if current_time - v.timestamp > max_age
            ]
            for k in expired_keys:
                del self._store[k]
