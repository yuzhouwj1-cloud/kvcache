from __future__ import annotations

from collections import deque

from kvcache_sim.cache.interfaces import Cache, CacheLookup, CacheMetadata


class ClockCache(Cache):
    def __init__(self, capacity_bytes: int) -> None:
        self.capacity_bytes = capacity_bytes
        self._items: dict[int, int] = {}
        self._ref_bits: dict[int, int] = {}
        self._queue: deque[int] = deque()
        self._used_bytes = 0
        self._hits = 0
        self._misses = 0

    def get(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> CacheLookup:
        if key in self._items:
            self._ref_bits[key] = 1
            self._hits += 1
            return CacheLookup(hit=True, level="l1")

        self._misses += 1
        self._insert(key, size_bytes)
        return CacheLookup(hit=False, level="miss")

    def put(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> None:
        if key in self._items:
            existing = self._items.get(key, 0)
            self._used_bytes -= existing
            self._items.pop(key, None)
            self._ref_bits.pop(key, None)
        self._insert(key, size_bytes)

    def _insert(self, key: int, size_bytes: int) -> None:
        if size_bytes > self.capacity_bytes:
            return
        while self._used_bytes + size_bytes > self.capacity_bytes and self._items:
            self._evict_one()
        self._items[key] = size_bytes
        self._ref_bits[key] = 1
        self._queue.append(key)
        self._used_bytes += size_bytes

    def _evict_one(self) -> None:
        while self._queue:
            candidate = self._queue[0]
            if candidate not in self._items:
                self._queue.popleft()
                continue
            if self._ref_bits.get(candidate, 0) == 0:
                self._queue.popleft()
                size = self._items.pop(candidate, 0)
                self._ref_bits.pop(candidate, None)
                self._used_bytes -= size
                return
            self._ref_bits[candidate] = 0
            self._queue.rotate(-1)

    def stats(self) -> dict:
        total = self._hits + self._misses
        hit_rate = self._hits / total if total else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "used_bytes": self._used_bytes,
            "capacity_bytes": self.capacity_bytes,
            "items": len(self._items),
        }
