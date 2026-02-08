from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from kvcache_sim.requests.models import Request
from kvcache_sim.cache.interfaces import CacheLookup
from kvcache_sim.config import TimeModelConfig


@dataclass
class MetricsReport:
    total_requests: int
    request_full_prefix_hits: int
    request_full_prefix_misses: int
    request_full_prefix_hit_rate: float
    bytes_requested: int
    bytes_cached: int
    bytes_read: int
    bytes_written: int
    prefix_block_hits: int
    prefix_block_total: int
    prefix_block_hit_rate: float
    ttft_mean_ms: float
    ttft_p95_ms: float
    ttft_p99_ms: float
    throughput_tokens_per_s: float
    throughput_source: str

    def to_text(self) -> str:
        hit_rate = self.request_full_prefix_hit_rate
        block_hit_rate = self.prefix_block_hit_rate
        return (
            "KV Cache Simulation Report\n"
            f"Total requests: {self.total_requests}\n"
            f"Request full-prefix hits: {self.request_full_prefix_hits}\n"
            f"Request full-prefix misses: {self.request_full_prefix_misses}\n"
            f"Request full-prefix hit rate: {hit_rate:.4f}\n"
            f"Bytes requested: {self.bytes_requested}\n"
            f"Bytes cached: {self.bytes_cached}\n"
            f"Bytes read: {self.bytes_read}\n"
            f"Bytes written: {self.bytes_written}\n"
            f"Prefix block hits: {self.prefix_block_hits}\n"
            f"Prefix block total: {self.prefix_block_total}\n"
            f"Prefix block hit rate: {block_hit_rate:.4f}\n"
            f"TTFT mean (ms): {self.ttft_mean_ms:.2f}\n"
            f"TTFT p95 (ms): {self.ttft_p95_ms:.2f}\n"
            f"TTFT p99 (ms): {self.ttft_p99_ms:.2f}\n"
            f"Throughput (tokens/s): {self.throughput_tokens_per_s:.2f} ({self.throughput_source})\n"
        )


class TimeModel:
    def __init__(self, cfg: TimeModelConfig) -> None:
        self.cfg = cfg

    def estimate_ttft_ms(
        self,
        total_tokens: int,
        hit_tokens: int,
        l1_bytes: int,
        l2_bytes: int,
        miss_bytes: int,
    ) -> float:
        miss_tokens = max(0, total_tokens - hit_tokens)
        compute_time_ms = (
            miss_tokens / self.cfg.compute_tokens_per_ms
            + (hit_tokens / self.cfg.compute_tokens_per_ms) * self.cfg.hit_compute_fraction
        )
        load_time_ms = (
            l1_bytes / self.cfg.l1_bandwidth_bytes_per_ms
            + l2_bytes / self.cfg.l2_bandwidth_bytes_per_ms
            + miss_bytes / self.cfg.miss_bandwidth_bytes_per_ms
        )
        return compute_time_ms + load_time_ms


class MetricsCollector:
    def __init__(self) -> None:
        self.total_requests = 0
        self.request_full_prefix_hits = 0
        self.request_full_prefix_misses = 0
        self.bytes_requested = 0
        self.bytes_cached = 0
        self.bytes_read = 0
        self.bytes_written = 0
        self.prefix_block_hits = 0
        self.prefix_block_total = 0
        self._ttft_ms: List[float] = []
        self._total_tokens = 0
        self._timestamped_tokens = 0
        self._first_timestamp_ms: int | None = None
        self._last_timestamp_ms: int | None = None

    def record_request(
        self,
        req: Request,
        cache_result: CacheLookup,
        kv_bytes: int,
        ttft_ms: float,
        read_bytes: int = 0,
        write_bytes: int = 0,
        block_hits: int = 0,
        block_total: int = 0,
    ) -> None:
        self.total_requests += 1
        self.bytes_requested += kv_bytes
        self.bytes_read += read_bytes
        self.bytes_written += write_bytes
        self._ttft_ms.append(ttft_ms)
        self._total_tokens += req.sequence_length
        if req.timestamp_ms is not None and req.timestamp_ms > 0:
            if self._first_timestamp_ms is None:
                self._first_timestamp_ms = req.timestamp_ms
            self._last_timestamp_ms = req.timestamp_ms
            self._timestamped_tokens += req.input_length or req.sequence_length
        self.prefix_block_hits += block_hits
        self.prefix_block_total += block_total
        if cache_result.hit:
            self.request_full_prefix_hits += 1
            self.bytes_cached += kv_bytes
        else:
            self.request_full_prefix_misses += 1

    def finalize(self) -> MetricsReport:
        hit_rate = (
            self.request_full_prefix_hits / self.total_requests
            if self.total_requests
            else 0.0
        )
        block_hit_rate = (
            self.prefix_block_hits / self.prefix_block_total
            if self.prefix_block_total
            else 0.0
        )
        ttft_mean = float(np.mean(self._ttft_ms)) if self._ttft_ms else 0.0
        ttft_p95 = float(np.percentile(self._ttft_ms, 95)) if self._ttft_ms else 0.0
        ttft_p99 = float(np.percentile(self._ttft_ms, 99)) if self._ttft_ms else 0.0
        throughput_source = "ttft"
        if (
            self._first_timestamp_ms is not None
            and self._last_timestamp_ms is not None
            and self._last_timestamp_ms > self._first_timestamp_ms
            and self._timestamped_tokens > 0
        ):
            total_time_s = (self._last_timestamp_ms - self._first_timestamp_ms) / 1000.0
            throughput = self._timestamped_tokens / total_time_s
            throughput_source = "timestamp"
        else:
            total_time_s = sum(self._ttft_ms) / 1000.0 if self._ttft_ms else 0.0
            throughput = self._total_tokens / total_time_s if total_time_s > 0 else 0.0
        return MetricsReport(
            total_requests=self.total_requests,
            request_full_prefix_hits=self.request_full_prefix_hits,
            request_full_prefix_misses=self.request_full_prefix_misses,
            request_full_prefix_hit_rate=hit_rate,
            bytes_requested=self.bytes_requested,
            bytes_cached=self.bytes_cached,
            bytes_read=self.bytes_read,
            bytes_written=self.bytes_written,
            prefix_block_hits=self.prefix_block_hits,
            prefix_block_total=self.prefix_block_total,
            prefix_block_hit_rate=block_hit_rate,
            ttft_mean_ms=ttft_mean,
            ttft_p95_ms=ttft_p95,
            ttft_p99_ms=ttft_p99,
            throughput_tokens_per_s=throughput,
            throughput_source=throughput_source,
        )
