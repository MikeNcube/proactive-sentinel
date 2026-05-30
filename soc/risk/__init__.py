"""Risk Engine package.

Implements the ``risk`` dependency of the SOC pipeline contract
described in ``docs/AI_OS_v3_SPEC.md`` (canonical: sections 4, 5.2,
5.3, 6.3, 8) and ``docs/architecture/risk-engine.md`` (sub-contract).

Public surface
--------------
- :class:`RiskEngine`        --- the engine itself
- :class:`RiskAssessment`    --- engine output (carries ``score``, 0-100)
- :class:`SecurityEvent`     --- input event shape (lightweight)
- :class:`DLPResult`         --- DLP scanner output shape used by engine
- :class:`DLPFinding`        --- single finding inside :class:`DLPResult`
- :class:`PolicyResult`      --- OPA policy output shape used by engine
- :data:`DEFAULT_FAST_PATH_RULES` --- default rule table (see sub-contract Â§3)
"""

from soc.risk.engine import (
    DEFAULT_FAST_PATH_RULES,
    RiskEngine,
)
from soc.risk.types import (
    DLPFinding,
    DLPResult,
    PolicyResult,
    RiskAssessment,
    SecurityEvent,
)

__all__ = [
    "DEFAULT_FAST_PATH_RULES",
    "DLPFinding",
    "DLPResult",
    "PolicyResult",
    "RiskAssessment",
    "RiskEngine",
    "SecurityEvent",
]

