"""Audit Logger redaction protocol (canonical spec section 5.3 A5).

Spec section 5.3 A5: "PII findings logged to the audit trail MUST be
redacted using Presidio's anonymizer. **Original PII never appears
in audit logs.**"

The :class:`AuditLogger` ALWAYS calls ``redactor.redact(payload)``
before hashing or writing. The redactor is dependency-injected, so
swapping the stub for a real Presidio-backed implementation is a
one-line wiring change.

Current state
-------------

The default :class:`PassthroughRedactor` is a STUB. It satisfies the
API contract (the logger calls a redactor before write) but does NOT
remove PII. Priority 1 (Presidio-based DLP scanner) is parked; see
``soc/dlp/__init__.py`` for status.

F3 acceptance criterion (no recognizer-detectable PII in any audit
record) is verified by a corpus test marked ``xfail(strict=True)``
against this default. The test will start passing the moment a real
:class:`Redactor` is wired into the pipeline.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class Redactor(Protocol):
    """Interface for PII redaction performed before audit write.

    Implementations MUST be deterministic and return a fresh mapping
    (mutating the input is forbidden). They MAY raise on malformed
    input but the audit logger does not catch --- exceptions propagate
    to the caller and the chain does not advance.
    """

    def redact(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


class PassthroughRedactor:
    """Default no-op redactor --- STUB pending Presidio (Priority 1).

    Returns a shallow copy of the payload unchanged. The copy ensures
    downstream mutations cannot leak back to the caller, matching the
    behaviour a real redactor (which would build a new sanitised
    payload) provides for free.

    Replace with a Presidio-backed implementation in pipeline wiring
    when Priority 1 lands. The audit logger needs no change.
    """

    def redact(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return dict(payload)

