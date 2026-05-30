"""Lightweight data shapes consumed and produced by the Risk Engine.

These types intentionally mirror only the fields the Risk Engine
reads. Full Event / DLP / Policy domain models live in their own
modules (or will, once those stages are implemented). Keeping the
engine's surface narrow protects it from churn in adjacent stages.

All types are frozen dataclasses so engine inputs and outputs are
hashable, comparable in tests, and safe to log without mutation
surprises.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


# Allowed severity strings (lowercase). Anything outside this set
# falls through to the "info" tier in the deterministic rule table.
SEVERITY_LEVELS: tuple[str, ...] = ("info", "low", "medium", "high", "critical")


@dataclass(frozen=True)
class SecurityEvent:
    """Input event scored by the Risk Engine and the Decision Engine.

    Only the fields the engines actually read are declared here.
    Upstream code MAY use a richer Event class; it just has to expose
    these attributes (duck typing is fine).

    The ``action`` and ``classification`` fields are consumed by the
    Decision Engine (canonical spec section 8). They default to safe
    values so existing Risk-Engine-only callers stay backward
    compatible.
    """

    event_id: str
    actor_id: str
    event_type: str
    severity: str
    numeric_signal: float
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)
    # Read by Decision Engine (spec section 8)
    action: str = ""                  # e.g. "mcp.tool_execute", "rag.query"
    classification: str = "internal"  # special | personal | internal | public


@dataclass(frozen=True)
class DLPFinding:
    """One PII finding produced by the DLP scanner."""

    entity_type: str  # e.g. "ZA_ID", "EMAIL", "PHONE"
    severity: str     # one of SEVERITY_LEVELS
    score: float      # detector confidence in [0.0, 1.0]


@dataclass(frozen=True)
class DLPResult:
    """Aggregated DLP scanner output (subset the engine reads)."""

    findings: tuple[DLPFinding, ...] = ()

    @property
    def has_findings(self) -> bool:
        return len(self.findings) > 0

    @property
    def max_severity(self) -> str:
        """Highest severity present, or 'info' if no findings.

        Severity order follows :data:`SEVERITY_LEVELS`.
        """
        if not self.findings:
            return "info"
        order = {s: i for i, s in enumerate(SEVERITY_LEVELS)}
        return max(
            (f.severity for f in self.findings),
            key=lambda s: order.get(s.lower(), 0),
        )


@dataclass(frozen=True)
class PolicyResult:
    """OPA policy evaluation output (subset the engines read).

    ``deny_reason`` is consumed by the Decision Engine (canonical spec
    section 8: ``BLOCK`` records ``reason=policy.deny_reason``). It
    defaults to an empty string so existing Risk-Engine-only callers
    stay backward compatible; the Decision Engine substitutes a
    fallback when the field is empty.
    """

    allowed: bool
    policy_version: str = "unversioned"
    violations: tuple[str, ...] = ()
    deny_reason: str = ""


@dataclass(frozen=True)
class RiskAssessment:
    """Risk Engine output, consumed by the Decision stage.

    Mapped onto the DecisionRecord per spec section 5.3 A4:

    - ``score``          --> DecisionRecord.risk_score
    - ``risk_inputs``    --> DecisionRecord.risk_inputs

    The attribute is named ``score`` (not ``risk_score``) to match the
    call site in canonical spec section 8, e.g. ``risk.score >= 80``.
    The Decision Engine maps it onto the ``risk_score`` field of the
    DecisionRecord.
    """

    event_id: str
    actor_id: str
    score: float                # final blended score in [0.0, 100.0]
    deterministic_score: float  # fast-path sub-score in [0.0, 1.0]
    statistical_score: float    # window-derived sub-score in [0.0, 1.0]
    confidence: float           # engine confidence in [0.0, 1.0]
    z_score: float | None       # None until min_samples reached
    rule_hits: tuple[str, ...]  # deterministic rule IDs that fired
    sample_count: int           # samples present BEFORE this event
    window_size: int

    @property
    def risk_inputs(self) -> Mapping[str, Any]:
        """Explainability payload safe to log (no raw PII).

        Maps onto ``DecisionRecord.risk_inputs`` per canonical spec
        section 5.3 A4.
        """
        return {
            "deterministic_score": self.deterministic_score,
            "statistical_score": self.statistical_score,
            "confidence": self.confidence,
            "z_score": self.z_score,
            "rule_hits": list(self.rule_hits),
            "sample_count": self.sample_count,
            "window_size": self.window_size,
        }

