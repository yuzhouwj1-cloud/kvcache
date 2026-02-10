from __future__ import annotations

from collections import OrderedDict

from kvcache_sim.cache.interfaces import Cache, CacheLookup, CacheMetadata


class TTLCache(Cache):
    def __init__(self, capacity_bytes: int, ttl_ms: int) -> None:
        self.capacity_bytes = capacity_bytes
        self.ttl_ms = max(0, int(ttl_ms))
        self._items: OrderedDict[int, int] = OrderedDict()
        self._expiry: dict[int, int] = {}
        self._used_bytes = 0
        self._hits = 0
        self._misses = 0
        self._now = 0

    def get(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> CacheLookup:
        now = self._advance(metadata)
        if key in self._items:
            if self._is_expired(key, now):
                self._remove(key)
            else:
                self._items.move_to_end(key)
                self._hits += 1
                return CacheLookup(hit=True, level="l1")

        self._misses += 1
        self._insert(key, size_bytes, now)
        return CacheLookup(hit=False, level="miss")

    def put(self, key: int, size_bytes: int, metadata: CacheMetadata | None = None) -> None:
        now = self._advance(metadata)
        if key in self._items:
            self._remove(key)
        self._insert(key, size_bytes, now)

    def _advance(self, metadata: CacheMetadata | None) -> int:
        if metadata and metadata.timestamp_ms is not None and metadata.timestamp_ms > 0:
            self._now = int(metadata.timestamp_ms)
        else:
            self._now += 1
        return self._now

    def _is_expired(self, key: int, now: int) -> bool:
        expiry = self._expiry.get(key)
        return expiry is not None and now >= expiry

    def _purge_expired(self, now: int) -> None:
        expired_keys = [k for k, exp in self._expiry.items() if now >= exp]
        for key in expired_keys:
            self._remove(key)

    def _remove(self, key: int) -> None:
        size_bytes = self._items.pop(key, None)
        if size_bytes is not None:
            self._used_bytes -= size_bytes
        self._expiry.pop(key, None)

    def _insert(self, key: int, size_bytes: int, now: int) -> None:
        if size_bytes > self.capacity_bytes:
            return

        if self.ttl_ms > 0:
            self._purge_expired(now)
            expiry = now + self.ttl_ms
        else:
            expiry = None

        while self._used_bytes + size_bytes > self.capacity_bytes and self._items:
            evict_key = next(iter(self._items))
            self._remove(evict_key)

        self._items[key] = size_bytes
        if expiry is not None:
            self._expiry[key] = expiry
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
            "ttl_ms": self.ttl_ms,
        }
