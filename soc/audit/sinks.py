"""Audit Logger sinks --- where records get written.

Three concrete sinks (this commit ships two):

- :class:`InMemorySink` --- list-backed, no I/O, used by unit tests.
- :class:`JSONLFileSink` --- append-only JSONL file, used in dev.
- ``S3ObjectLockSink`` --- production sink, intentionally deferred to
  the AWS promotion work (canonical spec section 11). The
  :class:`Sink` protocol is the contract everything else binds to.

The protocol exposes three methods so the :class:`AuditLogger` can
both *write* new records and *recover* its position on restart by
reading the last record back from the sink.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Optional, Protocol, runtime_checkable


@runtime_checkable
class Sink(Protocol):
    """Write/read interface for audit records.

    ``write`` MUST be atomic at the granularity of a single record:
    either the record lands in the sink or it does not. Partial
    writes corrupt the chain.

    ``read_all`` and ``read_last`` are used by the chain verifier and
    by the logger's restart-resume path; they MUST return records in
    write order.
    """

    def write(self, record: Mapping[str, Any]) -> None: ...

    def read_all(self) -> Iterable[Mapping[str, Any]]: ...

    def read_last(self) -> Optional[Mapping[str, Any]]: ...


class InMemorySink:
    """List-backed sink for unit tests.

    Records are stored as ``dict`` copies so callers cannot mutate
    sink contents after writing. Order matches write order.
    """

    def __init__(self) -> None:
        self._records: List[Mapping[str, Any]] = []

    def write(self, record: Mapping[str, Any]) -> None:
        # Deep-ish copy: the record is one level of mapping with
        # primitive values, so dict() is sufficient.
        self._records.append(dict(record))

    def read_all(self) -> Iterable[Mapping[str, Any]]:
        # Return a copy so callers cannot mutate internal state.
        return [dict(r) for r in self._records]

    def read_last(self) -> Optional[Mapping[str, Any]]:
        if not self._records:
            return None
        return dict(self._records[-1])


class JSONLFileSink:
    """Append-only JSONL file sink for dev (Railway disk).

    One record per line, each line a canonical-JSON serialised dict.
    The file is created (and parent dirs created) at construction
    time so the logger can call ``read_last`` immediately on startup
    without a separate setup step.

    Each ``write`` opens the file in append mode, writes one line,
    and closes. This makes the sink crash-safe at line granularity:
    a process killed mid-write either lands the full line or none of
    it (assuming POSIX-compatible append semantics on the host
    filesystem; Windows behaviour is best-effort).
    """

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            # Touch creates an empty file --- read_last returns None
            # the first time the logger boots against it.
            self._path.touch()

    @property
    def path(self) -> Path:
        return self._path

    def write(self, record: Mapping[str, Any]) -> None:
        # Canonical JSON for the on-disk line so re-reading produces
        # exactly the bytes that were hashed for verification later.
        line = json.dumps(
            record,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def read_all(self) -> Iterable[Mapping[str, Any]]:
        if not self._path.exists():
            return []
        records: List[Mapping[str, Any]] = []
        with self._path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                records.append(json.loads(line))
        return records

    def read_last(self) -> Optional[Mapping[str, Any]]:
        # Naive but adequate for dev volumes. The production S3 sink
        # will implement this against an index, not a full scan.
        last: Optional[Mapping[str, Any]] = None
        for record in self.read_all():
            last = record
        return last
