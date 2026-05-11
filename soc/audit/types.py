"""Audit Logger types.

Mirrors the record format specified in canonical spec section 10.1
verbatim --- field names, types, and order. Frozen dataclass so audit
records are hashable, comparable in tests, and impossible to mutate
after construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class AuditRecord:
    """A single hash-chained audit record.

    Field layout matches canonical spec section 10.1:

        seq, timestamp, manifest_hash, event_type, event_id,
        payload_hash, payload_ref, prev_hash, this_hash

    All hash fields are formatted as ``sha256:<hex>`` per the spec
    example. Timestamps are ISO 8601 with millisecond precision and
    a trailing ``Z`` (UTC).
    """

    seq: int
    timestamp: str
    manifest_hash: str
    event_type: str
    event_id: str
    payload_hash: str
    payload_ref: str
    prev_hash: str
    this_hash: str

    def to_dict(self) -> Mapping[str, Any]:
        """JSON-serialisable plain-dict view of the record.

        Field order matches canonical spec section 10.1. Used by sinks
        (JSONL line content) and by the chain verifier when
        recomputing ``this_hash`` for integrity checks.
        """
        return {
            "seq": self.seq,
            "timestamp": self.timestamp,
            "manifest_hash": self.manifest_hash,
            "event_type": self.event_type,
            "event_id": self.event_id,
            "payload_hash": self.payload_hash,
            "payload_ref": self.payload_ref,
            "prev_hash": self.prev_hash,
            "this_hash": self.this_hash,
        }
