from __future__ import annotations

from dataclasses import dataclass

from kvcache_sim.config import SimulatorConfig
from kvcache_sim.requests.models import Request
from kvcache_sim.cache.interfaces import Cache, CacheLookup, CacheMetadata
from kvcache_sim.analysis.metrics import MetricsCollector, TimeModel


@dataclass
class Simulator:
    cfg: SimulatorConfig
    cache: Cache
    metrics: MetricsCollector
    time_model: TimeModel

    def handle_request(self, req: Request) -> None:
        metadata = CacheMetadata(
            timestamp_ms=req.timestamp_ms,
            priority=req.priority,
            pinned=req.pinned,
            tenant_id=req.tenant_id,
        )
        if req.block_hashes:
            total_tokens = req.input_length or req.sequence_length
            block_tokens = _split_tokens(total_tokens, len(req.block_hashes), self.cfg.block_size_tokens)
            prefix_hits = 0
            prefix_hit_tokens = 0
            l1_bytes = 0
            l2_bytes = 0
            miss_bytes = 0
            read_bytes = 0
            write_bytes = 0
            prefix_active = True

            for block_id, tokens in zip(req.block_hashes, block_tokens):
                kv_bytes = tokens * self.cfg.model_kv_bytes_per_token
                if prefix_active:
                    result = self.cache.get(int(block_id), kv_bytes, metadata)
                    if result.hit:
                        prefix_hits += 1
                        prefix_hit_tokens += tokens
                        read_bytes += kv_bytes
                        if result.level == "l2":
                            l2_bytes += kv_bytes
                        else:
                            l1_bytes += kv_bytes
                        continue
                    prefix_active = False
                # Prefix cache: after first miss, treat the rest as misses and write KV.
                miss_bytes += kv_bytes
                write_bytes += kv_bytes
                self.cache.put(int(block_id), kv_bytes, metadata)

            kv_bytes_total = l1_bytes + l2_bytes + miss_bytes
            ttft_ms = self.time_model.estimate_ttft_ms(
                total_tokens=total_tokens,
                hit_tokens=prefix_hit_tokens,
                l1_bytes=l1_bytes,
                l2_bytes=l2_bytes,
                miss_bytes=miss_bytes,
            )
            full_hit = prefix_hits == len(req.block_hashes) and len(req.block_hashes) > 0
            if full_hit:
                level = "l2" if l2_bytes > 0 else "l1"
            else:
                level = "miss"
            cache_result = CacheLookup(hit=full_hit, level=level)
            self.metrics.record_request(
                req,
                cache_result,
                kv_bytes_total,
                ttft_ms,
                read_bytes=read_bytes,
                write_bytes=write_bytes,
                block_hits=prefix_hits,
                block_total=len(req.block_hashes),
            )
            return

        kv_bytes = req.sequence_length * self.cfg.model_kv_bytes_per_token
        cache_result = self.cache.get(req.sequence_id, kv_bytes, metadata)
        l1_bytes = kv_bytes if cache_result.hit and cache_result.level != "l2" else 0
        l2_bytes = kv_bytes if cache_result.hit and cache_result.level == "l2" else 0
        miss_bytes = kv_bytes if not cache_result.hit else 0
        hit_tokens = req.sequence_length if cache_result.hit else 0
        read_bytes = kv_bytes if cache_result.hit else 0
        write_bytes = 0 if cache_result.hit else kv_bytes
        ttft_ms = self.time_model.estimate_ttft_ms(
            total_tokens=req.sequence_length,
            hit_tokens=hit_tokens,
            l1_bytes=l1_bytes,
            l2_bytes=l2_bytes,
            miss_bytes=miss_bytes,
        )

        self.metrics.record_request(
            req,
            cache_result,
            kv_bytes,
            ttft_ms,
            read_bytes=read_bytes,
            write_bytes=write_bytes,
        )


def _split_tokens(total_tokens: int, num_blocks: int, block_size: int) -> list[int]:
    if num_blocks <= 0:
        return []
    if total_tokens <= 0:
        return [block_size] * num_blocks
    tokens_left = total_tokens
    sizes: list[int] = []
    for i in range(num_blocks):
        if i == num_blocks - 1:
            sizes.append(max(1, tokens_left))
        else:
            sizes.append(min(block_size, max(1, tokens_left)))
        tokens_left = max(0, tokens_left - block_size)
    return sizes
