from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List
import csv
import json
import sys

import numpy as np

from kvcache_sim.config import SimulatorConfig, SequenceLengthSpec
from kvcache_sim.requests.models import Request


@dataclass
class RequestGenerator:
    cfg: SimulatorConfig

    def generate(self) -> Iterable[Request]:
        if self.cfg.workload_type == "trace":
            if not self.cfg.trace_path:
                raise ValueError("Trace workload requires trace_path in config")
            yield from _iter_trace(self.cfg.trace_path)
            return

        rng = np.random.default_rng(self.cfg.seed)
        reuse_pool = _build_reuse_pool(self.cfg, rng)

        for i in range(self.cfg.num_requests):
            sequence_id = int(rng.choice(reuse_pool))
            sequence_length = _sample_sequence_length(self.cfg.sequence_length_dist, rng, self.cfg.sequence_length)
            yield Request(
                request_id=i,
                sequence_id=sequence_id,
                sequence_length=sequence_length,
            )


def _build_reuse_pool(cfg: SimulatorConfig, rng: np.random.Generator) -> np.ndarray:
    # Simple reuse model; later extend to dataset-driven or workload traces.
    if cfg.reuse_model == "uniform":
        return np.arange(cfg.num_sequences, dtype=np.int64)

    # Zipf-like reuse: smaller ids are reused more frequently.
    base = rng.zipf(a=cfg.reuse_zipf_a, size=cfg.num_sequences)
    base = np.clip(base, 1, cfg.num_sequences)
    return base - 1


def _sample_sequence_length(
    spec: SequenceLengthSpec,
    rng: np.random.Generator,
    fallback_length: int,
) -> int:
    if spec.dist == "fixed":
        return int(spec.value or fallback_length)
    if spec.dist == "uniform":
        low = int(spec.low or 1)
        high = int(spec.high or max(low + 1, fallback_length))
        return int(rng.integers(low, high + 1))
    if spec.dist == "normal":
        mean = float(spec.mean or fallback_length)
        std = float(spec.std or max(1.0, mean * 0.1))
        value = int(rng.normal(mean, std))
    elif spec.dist == "lognormal":
        mean = float(spec.mean or max(1.0, np.log(fallback_length)))
        std = float(spec.std or 0.5)
        value = int(rng.lognormal(mean, std))
    else:
        raise ValueError(f"Unknown sequence length distribution: {spec.dist}")

    value = max(spec.min_value, min(spec.max_value, value))
    return int(value)


def _iter_trace(trace_path: Path) -> Iterator[Request]:
    if trace_path.suffix.lower() == ".csv":
        with open(trace_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                yield Request(
                    request_id=idx,
                    sequence_id=int(row["sequence_id"]),
                    sequence_length=int(row["sequence_length"]),
                    request_type=row.get("request_type") or "prefill",
                    priority=int(row.get("priority", 0) or 0),
                    pinned=_parse_bool(row.get("pinned", False)),
                    tenant_id=row.get("tenant_id"),
                )
        return

    if trace_path.suffix.lower() == ".jsonl":
        decode_errors = 0
        with open(trace_path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    decode_errors += 1
                    continue
                hash_ids = _normalize_hash_ids(record.get("hash_ids"))
                input_length = int(record.get("input_length", 0))
                output_length = int(record.get("output_length", 0))
                yield Request(
                    request_id=idx,
                    sequence_id=int(hash_ids[0]) if hash_ids else idx,
                    sequence_length=input_length,
                    request_type="prefill",
                    timestamp_ms=int(record.get("timestamp", 0)),
                    input_length=input_length,
                    output_length=output_length,
                    priority=int(record.get("priority", 0) or 0),
                    pinned=_parse_bool(record.get("pinned", False)),
                    tenant_id=record.get("tenant_id"),
                    block_hashes=hash_ids,
                )
        if decode_errors:
            print(f"Warning: skipped {decode_errors} malformed JSONL lines in {trace_path}", file=sys.stderr)
        return

    raise ValueError(f"Unsupported trace format: {trace_path.suffix}")


def _normalize_hash_ids(value: object) -> List[int]:
    if value is None:
        return []
    if isinstance(value, list):
        return [int(v) for v in value]
    return [int(value)]


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
