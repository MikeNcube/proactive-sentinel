"""Audit chain verification (canonical spec section 10.3 F1).

Pure function over an iterable of record dicts. Reports the first
integrity break found (if any) along with the index and reason. No
I/O, no state.

Invoked by:

- Unit tests (this commit).
- An ad-hoc CLI script (future work).
- A daily AWS Lambda packaged under ``infra/terraform/modules/data/``
  (future work; Section 12).

The function itself is delivered here; transports are deferred.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from soc.audit.chain import GENESIS_PREV_HASH, compute_this_hash


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of a chain verification pass.

    On success: ``ok=True``, the other fields are sentinel values.
    On failure: ``ok=False``, ``error_index`` points at the offending
    record (zero-based) and ``error_reason`` is a short
    human-readable description.
    """

    ok: bool
    error_index: int = -1
    error_reason: str = ""


def verify_chain(records: Iterable[Mapping[str, Any]]) -> VerificationResult:
    """Verify hash-chain integrity over a sequence of records.

    Checks performed in order:

    1. ``seq`` is monotonic starting at 1 (no gaps, no reorderings).
    2. First record's ``prev_hash == GENESIS_PREV_HASH``.
    3. Each subsequent record's ``prev_hash`` equals the previous
       record's ``this_hash``.
    4. Each record's ``this_hash`` recomputes correctly from its
       other fields (i.e. payload_hash, prev_hash, seq, etc. have
       not been tampered with).

    Returns the first failure encountered. An empty chain is trivially
    valid.
    """
    expected_prev = GENESIS_PREV_HASH
    expected_seq = 1

    for idx, record in enumerate(records):
        # Rule 1: monotonic seq starting at 1
        actual_seq = record.get("seq")
        if actual_seq != expected_seq:
            return VerificationResult(
                ok=False,
                error_index=idx,
                error_reason=(
                    f"seq mismatch at index {idx}: "
                    f"expected {expected_seq}, got {actual_seq}"
                ),
            )

        # Rule 2 + 3: prev_hash linkage
        if record.get("prev_hash") != expected_prev:
            return VerificationResult(
                ok=False,
                error_index=idx,
                error_reason=f"prev_hash mismatch at index {idx}",
            )

        # Rule 4: this_hash integrity
        without_this = {k: v for k, v in record.items() if k != "this_hash"}
        recomputed = compute_this_hash(without_this)
        if record.get("this_hash") != recomputed:
            return VerificationResult(
                ok=False,
                error_index=idx,
                error_reason=f"this_hash mismatch at index {idx}",
            )

        expected_prev = record["this_hash"]
        expected_seq += 1

    return VerificationResult(ok=True)
