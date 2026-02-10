from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from kvcache_sim.analysis.metrics import MetricsCollector, TimeModel
from kvcache_sim.cache.factory import build_cache
from kvcache_sim.config import SequenceLengthSpec, SimulatorConfig, TimeModelConfig
from kvcache_sim.requests.generator import RequestGenerator
from kvcache_sim.requests.trace_utils import count_unique_hash_ids
from kvcache_sim.simulator.engine import Simulator


FRACTIONS = (0.25, 0.50, 0.75, 1.00)
POLICIES = ("lru", "lfu", "hierarchical_lru")


def _base_config(trace_path: Path) -> SimulatorConfig:
    time_model = TimeModelConfig(
        compute_tokens_per_ms=1000.0,
        l1_bandwidth_bytes_per_ms=5e8,
        l2_bandwidth_bytes_per_ms=2e8,
        miss_bandwidth_bytes_per_ms=5e7,
        hit_compute_fraction=0.0,
    )
    return SimulatorConfig(
        seed=7,
        num_requests=0,
        num_sequences=0,
        sequence_length=0,
        sequence_length_dist=SequenceLengthSpec(dist="fixed", value=0),
        model_kv_bytes_per_token=256,
        cache_capacity_bytes=1,
        cache_capacity_blocks=None,
        l1_cache_capacity_bytes=None,
        l2_cache_capacity_bytes=None,
        l1_cache_capacity_blocks=None,
        l2_cache_capacity_blocks=None,
        policy="lru",
        cache_ttl_ms=None,
        lru_k=2,
        twoq_a1in_fraction=0.25,
        twoq_a1out_fraction=0.5,
        arc_p_init_fraction=0.5,
        tenant_partition_count=1,
        reuse_model="zipf",
        reuse_zipf_a=1.2,
        workload_type="trace",
        trace_path=trace_path,
        block_size_tokens=512,
        trace_cache_capacity_fraction=None,
        time_model=time_model,
    )


def _make_config(trace_path: Path, policy: str, block_count: int) -> SimulatorConfig:
    base = _base_config(trace_path)
    block_bytes = base.block_size_tokens * base.model_kv_bytes_per_token
    cache_capacity_bytes = block_count * block_bytes
    if policy == "hierarchical_lru":
        l1_blocks = max(1, int(block_count * 0.25))
        l2_blocks = max(1, block_count - l1_blocks)
        return replace(
            base,
            policy=policy,
            cache_capacity_bytes=cache_capacity_bytes,
            cache_capacity_blocks=block_count,
            l1_cache_capacity_blocks=l1_blocks,
            l2_cache_capacity_blocks=l2_blocks,
            l1_cache_capacity_bytes=l1_blocks * block_bytes,
            l2_cache_capacity_bytes=l2_blocks * block_bytes,
        )
    return replace(
        base,
        policy=policy,
        cache_capacity_bytes=cache_capacity_bytes,
        cache_capacity_blocks=block_count,
        l1_cache_capacity_blocks=None,
        l2_cache_capacity_blocks=None,
        l1_cache_capacity_bytes=None,
        l2_cache_capacity_bytes=None,
    )


def _run_sim(cfg: SimulatorConfig, max_requests: int | None) -> tuple[float, float]:
    cache = build_cache(cfg)
    metrics = MetricsCollector()
    generator = RequestGenerator(cfg)
    time_model = TimeModel(cfg.time_model)
    sim = Simulator(cfg, cache, metrics, time_model)
    for idx, req in enumerate(generator.generate()):
        if max_requests is not None and idx >= max_requests:
            break
        sim.handle_request(req)
    report = metrics.finalize()
    return report.request_full_prefix_hit_rate, report.prefix_block_hit_rate


def _timestamp_throughput(trace_path: Path) -> float:
    base = _base_config(trace_path)
    generator = RequestGenerator(base)
    first_ts: int | None = None
    last_ts: int | None = None
    tokens = 0
    for req in generator.generate():
        if req.timestamp_ms is None or req.timestamp_ms <= 0:
            continue
        if first_ts is None:
            first_ts = req.timestamp_ms
        last_ts = req.timestamp_ms
        tokens += req.input_length or req.sequence_length
    if first_ts is None or last_ts is None or last_ts <= first_ts:
        return 0.0
    return tokens / ((last_ts - first_ts) / 1000.0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Trace cache hit-rate benchmark")
    parser.add_argument(
        "--traces",
        nargs="+",
        required=True,
        help="List of JSONL trace paths",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=None,
        help="Optional cap on number of trace requests to simulate per run.",
    )
    parser.add_argument(
        "--policies",
        nargs="+",
        default=list(POLICIES),
        help="Cache policies to benchmark (default: all).",
    )
    args = parser.parse_args()

    traces = [Path(p) for p in args.traces]
    policies = tuple(args.policies)

    print("# Trace Cache Hit-Rate Matrix")
    print()
    for trace_path in traces:
        unique_blocks = count_unique_hash_ids(trace_path)
        if unique_blocks <= 0:
            raise ValueError(f"No hash_ids found in trace: {trace_path}")
        print(f"## {trace_path}")
        print()
        print(f"Unique blocks (deduplicated): **{unique_blocks:,}**")
        timestamp_throughput = _timestamp_throughput(trace_path)
        if timestamp_throughput > 0:
            print(f"Timestamp throughput (tokens/s): **{timestamp_throughput:,.2f}**")
        print()
        print(f"Policies: **{', '.join(policies)}**")
        if args.max_requests is not None:
            print(f"Simulated requests per run: **{args.max_requests:,}**")
            print()
        print(
            "| Policy | Cache fraction | Cache time (s) | Cache blocks | Cache capacity (GB) | Hit rate | Prefix block hit rate | Notes |"
        )
        print("| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
        for policy in policies:
            for fraction in FRACTIONS:
                blocks = max(1, int(unique_blocks * fraction))
                cfg = _make_config(trace_path, policy, blocks)
                cache_time_s = ""
                cache_capacity_gb = ""
                cache_bytes = blocks * cfg.block_size_tokens * 69 * 1024
                cache_capacity_gb = f"{cache_bytes / (1024 ** 3):.2f}"
                if timestamp_throughput > 0:
                    cache_tokens = blocks * cfg.block_size_tokens
                    cache_time_s = f"{cache_tokens / timestamp_throughput:.2f}"
                hit_rate, prefix_hit_rate = _run_sim(cfg, args.max_requests)
                note = ""
                if policy == "hierarchical_lru":
                    l1_blocks = cfg.l1_cache_capacity_blocks or 0
                    l2_blocks = cfg.l2_cache_capacity_blocks or 0
                    note = f"L1 {l1_blocks:,} / L2 {l2_blocks:,} blocks"
                print(
                    f"| {policy} | {fraction:.0%} | {cache_time_s} | {blocks:,} | {cache_capacity_gb} | {hit_rate:.4f} | {prefix_hit_rate:.4f} | {note} |"
                )
        print()


if __name__ == "__main__":
    main()
