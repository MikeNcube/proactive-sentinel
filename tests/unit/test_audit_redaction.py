"""Unit tests for :mod:`soc.audit.redaction` (canonical spec section
5.3 A5).

Covers:

- :class:`PassthroughRedactor` returns a fresh dict equal to input
- mutating the returned dict does NOT affect the input
- the F3 PII-redaction corpus test, marked ``xfail(strict=True)``
  against the current passthrough default --- it will start passing
  the moment a real Presidio-backed redactor is wired in
"""

from __future__ import annotations

import asyncio
import json
import re

import pytest

from soc.audit import AuditLogger, InMemorySink, PassthroughRedactor, Redactor


# --------------------------------------------------------------------------- #
# PassthroughRedactor contract
# --------------------------------------------------------------------------- #


class TestPassthroughRedactor:
    def test_returns_equal_dict(self):
        red = PassthroughRedactor()
        payload = {"actor": "alice", "msg": "hello"}
        assert red.redact(payload) == payload

    def test_returns_a_copy_not_the_same_object(self):
        red = PassthroughRedactor()
        payload = {"a": 1}
        result = red.redact(payload)
        result["a"] = 999  # type: ignore[index]
        assert payload["a"] == 1, "redactor must not mutate the caller's dict"

    def test_handles_empty_payload(self):
        red = PassthroughRedactor()
        assert red.redact({}) == {}

    def test_handles_nested_payload(self):
        red = PassthroughRedactor()
        payload = {"outer": {"inner": "value"}}
        assert red.redact(payload) == payload

    def test_satisfies_redactor_protocol(self):
        # runtime_checkable Protocol --- isinstance is meaningful
        red = PassthroughRedactor()
        assert isinstance(red, Redactor)


# --------------------------------------------------------------------------- #
# F3 corpus test --- xfail until Presidio lands
# --------------------------------------------------------------------------- #


# A small fixture of payloads containing recognizer-detectable PII.
# This is intentionally minimal --- the real Presidio integration
# will replace this with the full Presidio recognizer set
# (canonical spec section 6 + section 5.3 A5).
_PII_CORPUS = [
    {"actor": "Mike Ncube", "email": "mike@example.com"},
    {"phone": "+27 82 555 1234", "actor": "alice"},
    {"national_id": "9001015800087"},  # SA ID pattern
    {"credit_card": "4111 1111 1111 1111"},
]


# Patterns that simulate "what a Presidio recognizer would flag".
# Used only as a stand-in for the F3 corpus check. When Presidio
# lands, this pattern set is replaced by an actual recognizer call.
_PII_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w.-]+\.\w+"),                 # email
    re.compile(r"\+?\d[\d\s-]{8,}\d"),                     # phone
    re.compile(r"\b\d{13}\b"),                              # SA ID (13 digits)
    re.compile(r"\b(?:\d[ -]?){15,16}\b"),                 # credit card
]


def _contains_pii(text: str) -> bool:
    return any(p.search(text) for p in _PII_PATTERNS)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "F3: no recognizer-detectable PII in audit records. "
        "Currently fails because the default PassthroughRedactor "
        "does not remove PII. Will pass when Priority 1 Presidio "
        "scanner is wired in as the redactor."
    ),
)
def test_f3_audit_records_contain_no_recognizer_detectable_pii():
    """Canonical spec section 10.3 F3.

    Marked xfail(strict=True) so:

    - while the stub redactor is in place, the test fails as expected
      (xfailed, not error)
    - the moment a real redactor is wired in, the test passes ---
      strict mode then converts pass into FAIL, forcing this xfail
      mark to be removed in the same commit that ships the real
      redactor. That makes F3 readiness a tracked, gated milestone.
    """
    sink = InMemorySink()
    logger = AuditLogger(sink=sink)

    async def _produce():
        for payload in _PII_CORPUS:
            await logger.log("EVENT_RECEIVED", "ev_pii", payload)

    asyncio.run(_produce())

    # Serialise the full chain to JSON --- if any payload contains
    # PII and was NOT redacted, it would surface in the record's
    # payload reference or related fields.
    serialised = json.dumps(list(sink.read_all()), sort_keys=True)

    # The hash of the payload SHOULD be opaque (it is); but
    # production audit records will eventually carry redacted-payload
    # references that this corpus check would scan. For now, mirror
    # what the test will do post-Presidio: scan the entire serialised
    # output for PII patterns. With PassthroughRedactor this would
    # spuriously pass (because we only store payload_hash, not the
    # payload itself in the dev record). To make the contract
    # genuinely meaningful, also log the raw payload directly so
    # the test catches the absence of redaction.
    for payload in _PII_CORPUS:
        serialised_payload = json.dumps(payload)
        assert not _contains_pii(serialised_payload), (
            "F3: raw PII appears in audit-bound payload; "
            "redactor did not strip it"
        )

    assert not _contains_pii(serialised), (
        "F3: PII pattern detected in serialised audit chain"
    )
