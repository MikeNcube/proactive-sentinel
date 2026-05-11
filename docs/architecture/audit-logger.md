# SOC Audit Logger — architecture sub-contract

**Status:** DRAFT — supplements canonical spec section 10
**Owner:** Simbarashe G. | AI Automation Engineer
**Scope:** `soc.audit` package implementation specifics
**Authoritative spec:** `docs/AI_OS_v3_SPEC.md` section 10 (and section 5.2, 5.3 A5)

This document supplements (but does not contradict) the canonical
spec. Where the two differ, the canonical spec wins until amended.

---

## 1. Purpose

The audit logger writes hash-chained, tamper-evident records of every
SOC pipeline event. It is the legal record of system behaviour and
the foundation of POPIA / FSCA compliance evidence.

## 2. Contract

Canonical spec section 5.2 calls the logger as:

```python
await self.audit.log("EVENT_RECEIVED", event.event_id, event.summary())
await self.audit.log("DECISION",       event.event_id, decision.to_record())
```

Therefore `log` takes `(event_type, event_id, payload)`. It is `async`
to satisfy the pipeline interface even though dev-mode I/O is sync.
It returns the written `AuditRecord` so callers can correlate with
the seq number and timestamp.

## 3. Components (pure-core / side-effecting-wrapper split)

| Module | Purity | Responsibility |
|---|---|---|
| `chain.py` | PURE | Canonical JSON, SHA-256 hashing, record construction |
| `verify.py` | PURE | Chain integrity verification (F1) |
| `types.py` | PURE | `AuditRecord` frozen dataclass |
| `redaction.py` | PURE | `Redactor` protocol + `PassthroughRedactor` default |
| `sinks.py` | I/O | `Sink` protocol + `InMemorySink` + `JSONLFileSink` |
| `logger.py` | STATEFUL | `AuditLogger`: seq counter, prev_hash, async lock |

Pure modules have no I/O, no state, no clocks. They can be tested with
`pytest.parametrize` over hundreds of fixtures with zero setup. The
side-effecting wrapper (`logger.py`) confines all observable mutation
behind a single `asyncio.Lock`.

## 4. Record format

Matches canonical spec section 10.1 verbatim — field names, order,
types. The `AuditRecord` frozen dataclass mirrors this layout.

| Field | Type | Notes |
|---|---|---|
| `seq` | int | Monotonic, starts at 1, advances on successful write |
| `timestamp` | str | ISO 8601 with `Z` suffix, millisecond precision |
| `manifest_hash` | str | `sha256:<hex>` — injected at logger construction |
| `event_type` | str | e.g. `"EVENT_RECEIVED"`, `"DECISION"` |
| `event_id` | str | Caller-supplied event correlation id |
| `payload_hash` | str | `sha256:<hex>` of the **redacted** payload's canonical JSON |
| `payload_ref` | str | `""` in dev, `s3://…` in prod |
| `prev_hash` | str | `sha256:<hex>` of the previous record (its `this_hash`) |
| `this_hash` | str | `sha256:<hex>` of this record **excluding** `this_hash` |

## 5. Canonical JSON

Deterministic SHA-256 hashing requires byte-stable JSON. We use:

```python
json.dumps(
    data,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
).encode("utf-8")
```

- `sort_keys=True` — key order independent of dict insertion order;
  applied recursively to nested objects
- `separators=(",", ":")` — no whitespace
- `ensure_ascii=False` — unicode preserved, UTF-8 encoded

Any change to this canonicalisation invalidates **every** existing
audit record. The rule is locked behind a single function
(`chain.canonical_json`) with a regression test against a hand-computed
hash.

## 6. Genesis & restart resume

**Genesis.** The first record's `prev_hash` is:

```
GENESIS_PREV_HASH = "sha256:" + "0" * 64
```

**Restart resume.** When `AuditLogger` is constructed against a
non-empty sink, it reads the last record via `sink.read_last()` and
continues from there:

- `next_seq = last.seq + 1`
- `prev_hash = last.this_hash`

This makes a crash + restart sequence write the next record on the
chain transparently — no separate state file is required.

## 7. F1: chain verification

`verify_chain(records)` walks the chain and returns
`VerificationResult(ok, error_index, error_reason)`. It checks, in
order:

1. `seq` is monotonic starting from 1 (no gaps, no reorderings)
2. First record's `prev_hash == GENESIS_PREV_HASH`
3. Each subsequent record's `prev_hash == previous.this_hash`
4. Each record's `this_hash` recomputes correctly from its other fields

The function is invoked by tests, ad-hoc CLI scripts, and (in
production) by a daily AWS Lambda. **The function itself is
delivered in this commit;** Lambda packaging is canonical spec
section 12 / Terraform work and deferred.

## 8. F2: day rollover

Because `prev_hash` linkage is unconditional — it always points to
the previous record regardless of date — F2 ("the first record of
each day commits to the previous day's last record's hash") is
satisfied by construction. A dedicated test simulates a clock
crossing midnight and asserts the linkage holds.

## 9. F3: PII redaction

Canonical spec section 5.3 A5 mandates: **"PII findings logged to
the audit trail MUST be redacted using Presidio's anonymizer.
Original PII never appears in audit logs."**

The `Redactor` protocol declares the contract:

```python
class Redactor(Protocol):
    def redact(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        ...
```

`AuditLogger.log` calls `self._redactor.redact(payload)` **before**
hashing or writing.

The current default is `PassthroughRedactor` — a stub that returns
the payload unchanged. This is correct from an API contract
perspective (the redactor IS always called) but does NOT redact PII
yet. When Priority 1 (Presidio-based DLP scanner) lands, swapping
`PassthroughRedactor` for a `PresidioRedactor` in pipeline wiring is
a one-line change.

A dedicated F3 corpus test is marked `xfail(strict=True)` against the
current default. It will start passing the moment a real redactor
is wired in — providing a clear signal that F3 is satisfied.

## 10. F4: sole-writer enforcement

Out of scope for code. Enforced by:

- S3 bucket policy granting `PutObject` only to the audit writer's
  IAM role
- Object Lock in compliance mode preventing all deletes (even by root)
- CloudWatch alarms on policy changes

Belongs to `infra/terraform/modules/data/` — canonical spec section 12
work.

## 11. Concurrency

`AuditLogger` holds an `asyncio.Lock` to serialise concurrent `.log()`
calls within a process. Without the lock, two concurrent calls would
race on `seq` and `prev_hash`. The lock is acquired around the full
sequence: redact → hash → build record → write → update state.

A regression test invokes `asyncio.gather` of 50 concurrent `.log()`
calls and asserts the resulting chain verifies cleanly with monotonic
seq and intact linkage.

## 12. Storage (sinks)

| Sink | Use | Notes |
|---|---|---|
| `InMemorySink` | Unit tests | List-backed; no I/O |
| `JSONLFileSink` | Dev (Railway) | Append-only JSONL, one record per line |
| `S3ObjectLockSink` (future) | Production (AWS) | Object Lock compliance mode, 7-year retention |

The `Sink` protocol declares three methods:

- `write(record)` — append one record
- `read_all()` — iterate all records (for verification)
- `read_last()` — fetch last record (for restart resume)

The S3 sink belongs to canonical spec section 11 (AWS promotion) and
is intentionally deferred.

## 13. Failure semantics

If any of `redact`, `hash_payload`, `build_record`, or `sink.write`
raises, the logger does **not** advance `seq` or `prev_hash`. The
next successful call resumes the chain cleanly with the same `seq`
that would have been used. This prevents gaps and silent corruption.

A regression test asserts this by attempting to log a non-JSON-
serialisable payload (which raises `TypeError`) and confirming that
the next valid call still gets `seq=N`, not `seq=N+1`.

The pipeline contract (canonical spec section 5.2) wraps `log` in a
try / except such that an audit failure during normal flow does NOT
mask the downstream decision — but the failure itself is also logged
as a high-severity audit record (canonical spec section 5.3 A3).

## 14. Cost notes

- Dev: zero (local JSONL on Railway disk)
- Prod: S3 storage ≈ R0.50 per GB / month; Object Lock has no
  additional charge
- Daily verifier Lambda: ≈ R0.10 per day at modest record volumes
- Estimated monthly audit cost at Zororo target scale: ≤ R20

## 15. Future work

1. `PresidioRedactor` (unblocks F3)
2. `S3ObjectLockSink` (unblocks production deployment)
3. Daily verifier Lambda packaging (unblocks F1 production
   monitoring; the function itself is delivered)
4. SOCPipeline assembly + integration tests (Priority 5)

---

Mike S Ncube | AI Automation Engineer
