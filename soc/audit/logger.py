"""Hash-chained tamper-evident Audit Logger (canonical spec section 10).

The logger is the only stateful, side-effecting component in the
``soc.audit`` package. State held:

- the next sequence number to issue (``_next_seq``)
- the previous record's ``this_hash`` (``_prev_hash``)
- an :class:`asyncio.Lock` serialising concurrent ``.log()`` calls

State is initialised from the configured :class:`Sink` at
construction time: if the sink already contains records, the logger
reads the last one and continues the chain. If empty, the logger
starts with ``seq=1`` and ``prev_hash=GENESIS_PREV_HASH``. This
makes a crash + restart sequence write the next record on the chain
transparently --- no separate state file is required.

External concerns are dependency-injected:

- ``sink`` --- where records land (``InMemorySink``, ``JSONLFileSink``,
  or any other :class:`Sink` implementation).
- ``redactor`` --- A5 PII redaction (defaults to ``PassthroughRedactor``
  pending Presidio; see ``soc/audit/redaction.py``).
- ``clock`` --- a zero-arg callable returning a timezone-aware
  ``datetime``. Defaults to ``datetime.now(timezone.utc)``. Tests
  inject deterministic clocks.
- ``manifest_hash`` --- recorded on every audit row so each entry
  is traceable to a specific MANIFEST.yaml revision (canonical spec
  section 3 cross-cutting principle).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Optional

from soc.audit.chain import GENESIS_PREV_HASH, build_record, hash_payload
from soc.audit.redaction import PassthroughRedactor, Redactor
from soc.audit.sinks import Sink
from soc.audit.types import AuditRecord


def _utc_now() -> datetime:
    """Default clock: UTC ``datetime.now``.

    Isolated as a module-level function so the default is captured
    once and tests can monkeypatch it if needed (though injection via
    constructor is the preferred path).
    """
    return datetime.now(timezone.utc)


def _format_iso(dt: datetime) -> str:
    """Format a datetime as ISO 8601 with ``Z`` suffix and ms precision.

    Canonical spec section 10.1 example uses
    ``"2026-04-30T10:15:42.001Z"`` --- millisecond precision, ``Z``
    timezone marker. Python's ``isoformat`` emits ``+00:00`` by
    default; we replace that with ``Z`` to match.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


class AuditLogger:
    """Hash-chained audit logger.

    Construct once per process. Call :meth:`log` from anywhere; the
    internal lock serialises concurrent calls. Safe to use across
    asyncio tasks within a single event loop.

    Constructor parameters
    ----------------------
    sink : Sink
        Where records get written. The logger reads ``sink.read_last``
        once at construction to recover its position; subsequent
        ``.log`` calls only ``sink.write``.
    redactor : Redactor, optional
        Called on every payload BEFORE hashing or writing
        (canonical spec section 5.3 A5). Defaults to
        :class:`PassthroughRedactor`.
    clock : Callable[[], datetime], optional
        Zero-arg callable returning a timezone-aware ``datetime``.
        Defaults to :func:`datetime.now(timezone.utc)`.
    manifest_hash : str, optional
        ``sha256:<hex>`` identifier of the active MANIFEST.yaml.
        Recorded on every row. Defaults to all-zeros (development).
    """

    def __init__(
        self,
        *,
        sink: Sink,
        redactor: Optional[Redactor] = None,
        clock: Optional[Callable[[], datetime]] = None,
        manifest_hash: str = "sha256:" + "0" * 64,
    ) -> None:
        self._sink = sink
        self._redactor = redactor if redactor is not None else PassthroughRedactor()
        self._clock = clock if clock is not None else _utc_now
        self._manifest_hash = manifest_hash
        self._lock = asyncio.Lock()
        self._next_seq, self._prev_hash = self._recover_state()

    def _recover_state(self) -> tuple[int, str]:
        """Initialise (seq, prev_hash) from the sink's last record.

        Empty sink --> (1, GENESIS_PREV_HASH).
        Non-empty sink --> (last_seq + 1, last_this_hash).
        """
        last = self._sink.read_last()
        if last is None:
            return 1, GENESIS_PREV_HASH
        return int(last["seq"]) + 1, str(last["this_hash"])

    async def log(
        self,
        event_type: str,
        event_id: str,
        payload: Mapping[str, Any],
    ) -> AuditRecord:
        """Write a single audit record and return it.

        Sequence:

        1. Redact the payload (A5).
        2. Hash the redacted payload --> ``payload_hash``.
        3. Build the record (computes ``this_hash``).
        4. Write to the sink.
        5. Advance ``seq`` and ``prev_hash`` *after* a successful write.

        If any step raises, internal state is NOT advanced, so the
        next successful call resumes the chain cleanly with the same
        ``seq`` that would have been used. This prevents gaps and
        silent corruption.
        """
        async with self._lock:
            redacted = self._redactor.redact(payload)
            payload_hash = hash_payload(redacted)
            timestamp = _format_iso(self._clock())
            record = build_record(
                seq=self._next_seq,
                timestamp=timestamp,
                manifest_hash=self._manifest_hash,
                event_type=event_type,
                event_id=event_id,
                payload_hash=payload_hash,
                # Empty in dev (file sink); a "s3://..." URI in prod.
                payload_ref="",
                prev_hash=self._prev_hash,
            )
            self._sink.write(record.to_dict())
            self._next_seq += 1
            self._prev_hash = record.this_hash
            return record

    # Read-only accessors for tests and diagnostics. The logger is
    # otherwise opaque from outside the package.

    @property
    def next_seq(self) -> int:
        return self._next_seq

    @property
    def prev_hash(self) -> str:
        return self._prev_hash

