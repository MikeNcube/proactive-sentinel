"""SOC pipeline components (per docs/AI_OS_v3_SPEC.md section 5).

Subpackages
-----------
- :mod:`soc.risk`     --- Risk Engine (canonical spec section 4 row 4,
  section 5.2 call signature, section 6.3 B3 confidence weighting,
  section 8 output contract). See ``docs/architecture/risk-engine.md``.
- :mod:`soc.decision` --- Decision Engine (canonical spec section 8).
  Pure function over (event, policy, risk, manifest); no I/O, no
  state, no clocks, no randoms. Maps inputs to ALLOW / MONITOR /
  REQUIRE_APPROVAL / BLOCK following the spec branch order verbatim.
- :mod:`soc.dlp`      --- DLP scanner INTERFACE STUB ONLY. Priority 1
  work is parked; production implementation per canonical spec
  section 6 is not yet present. See ``soc/dlp/__init__.py``.

Future subpackages (placeholders, not yet implemented):
- ``soc.policy`` --- OPA policy client (canonical spec section 7)
- ``soc.audit``  --- Hash-chained audit logger (canonical spec section 10)
"""
