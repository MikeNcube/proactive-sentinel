"""Integration tests for :class:`soc.audit.JSONLFileSink`.

Exercises the real filesystem path with ``tmp_path``:

- writes 20 records, reads them back, verifies the chain
- each line of the file is independently valid JSON
- restart-resume against an existing file produces a chain that
  verifies end-to-end
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import pytest

from soc.audit import (
    AuditLogger,
    JSONLFileSink,
    verify_chain,
)


def _run(coro):
    return asyncio.run(coro)


def _make_fixed_clock():
    from datetime import timedelta

    counter = {"n": 0}
    base = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def _clock():
        ts = base + timedelta(milliseconds=counter["n"])
        counter["n"] += 1
        return ts

    return _clock


# --------------------------------------------------------------------------- #
# JSONLFileSink construction
# --------------------------------------------------------------------------- #


class TestJSONLFileSinkConstruction:
    def test_creates_parent_directories(self, tmp_path):
        target = tmp_path / "audit" / "deep" / "nested" / "log.jsonl"
        sink = JSONLFileSink(target)
        assert target.exists()
        assert target.parent.is_dir()

    def test_accepts_string_path(self, tmp_path):
        target = tmp_path / "log.jsonl"
        sink = JSONLFileSink(str(target))
        assert sink.path == target

    def test_empty_file_returns_none_for_read_last(self, tmp_path):
        sink = JSONLFileSink(tmp_path / "log.jsonl")
        assert sink.read_last() is None
        assert list(sink.read_all()) == []


# --------------------------------------------------------------------------- #
# Round-trip
# --------------------------------------------------------------------------- #


class TestRoundTrip:
    def test_twenty_record_chain_round_trips_through_disk(self, tmp_path):
        sink = JSONLFileSink(tmp_path / "audit.jsonl")
        logger = AuditLogger(
            sink=sink,
            clock=_make_fixed_clock(),
            manifest_hash="sha256:test",
        )

        async def _produce():
            for i in range(20):
                await logger.log("DECISION", f"ev_{i}", {"i": i})

        _run(_produce())

        records = list(sink.read_all())
        assert len(records) == 20
        assert verify_chain(records).ok is True

    def test_every_line_in_file_is_valid_json(self, tmp_path):
        sink = JSONLFileSink(tmp_path / "audit.jsonl")
        logger = AuditLogger(
            sink=sink,
            clock=_make_fixed_clock(),
        )

        async def _produce():
            for i in range(10):
                await logger.log("DECISION", f"ev_{i}", {"i": i})

        _run(_produce())

        with open(tmp_path / "audit.jsonl", "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                parsed = json.loads(line)
                # Spec section 10.1 fields all present
                for key in (
                    "seq",
                    "timestamp",
                    "manifest_hash",
                    "event_type",
                    "event_id",
                    "payload_hash",
                    "payload_ref",
                    "prev_hash",
                    "this_hash",
                ):
                    assert key in parsed

    def test_each_record_is_on_its_own_line(self, tmp_path):
        path = tmp_path / "audit.jsonl"
        sink = JSONLFileSink(path)
        logger = AuditLogger(sink=sink, clock=_make_fixed_clock())

        async def _produce():
            for i in range(5):
                await logger.log("DECISION", f"ev_{i}", {})

        _run(_produce())

        with open(path, "r", encoding="utf-8") as fh:
            lines = [line for line in fh if line.strip()]
        assert len(lines) == 5


# --------------------------------------------------------------------------- #
# Restart resume against a real file
# --------------------------------------------------------------------------- #


class TestRestartResumeOnDisk:
    def test_second_logger_continues_chain_from_existing_file(self, tmp_path):
        path = tmp_path / "audit.jsonl"

        # Phase A: first logger writes 5 records
        sink_a = JSONLFileSink(path)
        logger_a = AuditLogger(
            sink=sink_a,
            clock=_make_fixed_clock(),
            manifest_hash="sha256:test",
        )

        async def _phase_a():
            for i in range(5):
                await logger_a.log("DECISION", f"a_{i}", {"i": i})

        _run(_phase_a())

        # Phase B: a NEW sink + logger against the same file
        sink_b = JSONLFileSink(path)
        last_a = sink_b.read_last()
        assert last_a is not None
        assert last_a["seq"] == 5

        logger_b = AuditLogger(
            sink=sink_b,
            clock=_make_fixed_clock(),
            manifest_hash="sha256:test",
        )
        assert logger_b.next_seq == 6
        assert logger_b.prev_hash == last_a["this_hash"]

        async def _phase_b():
            for i in range(3):
                await logger_b.log("DECISION", f"b_{i}", {"i": i})

        _run(_phase_b())

        # Final chain has 8 records and verifies clean end-to-end
        sink_final = JSONLFileSink(path)
        all_records = list(sink_final.read_all())
        assert len(all_records) == 8
        assert [r["seq"] for r in all_records] == list(range(1, 9))
        assert verify_chain(all_records).ok is True


# --------------------------------------------------------------------------- #
# Tamper detection on disk
# --------------------------------------------------------------------------- #


class TestOnDiskTamperDetection:
    def test_overwriting_one_line_breaks_verification(self, tmp_path):
        path = tmp_path / "audit.jsonl"
        sink = JSONLFileSink(path)
        logger = AuditLogger(sink=sink, clock=_make_fixed_clock())

        async def _produce():
            for i in range(5):
                await logger.log("DECISION", f"ev_{i}", {"i": i})

        _run(_produce())

        # Read, mutate line 3, write back
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()

        # Tamper with event_id on the third record (index 2)
        record = json.loads(lines[2])
        record["event_id"] = "tampered"
        lines[2] = json.dumps(record) + "\n"

        with open(path, "w", encoding="utf-8") as fh:
            fh.writelines(lines)

        # Re-verify --- must catch the break
        sink2 = JSONLFileSink(path)
        result = verify_chain(list(sink2.read_all()))
        assert result.ok is False
        assert result.error_index == 2
