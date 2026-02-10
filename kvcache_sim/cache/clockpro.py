from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from kvcache_sim.cache.interfaces import Cache, CacheLookup, CacheMetadata


@dataclass
class _Entry:
    size: int
    ref: int
    hot: bool


class ClockProCache(Cache):
    def __init__(self, capacity_bytes: int) -> None:
        self.capacity_bytes = capacity_bytes
        self._entries: dict[int, _Entry] = {}
        self._order: deque[int] = deque()
        self._ghost: deque[int] = deque()
        self._ghost_set: set[int] = set()
        self._used_bytes = 0
        self._hot_bytes = 0
        self._hot_target = capacity_bytes // 2
        self._hits = 0
        self._misses = 0

    def get(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> CacheLookup:
        if key in self._entries:
            entry = self._entries[key]
            entry.ref = 1
            if not entry.hot:
                entry.hot = True
                self._hot_bytes += entry.size
            self._hits += 1
            return CacheLookup(hit=True, level="l1")

        self._misses += 1
        if key in self._ghost_set:
            self._ghost_set.remove(key)
            try:
                self._ghost.remove(key)
            except ValueError:
                pass
            self._hot_target = min(self.capacity_bytes, self._hot_target + size_bytes)
        else:
            self._hot_target = max(0, self._hot_target - size_bytes)

        self._insert(key, size_bytes)
        return CacheLookup(hit=False, level="miss")

    def put(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> None:
        if key in self._entries:
            entry = self._entries.pop(key)
            self._used_bytes -= entry.size
            if entry.hot:
                self._hot_bytes -= entry.size
            try:
                self._order.remove(key)
            except ValueError:
                pass
        self._insert(key, size_bytes)

    def _insert(self, key: int, size_bytes: int) -> None:
        if size_bytes > self.capacity_bytes:
            return
        while self._used_bytes + size_bytes > self.capacity_bytes and self._entries:
            self._evict_one()
        entry = _Entry(size=size_bytes, ref=1, hot=False)
        self._entries[key] = entry
        self._order.append(key)
        self._used_bytes += size_bytes

    def _evict_one(self) -> None:
        while self._order:
            key = self._order[0]
            entry = self._entries.get(key)
            if entry is None:
                self._order.popleft()
                continue
            if entry.ref == 1:
                entry.ref = 0
                if not entry.hot and self._hot_bytes < self._hot_target:
                    entry.hot = True
                    self._hot_bytes += entry.size
                self._order.rotate(-1)
                continue

            if entry.hot:
                entry.hot = False
                self._hot_bytes -= entry.size
                self._order.rotate(-1)
                continue

            self._order.popleft()
            self._entries.pop(key, None)
            self._used_bytes -= entry.size
            self._ghost.append(key)
            self._ghost_set.add(key)
            self._trim_ghost()
            return

    def _trim_ghost(self) -> None:
        while len(self._ghost) > 0 and len(self._ghost_set) > 0 and len(self._ghost) > 2 * len(self._entries):
            old = self._ghost.popleft()
            self._ghost_set.discard(old)

    def stats(self) -> dict:
        total = self._hits + self._misses
        hit_rate = self._hits / total if total else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "used_bytes": self._used_bytes,
            "capacity_bytes": self.capacity_bytes,
            "hot_target_bytes": self._hot_target,
            "items": len(self._entries),
        }
