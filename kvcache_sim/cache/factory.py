from __future__ import annotations

from kvcache_sim.config import SimulatorConfig
from kvcache_sim.cache.lru import LRUCache
from kvcache_sim.cache.lfu import LFUCache
from kvcache_sim.cache.hierarchical_lru import HierarchicalLRUCache
from kvcache_sim.cache.fifo import FIFOCache
from kvcache_sim.cache.mru import MRUCache
from kvcache_sim.cache.ttl import TTLCache
from kvcache_sim.cache.twoq import TwoQCache
from kvcache_sim.cache.arc import ARCCache
from kvcache_sim.cache.lruk import LRUKCache
from kvcache_sim.cache.clock import ClockCache
from kvcache_sim.cache.clockpro import ClockProCache
from kvcache_sim.cache.priority_lru import PriorityLRUCache
from kvcache_sim.cache.partitioned_lru import PartitionedLRUCache
from kvcache_sim.cache.interfaces import Cache


def build_cache(cfg: SimulatorConfig) -> Cache:
    if cfg.policy == "lru":
        return LRUCache(cfg.cache_capacity_bytes)
    if cfg.policy == "lfu":
        return LFUCache(cfg.cache_capacity_bytes)
    if cfg.policy == "fifo":
        return FIFOCache(cfg.cache_capacity_bytes)
    if cfg.policy == "mru":
        return MRUCache(cfg.cache_capacity_bytes)
    if cfg.policy == "ttl":
        return TTLCache(cfg.cache_capacity_bytes, cfg.cache_ttl_ms or 0)
    if cfg.policy in {"2q", "twoq"}:
        return TwoQCache(
            cfg.cache_capacity_bytes,
            a1in_fraction=cfg.twoq_a1in_fraction,
            a1out_fraction=cfg.twoq_a1out_fraction,
        )
    if cfg.policy == "arc":
        return ARCCache(cfg.cache_capacity_bytes, p_init_fraction=cfg.arc_p_init_fraction)
    if cfg.policy in {"lru_k", "lruk"}:
        return LRUKCache(cfg.cache_capacity_bytes, k=cfg.lru_k)
    if cfg.policy == "clock":
        return ClockCache(cfg.cache_capacity_bytes)
    if cfg.policy in {"clock_pro", "clockpro"}:
        return ClockProCache(cfg.cache_capacity_bytes)
    if cfg.policy == "priority_lru":
        return PriorityLRUCache(cfg.cache_capacity_bytes)
    if cfg.policy == "tenant_lru":
        return PartitionedLRUCache(cfg.cache_capacity_bytes, partitions=cfg.tenant_partition_count)
    if cfg.policy == "hierarchical_lru":
        if cfg.l1_cache_capacity_bytes is None or cfg.l2_cache_capacity_bytes is None:
            raise ValueError("hierarchical_lru requires l1_cache_capacity_bytes and l2_cache_capacity_bytes")
        return HierarchicalLRUCache(cfg.l1_cache_capacity_bytes, cfg.l2_cache_capacity_bytes)
    raise ValueError(f"Unknown cache policy: {cfg.policy}")
