from __future__ import annotations

import argparse
import csv
from dataclasses import replace
from pathlib import Path

from kvcache_sim.analysis.metrics import MetricsCollector, TimeModel
from kvcache_sim.cache.factory import build_cache
from kvcache_sim.config import SimulatorConfig, load_config
from kvcache_sim.requests.generator import RequestGenerator
from kvcache_sim.requests.trace_utils import count_unique_hash_ids
from kvcache_sim.simulator.engine import Simulator


DEFAULT_TRACES = [
    "FAST25-release/arxiv-trace/mooncake_trace.jsonl",
    "FAST25-release/traces/conversation_trace.jsonl",
    "FAST25-release/traces/toolagent_trace.jsonl",
    "FAST25-release/traces/synthetic_trace.jsonl",
]

DEFAULT_POLICIES = [
    "lru",
    "fifo",
    "mru",
    "lfu",
    "ttl",
    "2q",
    "arc",
    "lru_k",
    "clock",
    "clock_pro",
    "priority_lru",
    "tenant_lru",
    "hierarchical_lru",
]

DEFAULT_FRACTIONS = [0.10, 0.25, 0.50, 0.75]


def _simulate(cfg: SimulatorConfig) -> dict:
    cache = build_cache(cfg)
    metrics = MetricsCollector()
    generator = RequestGenerator(cfg)
    time_model = TimeModel(cfg.time_model)
    sim = Simulator(cfg, cache, metrics, time_model)
    for req in generator.generate():
        sim.handle_request(req)
    report = metrics.finalize()
    return {
        "requests": report.total_requests,
        "req_hit_rate": report.request_full_prefix_hit_rate,
        "block_hit_rate": report.prefix_block_hit_rate,
        "ttft_mean_ms": report.ttft_mean_ms,
        "ttft_p95_ms": report.ttft_p95_ms,
        "ttft_p99_ms": report.ttft_p99_ms,
        "throughput_tps": report.throughput_tokens_per_s,
        "throughput_source": report.throughput_source,
    }


def _capacity_from_fraction(cfg: SimulatorConfig, trace_path: Path, fraction: float) -> tuple[int, int]:
    unique_blocks = count_unique_hash_ids(trace_path)
    if unique_blocks <= 0:
        raise ValueError(f"No hash_ids found in trace: {trace_path}")
    capacity_blocks = max(1, int(unique_blocks * fraction))
    block_bytes = cfg.block_size_tokens * cfg.model_kv_bytes_per_token
    capacity_bytes = capacity_blocks * block_bytes
    return capacity_bytes, capacity_blocks


def main() -> None:
    parser = argparse.ArgumentParser(description="Run trace matrix for multiple policies/capacities.")
    parser.add_argument("--base-config", default="configs/fast25_trace.yaml")
    parser.add_argument("--output", default="outputs/trace_matrix.csv")
    parser.add_argument("--ttl-ms", type=int, default=600_000)
    parser.add_argument("--traces", nargs="*", default=None)
    parser.add_argument("--fractions", nargs="*", type=float, default=None)
    parser.add_argument("--policies", nargs="*", default=None)
    args = parser.parse_args()

    base_cfg = load_config(args.base_config)
    repo_root = Path(args.base_config).resolve().parent.parent
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    traces = args.traces if args.traces else DEFAULT_TRACES
    fractions = args.fractions if args.fractions else DEFAULT_FRACTIONS
    policies = args.policies if args.policies else DEFAULT_POLICIES

    rows = []
    for trace_rel in traces:
        trace_path = Path(trace_rel)
        if not trace_path.is_absolute():
            trace_path = repo_root / trace_path
        for fraction in fractions:
            capacity_bytes, capacity_blocks = _capacity_from_fraction(base_cfg, trace_path, fraction)
            for policy in policies:
                cfg = replace(
                    base_cfg,
                    trace_path=trace_path,
                    workload_type="trace",
                    policy=policy,
                    cache_capacity_bytes=capacity_bytes,
                    cache_capacity_blocks=capacity_blocks,
                    l1_cache_capacity_bytes=None,
                    l2_cache_capacity_bytes=None,
                    l1_cache_capacity_blocks=None,
                    l2_cache_capacity_blocks=None,
                    trace_cache_capacity_fraction=None,
                    cache_ttl_ms=args.ttl_ms,
                    tenant_partition_count=1,
                )
                if policy == "hierarchical_lru":
                    l1 = capacity_bytes // 2
                    l2 = capacity_bytes - l1
                    cfg = replace(
                        cfg,
                        l1_cache_capacity_bytes=l1,
                        l2_cache_capacity_bytes=l2,
                    )

                result = _simulate(cfg)
                rows.append(
                    {
                        "trace": str(trace_path),
                        "policy": policy,
                        "capacity_fraction": fraction,
                        "capacity_bytes": capacity_bytes,
                        "capacity_blocks": capacity_blocks,
                        **result,
                    }
                )

    fieldnames = list(rows[0].keys()) if rows else []
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
