from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Union


@dataclass(frozen=True)
class CacheLookup:
    hit: bool
    level: str  # "l1", "l2", or "miss"


@dataclass(frozen=True)
class CacheMetadata:
    timestamp_ms: Optional[int] = None
    priority: int = 0
    pinned: bool = False
    tenant_id: Optional[Union[int, str]] = None


class Cache(ABC):
    @abstractmethod
    def get(self, key: int, size_bytes: int, metadata: Optional[CacheMetadata] = None) -> CacheLookup:
        """Return lookup result; update internal state."""

    @abstractmethod
    def put(self, key: int, size_bytes: int, metadata: Optional[CacheMetadata] = None) -> None:
        """Insert/update cache entry without counting as a lookup."""

    @abstractmethod
    def stats(self) -> dict:
        """Return cache-level stats snapshot."""
