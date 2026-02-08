# KV Cache Simulator

This repo provides a modular framework for simulating KV cache behavior in LLM prefill/decoding workflows.

## Quick Start
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m kvcache_sim.main --config configs/basic.yaml
```

## Project Layout
```
kvcache_sim/
  main.py                 # CLI entry
  config.py               # Config loading and validation
  requests/               # Request generation and input sequence models
  simulator/              # Core simulator and event loop
  cache/                  # Cache models + replacement policies
  analysis/               # Metrics and reuse analysis
  datasets/               # Optional input data loaders
configs/                  # Example configs
```

## Config Notes
- Policies: `lru`, `lfu`, `hierarchical_lru` (use `l1_cache_capacity_bytes` + `l2_cache_capacity_bytes`).
- Workloads: `synthetic` (default) or `trace` (CSV with `sequence_id`, `sequence_length`, optional `request_type`).
- JSONL traces: support Mooncake-style records with `timestamp`, `input_length`, `output_length`, `hash_ids` (block hashes).
- Sequence lengths: fixed (`sequence_length`) or `sequence_length_dist` with `dist` in `fixed|uniform|normal|lognormal`.
- Time model: `time_model` controls TTFT estimation (compute + load); throughput defaults to timestamp-based for trace inputs (falls back to TTFT if timestamps are missing).
- Block size: `block_size_tokens` (default `512`) controls per-block KV size for trace inputs.
- Prefix cache: JSONL traces use prefix-hit semantics (stop at first miss; remaining blocks treated as misses and written).
- Cache sizing: `cache_capacity_bytes` is still supported, but you can also specify `cache_capacity_blocks` (block count) which is converted using `block_size_tokens * model_kv_bytes_per_token`.
- Trace cache sizing: `workload.cache_capacity_fraction` (or `trace_cache_capacity_fraction`) sets cache capacity to a fraction of unique `hash_ids` in JSONL traces (deduplicated by block ID).

Example trace run:
```bash
python3 -m kvcache_sim.main --config configs/trace.yaml
```
