from __future__ import annotations

from collections import deque

from kvcache_sim.cache.interfaces import Cache, CacheLookup, CacheMetadata


class LRUKCache(Cache):
    def __init__(self, capacity_bytes: int, k: int = 2) -> None:
        self.capacity_bytes = capacity_bytes
        self.k = max(1, int(k))
        self._items: dict[int, int] = {}
        self._history: dict[int, deque[int]] = {}
        self._used_bytes = 0
        self._hits = 0
        self._misses = 0
        self._clock = 0

    def get(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> CacheLookup:
        self._clock += 1
        self._record_access(key, self._clock)
        if key in self._items:
            self._hits += 1
            return CacheLookup(hit=True, level="l1")

        self._misses += 1
        self._insert(key, size_bytes)
        return CacheLookup(hit=False, level="miss")

    def put(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> None:
        self._clock += 1
        self._record_access(key, self._clock)
        if key in self._items:
            existing = self._items.get(key, 0)
            self._used_bytes -= existing
            self._items.pop(key, None)
        self._insert(key, size_bytes)

    def _record_access(self, key: int, ts: int) -> None:
        history = self._history.get(key)
        if history is None:
            history = deque(maxlen=self.k)
            self._history[key] = history
        history.append(ts)

    def _insert(self, key: int, size_bytes: int) -> None:
        if size_bytes > self.capacity_bytes:
            return

        while self._used_bytes + size_bytes > self.capacity_bytes and self._items:
            self._evict()

        self._items[key] = size_bytes
        self._used_bytes += size_bytes

    def _evict(self) -> None:
        if not self._items:
            return
        victim = None
        victim_score = None
        for key in self._items.keys():
            history = self._history.get(key, deque())
            if len(history) >= self.k:
                score = history[0]
            else:
                score = history[-1] if history else -1
            if victim_score is None or score < victim_score:
                victim_score = score
                victim = key
        if victim is None:
            return
        size_bytes = self._items.pop(victim, 0)
        self._used_bytes -= size_bytes

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
            "k": self.k,
        }
