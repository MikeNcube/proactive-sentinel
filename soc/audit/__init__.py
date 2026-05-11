"""Audit Logger package (canonical spec section 10).

Hash-chained, tamper-evident audit logging. Used by the SOC pipeline
(canonical spec section 5.2):

    await self.audit.log("EVENT_RECEIVED", event.event_id, event.summary())
    await self.audit.log("DECISION",       event.event_id, decision.to_record())

Architecture
------------
Pure-core / side-effecting-wrapper split:

- :mod:`soc.audit.types`     --- :class:`AuditRecord` frozen dataclass
- :mod:`soc.audit.chain`     --- canonical JSON + SHA-256 primitives (pure)
- :mod:`soc.audit.verify`    --- :func:`verify_chain` integrity check (pure)
- :mod:`soc.audit.redaction` --- :class:`Redactor` protocol + stub (A5)
- :mod:`soc.audit.sinks`     --- :class:`Sink` protocol + in-memory + JSONL
- :mod:`soc.audit.logger`    --- stateful :class:`AuditLogger`

See ``docs/architecture/audit-logger.md`` for the sub-contract.

Out of scope for this commit
----------------------------
- Presidio-backed :class:`Redactor` (waits on Priority 1 DLP scanner)
- S3 Object Lock sink (canonical spec section 11; AWS promotion work)
- Daily verifier Lambda packaging (canonical spec section 12;
  ``verify_chain`` itself is delivered)
- F4 IAM/bucket policy (infrastructure work)
"""

from soc.audit.chain import GENESIS_PREV_HASH, build_record, hash_payload
from soc.audit.logger import AuditLogger
from soc.audit.redaction import PassthroughRedactor, Redactor
from soc.audit.sinks import InMemorySink, JSONLFileSink, Sink
from soc.audit.types import AuditRecord
from soc.audit.verify import VerificationResult, verify_chain

__all__ = [
    "AuditLogger",
    "AuditRecord",
    "GENESIS_PREV_HASH",
    "InMemorySink",
    "JSONLFileSink",
    "PassthroughRedactor",
    "Redactor",
    "Sink",
    "VerificationResult",
    "build_record",
    "hash_payload",
    "verify_chain",
]
