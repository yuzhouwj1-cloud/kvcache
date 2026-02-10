from __future__ import annotations

from collections import OrderedDict

from kvcache_sim.cache.interfaces import Cache, CacheLookup, CacheMetadata


class TwoQCache(Cache):
    def __init__(self, capacity_bytes: int, a1in_fraction: float = 0.25, a1out_fraction: float = 0.5) -> None:
        self.capacity_bytes = capacity_bytes
        self.a1in_capacity = int(capacity_bytes * max(0.0, min(1.0, a1in_fraction)))
        self.a1out_capacity = int(capacity_bytes * max(0.0, min(1.0, a1out_fraction)))
        self._a1in: OrderedDict[int, int] = OrderedDict()
        self._a1out: OrderedDict[int, int] = OrderedDict()
        self._am: OrderedDict[int, int] = OrderedDict()
        self._a1in_bytes = 0
        self._am_bytes = 0
        self._hits = 0
        self._misses = 0

    def get(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> CacheLookup:
        if key in self._am:
            self._am.move_to_end(key)
            self._hits += 1
            return CacheLookup(hit=True, level="l1")

        if key in self._a1in:
            size = self._a1in.pop(key)
            self._a1in_bytes -= size
            self._am[key] = size
            self._am_bytes += size
            self._hits += 1
            self._evict_if_needed()
            return CacheLookup(hit=True, level="l1")

        if key in self._a1out:
            self._misses += 1
            self._a1out.pop(key, None)
            self._insert_am(key, size_bytes)
            return CacheLookup(hit=False, level="miss")

        self._misses += 1
        self._insert_a1in(key, size_bytes)
        return CacheLookup(hit=False, level="miss")

    def put(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> None:
        if key in self._am:
            existing = self._am.pop(key)
            self._am_bytes -= existing
            self._insert_am(key, size_bytes)
            return
        if key in self._a1in:
            existing = self._a1in.pop(key)
            self._a1in_bytes -= existing
            self._insert_a1in(key, size_bytes)
            return
        if key in self._a1out:
            self._a1out.pop(key, None)
            self._insert_am(key, size_bytes)
            return
        self._insert_a1in(key, size_bytes)

    def _insert_a1in(self, key: int, size_bytes: int) -> None:
        if size_bytes > self.capacity_bytes:
            return
        self._a1in[key] = size_bytes
        self._a1in_bytes += size_bytes
        self._evict_if_needed()

    def _insert_am(self, key: int, size_bytes: int) -> None:
        if size_bytes > self.capacity_bytes:
            return
        self._am[key] = size_bytes
        self._am_bytes += size_bytes
        self._evict_if_needed()

    def _evict_if_needed(self) -> None:
        while self._a1in_bytes + self._am_bytes > self.capacity_bytes:
            if self._a1in and self._a1in_bytes > self.a1in_capacity:
                evict_key, evict_size = self._a1in.popitem(last=False)
                self._a1in_bytes -= evict_size
                self._a1out[evict_key] = evict_size
                self._trim_a1out()
            elif self._am:
                evict_key, evict_size = self._am.popitem(last=False)
                self._am_bytes -= evict_size
                self._a1out[evict_key] = evict_size
                self._trim_a1out()
            elif self._a1in:
                evict_key, evict_size = self._a1in.popitem(last=False)
                self._a1in_bytes -= evict_size
                self._a1out[evict_key] = evict_size
                self._trim_a1out()
            else:
                break

    def _trim_a1out(self) -> None:
        total_ghost = sum(self._a1out.values())
        while total_ghost > self.a1out_capacity and self._a1out:
            _, evict_size = self._a1out.popitem(last=False)
            total_ghost -= evict_size

    def stats(self) -> dict:
        total = self._hits + self._misses
        hit_rate = self._hits / total if total else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "used_bytes": self._a1in_bytes + self._am_bytes,
            "capacity_bytes": self.capacity_bytes,
            "a1in_bytes": self._a1in_bytes,
            "am_bytes": self._am_bytes,
            "items": len(self._a1in) + len(self._am),
        }
