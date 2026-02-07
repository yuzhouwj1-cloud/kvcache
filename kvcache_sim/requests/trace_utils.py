from __future__ import annotations

from pathlib import Path
import json


def count_unique_hash_ids(trace_path: Path) -> int:
    if trace_path.suffix.lower() != ".jsonl":
        raise ValueError(f"Trace cache capacity fraction requires JSONL trace: {trace_path}")

    unique_ids: set[int] = set()
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            hash_ids = record.get("hash_ids")
            if hash_ids is None:
                continue
            if isinstance(hash_ids, list):
                for value in hash_ids:
                    unique_ids.add(int(value))
            else:
                unique_ids.add(int(hash_ids))
    return len(unique_ids)
