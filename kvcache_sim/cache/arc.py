from __future__ import annotations

from collections import OrderedDict

from kvcache_sim.cache.interfaces import Cache, CacheLookup, CacheMetadata


class ARCCache(Cache):
    def __init__(self, capacity_bytes: int, p_init_fraction: float = 0.5) -> None:
        self.capacity_bytes = capacity_bytes
        self._p = int(capacity_bytes * max(0.0, min(1.0, p_init_fraction)))
        self._t1: OrderedDict[int, int] = OrderedDict()
        self._t2: OrderedDict[int, int] = OrderedDict()
        self._b1: OrderedDict[int, int] = OrderedDict()
        self._b2: OrderedDict[int, int] = OrderedDict()
        self._t1_bytes = 0
        self._t2_bytes = 0
        self._hits = 0
        self._misses = 0

    def get(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> CacheLookup:
        if key in self._t1:
            size = self._t1.pop(key)
            self._t1_bytes -= size
            self._t2[key] = size
            self._t2_bytes += size
            self._hits += 1
            return CacheLookup(hit=True, level="l1")

        if key in self._t2:
            self._t2.move_to_end(key)
            self._hits += 1
            return CacheLookup(hit=True, level="l1")

        self._misses += 1

        if key in self._b1:
            self._adapt_p(increase=True, ghost_size=self._b1.pop(key))
            self._replace(key)
            self._insert_t2(key, size_bytes)
            return CacheLookup(hit=False, level="miss")

        if key in self._b2:
            self._adapt_p(increase=False, ghost_size=self._b2.pop(key))
            self._replace(key)
            self._insert_t2(key, size_bytes)
            return CacheLookup(hit=False, level="miss")

        self._replace(key)
        self._insert_t1(key, size_bytes)
        return CacheLookup(hit=False, level="miss")

    def put(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> None:
        if key in self._t1:
            size = self._t1.pop(key)
            self._t1_bytes -= size
            self._insert_t2(key, size_bytes)
            return
        if key in self._t2:
            size = self._t2.pop(key)
            self._t2_bytes -= size
            self._insert_t2(key, size_bytes)
            return
        if key in self._b1:
            self._b1.pop(key, None)
            self._replace(key)
            self._insert_t2(key, size_bytes)
            return
        if key in self._b2:
            self._b2.pop(key, None)
            self._replace(key)
            self._insert_t2(key, size_bytes)
            return
        self._replace(key)
        self._insert_t1(key, size_bytes)

    def _adapt_p(self, increase: bool, ghost_size: int | None) -> None:
        ghost_size = ghost_size or 0
        delta = max(1, ghost_size)
        if increase:
            self._p = min(self.capacity_bytes, self._p + delta)
        else:
            self._p = max(0, self._p - delta)

    def _replace(self, key: int) -> None:
        while self._t1_bytes + self._t2_bytes >= self.capacity_bytes and (self._t1 or self._t2):
            if self._t1 and (self._t1_bytes > self._p or (key in self._b2 and self._t1_bytes == self._p)):
                evict_key, evict_size = self._t1.popitem(last=False)
                self._t1_bytes -= evict_size
                self._b1[evict_key] = evict_size
                self._trim_ghost(self._b1)
            elif self._t2:
                evict_key, evict_size = self._t2.popitem(last=False)
                self._t2_bytes -= evict_size
                self._b2[evict_key] = evict_size
                self._trim_ghost(self._b2)
            else:
                break

    def _trim_ghost(self, ghost: OrderedDict[int, int]) -> None:
        total_ghost = sum(ghost.values())
        while total_ghost > self.capacity_bytes and ghost:
            _, size = ghost.popitem(last=False)
            total_ghost -= size

    def _insert_t1(self, key: int, size_bytes: int) -> None:
        if size_bytes > self.capacity_bytes:
            return
        self._t1[key] = size_bytes
        self._t1_bytes += size_bytes

    def _insert_t2(self, key: int, size_bytes: int) -> None:
        if size_bytes > self.capacity_bytes:
            return
        self._t2[key] = size_bytes
        self._t2_bytes += size_bytes

    def stats(self) -> dict:
        total = self._hits + self._misses
        hit_rate = self._hits / total if total else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "used_bytes": self._t1_bytes + self._t2_bytes,
            "capacity_bytes": self.capacity_bytes,
            "p_bytes": self._p,
            "items": len(self._t1) + len(self._t2),
        }
