from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


def _iter_requests(trace_path: Path) -> Iterable[dict]:
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            yield record


def _normalize_hash_ids(value: object) -> List[int]:
    if value is None:
        return []
    if isinstance(value, list):
        return [int(v) for v in value]
    return [int(value)]


@dataclass
class SessionSummary:
    requests: int
    avg_gap_ms: float


def _match_blocks(prefix: list[int], blocks: list[int], length: int) -> bool:
    if length <= 0:
        return False
    return prefix[:length] == blocks[:length]


def _analyze_sessions(
    requests: list[dict], session_gap_ms: int
) -> tuple[list[SessionSummary], list[tuple[int, list[int]]], set[int]]:
    sessions: list[SessionSummary] = []
    active_sessions: list[dict] = []
    longest_entries: list[tuple[int, list[int]]] = []
    longest_count = 0
    multi_request_indices: set[int] = set()

    def finalize_session(session: dict) -> None:
        nonlocal longest_count, longest_entries
        avg_gap = sum(session["gaps"]) / len(session["gaps"]) if session["gaps"] else 0.0
        sessions.append(SessionSummary(requests=session["count"], avg_gap_ms=avg_gap))
        if session["count"] > longest_count:
            longest_count = session["count"]
            longest_entries = list(session["entries"])
        if session["count"] > 1:
            multi_request_indices.update(entry[0] for entry in session["entries"])

    for idx, record in enumerate(requests):
        blocks = _normalize_hash_ids(record.get("hash_ids"))
        ts = int(record.get("timestamp", 0))
        input_length = int(record.get("input_length", 0))
        ignore_last_block = input_length % 512 != 0
        compare_len = max(len(blocks) - 1, 0) if ignore_last_block else len(blocks)

        if ts > 0 and session_gap_ms > 0:
            expired = [
                s for s in active_sessions if s["last_ts"] is not None and ts - s["last_ts"] > session_gap_ms
            ]
            for session in expired:
                finalize_session(session)
            active_sessions = [s for s in active_sessions if s not in expired]

        best_idx = None
        best_len = -1
        for idx, session in enumerate(active_sessions):
            prefix = session["blocks"]
            prefix_len = session["compare_len"]
            if prefix and _match_blocks(prefix, blocks, min(prefix_len, compare_len)):
                if len(prefix) > best_len:
                    best_len = len(prefix)
                    best_idx = idx

        if best_idx is None:
            active_sessions.append(
                {
                    "blocks": blocks,
                    "compare_len": compare_len,
                    "count": 1,
                    "gaps": [],
                    "last_ts": ts if ts > 0 else None,
                    "entries": [(idx, ts, blocks)],
                }
            )
            continue

        session = active_sessions[best_idx]
        session["blocks"] = blocks
        session["compare_len"] = compare_len
        session["count"] += 1
        session["entries"].append((idx, ts, blocks))
        if session["last_ts"] is not None and ts > 0:
            session["gaps"].append(ts - session["last_ts"])
        session["last_ts"] = ts if ts > 0 else session["last_ts"]

    for session in active_sessions:
        finalize_session(session)

    longest_entries = [(ts, blocks) for _, ts, blocks in longest_entries]
    return sessions, longest_entries, multi_request_indices


def _top_system_prompts(requests: list[dict], max_prefix_blocks: int, min_share: float) -> list[tuple[tuple[int, ...], int]]:
    prefix_counts: Counter[tuple[int, ...]] = Counter()
    total = 0
    for record in requests:
        blocks = _normalize_hash_ids(record.get("hash_ids"))
        if not blocks:
            continue
        total += 1
        max_len = min(len(blocks), max_prefix_blocks)
        for length in range(1, max_len + 1):
            prefix_counts[tuple(blocks[:length])] += 1

    min_count = max(1, int(total * min_share))
    candidates = [(prefix, count) for prefix, count in prefix_counts.items() if count >= min_count]
    candidates.sort(key=lambda item: (-len(item[0]), -item[1]))

    selected: list[tuple[tuple[int, ...], int]] = []
    for prefix, count in candidates:
        if any(prefix[: len(existing)] == existing for existing, _ in selected):
            continue
        selected.append((prefix, count))
    selected.sort(key=lambda item: -item[1])
    return selected


def _system_prompt_hits(
    requests: list[dict], prompts: list[tuple[tuple[int, ...], int]]
) -> tuple[int, int, Counter[int], set[int]]:
    total = 0
    hits = 0
    prompt_usage: Counter[int] = Counter()
    hit_indices: set[int] = set()
    for req_idx, record in enumerate(requests):
        blocks = _normalize_hash_ids(record.get("hash_ids"))
        if not blocks:
            continue
        total += 1
        matched = False
        for prompt_idx, (prefix, _) in enumerate(prompts):
            if blocks[: len(prefix)] == list(prefix):
                hits += 1
                prompt_usage[prompt_idx] += 1
                hit_indices.add(req_idx)
                matched = True
                break
        if not matched:
            continue
    return hits, total, prompt_usage, hit_indices


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze trace request patterns")
    parser.add_argument("trace", type=Path)
    parser.add_argument("--max-prefix-blocks", type=int, default=8)
    parser.add_argument("--min-share", type=float, default=0.02)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--session-gap-ms",
        type=int,
        default=0,
        help="Close sessions after this idle gap in ms (0 disables expiry).",
    )
    args = parser.parse_args()

    records = list(_iter_requests(args.trace))
    prompts = _top_system_prompts(records, args.max_prefix_blocks, args.min_share)
    hits, total, usage, system_hit_indices = _system_prompt_hits(records, prompts)
    sessions, longest_entries, session_hit_indices = _analyze_sessions(records, args.session_gap_ms)

    avg_requests = sum(s.requests for s in sessions) / len(sessions) if sessions else 0.0
    avg_gap = sum(s.avg_gap_ms for s in sessions) / len(sessions) if sessions else 0.0

    other_pattern_count = sum(1 for s in sessions if s.requests == 1)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("# Trace Pattern Analysis\n\n")
        f.write(f"Trace: `{args.trace}`\n\n")
        f.write("## System prompt patterns\n\n")
        f.write(f"Detected {len(prompts)} system-prompt prefixes (min share {args.min_share:.0%}, max prefix {args.max_prefix_blocks} blocks).\n\n")
        if total > 0:
            f.write(f"Requests matching system prompts: {hits}/{total} ({hits/total:.2%}).\n\n")
        if prompts:
            f.write("| Rank | Prefix length (blocks) | Requests | Share | Prefix hashes |\n")
            f.write("| --- | ---: | ---: | ---: | --- |\n")
            for idx, (prefix, count) in enumerate(prompts[:10], start=1):
                share = count / total if total else 0.0
                f.write(
                    f"| {idx} | {len(prefix)} | {count} | {share:.2%} | {list(prefix)} |\n"
                )
        f.write("\n")

        f.write("## Session-style growth patterns\n\n")
        f.write(
            "Sessions are defined by prefix growth even when requests are interleaved. "
            "Each request extends the most recent active prefix (longest match). "
            "Sessions close after an idle gap exceeding the configured threshold.\n\n"
        )
        f.write(f"Session gap threshold (ms): {args.session_gap_ms}\n\n")
        f.write(f"Total sessions: {len(sessions)}\n\n")
        f.write(f"Average requests per session: {avg_requests:.2f}\n\n")
        f.write(f"Average inter-request gap (ms): {avg_gap:.2f}\n\n")

        f.write("## Prefix hit attribution\n\n")
        prefix_hit_indices = system_hit_indices | session_hit_indices
        prefix_hit_total = len(prefix_hit_indices)
        system_hit_count = len(system_hit_indices)
        session_hit_count = len(session_hit_indices)
        overlap_count = len(system_hit_indices & session_hit_indices)
        if prefix_hit_total > 0:
            f.write(f"Total prefix-hit requests (system or session): {prefix_hit_total}\n\n")
            f.write(
                f"System prompt hits: {system_hit_count} "
                f"({system_hit_count / prefix_hit_total:.2%} of prefix hits)\n\n"
            )
            f.write(
                f"Session hits: {session_hit_count} "
                f"({session_hit_count / prefix_hit_total:.2%} of prefix hits)\n\n"
            )
            f.write(
                f"Overlap (both): {overlap_count} "
                f"({overlap_count / prefix_hit_total:.2%} of prefix hits)\n\n"
            )
        else:
            f.write("No prefix-hit requests detected.\n\n")

        f.write("## Other patterns\n\n")
        f.write(
            f"Single-request sessions (no prefix growth): {other_pattern_count} "
            f"({(other_pattern_count/len(sessions)):.2%} of sessions).\n"
        )
        f.write("\n\n")
        f.write("## Longest session example\n\n")
        if longest_entries:
            for ts, blocks in sorted(longest_entries, key=lambda item: item[0]):
                f.write(f"- {ts}: {blocks}\n")


if __name__ == "__main__":
    main()
