from __future__ import annotations

from kvcache_sim.cache.interfaces import Cache, CacheLookup, CacheMetadata
from kvcache_sim.cache.lru import LRUCache


class HierarchicalLRUCache(Cache):
    def __init__(self, l1_capacity_bytes: int, l2_capacity_bytes: int) -> None:
        self.l1 = LRUCache(l1_capacity_bytes)
        self.l2 = LRUCache(l2_capacity_bytes)
        self._l1_hits = 0
        self._l2_hits = 0
        self._misses = 0

    def get(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> CacheLookup:
        if self.l1.contains(key):
            self._l1_hits += 1
            self.l1.get(key, size_bytes, metadata)
            return CacheLookup(hit=True, level="l1")

        if self.l2.contains(key):
            self._l2_hits += 1
            self.l2.get(key, size_bytes, metadata)
            # Promote to L1 while keeping in L2 (inclusive policy).
            self.l1.get(key, size_bytes, metadata)
            return CacheLookup(hit=True, level="l2")

        self._misses += 1
        # Insert into L2 by default; L1 will be filled on future reuse or promotion.
        self.l2.get(key, size_bytes, metadata)
        return CacheLookup(hit=False, level="miss")

    def put(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> None:
        # Insert into L2 by default; L1 will be filled on future reuse or promotion.
        self.l2.put(key, size_bytes, metadata)

    def stats(self) -> dict:
        total = self._l1_hits + self._l2_hits + self._misses
        hit_rate = (self._l1_hits + self._l2_hits) / total if total else 0.0
        return {
            "l1_hits": self._l1_hits,
            "l2_hits": self._l2_hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "l1_used_bytes": self.l1.stats().get("used_bytes", 0),
            "l1_capacity_bytes": self.l1.stats().get("capacity_bytes", 0),
            "l2_used_bytes": self.l2.stats().get("used_bytes", 0),
            "l2_capacity_bytes": self.l2.stats().get("capacity_bytes", 0),
        }
