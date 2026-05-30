"""Unit tests for :class:`soc.audit.AuditLogger`.

Covers the stateful wrapper: seq monotonicity, prev_hash linkage,
deterministic timestamps via injected clock, redactor invocation,
F2 day rollover, restart-resume, concurrent writes, and failure
semantics (no state advance on a failed write).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, List, Mapping

import pytest

from soc.audit import (
    AuditLogger,
    GENESIS_PREV_HASH,
    InMemorySink,
    PassthroughRedactor,
    verify_chain,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _run(coro):
    return asyncio.run(coro)


def _make_fixed_clock(start: datetime | None = None):
    """Return a clock callable that advances by 1ms per call.

    Tests use this to get deterministic timestamps without relying
    on the system clock.
    """
    counter = {"n": 0}
    base = start or datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def _clock() -> datetime:
        ts = base + timedelta(milliseconds=counter["n"])
        counter["n"] += 1
        return ts

    return _clock


class _SpyRedactor:
    """Records every redact() call so tests can assert ordering."""

    def __init__(self) -> None:
        self.calls: List[Mapping[str, Any]] = []

    def redact(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append(dict(payload))
        return dict(payload)


# --------------------------------------------------------------------------- #
# Construction & initial state
# --------------------------------------------------------------------------- #


class TestConstruction:
    def test_logger_against_empty_sink_starts_at_seq_one(self):
        logger = AuditLogger(sink=InMemorySink())
        assert logger.next_seq == 1
        assert logger.prev_hash == GENESIS_PREV_HASH

    def test_logger_uses_passthrough_redactor_by_default(self):
        logger = AuditLogger(sink=InMemorySink())
        # ``_redactor`` is private but instance-of check is fine
        assert isinstance(logger._redactor, PassthroughRedactor)

    def test_logger_accepts_custom_manifest_hash(self):
        logger = AuditLogger(
            sink=InMemorySink(),
            manifest_hash="sha256:custom",
        )

        async def _go():
            return await logger.log("DECISION", "ev_1", {})

        record = _run(_go())
        assert record.manifest_hash == "sha256:custom"


# --------------------------------------------------------------------------- #
# Single-call behaviour
# --------------------------------------------------------------------------- #


class TestSingleCall:
    def test_first_record_has_seq_one_and_genesis_prev_hash(self):
        sink = InMemorySink()
        logger = AuditLogger(sink=sink)

        record = _run(logger.log("DECISION", "ev_1", {"a": 1}))

        assert record.seq == 1
        assert record.prev_hash == GENESIS_PREV_HASH

    def test_record_event_type_and_id_propagate(self):
        sink = InMemorySink()
        logger = AuditLogger(sink=sink)

        record = _run(logger.log("EVENT_RECEIVED", "ev_xyz", {}))

        assert record.event_type == "EVENT_RECEIVED"
        assert record.event_id == "ev_xyz"

    def test_payload_ref_is_empty_string_in_dev(self):
        sink = InMemorySink()
        logger = AuditLogger(sink=sink)

        record = _run(logger.log("DECISION", "ev_1", {}))

        assert record.payload_ref == ""

    def test_record_is_persisted_to_sink(self):
        sink = InMemorySink()
        logger = AuditLogger(sink=sink)

        _run(logger.log("DECISION", "ev_1", {"a": 1}))

        records = list(sink.read_all())
        assert len(records) == 1
        assert records[0]["seq"] == 1


# --------------------------------------------------------------------------- #
# Chain linkage
# --------------------------------------------------------------------------- #


class TestChainLinkage:
    def test_seq_is_monotonic_across_calls(self):
        sink = InMemorySink()
        logger = AuditLogger(sink=sink)

        async def _go():
            for i in range(10):
                await logger.log("DECISION", f"ev_{i}", {"i": i})

        _run(_go())
        records = list(sink.read_all())
        assert [r["seq"] for r in records] == list(range(1, 11))

    def test_prev_hash_links_to_previous_records_this_hash(self):
        sink = InMemorySink()
        logger = AuditLogger(sink=sink)

        async def _go():
            return [
                await logger.log("DECISION", f"ev_{i}", {"i": i})
                for i in range(5)
            ]

        records = _run(_go())
        for prev, curr in zip(records, records[1:]):
            assert curr.prev_hash == prev.this_hash

    def test_internal_next_seq_advances_after_each_call(self):
        logger = AuditLogger(sink=InMemorySink())

        async def _go():
            for i in range(3):
                await logger.log("DECISION", f"ev_{i}", {})
            return logger.next_seq

        assert _run(_go()) == 4  # 3 records written, next is seq=4

    def test_verify_chain_after_ten_writes(self):
        sink = InMemorySink()
        logger = AuditLogger(sink=sink)

        async def _go():
            for i in range(10):
                await logger.log("DECISION", f"ev_{i}", {"i": i})

        _run(_go())
        assert verify_chain(list(sink.read_all())).ok is True


# --------------------------------------------------------------------------- #
# Injected clock
# --------------------------------------------------------------------------- #


class TestInjectedClock:
    def test_clock_is_used_for_timestamp(self):
        sink = InMemorySink()
        fixed = _make_fixed_clock(
            datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)
        )
        logger = AuditLogger(sink=sink, clock=fixed)

        record = _run(logger.log("DECISION", "ev_1", {}))

        assert record.timestamp == "2026-05-11T12:00:00.000Z"

    def test_clock_advances_per_call(self):
        sink = InMemorySink()
        fixed = _make_fixed_clock(
            datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)
        )
        logger = AuditLogger(sink=sink, clock=fixed)

        async def _go():
            return [
                await logger.log("DECISION", f"ev_{i}", {})
                for i in range(3)
            ]

        records = _run(_go())
        assert records[0].timestamp == "2026-05-11T12:00:00.000Z"
        assert records[1].timestamp == "2026-05-11T12:00:00.001Z"
        assert records[2].timestamp == "2026-05-11T12:00:00.002Z"

    def test_naive_datetime_from_clock_is_treated_as_utc(self):
        sink = InMemorySink()
        # A bad clock returning a naive datetime
        counter = {"n": 0}

        def _bad_clock():
            ts = datetime(2026, 5, 11, 12, 0, counter["n"])
            counter["n"] += 1
            return ts

        logger = AuditLogger(sink=sink, clock=_bad_clock)

        record = _run(logger.log("DECISION", "ev_1", {}))

        # Logger must coerce to Z; not raise
        assert record.timestamp.endswith("Z")


# --------------------------------------------------------------------------- #
# Redactor invocation (A5)
# --------------------------------------------------------------------------- #


class TestRedactorInvocation:
    def test_redactor_is_called_before_write(self):
        spy = _SpyRedactor()
        sink = InMemorySink()
        logger = AuditLogger(sink=sink, redactor=spy)

        payload = {"actor": "alice", "msg": "hi"}
        _run(logger.log("EVENT_RECEIVED", "ev_1", payload))

        assert len(spy.calls) == 1
        assert spy.calls[0] == payload

    def test_redactor_called_for_every_log_call(self):
        spy = _SpyRedactor()
        sink = InMemorySink()
        logger = AuditLogger(sink=sink, redactor=spy)

        async def _go():
            for i in range(5):
                await logger.log("DECISION", f"ev_{i}", {"i": i})

        _run(_go())
        assert len(spy.calls) == 5

    def test_redactor_output_is_what_gets_hashed(self):
        """If the redactor returns a different payload than the input,
        the payload_hash MUST match the returned payload, not the
        original."""

        class _ReplacingRedactor:
            def redact(self, payload):
                return {"redacted": True}

        sink = InMemorySink()
        logger = AuditLogger(sink=sink, redactor=_ReplacingRedactor())

        record = _run(logger.log("DECISION", "ev_1", {"raw": "secret"}))

        from soc.audit.chain import hash_payload

        assert record.payload_hash == hash_payload({"redacted": True})
        assert record.payload_hash != hash_payload({"raw": "secret"})


# --------------------------------------------------------------------------- #
# F2: day rollover
# --------------------------------------------------------------------------- #


class TestDayRollover:
    def test_chain_links_across_midnight(self):
        """Canonical spec section 10.3 F2: 'The first record of each
        day commits to the previous day's last record's hash, so
        days form a chain too.'"""

        # Two timestamps: 23:59:59.500 on day N, 00:00:00.500 on day N+1
        timestamps = iter([
            datetime(2026, 5, 11, 23, 59, 59, 500_000, tzinfo=timezone.utc),
            datetime(2026, 5, 12, 0, 0, 0, 500_000, tzinfo=timezone.utc),
        ])

        def _midnight_clock():
            return next(timestamps)

        sink = InMemorySink()
        logger = AuditLogger(sink=sink, clock=_midnight_clock)

        async def _go():
            r1 = await logger.log("DECISION", "ev_eod", {})
            r2 = await logger.log("DECISION", "ev_sod", {})
            return r1, r2

        r1, r2 = _run(_go())

        assert r1.timestamp.startswith("2026-05-11T23:59:59")
        assert r2.timestamp.startswith("2026-05-12T00:00:00")
        # Linkage holds across the day boundary --- the spec F2
        # requirement is satisfied by construction (prev_hash is
        # unconditional).
        assert r2.prev_hash == r1.this_hash
        assert verify_chain(list(sink.read_all())).ok is True


# --------------------------------------------------------------------------- #
# Restart resume
# --------------------------------------------------------------------------- #


class TestRestartResume:
    def test_new_logger_against_existing_sink_continues_chain(self):
        sink = InMemorySink()

        # First logger writes 3 records, then "dies"
        logger_a = AuditLogger(sink=sink)

        async def _phase_a():
            for i in range(3):
                await logger_a.log("DECISION", f"a_{i}", {"i": i})

        _run(_phase_a())
        last_a = list(sink.read_all())[-1]

        # Second logger picks up against the same sink
        logger_b = AuditLogger(sink=sink)
        assert logger_b.next_seq == 4
        assert logger_b.prev_hash == last_a["this_hash"]

        async def _phase_b():
            for i in range(2):
                await logger_b.log("DECISION", f"b_{i}", {"i": i})

        _run(_phase_b())
        all_records = list(sink.read_all())
        assert len(all_records) == 5
        assert verify_chain(all_records).ok is True

    def test_restart_starts_at_one_against_empty_sink(self):
        sink = InMemorySink()
        # No writes
        logger_b = AuditLogger(sink=sink)
        assert logger_b.next_seq == 1
        assert logger_b.prev_hash == GENESIS_PREV_HASH


# --------------------------------------------------------------------------- #
# Concurrency
# --------------------------------------------------------------------------- #


class TestConcurrency:
    def test_concurrent_log_calls_produce_valid_chain(self):
        """50 concurrent log() calls via asyncio.gather. With the
        internal lock, the resulting chain MUST verify cleanly with
        monotonic seq and intact prev_hash linkage."""
        sink = InMemorySink()
        logger = AuditLogger(sink=sink)

        async def _go():
            await asyncio.gather(*[
                logger.log("DECISION", f"ev_{i}", {"i": i})
                for i in range(50)
            ])

        _run(_go())
        records = list(sink.read_all())
        assert len(records) == 50
        seqs = [r["seq"] for r in records]
        assert seqs == sorted(seqs)
        assert seqs == list(range(1, 51))
        assert verify_chain(records).ok is True


# --------------------------------------------------------------------------- #
# Failure semantics: no state advance on failed write
# --------------------------------------------------------------------------- #


class TestFailureSemantics:
    def test_non_serialisable_payload_raises_and_does_not_advance_state(self):
        sink = InMemorySink()
        logger = AuditLogger(sink=sink)

        # A first valid call to establish state
        _run(logger.log("DECISION", "ev_1", {"a": 1}))
        assert logger.next_seq == 2

        # A second call with a non-JSON-serialisable object MUST raise
        class _NotJSON:
            pass

        with pytest.raises((TypeError, ValueError)):
            _run(logger.log("DECISION", "ev_2", {"obj": _NotJSON()}))

        # State must NOT have advanced
        assert logger.next_seq == 2

        # A third valid call resumes cleanly at seq=2
        record3 = _run(logger.log("DECISION", "ev_3", {"a": 3}))
        assert record3.seq == 2
        assert verify_chain(list(sink.read_all())).ok is True

    def test_failing_redactor_does_not_advance_state(self):
        class _FailingRedactor:
            def redact(self, payload):
                raise RuntimeError("redactor exploded")

        sink = InMemorySink()
        logger = AuditLogger(sink=sink, redactor=_FailingRedactor())

        with pytest.raises(RuntimeError):
            _run(logger.log("DECISION", "ev_1", {}))

        assert logger.next_seq == 1
        assert logger.prev_hash == GENESIS_PREV_HASH
        assert list(sink.read_all()) == []

