"""Unit tests for the Audit Logger pure-core primitives.

Covers ``soc.audit.chain`` and ``soc.audit.types``:

- canonical JSON byte-stability and unicode handling
- SHA-256 hashing format (``sha256:<hex>``)
- regression hashes against hand-computed values (locks the
  canonicalisation contract)
- ``build_record`` produces every canonical spec section 10.1 field
- ``compute_this_hash`` refuses to operate when ``this_hash`` is
  already present
- ``GENESIS_PREV_HASH`` shape
"""

from __future__ import annotations

import pytest

from soc.audit.chain import (
    GENESIS_PREV_HASH,
    HASH_PREFIX,
    build_record,
    canonical_json,
    compute_this_hash,
    hash_bytes,
    hash_payload,
)
from soc.audit.types import AuditRecord


# --------------------------------------------------------------------------- #
# canonical_json
# --------------------------------------------------------------------------- #


class TestCanonicalJSON:
    def test_dict_with_keys_in_different_insertion_order_is_byte_identical(self):
        a = canonical_json({"a": 1, "b": 2})
        b = canonical_json({"b": 2, "a": 1})
        assert a == b

    def test_nested_dict_keys_are_also_sorted(self):
        a = canonical_json({"outer": {"a": 1, "b": 2}})
        b = canonical_json({"outer": {"b": 2, "a": 1}})
        assert a == b

    def test_emits_compact_separators_no_whitespace(self):
        cj = canonical_json({"a": 1, "b": 2})
        assert b" " not in cj
        assert cj == b'{"a":1,"b":2}'

    def test_returns_utf8_bytes(self):
        cj = canonical_json({"a": 1})
        assert isinstance(cj, bytes)

    def test_unicode_characters_preserved_as_utf8(self):
        cj = canonical_json({"name": "\u00fc"})  # u with diaeresis
        # ensure_ascii=False keeps the codepoint; UTF-8 encodes as 2 bytes
        assert b"\xc3\xbc" in cj

    def test_empty_dict_serialises_to_empty_braces(self):
        assert canonical_json({}) == b"{}"


# --------------------------------------------------------------------------- #
# hash primitives
# --------------------------------------------------------------------------- #


class TestHashing:
    def test_hash_bytes_has_sha256_prefix(self):
        h = hash_bytes(b"anything")
        assert h.startswith(HASH_PREFIX)
        # sha256 hex digest is 64 chars; prefix is 7 chars; total 71
        assert len(h) == 71

    def test_hash_payload_has_sha256_prefix(self):
        h = hash_payload({"a": 1})
        assert h.startswith(HASH_PREFIX)
        assert len(h) == 71

    def test_hash_payload_deterministic_across_calls(self):
        assert hash_payload({"a": 1}) == hash_payload({"a": 1})

    def test_hash_payload_independent_of_key_insertion_order(self):
        assert hash_payload({"a": 1, "b": 2}) == hash_payload({"b": 2, "a": 1})

    def test_different_payloads_yield_different_hashes(self):
        assert hash_payload({"a": 1}) != hash_payload({"a": 2})

    def test_regression_empty_dict_hash_is_stable(self):
        """Locks the canonicalisation contract. If this changes,
        every existing audit record's hash also changes --- a
        breaking change that needs explicit approval."""
        assert hash_payload({}) == (
            "sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e"
            "8310c060f61caaff8a"
        )

    def test_regression_known_payload_hash_is_stable(self):
        """Same contract lock, for a non-trivial payload."""
        assert hash_payload({"a": 1, "b": "test"}) == (
            "sha256:1e5d5cdc877a04ceb3d86ec5d57f088a03eef89a4d0669"
            "556f3feebfbd59868b"
        )


# --------------------------------------------------------------------------- #
# compute_this_hash guard
# --------------------------------------------------------------------------- #


class TestComputeThisHash:
    def test_refuses_if_this_hash_key_already_present(self):
        with pytest.raises(ValueError):
            compute_this_hash({"seq": 1, "this_hash": "anything"})

    def test_computes_deterministic_hash_for_record_skeleton(self):
        skeleton = {
            "seq": 1,
            "timestamp": "2026-01-01T00:00:00.000Z",
            "manifest_hash": "sha256:abc",
            "event_type": "DECISION",
            "event_id": "ev_1",
            "payload_hash": "sha256:def",
            "payload_ref": "",
            "prev_hash": GENESIS_PREV_HASH,
        }
        h1 = compute_this_hash(skeleton)
        h2 = compute_this_hash(skeleton)
        assert h1 == h2
        assert h1.startswith(HASH_PREFIX)


# --------------------------------------------------------------------------- #
# build_record
# --------------------------------------------------------------------------- #


class TestBuildRecord:
    def _skeleton(self, **overrides):
        base = {
            "seq": 1,
            "timestamp": "2026-01-01T00:00:00.000Z",
            "manifest_hash": "sha256:abc",
            "event_type": "DECISION",
            "event_id": "ev_1",
            "payload_hash": "sha256:def",
            "payload_ref": "",
            "prev_hash": GENESIS_PREV_HASH,
        }
        base.update(overrides)
        return base

    def test_returns_audit_record_instance(self):
        record = build_record(**self._skeleton())
        assert isinstance(record, AuditRecord)

    def test_record_has_every_spec_10_1_field(self):
        record = build_record(**self._skeleton())
        for field_name in (
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
            assert hasattr(record, field_name), f"missing field: {field_name}"

    def test_this_hash_has_correct_format(self):
        record = build_record(**self._skeleton())
        assert record.this_hash.startswith(HASH_PREFIX)
        assert len(record.this_hash) == 71

    def test_this_hash_is_deterministic_for_same_inputs(self):
        r1 = build_record(**self._skeleton())
        r2 = build_record(**self._skeleton())
        assert r1.this_hash == r2.this_hash
        assert r1 == r2

    def test_this_hash_changes_when_any_field_changes(self):
        base = build_record(**self._skeleton())
        for changed_key, new_value in [
            ("seq", 2),
            ("timestamp", "2026-01-01T00:00:01.000Z"),
            ("manifest_hash", "sha256:zzz"),
            ("event_type", "EVENT_RECEIVED"),
            ("event_id", "ev_2"),
            ("payload_hash", "sha256:other"),
            ("payload_ref", "s3://x"),
            ("prev_hash", "sha256:" + "1" * 64),
        ]:
            mutated = build_record(**self._skeleton(**{changed_key: new_value}))
            assert mutated.this_hash != base.this_hash, (
                f"this_hash should change when {changed_key} changes"
            )

    def test_to_dict_round_trip_preserves_fields(self):
        record = build_record(**self._skeleton())
        d = record.to_dict()
        for k, v in d.items():
            assert getattr(record, k) == v


# --------------------------------------------------------------------------- #
# GENESIS_PREV_HASH
# --------------------------------------------------------------------------- #


class TestGenesisPrevHash:
    def test_has_sha256_prefix(self):
        assert GENESIS_PREV_HASH.startswith(HASH_PREFIX)

    def test_is_sixty_four_zeros_after_prefix(self):
        suffix = GENESIS_PREV_HASH[len(HASH_PREFIX):]
        assert suffix == "0" * 64

    def test_total_length_matches_a_real_hash(self):
        assert len(GENESIS_PREV_HASH) == 71


# --------------------------------------------------------------------------- #
# AuditRecord immutability
# --------------------------------------------------------------------------- #


class TestAuditRecordImmutability:
    def test_record_is_frozen(self):
        record = build_record(
            seq=1,
            timestamp="2026-01-01T00:00:00.000Z",
            manifest_hash="sha256:abc",
            event_type="DECISION",
            event_id="ev_1",
            payload_hash="sha256:def",
            payload_ref="",
            prev_hash=GENESIS_PREV_HASH,
        )
        with pytest.raises((AttributeError, TypeError)):
            record.seq = 2  # type: ignore[misc]

    def test_record_is_hashable(self):
        record = build_record(
            seq=1,
            timestamp="2026-01-01T00:00:00.000Z",
            manifest_hash="sha256:abc",
            event_type="DECISION",
            event_id="ev_1",
            payload_hash="sha256:def",
            payload_ref="",
            prev_hash=GENESIS_PREV_HASH,
        )
        # frozen dataclass with hashable fields is hashable
        {record}
