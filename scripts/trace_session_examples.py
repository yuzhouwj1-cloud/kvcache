from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


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


def _match_blocks(prefix: list[int], blocks: list[int], length: int) -> bool:
    if length <= 0:
        return False
    return prefix[:length] == blocks[:length]


@dataclass
class Session:
    entries: list[tuple[int, list[int]]]
    compare_len: int
    last_ts: Optional[int]


def _build_sessions(trace_path: Path) -> list[Session]:
    sessions: list[Session] = []

    for record in _iter_requests(trace_path):
        blocks = _normalize_hash_ids(record.get("hash_ids"))
        ts = int(record.get("timestamp", 0))
        input_length = int(record.get("input_length", 0))
        ignore_last_block = input_length % 512 != 0
        compare_len = max(len(blocks) - 1, 0) if ignore_last_block else len(blocks)

        best_idx = None
        best_len = -1
        for idx, session in enumerate(sessions):
            prefix = session.entries[-1][1] if session.entries else []
            prefix_len = session.compare_len
            if prefix and _match_blocks(prefix, blocks, min(prefix_len, compare_len)):
                if len(prefix) > best_len:
                    best_len = len(prefix)
                    best_idx = idx

        if best_idx is None:
            sessions.append(Session(entries=[(ts, blocks)], compare_len=compare_len, last_ts=ts))
            continue

        session = sessions[best_idx]
        session.entries.append((ts, blocks))
        session.compare_len = compare_len
        session.last_ts = ts

    return sessions


def _pick_examples(sessions: list[Session]) -> tuple[Session, Session, Session]:
    if not sessions:
        raise ValueError("No sessions found")
    first_session = min(sessions, key=lambda s: s.entries[0][0] if s.entries else 0)
    longest_session = max(sessions, key=lambda s: len(s.entries))
    avg_len = sum(len(s.entries) for s in sessions) / len(sessions)
    avg_session = min(sessions, key=lambda s: abs(len(s.entries) - avg_len))
    return first_session, longest_session, avg_session


def _format_session(session: Session) -> str:
    lines = []
    for ts, blocks in sorted(session.entries, key=lambda item: item[0]):
        lines.append(f"- {ts}: {blocks}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract session examples from a trace")
    parser.add_argument("trace", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sessions = _build_sessions(args.trace)
    first_session, longest_session, avg_session = _pick_examples(sessions)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("# Trace Session Examples\n\n")
        f.write(f"Trace: `{args.trace}`\n\n")
        f.write("## First session\n\n")
        f.write(_format_session(first_session))
        f.write("\n\n")
        f.write("## Longest session\n\n")
        f.write(_format_session(longest_session))
        f.write("\n\n")
        f.write("## Average-length session\n\n")
        f.write(_format_session(avg_session))
        f.write("\n")


if __name__ == "__main__":
    main()
