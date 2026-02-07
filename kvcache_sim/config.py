from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


@dataclass
class SimulatorConfig:
    seed: int
    num_requests: int
    num_sequences: int
    sequence_length: int
    sequence_length_dist: "SequenceLengthSpec"
    model_kv_bytes_per_token: int
    cache_capacity_bytes: int
    l1_cache_capacity_bytes: Optional[int]
    l2_cache_capacity_bytes: Optional[int]
    policy: str
    reuse_model: str
    reuse_zipf_a: float
    workload_type: str
    trace_path: Optional[Path]
    block_size_tokens: int
    trace_cache_capacity_fraction: Optional[float]
    time_model: "TimeModelConfig"


@dataclass(frozen=True)
class SequenceLengthSpec:
    dist: str
    value: Optional[int] = None
    low: Optional[int] = None
    high: Optional[int] = None
    mean: Optional[float] = None
    std: Optional[float] = None
    min_value: int = 1
    max_value: int = 131072


@dataclass(frozen=True)
class TimeModelConfig:
    compute_tokens_per_ms: float
    l1_bandwidth_bytes_per_ms: float
    l2_bandwidth_bytes_per_ms: float
    miss_bandwidth_bytes_per_ms: float
    hit_compute_fraction: float


def load_config(path: str | Path) -> SimulatorConfig:
    data = _read_yaml(path)
    base_dir = Path(path).resolve().parent
    workload = data.get("workload", {}) if isinstance(data.get("workload", {}), dict) else {}
    workload_type = str(workload.get("type", data.get("workload_type", "synthetic"))).lower()
    trace_path = workload.get("trace_path", data.get("trace_path"))
    trace_cache_capacity_fraction = workload.get(
        "cache_capacity_fraction",
        data.get("trace_cache_capacity_fraction"),
    )
    if trace_path:
        trace_path = Path(trace_path)
        if not trace_path.is_absolute():
            trace_path = base_dir / trace_path
    sequence_length = int(data.get("sequence_length", 0) or 0)
    seq_spec_data = data.get("sequence_length_dist")
    if seq_spec_data is None:
        seq_spec = SequenceLengthSpec(dist="fixed", value=sequence_length)
    else:
        seq_spec = SequenceLengthSpec(
            dist=str(seq_spec_data.get("dist", "fixed")),
            value=_maybe_int(seq_spec_data.get("value")),
            low=_maybe_int(seq_spec_data.get("low")),
            high=_maybe_int(seq_spec_data.get("high")),
            mean=_maybe_float(seq_spec_data.get("mean")),
            std=_maybe_float(seq_spec_data.get("std")),
            min_value=int(seq_spec_data.get("min_value", 1)),
            max_value=int(seq_spec_data.get("max_value", 131072)),
        )

    time_data = data.get("time_model", {}) if isinstance(data.get("time_model", {}), dict) else {}
    time_model = TimeModelConfig(
        compute_tokens_per_ms=float(time_data.get("compute_tokens_per_ms", 1000.0)),
        l1_bandwidth_bytes_per_ms=float(time_data.get("l1_bandwidth_bytes_per_ms", 5e8)),
        l2_bandwidth_bytes_per_ms=float(time_data.get("l2_bandwidth_bytes_per_ms", 2e8)),
        miss_bandwidth_bytes_per_ms=float(time_data.get("miss_bandwidth_bytes_per_ms", 5e7)),
        hit_compute_fraction=float(time_data.get("hit_compute_fraction", 0.0)),
    )

    return SimulatorConfig(
        seed=int(data.get("seed", 1)),
        num_requests=int(data["num_requests"]),
        num_sequences=int(data.get("num_sequences", data["num_requests"])),
        sequence_length=sequence_length,
        sequence_length_dist=seq_spec,
        model_kv_bytes_per_token=int(data["model_kv_bytes_per_token"]),
        cache_capacity_bytes=int(data["cache_capacity_bytes"]),
        l1_cache_capacity_bytes=_maybe_int(data.get("l1_cache_capacity_bytes")),
        l2_cache_capacity_bytes=_maybe_int(data.get("l2_cache_capacity_bytes")),
        policy=str(data.get("policy", "lru")),
        reuse_model=str(data.get("reuse_model", "zipf")),
        reuse_zipf_a=float(data.get("reuse_zipf_a", 1.2)),
        workload_type=workload_type,
        trace_path=trace_path,
        block_size_tokens=int(data.get("block_size_tokens", 512)),
        trace_cache_capacity_fraction=_maybe_float(trace_cache_capacity_fraction),
        time_model=time_model,
    )


def _read_yaml(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        if yaml is not None:
            return yaml.safe_load(f)
        return _read_yaml_fallback(f.read())


def _read_yaml_fallback(text: str) -> Dict[str, Any]:
    # Minimal YAML subset parser: supports nested mappings via indentation,
    # scalar values (int/float/bool/str), and comments.
    root: Dict[str, Any] = {}
    stack: list[Dict[str, Any]] = [root]
    indents: list[int] = [0]

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        line = line.lstrip()

        while indent < indents[-1]:
            stack.pop()
            indents.pop()

        if ":" not in line:
            raise ValueError(f"Invalid YAML line: {raw_line}")

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if value == "":
            new_dict: Dict[str, Any] = {}
            stack[-1][key] = new_dict
            stack.append(new_dict)
            indents.append(indent + 2)
            continue

        stack[-1][key] = _parse_scalar(value)

    return root


def _parse_scalar(value: str) -> Any:
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _maybe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    return int(value)


def _maybe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    return float(value)
