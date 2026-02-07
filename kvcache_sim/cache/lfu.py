from __future__ import annotations

from collections import OrderedDict, defaultdict

from kvcache_sim.cache.interfaces import Cache, CacheLookup


class LFUCache(Cache):
    def __init__(self, capacity_bytes: int) -> None:
        self.capacity_bytes = capacity_bytes
        self._items: dict[int, int] = {}
        self._freq: dict[int, int] = {}
        self._freq_buckets: dict[int, OrderedDict[int, None]] = defaultdict(OrderedDict)
        self._used_bytes = 0
        self._min_freq = 0
        self._hits = 0
        self._misses = 0

    def get(self, key: int, size_bytes: int) -> CacheLookup:
        if key in self._items:
            self._hits += 1
            self._bump_freq(key)
            return CacheLookup(hit=True, level="l1")

        self._misses += 1
        self._insert(key, size_bytes)
        return CacheLookup(hit=False, level="miss")

    def put(self, key: int, size_bytes: int) -> None:
        if key in self._items:
            existing = self._items.get(key, 0)
            self._used_bytes -= existing
            self._items[key] = size_bytes
            self._used_bytes += size_bytes
            self._bump_freq(key)
            return
        self._insert(key, size_bytes)

    def _bump_freq(self, key: int) -> None:
        freq = self._freq[key]
        bucket = self._freq_buckets[freq]
        bucket.pop(key, None)
        if not bucket and self._min_freq == freq:
            self._min_freq += 1

        new_freq = freq + 1
        self._freq[key] = new_freq
        self._freq_buckets[new_freq][key] = None

    def _insert(self, key: int, size_bytes: int) -> None:
        if size_bytes > self.capacity_bytes:
            return

        while self._used_bytes + size_bytes > self.capacity_bytes and self._items:
            self._evict()

        self._items[key] = size_bytes
        self._used_bytes += size_bytes
        self._freq[key] = 1
        self._freq_buckets[1][key] = None
        self._min_freq = 1

    def _evict(self) -> None:
        bucket = self._freq_buckets[self._min_freq]
        if not bucket:
            return
        key, _ = bucket.popitem(last=False)
        size_bytes = self._items.pop(key, 0)
        self._freq.pop(key, None)
        self._used_bytes -= size_bytes
        if not bucket:
            self._freq_buckets.pop(self._min_freq, None)

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
