"""Audit Logger pure-core primitives.

Canonical JSON + SHA-256 hashing + record construction. No I/O, no
state, no clocks, no randoms. Every function here is deterministic
and trivially testable.

Two contracts are locked behind this module:

1. **Canonical JSON.** Any change to the serialisation rules
   invalidates the hash of *every* existing audit record. The single
   :func:`canonical_json` function is the authoritative implementation.
   A regression test against a hand-computed hash freezes the contract.

2. **Hash prefix.** Spec section 10.1 shows ``sha256:<hex>`` in every
   hash field; we emit exactly that prefix.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from soc.audit.types import AuditRecord

HASH_PREFIX = "sha256:"

# The genesis prev_hash --- the value used as ``prev_hash`` on the
# first record of a chain. Sixty-four ``0`` hex chars after the
# standard prefix. Chosen so it is visibly distinct from any real
# SHA-256 output yet still parses through the same code path.
GENESIS_PREV_HASH = HASH_PREFIX + "0" * 64


def canonical_json(data: Mapping[str, Any]) -> bytes:
    """Deterministic UTF-8 encoded JSON for hashing.

    Rules:

    - ``sort_keys=True`` --- key order is independent of dict insertion
      order. Recursively applied to nested objects.
    - ``separators=(",", ":")`` --- no whitespace.
    - ``ensure_ascii=False`` --- unicode preserved; UTF-8 encoded.

    Changing any of these rules invalidates every existing record's
    hash. The regression test in ``test_audit_chain.py`` captures
    this.
    """
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def hash_bytes(payload: bytes) -> str:
    """SHA-256 of raw bytes formatted as ``sha256:<hex>``."""
    return HASH_PREFIX + hashlib.sha256(payload).hexdigest()


def hash_payload(payload: Mapping[str, Any]) -> str:
    """SHA-256 of the canonical JSON of a mapping.

    Used for ``payload_hash`` (over the redacted payload) and
    indirectly via :func:`compute_this_hash` for ``this_hash``.
    """
    return hash_bytes(canonical_json(payload))


def compute_this_hash(record_without_this_hash: Mapping[str, Any]) -> str:
    """Compute ``this_hash`` for a record dict.

    Per canonical spec section 10.1: ``this_hash`` is the hash of the
    record JSON **excluding** the ``this_hash`` field itself. This
    function refuses to operate on a dict that still contains the
    ``this_hash`` key --- a guard against accidentally hashing over
    a previous value.
    """
    if "this_hash" in record_without_this_hash:
        raise ValueError(
            "compute_this_hash requires the 'this_hash' key to be absent",
        )
    return hash_bytes(canonical_json(record_without_this_hash))


def build_record(
    *,
    seq: int,
    timestamp: str,
    manifest_hash: str,
    event_type: str,
    event_id: str,
    payload_hash: str,
    payload_ref: str,
    prev_hash: str,
) -> AuditRecord:
    """Build a fully-hashed :class:`AuditRecord` from its components.

    Computes ``this_hash`` over the canonical JSON of every other
    field and returns the immutable record. Pure function: same
    inputs always produce the same record (the timestamp string is
    treated as a plain input, not generated here).
    """
    skeleton = {
        "seq": seq,
        "timestamp": timestamp,
        "manifest_hash": manifest_hash,
        "event_type": event_type,
        "event_id": event_id,
        "payload_hash": payload_hash,
        "payload_ref": payload_ref,
        "prev_hash": prev_hash,
    }
    this_hash = compute_this_hash(skeleton)
    return AuditRecord(
        seq=seq,
        timestamp=timestamp,
        manifest_hash=manifest_hash,
        event_type=event_type,
        event_id=event_id,
        payload_hash=payload_hash,
        payload_ref=payload_ref,
        prev_hash=prev_hash,
        this_hash=this_hash,
    )

