"""DLP scanner package --- INTERFACE STUB ONLY.

[STATUS] TODO --- implementation parked. The concrete Presidio-based
scanner described in ``docs/AI_OS_v3_SPEC.md`` section 6 is not yet
present in this repository. This package exposes only the abstract
interface so that downstream stages (Risk Engine, Decision Engine,
SOCPipeline) can be implemented and tested with mocked DLP behaviour.

Relationship to existing credential redaction (``detections/vrl_filter.py``)
----------------------------------------------------------------------------
A regex-based **credential** redaction filter already lives in
``detections/vrl_filter.py`` (added in commit ``0bc798dd``: AWS keys,
PEM blocks, GitHub tokens, JWTs, generic API keys, plaintext
passwords; masked as ``[REDACTED_CRED_<TYPE>]``). That filter runs in
the legacy event-ingest path and is **complementary** to the DLP
scanner described here, not a substitute. Specifically:

- ``vrl_filter.py`` masks SECRETS in free-text log payloads at ingest.
- The DLP scanner in this package detects PII (SA ID, ZW ID, SARS
  tax, medical aid, phone, email) on the SOCPipeline critical path,
  emits structured :class:`~soc.risk.types.DLPResult` findings, and
  feeds the Risk and Decision engines.

When the production DLP scanner is implemented, it MUST NOT duplicate
the credential patterns already handled in ``vrl_filter.py``; reuse
or coordinate, do not re-implement.

Resolution path
---------------
One of the following must happen before this package goes to
production:

1. Implement the canonical spec section 6 from scratch
   (``presidio-analyzer`` + SA-specific recognisers: SA ID with Luhn,
   ZW National ID, SA asylum/refugee permits, SARS tax ref, KGA
   policy number, medical aid, phone, email).
2. Adopt an alternative engine and update canonical spec section 6
   to match.

Until then, every consumer of this package must inject a mock or a
production-grade scanner that satisfies :class:`DLPScannerProtocol`.

See ``docs/architecture/dlp-scanner.md`` (to be written) for the
implementation contract.
"""

from soc.dlp.scanner import DLPScannerProtocol, NotImplementedDLPScanner

__all__ = ["DLPScannerProtocol", "NotImplementedDLPScanner"]

