# Test Cache Capacity Matrix

This matrix records the cache capacity settings used for the recent high/medium/low hit-rate test runs.
Block counts assume `block_size_tokens=512` and `model_kv_bytes_per_token=256` (131,072 bytes per block).

## LRU / LFU (single-tier)

| Level | cache_capacity_bytes | cache_capacity_blocks | Approx. size |
| --- | ---: | ---: | --- |
| low | 33,554,432 | 256 | 32 MiB |
| mid | 268,435,456 | 2,048 | 256 MiB |
| high | 1,073,741,824 | 8,192 | 1 GiB |

## Hierarchical LRU (two-tier)

| Level | l1_cache_capacity_bytes | l1_cache_capacity_blocks | l2_cache_capacity_bytes | l2_cache_capacity_blocks | Approx. size (L1/L2) |
| --- | ---: | ---: | ---: | ---: | --- |
| low | 33,554,432 | 256 | 134,217,728 | 1,024 | 32 MiB / 128 MiB |
| mid | 67,108,864 | 512 | 469,762,048 | 3,584 | 64 MiB / 448 MiB |
| high | 134,217,728 | 1,024 | 1,207,959,552 | 9,216 | 128 MiB / 1,152 MiB |
