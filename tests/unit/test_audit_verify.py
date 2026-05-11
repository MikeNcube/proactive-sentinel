"""Unit tests for :func:`soc.audit.verify.verify_chain` (canonical
spec section 10.3 F1).

Covers:

- empty chain --> trivially OK
- single valid record --> OK
- N-record valid chain --> OK
- tampering with payload_hash, prev_hash, this_hash on any record
  --> failure pinpointing the offending index
- reordering / seq gaps --> failure
- wrong genesis prev_hash on first record --> failure
"""

from __future__ import annotations

import asyncio

import pytest

from soc.audit import (
    AuditLogger,
    GENESIS_PREV_HASH,
    InMemorySink,
    VerificationResult,
    build_record,
    verify_chain,
)


def _run(coro):
    """Run a coroutine to completion using ``asyncio.run``."""
    return asyncio.run(coro)


def _build_chain(n: int) -> list[dict]:
    """Build a valid chain of ``n`` records via a real AuditLogger so
    the fixtures stay in sync with the production code path."""
    sink = InMemorySink()
    logger = AuditLogger(sink=sink, manifest_hash="sha256:test")

    async def _produce():
        for i in range(n):
            await logger.log("DECISION", f"ev_{i}", {"i": i})

    _run(_produce())
    return [dict(r) for r in sink.read_all()]


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #


class TestVerifyHappyPath:
    def test_empty_chain_is_trivially_ok(self):
        result = verify_chain([])
        assert isinstance(result, VerificationResult)
        assert result.ok is True

    def test_single_record_chain_passes(self):
        chain = _build_chain(1)
        assert verify_chain(chain).ok is True

    def test_ten_record_chain_passes(self):
        chain = _build_chain(10)
        assert verify_chain(chain).ok is True

    @pytest.mark.parametrize("n", [1, 2, 5, 20, 100])
    def test_chain_of_n_records_passes(self, n):
        chain = _build_chain(n)
        assert verify_chain(chain).ok is True


# --------------------------------------------------------------------------- #
# Tamper detection
# --------------------------------------------------------------------------- #


class TestVerifyTamperDetection:
    def test_tampering_with_payload_hash_is_detected(self):
        chain = _build_chain(5)
        chain[2] = {**chain[2], "payload_hash": "sha256:" + "f" * 64}
        result = verify_chain(chain)
        assert result.ok is False
        assert result.error_index == 2
        assert "this_hash" in result.error_reason

    def test_tampering_with_event_type_is_detected(self):
        chain = _build_chain(5)
        chain[3] = {**chain[3], "event_type": "DIFFERENT"}
        result = verify_chain(chain)
        assert result.ok is False
        assert result.error_index == 3

    def test_tampering_with_this_hash_is_detected(self):
        chain = _build_chain(5)
        chain[1] = {**chain[1], "this_hash": "sha256:" + "0" * 64}
        result = verify_chain(chain)
        assert result.ok is False
        assert result.error_index == 1
        assert "this_hash" in result.error_reason

    def test_tampering_with_prev_hash_is_detected(self):
        chain = _build_chain(5)
        chain[2] = {**chain[2], "prev_hash": "sha256:" + "0" * 64}
        result = verify_chain(chain)
        assert result.ok is False
        assert result.error_index == 2
        # prev_hash check fires before this_hash recomputation
        assert "prev_hash" in result.error_reason

    def test_wrong_genesis_prev_hash_on_first_record(self):
        chain = _build_chain(3)
        chain[0] = {**chain[0], "prev_hash": "sha256:" + "1" * 64}
        result = verify_chain(chain)
        assert result.ok is False
        assert result.error_index == 0
        assert "prev_hash" in result.error_reason

    def test_reordering_records_is_detected(self):
        chain = _build_chain(5)
        # Swap records 2 and 3 --- seq is now [1, 2, 4, 3, 5]
        chain[2], chain[3] = chain[3], chain[2]
        result = verify_chain(chain)
        assert result.ok is False
        assert result.error_index == 2
        assert "seq" in result.error_reason

    def test_missing_record_in_middle_is_detected(self):
        chain = _build_chain(5)
        # Remove the third record --- seq gap appears
        del chain[2]
        result = verify_chain(chain)
        assert result.ok is False
        assert result.error_index == 2
        assert "seq" in result.error_reason

    def test_seq_not_starting_at_one_is_detected(self):
        chain = _build_chain(3)
        # Bump every seq by one --- first record now has seq=2
        for i, r in enumerate(chain):
            chain[i] = {**r, "seq": r["seq"] + 1}
        result = verify_chain(chain)
        assert result.ok is False
        assert result.error_index == 0
        assert "seq" in result.error_reason


# --------------------------------------------------------------------------- #
# Result shape
# --------------------------------------------------------------------------- #


class TestVerificationResult:
    def test_ok_result_sentinel_values(self):
        result = verify_chain([])
        assert result.ok is True
        assert result.error_index == -1
        assert result.error_reason == ""

    def test_failure_result_carries_index_and_reason(self):
        chain = _build_chain(3)
        chain[1] = {**chain[1], "event_id": "tampered"}
        result = verify_chain(chain)
        assert result.ok is False
        assert result.error_index == 1
        assert isinstance(result.error_reason, str)
        assert len(result.error_reason) > 0

    def test_result_is_frozen(self):
        result = verify_chain([])
        with pytest.raises((AttributeError, TypeError)):
            result.ok = False  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# Hand-crafted fixtures (without the live logger)
# --------------------------------------------------------------------------- #


class TestHandCraftedFixtures:
    def test_two_unlinked_records_fail_at_second(self):
        """Build two valid-on-their-own records that don't link to
        each other. verify_chain must catch the break."""
        r1 = build_record(
            seq=1,
            timestamp="2026-01-01T00:00:00.000Z",
            manifest_hash="sha256:m",
            event_type="DECISION",
            event_id="ev_1",
            payload_hash="sha256:p1",
            payload_ref="",
            prev_hash=GENESIS_PREV_HASH,
        )
        # r2 points at the WRONG prev_hash, not r1.this_hash
        r2 = build_record(
            seq=2,
            timestamp="2026-01-01T00:00:00.001Z",
            manifest_hash="sha256:m",
            event_type="DECISION",
            event_id="ev_2",
            payload_hash="sha256:p2",
            payload_ref="",
            prev_hash="sha256:" + "9" * 64,
        )
        result = verify_chain([r1.to_dict(), r2.to_dict()])
        assert result.ok is False
        assert result.error_index == 1
