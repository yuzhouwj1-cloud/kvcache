from __future__ import annotations

from kvcache_sim.config import SimulatorConfig
from kvcache_sim.cache.lru import LRUCache
from kvcache_sim.cache.lfu import LFUCache
from kvcache_sim.cache.hierarchical_lru import HierarchicalLRUCache
from kvcache_sim.cache.interfaces import Cache


def build_cache(cfg: SimulatorConfig) -> Cache:
    if cfg.policy == "lru":
        return LRUCache(cfg.cache_capacity_bytes)
    if cfg.policy == "lfu":
        return LFUCache(cfg.cache_capacity_bytes)
    if cfg.policy == "hierarchical_lru":
        if cfg.l1_cache_capacity_bytes is None or cfg.l2_cache_capacity_bytes is None:
            raise ValueError("hierarchical_lru requires l1_cache_capacity_bytes and l2_cache_capacity_bytes")
        return HierarchicalLRUCache(cfg.l1_cache_capacity_bytes, cfg.l2_cache_capacity_bytes)
    raise ValueError(f"Unknown cache policy: {cfg.policy}")
