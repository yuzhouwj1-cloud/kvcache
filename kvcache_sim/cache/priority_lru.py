from __future__ import annotations

from collections import OrderedDict, defaultdict

from kvcache_sim.cache.interfaces import Cache, CacheLookup, CacheMetadata


class PriorityLRUCache(Cache):
    def __init__(self, capacity_bytes: int) -> None:
        self.capacity_bytes = capacity_bytes
        self._buckets: dict[int, OrderedDict[int, int]] = defaultdict(OrderedDict)
        self._priorities: dict[int, int] = {}
        self._pinned: set[int] = set()
        self._used_bytes = 0
        self._hits = 0
        self._misses = 0

    def get(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> CacheLookup:
        if key in self._priorities:
            priority = self._priorities[key]
            bucket = self._buckets[priority]
            if key in bucket:
                bucket.move_to_end(key)
            self._hits += 1
            return CacheLookup(hit=True, level="l1")

        self._misses += 1
        self._insert(key, size_bytes, metadata)
        return CacheLookup(hit=False, level="miss")

    def put(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> None:
        if key in self._priorities:
            priority = self._priorities[key]
            bucket = self._buckets[priority]
            existing = bucket.pop(key, None)
            if existing is not None:
                self._used_bytes -= existing
        self._insert(key, size_bytes, metadata)

    def _insert(self, key: int, size_bytes: int, metadata: CacheMetadata | None) -> None:
        if size_bytes > self.capacity_bytes:
            return
        priority = metadata.priority if metadata else 0
        if metadata and metadata.pinned:
            self._pinned.add(key)
        self._evict_if_needed(size_bytes)
        self._priorities[key] = priority
        self._buckets[priority][key] = size_bytes
        self._used_bytes += size_bytes

    def _evict_if_needed(self, incoming_size: int) -> None:
        while self._used_bytes + incoming_size > self.capacity_bytes:
            victim = self._select_victim()
            if victim is None:
                break
            key, priority = victim
            bucket = self._buckets[priority]
            size = bucket.pop(key, 0)
            self._priorities.pop(key, None)
            self._pinned.discard(key)
            self._used_bytes -= size
            if not bucket:
                self._buckets.pop(priority, None)

    def _select_victim(self) -> tuple[int, int] | None:
        for priority in sorted(self._buckets.keys()):
            bucket = self._buckets[priority]
            for key in list(bucket.keys()):
                if key in self._pinned:
                    continue
                return key, priority
        # If everything is pinned, fall back to lowest priority anyway.
        for priority in sorted(self._buckets.keys()):
            bucket = self._buckets[priority]
            if bucket:
                key = next(iter(bucket.keys()))
                return key, priority
        return None

    def stats(self) -> dict:
        total = self._hits + self._misses
        hit_rate = self._hits / total if total else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "used_bytes": self._used_bytes,
            "capacity_bytes": self.capacity_bytes,
            "items": len(self._priorities),
            "pinned": len(self._pinned),
        }
