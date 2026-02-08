from __future__ import annotations

import argparse
from dataclasses import replace

from kvcache_sim.config import load_config
from kvcache_sim.requests.generator import RequestGenerator
from kvcache_sim.requests.trace_utils import count_unique_hash_ids
from kvcache_sim.simulator.engine import Simulator
from kvcache_sim.analysis.metrics import MetricsCollector, TimeModel
from kvcache_sim.cache.factory import build_cache


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KV cache simulator")
    parser.add_argument("--config", required=True, help="Path to YAML config")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)

    if cfg.workload_type == "trace" and cfg.trace_cache_capacity_fraction is not None:
        if cfg.trace_path is None:
            raise ValueError("trace_cache_capacity_fraction requires trace_path")
        if cfg.policy not in {"lru", "lfu"}:
            raise ValueError("trace_cache_capacity_fraction currently supports policy=lru or policy=lfu")
        if cfg.trace_cache_capacity_fraction <= 0 or cfg.trace_cache_capacity_fraction > 1:
            raise ValueError("trace_cache_capacity_fraction must be in the (0, 1] range")
        unique_blocks = count_unique_hash_ids(cfg.trace_path)
        if unique_blocks <= 0:
            raise ValueError(f"No hash_ids found in trace: {cfg.trace_path}")
        capacity_blocks = int(unique_blocks * cfg.trace_cache_capacity_fraction)
        if capacity_blocks <= 0:
            raise ValueError("Computed cache capacity blocks is zero; check trace_cache_capacity_fraction")
        block_bytes = cfg.block_size_tokens * cfg.model_kv_bytes_per_token
        capacity = capacity_blocks * block_bytes
        cfg = replace(
            cfg,
            cache_capacity_bytes=capacity,
            cache_capacity_blocks=capacity_blocks,
            l1_cache_capacity_bytes=None,
            l2_cache_capacity_bytes=None,
            l1_cache_capacity_blocks=None,
            l2_cache_capacity_blocks=None,
        )

    cache = build_cache(cfg)
    metrics = MetricsCollector()
    generator = RequestGenerator(cfg)
    time_model = TimeModel(cfg.time_model)
    sim = Simulator(cfg, cache, metrics, time_model)

    for req in generator.generate():
        sim.handle_request(req)

    report = metrics.finalize()
    print(report.to_text())


if __name__ == "__main__":
    main()
