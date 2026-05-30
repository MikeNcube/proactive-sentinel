"""Risk Engine implementation.

Implements the ``risk`` dependency of the SOCPipeline declared in
canonical spec section 5.2 (``docs/AI_OS_v3_SPEC.md``):

    risk_result = await self.risk.score(event, dlp_result, policy_result)

The engine-specific contract lives in
``docs/architecture/risk-engine.md``. If anything below disagrees with
the canonical spec, the canonical spec wins.

Design notes
------------
- Pure standard-library implementation. No numpy, no scipy.
- ``score()`` is ``async`` to honour pipeline acceptance criterion
  A1, but all internal work is CPU-bound and synchronous; the method
  is async so the SOCPipeline composes cleanly with the rest of the
  await-chain in canonical spec section 5.2.
- The engine is stateful (per-actor sliding window) but
  reproducible: see ``reset()`` and ``reset_actor()`` for test
  determinism (sub-contract REQ-RE-1).
- Decision banding (ALLOW / MONITOR / REQUIRE_APPROVAL / BLOCK) is NOT
  the engine's responsibility --- that belongs to the Decision Engine
  per canonical spec section 8. The engine only emits ``score`` (0-100)
  and an explainability payload (``risk_inputs``).
"""

from __future__ import annotations

import math
import statistics
from collections import deque
from collections.abc import Callable, Iterable
from typing import Final

from soc.risk.types import (
    DLPResult,
    PolicyResult,
    RiskAssessment,
    SecurityEvent,
)


# --------------------------------------------------------------------------- #
# Fast-path rules
# --------------------------------------------------------------------------- #

# A fast-path rule is a (rule_id, predicate, base_score, selector)
# tuple. ``predicate`` decides whether the rule fires.
# ``base_score`` is the raw contribution to the deterministic sub-score
# (range [0.0, 1.0]). ``selector`` is an optional function that returns
# the subset of DLP findings this rule "owns"; the rule's effective
# contribution is then ``base_score * max(f.score for f in subset)``.
# This implements the DLP confidence-weighting requirement from
# canonical spec section 6.3 B3 (SA-002): "Confidence affects the risk
# engine's weighting of the finding, not the classification itself."
FastPathPredicate = Callable[
    [SecurityEvent, DLPResult, PolicyResult],
    bool,
]
FastPathSelector = Callable[[DLPResult], tuple]  # returns tuple of DLPFinding
FastPathRule = tuple[str, FastPathPredicate, float, FastPathSelector | None]


def _dlp_has_severity(target: str) -> FastPathPredicate:
    target_lc = target.lower()

    def _pred(event: SecurityEvent, dlp: DLPResult, policy: PolicyResult) -> bool:
        return any(f.severity.lower() == target_lc for f in dlp.findings)

    return _pred


def _dlp_select_severity(target: str) -> FastPathSelector:
    target_lc = target.lower()

    def _sel(dlp: DLPResult) -> tuple:
        return tuple(f for f in dlp.findings if f.severity.lower() == target_lc)

    return _sel


def _dlp_select_any(dlp: DLPResult) -> tuple:
    return tuple(dlp.findings)


DEFAULT_FAST_PATH_RULES: Final[tuple[FastPathRule, ...]] = (
    # Event-severity tier. No DLP selector --- these rules do not
    # depend on DLP confidence.
    ("severity_critical",
     lambda e, d, p: e.severity.lower() == "critical",
     1.00, None),
    ("severity_high",
     lambda e, d, p: e.severity.lower() == "high",
     0.75, None),
    ("severity_medium",
     lambda e, d, p: e.severity.lower() == "medium",
     0.40, None),
    # Policy denial. Hard signal; no DLP weighting.
    ("policy_denied",
     lambda e, d, p: p.allowed is False,
     1.00, None),
    # DLP tiers. Each rule "owns" a slice of the findings and scales
    # its contribution by the max confidence in that slice (SA-002).
    ("dlp_pii_critical",
     _dlp_has_severity("critical"),
     0.90,
     _dlp_select_severity("critical")),
    ("dlp_pii_high",
     _dlp_has_severity("high"),
     0.65,
     _dlp_select_severity("high")),
    ("dlp_pii_any",
     lambda e, d, p: d.has_findings,
     0.30,
     _dlp_select_any),
)


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #


class RiskEngine:
    """Stateful risk scorer keyed by ``event.actor_id``.

    The engine combines a deterministic fast-path sub-score with a
    sliding-window z-score per actor, attenuated by confidence (which
    rises with sample count). See spec section 5.2.1 for the
    authoritative contract.

    Parameters
    ----------
    window_size:
        Maximum number of past ``numeric_signal`` values kept per
        actor. Default 50.
    min_samples:
        Number of past samples required before the statistical
        sub-score becomes non-neutral. Default 5. Must satisfy
        ``1 <= min_samples <= window_size``.
    fast_path_rules:
        Ordered tuple of rules evaluated on every call. Defaults to
        :data:`DEFAULT_FAST_PATH_RULES`.
    det_weight, stat_weight:
        Weights blending the deterministic and statistical
        sub-scores. Must sum to 1.0. Default (0.6, 0.4).
    sigmoid_k:
        Steepness parameter for the z-to-probability sigmoid.
        Default 1.0.
    actor_allowlist, actor_blocklist:
        Optional iterables of actor IDs. Allowlisted actors
        short-circuit to ``risk_score = 0.0``; blocklisted actors
        short-circuit to ``risk_score = 1.0``.
    """

    def __init__(
        self,
        *,
        window_size: int = 50,
        min_samples: int = 5,
        fast_path_rules: Iterable[FastPathRule] = DEFAULT_FAST_PATH_RULES,
        det_weight: float = 0.6,
        stat_weight: float = 0.4,
        sigmoid_k: float = 1.0,
        actor_allowlist: Iterable[str] | None = None,
        actor_blocklist: Iterable[str] | None = None,
    ) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        if min_samples < 1 or min_samples > window_size:
            raise ValueError("min_samples must satisfy 1 <= min_samples <= window_size")
        if not math.isclose(det_weight + stat_weight, 1.0, abs_tol=1e-9):
            raise ValueError(
                f"det_weight + stat_weight must equal 1.0 "
                f"(got {det_weight} + {stat_weight})"
            )
        if det_weight < 0.0 or stat_weight < 0.0:
            raise ValueError("weights must be non-negative")

        self._window_size = window_size
        self._min_samples = min_samples
        self._fast_path_rules: tuple[FastPathRule, ...] = tuple(fast_path_rules)
        self._det_weight = det_weight
        self._stat_weight = stat_weight
        self._sigmoid_k = sigmoid_k
        self._allowlist = frozenset(actor_allowlist or ())
        self._blocklist = frozenset(actor_blocklist or ())

        # Per-actor sliding windows of numeric_signal values.
        self._windows: dict[str, deque[float]] = {}

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def score(
        self,
        event: SecurityEvent,
        dlp_result: DLPResult,
        policy_result: PolicyResult,
    ) -> RiskAssessment:
        """Score one security event.

        Async to compose with the SOCPipeline await-chain (canonical
        spec A1); internal work is CPU-bound stdlib. Returns a
        :class:`RiskAssessment` whose ``score`` is on the 0--100 scale
        consumed by the Decision Engine (canonical spec section 8).
        """
        # Allow/block list short-circuits take precedence over everything.
        if event.actor_id in self._allowlist:
            return self._make_assessment(
                event=event,
                deterministic_score=0.0,
                statistical_score=0.5,
                confidence=0.0,
                z_score=None,
                rule_hits=("actor_allowlist",),
                sample_count=len(self._windows.get(event.actor_id, ())),
                final_unit=0.0,
            )

        if event.actor_id in self._blocklist:
            sample_count = len(self._windows.get(event.actor_id, ()))
            assessment = self._make_assessment(
                event=event,
                deterministic_score=1.0,
                statistical_score=0.5,
                confidence=0.0,
                z_score=None,
                rule_hits=("actor_blocklist",),
                sample_count=sample_count,
                final_unit=1.0,
            )
            # Still update the window so future stats stay coherent.
            self._append_signal(event)
            return assessment

        deterministic_score, rule_hits = self._evaluate_fast_path(
            event, dlp_result, policy_result,
        )

        window = self._windows.get(event.actor_id, deque(maxlen=self._window_size))
        sample_count = len(window)
        statistical_score, z_score = self._statistical_score(
            window=window,
            value=event.numeric_signal,
        )

        confidence = min(1.0, sample_count / self._window_size)

        stat_blended = (
            statistical_score * confidence
            + 0.5 * (1.0 - confidence)
        )
        final_unit = _clamp_unit(
            self._det_weight * deterministic_score
            + self._stat_weight * stat_blended
        )

        assessment = self._make_assessment(
            event=event,
            deterministic_score=deterministic_score,
            statistical_score=statistical_score,
            confidence=confidence,
            z_score=z_score,
            rule_hits=rule_hits,
            sample_count=sample_count,
            final_unit=final_unit,
        )

        # Append AFTER scoring so the event being scored is not part
        # of its own baseline.
        self._append_signal(event)

        return assessment

    def reset(self) -> None:
        """Clear all per-actor sliding windows. Use in test setUp."""
        self._windows.clear()

    def reset_actor(self, actor_id: str) -> None:
        """Clear the sliding window for a single actor."""
        self._windows.pop(actor_id, None)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _evaluate_fast_path(
        self,
        event: SecurityEvent,
        dlp_result: DLPResult,
        policy_result: PolicyResult,
    ) -> tuple[float, tuple[str, ...]]:
        """Walk the fast-path rule table.

        Multiple rules may fire; the deterministic sub-score is the
        ``max()`` of all firing rules' contributions so a single
        severe rule is enough to escalate.

        Each rule's effective contribution is ``base_score`` scaled by
        the maximum ``DLPFinding.score`` among findings the rule's
        ``selector`` claims (canonical spec section 6.3 B3, SA-002).
        Rules without a selector contribute their ``base_score``
        unchanged.
        """
        best_score = 0.0
        hits: list[str] = []
        for rule_id, predicate, base_score, selector in self._fast_path_rules:
            try:
                fired = predicate(event, dlp_result, policy_result)
            except Exception:
                # A misbehaving predicate must not poison the whole
                # scoring path. Treat it as a non-match. Pipeline-level
                # error handling (canonical spec A3) belongs to the
                # SOCPipeline.
                fired = False
            if not fired:
                continue
            hits.append(rule_id)
            contribution = self._rule_contribution(
                base_score=base_score,
                selector=selector,
                dlp_result=dlp_result,
            )
            if contribution > best_score:
                best_score = contribution
        return best_score, tuple(hits)

    @staticmethod
    def _rule_contribution(
        *,
        base_score: float,
        selector: FastPathSelector | None,
        dlp_result: DLPResult,
    ) -> float:
        """Compute a single rule's effective contribution to the
        deterministic sub-score, applying SA-002 confidence weighting
        for rules that own a DLP slice."""
        if selector is None:
            return base_score
        owned = selector(dlp_result)
        if not owned:
            return base_score
        confidence = max(f.score for f in owned)
        return base_score * confidence

    def _statistical_score(
        self,
        *,
        window: deque[float],
        value: float,
    ) -> tuple[float, float | None]:
        """Compute the window-derived sub-score.

        Returns (statistical_score, z_score). z_score is None when
        the window has fewer than ``min_samples`` entries.
        """
        n = len(window)
        if n < self._min_samples:
            return 0.5, None

        mean = statistics.mean(window)
        stdev = statistics.pstdev(window)
        if stdev == 0.0:
            return 0.5, 0.0

        z = (value - mean) / stdev
        score = _sigmoid(z, self._sigmoid_k)
        return score, z

    def _append_signal(self, event: SecurityEvent) -> None:
        """Append ``event.numeric_signal`` to the actor's window,
        creating the window lazily."""
        window = self._windows.get(event.actor_id)
        if window is None:
            window = deque(maxlen=self._window_size)
            self._windows[event.actor_id] = window
        window.append(float(event.numeric_signal))

    def _make_assessment(
        self,
        *,
        event: SecurityEvent,
        deterministic_score: float,
        statistical_score: float,
        confidence: float,
        z_score: float | None,
        rule_hits: tuple[str, ...],
        sample_count: int,
        final_unit: float,
    ) -> RiskAssessment:
        # Canonical spec section 8 consumes ``risk.score`` on a 0--100
        # scale; rescale here so callers do not have to.
        return RiskAssessment(
            event_id=event.event_id,
            actor_id=event.actor_id,
            score=100.0 * final_unit,
            deterministic_score=deterministic_score,
            statistical_score=statistical_score,
            confidence=confidence,
            z_score=z_score,
            rule_hits=rule_hits,
            sample_count=sample_count,
            window_size=self._window_size,
        )


# --------------------------------------------------------------------------- #
# Math helpers
# --------------------------------------------------------------------------- #


def _clamp_unit(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _sigmoid(z: float, k: float) -> float:
    # math.exp overflows for very negative -k*z; clamp the exponent
    # to a safe range to keep the sigmoid numerically stable.
    arg = -k * z
    if arg > 700.0:
        return 0.0
    if arg < -700.0:
        return 1.0
    return 1.0 / (1.0 + math.exp(arg))

