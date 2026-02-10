from __future__ import annotations

from collections import OrderedDict

from kvcache_sim.cache.interfaces import Cache, CacheLookup, CacheMetadata


class MRUCache(Cache):
    def __init__(self, capacity_bytes: int) -> None:
        self.capacity_bytes = capacity_bytes
        self._items: OrderedDict[int, int] = OrderedDict()
        self._used_bytes = 0
        self._hits = 0
        self._misses = 0

    def get(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> CacheLookup:
        if key in self._items:
            self._items.move_to_end(key)
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
        self._insert(key, size_bytes)

    def _insert(self, key: int, size_bytes: int) -> None:
        if size_bytes > self.capacity_bytes:
            return

        while self._used_bytes + size_bytes > self.capacity_bytes and self._items:
            _, evicted_size = self._items.popitem(last=True)
            self._used_bytes -= evicted_size

        self._items[key] = size_bytes
        self._used_bytes += size_bytes

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
