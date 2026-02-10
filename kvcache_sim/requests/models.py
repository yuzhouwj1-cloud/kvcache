from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class Request:
    request_id: int
    sequence_id: int
    sequence_length: int
    request_type: str = "prefill"
    timestamp_ms: Optional[int] = None
    input_length: Optional[int] = None
    output_length: Optional[int] = None
    priority: int = 0
    pinned: bool = False
    tenant_id: Optional[object] = None
    block_hashes: List[int] = field(default_factory=list)
