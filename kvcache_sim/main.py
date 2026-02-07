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
        if cfg.policy != "lru":
            raise ValueError("trace_cache_capacity_fraction currently requires policy=lru")
        unique_blocks = count_unique_hash_ids(cfg.trace_path)
        if unique_blocks <= 0:
            raise ValueError(f"No hash_ids found in trace: {cfg.trace_path}")
        block_bytes = cfg.block_size_tokens * cfg.model_kv_bytes_per_token
        capacity = int(unique_blocks * block_bytes * cfg.trace_cache_capacity_fraction)
        if capacity <= 0:
            raise ValueError("Computed cache capacity is zero; check trace_cache_capacity_fraction")
        cfg = replace(
            cfg,
            cache_capacity_bytes=capacity,
            l1_cache_capacity_bytes=None,
            l2_cache_capacity_bytes=None,
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
