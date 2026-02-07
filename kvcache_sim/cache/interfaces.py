from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CacheLookup:
    hit: bool
    level: str  # "l1", "l2", or "miss"


class Cache(ABC):
    @abstractmethod
    def get(self, key: int, size_bytes: int) -> CacheLookup:
        """Return lookup result; update internal state."""

    @abstractmethod
    def put(self, key: int, size_bytes: int) -> None:
        """Insert/update cache entry without counting as a lookup."""

    @abstractmethod
    def stats(self) -> dict:
        """Return cache-level stats snapshot."""
