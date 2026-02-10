from __future__ import annotations

from kvcache_sim.cache.interfaces import Cache, CacheLookup, CacheMetadata
from kvcache_sim.cache.lru import LRUCache


class PartitionedLRUCache(Cache):
    def __init__(self, capacity_bytes: int, partitions: int) -> None:
        self.capacity_bytes = capacity_bytes
        self.partitions = max(1, int(partitions))
        per_partition = capacity_bytes // self.partitions
        self._caches = [LRUCache(per_partition) for _ in range(self.partitions)]
        self._hits = 0
        self._misses = 0

    def get(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> CacheLookup:
        idx = self._select_partition(metadata)
        result = self._caches[idx].get(key, size_bytes, metadata)
        if result.hit:
            self._hits += 1
        else:
            self._misses += 1
        return result

    def put(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> None:
        idx = self._select_partition(metadata)
        self._caches[idx].put(key, size_bytes, metadata)

    def _select_partition(self, metadata: CacheMetadata | None) -> int:
        tenant = metadata.tenant_id if metadata else None
        if tenant is None:
            return 0
        return hash(tenant) % self.partitions

    def stats(self) -> dict:
        total = self._hits + self._misses
        hit_rate = self._hits / total if total else 0.0
        used_bytes = sum(cache.stats().get("used_bytes", 0) for cache in self._caches)
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "used_bytes": used_bytes,
            "capacity_bytes": self.capacity_bytes,
            "partitions": self.partitions,
        }
