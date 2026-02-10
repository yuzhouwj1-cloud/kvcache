from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from kvcache_sim.analysis.metrics import MetricsCollector, TimeModel
from kvcache_sim.cache.factory import build_cache
from kvcache_sim.config import SimulatorConfig, SequenceLengthSpec, TimeModelConfig
from kvcache_sim.requests.generator import RequestGenerator


@dataclass(frozen=True)
class CompareResult:
    label: str
    report_text: str
    throughput_tokens_per_s: float
    block_hit_rate: float
    request_hit_rate: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare trace throughput with and without KV cache.")
    parser.add_argument("--trace-dir", required=True, help="Directory containing JSONL traces")
    parser.add_argument("--cache-capacity-bytes", type=int, required=True)
    parser.add_argument("--block-size-tokens", type=int, default=512)
    parser.add_argument("--model-kv-bytes-per-token", type=int, default=256)
    parser.add_argument("--policy", default="lru")
    parser.add_argument("--compute-tokens-per-ms", type=float, default=1200.0)
    parser.add_argument("--l1-bandwidth-bytes-per-ms", type=float, default=7.5e8)
    parser.add_argument("--l2-bandwidth-bytes-per-ms", type=float, default=3.0e8)
    parser.add_argument("--miss-bandwidth-bytes-per-ms", type=float, default=6.0e7)
    parser.add_argument("--hit-compute-fraction", type=float, default=0.2)
    return parser.parse_args()


def _build_cfg(trace_path: Path, cache_capacity_bytes: int, args: argparse.Namespace) -> SimulatorConfig:
    seq_spec = SequenceLengthSpec(dist="fixed", value=0)
    time_model = TimeModelConfig(
        compute_tokens_per_ms=args.compute_tokens_per_ms,
        l1_bandwidth_bytes_per_ms=args.l1_bandwidth_bytes_per_ms,
        l2_bandwidth_bytes_per_ms=args.l2_bandwidth_bytes_per_ms,
        miss_bandwidth_bytes_per_ms=args.miss_bandwidth_bytes_per_ms,
        hit_compute_fraction=args.hit_compute_fraction,
    )
    return SimulatorConfig(
        seed=1,
        num_requests=0,
        num_sequences=0,
        sequence_length=0,
        sequence_length_dist=seq_spec,
        model_kv_bytes_per_token=args.model_kv_bytes_per_token,
        cache_capacity_bytes=cache_capacity_bytes,
        cache_capacity_blocks=None,
        l1_cache_capacity_bytes=None,
        l2_cache_capacity_bytes=None,
        l1_cache_capacity_blocks=None,
        l2_cache_capacity_blocks=None,
        policy=args.policy,
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
        block_size_tokens=args.block_size_tokens,
        trace_cache_capacity_fraction=None,
        time_model=time_model,
    )


def _run_sim(cfg: SimulatorConfig, label: str) -> CompareResult:
    cache = build_cache(cfg)
    metrics = MetricsCollector()
    time_model = TimeModel(cfg.time_model)
    generator = RequestGenerator(cfg)

    from kvcache_sim.simulator.engine import Simulator

    sim = Simulator(cfg, cache, metrics, time_model)
    for req in generator.generate():
        sim.handle_request(req)

    report = metrics.finalize()
    block_hit_rate = report.block_hits / report.block_total if report.block_total else 0.0
    request_hit_rate = report.hits / report.total_requests if report.total_requests else 0.0
    return CompareResult(
        label=label,
        report_text=report.to_text(),
        throughput_tokens_per_s=report.throughput_tokens_per_s,
        block_hit_rate=block_hit_rate,
        request_hit_rate=request_hit_rate,
    )


def _compare_trace(trace_path: Path, args: argparse.Namespace) -> None:
    cfg_cache = _build_cfg(trace_path, args.cache_capacity_bytes, args)
    cfg_nocache = _build_cfg(trace_path, 0, args)

    with_cache = _run_sim(cfg_cache, "with_cache")
    no_cache = _run_sim(cfg_nocache, "no_cache")

    improvement = (
        (with_cache.throughput_tokens_per_s / no_cache.throughput_tokens_per_s)
        if no_cache.throughput_tokens_per_s > 0
        else 0.0
    )

    print(f"\n== Trace: {trace_path.name} ==")
    print("-- With Cache --")
    print(with_cache.report_text)
    print("-- No Cache --")
    print(no_cache.report_text)
    print(f"Throughput speedup (with/without): {improvement:.3f}x")
    print(f"Block hit rate (prefix): {with_cache.block_hit_rate:.4f}")
    print(f"Request hit rate: {with_cache.request_hit_rate:.4f}")


def main() -> None:
    args = parse_args()
    trace_dir = Path(args.trace_dir)
    traces = sorted(trace_dir.glob("*.jsonl"))
    if not traces:
        raise ValueError(f"No JSONL traces found in {trace_dir}")
    for trace_path in traces:
        _compare_trace(trace_path, args)


if __name__ == "__main__":
    main()
