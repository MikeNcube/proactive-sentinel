"""Unit tests for the SOC Risk Engine.

Spec references:
- canonical spec: ``docs/AI_OS_v3_SPEC.md`` (sections 4, 5.2, 5.3, 6.3, 8)
- sub-contract:   ``docs/architecture/risk-engine.md``

Determinism note (REQ-RE-1)
---------------------------
The Risk Engine maintains a per-actor sliding window of recent
``numeric_signal`` values. To keep tests order-independent, every
test receives a brand-new ``RiskEngine`` via the ``engine`` fixture
below (function scope is the pytest default). No test relies on
state set up by another test.
"""

from __future__ import annotations

import asyncio
import statistics

import pytest

from soc.risk import (
    DEFAULT_FAST_PATH_RULES,
    DLPFinding,
    DLPResult,
    PolicyResult,
    RiskAssessment,
    RiskEngine,
    SecurityEvent,
)


# --------------------------------------------------------------------------- #
# Fixtures and helpers
# --------------------------------------------------------------------------- #


@pytest.fixture
def engine() -> RiskEngine:
    """Fresh engine per test --- guarantees deterministic tests."""
    return RiskEngine()


def _run(coro):
    """Tiny adapter so we do not need pytest-asyncio."""
    return asyncio.run(coro)


def _event(
    *,
    event_id: str = "evt-1",
    actor_id: str = "alice",
    severity: str = "low",
    numeric_signal: float = 0.0,
    event_type: str = "login",
) -> SecurityEvent:
    return SecurityEvent(
        event_id=event_id,
        actor_id=actor_id,
        event_type=event_type,
        severity=severity,
        numeric_signal=numeric_signal,
    )


def _allowed_policy() -> PolicyResult:
    return PolicyResult(allowed=True, policy_version="v1")


def _no_dlp() -> DLPResult:
    return DLPResult()


# --------------------------------------------------------------------------- #
# Construction validation
# --------------------------------------------------------------------------- #


class TestConstruction:
    def test_default_construction_succeeds(self):
        eng = RiskEngine()
        assert isinstance(eng, RiskEngine)

    def test_rejects_zero_window_size(self):
        with pytest.raises(ValueError, match="window_size"):
            RiskEngine(window_size=0)

    def test_rejects_min_samples_greater_than_window(self):
        with pytest.raises(ValueError, match="min_samples"):
            RiskEngine(window_size=5, min_samples=10)

    def test_rejects_min_samples_zero(self):
        with pytest.raises(ValueError, match="min_samples"):
            RiskEngine(min_samples=0)

    def test_rejects_weights_that_do_not_sum_to_one(self):
        with pytest.raises(ValueError, match="weight"):
            RiskEngine(det_weight=0.7, stat_weight=0.4)

    def test_rejects_negative_weights(self):
        with pytest.raises(ValueError, match="weight"):
            RiskEngine(det_weight=-0.1, stat_weight=1.1)

    def test_accepts_custom_balanced_weights(self):
        eng = RiskEngine(det_weight=0.5, stat_weight=0.5)
        assert isinstance(eng, RiskEngine)


# --------------------------------------------------------------------------- #
# Fast-path rules (REQ-RE-2)
# --------------------------------------------------------------------------- #


class TestFastPathRules:
    def test_critical_severity_pins_deterministic_to_one(self, engine):
        ev = _event(severity="critical", numeric_signal=0.0)
        result = _run(engine.score(ev, _no_dlp(), _allowed_policy()))
        assert result.deterministic_score == 1.0
        assert "severity_critical" in result.rule_hits

    def test_high_severity_pins_deterministic_to_0_75(self, engine):
        ev = _event(severity="high")
        result = _run(engine.score(ev, _no_dlp(), _allowed_policy()))
        assert result.deterministic_score == pytest.approx(0.75)
        assert "severity_high" in result.rule_hits

    def test_medium_severity_pins_deterministic_to_0_40(self, engine):
        ev = _event(severity="medium")
        result = _run(engine.score(ev, _no_dlp(), _allowed_policy()))
        assert result.deterministic_score == pytest.approx(0.40)
        assert "severity_medium" in result.rule_hits

    def test_low_severity_does_not_trigger_severity_rules(self, engine):
        ev = _event(severity="low")
        result = _run(engine.score(ev, _no_dlp(), _allowed_policy()))
        assert result.deterministic_score == 0.0
        assert not any(h.startswith("severity_") for h in result.rule_hits)

    def test_policy_denied_pins_deterministic_to_one(self, engine):
        ev = _event(severity="low")
        denied = PolicyResult(allowed=False, policy_version="v1", violations=("R1",))
        result = _run(engine.score(ev, _no_dlp(), denied))
        assert result.deterministic_score == 1.0
        assert "policy_denied" in result.rule_hits

    def test_dlp_critical_finding_at_full_confidence(self, engine):
        """At DLPFinding.score == 1.0, the rule contributes its full base."""
        dlp = DLPResult(findings=(DLPFinding("ZA_ID", "critical", 1.0),))
        result = _run(engine.score(_event(), dlp, _allowed_policy()))
        assert result.deterministic_score == pytest.approx(0.90)
        assert "dlp_pii_critical" in result.rule_hits
        assert "dlp_pii_any" in result.rule_hits

    def test_dlp_high_finding_at_full_confidence(self, engine):
        dlp = DLPResult(findings=(DLPFinding("EMAIL", "high", 1.0),))
        result = _run(engine.score(_event(), dlp, _allowed_policy()))
        assert result.deterministic_score == pytest.approx(0.65)
        assert "dlp_pii_high" in result.rule_hits

    def test_dlp_low_finding_only_hits_any_rule(self, engine):
        dlp = DLPResult(findings=(DLPFinding("PHONE", "low", 1.0),))
        result = _run(engine.score(_event(), dlp, _allowed_policy()))
        assert result.deterministic_score == pytest.approx(0.30)
        assert "dlp_pii_any" in result.rule_hits
        assert "dlp_pii_critical" not in result.rule_hits
        assert "dlp_pii_high" not in result.rule_hits

    def test_multiple_rules_fire_score_takes_max(self, engine):
        """High severity (0.75) AND dlp_critical @1.0 (0.90) --> 0.90."""
        ev = _event(severity="high")
        dlp = DLPResult(findings=(DLPFinding("ZA_ID", "critical", 1.0),))
        result = _run(engine.score(ev, dlp, _allowed_policy()))
        assert result.deterministic_score == pytest.approx(0.90)
        assert {"severity_high", "dlp_pii_critical", "dlp_pii_any"}.issubset(
            set(result.rule_hits)
        )

    def test_predicate_exception_is_swallowed(self, engine):
        """A misbehaving custom rule must not crash the whole score."""

        def boom(e, d, p):
            raise RuntimeError("intentional")

        eng = RiskEngine(
            fast_path_rules=(
                ("buggy_rule", boom, 0.5, None),
                *DEFAULT_FAST_PATH_RULES,
            )
        )
        ev = _event(severity="critical")
        result = _run(eng.score(ev, _no_dlp(), _allowed_policy()))
        assert "buggy_rule" not in result.rule_hits
        assert result.deterministic_score == 1.0


# --------------------------------------------------------------------------- #
# SA-002: DLP confidence weighting
# --------------------------------------------------------------------------- #


class TestSA002ConfidenceWeighting:
    """Canonical spec section 6.3 B3 (SA-002): the DLP finding's own
    confidence affects the risk engine's weighting of the finding."""

    def test_critical_finding_at_half_confidence_halves_contribution(self, engine):
        dlp = DLPResult(findings=(DLPFinding("ZA_ID", "critical", 0.5),))
        result = _run(engine.score(_event(), dlp, _allowed_policy()))
        # base 0.90 * confidence 0.5 = 0.45
        assert result.deterministic_score == pytest.approx(0.45)

    def test_high_finding_scales_linearly_with_confidence(self, engine):
        dlp = DLPResult(findings=(DLPFinding("EMAIL", "high", 0.4),))
        result = _run(engine.score(_event(), dlp, _allowed_policy()))
        # base 0.65 * 0.4 = 0.26 ... but the any-rule fires too:
        # base 0.30 * 0.4 = 0.12. max(0.26, 0.12) = 0.26
        assert result.deterministic_score == pytest.approx(0.26)

    def test_max_confidence_among_owned_findings_is_used(self, engine):
        """When multiple findings of the same severity tier exist, the
        rule takes the MAX of their confidences --- not the average,
        not the sum --- so a single high-confidence hit cannot be
        diluted by low-confidence neighbours."""
        dlp = DLPResult(findings=(
            DLPFinding("PHONE", "critical", 0.20),
            DLPFinding("ZA_ID", "critical", 0.90),
            DLPFinding("EMAIL", "critical", 0.10),
        ))
        result = _run(engine.score(_event(), dlp, _allowed_policy()))
        # base 0.90 * max(0.2, 0.9, 0.1) = 0.81
        assert result.deterministic_score == pytest.approx(0.81)

    def test_low_confidence_finding_is_not_suppressed(self, engine):
        """SA-002: a low-confidence hit must not be suppressed.
        Even at confidence 0.05 the engine still contributes
        SOMETHING, not zero."""
        dlp = DLPResult(findings=(DLPFinding("PHONE", "critical", 0.05),))
        result = _run(engine.score(_event(), dlp, _allowed_policy()))
        # 0.90 * 0.05 = 0.045 - tiny but non-zero
        assert result.deterministic_score == pytest.approx(0.045)
        assert result.deterministic_score > 0.0
        assert "dlp_pii_critical" in result.rule_hits

    def test_dlp_confidence_does_not_affect_severity_rules(self, engine):
        """severity_critical does not own DLP findings, so its
        contribution is base_score regardless of any DLP confidence."""
        dlp = DLPResult(findings=(DLPFinding("PHONE", "low", 0.05),))
        ev = _event(severity="critical")
        result = _run(engine.score(ev, dlp, _allowed_policy()))
        # severity_critical = 1.00 wins over the tiny DLP contribution.
        assert result.deterministic_score == 1.0

    def test_dlp_confidence_does_not_affect_policy_rule(self, engine):
        """policy_denied is a hard signal --- not weighted by DLP."""
        denied = PolicyResult(allowed=False)
        dlp = DLPResult(findings=(DLPFinding("EMAIL", "low", 0.05),))
        result = _run(engine.score(_event(), dlp, denied))
        assert result.deterministic_score == 1.0


# --------------------------------------------------------------------------- #
# Sliding-window z-score (REQ-RE-3)
# --------------------------------------------------------------------------- #


class TestSlidingWindow:
    def test_neutral_score_before_min_samples(self, engine):
        for i in range(4):  # default min_samples = 5
            ev = _event(event_id=f"e{i}", numeric_signal=float(i))
            result = _run(engine.score(ev, _no_dlp(), _allowed_policy()))
            assert result.statistical_score == 0.5
            assert result.z_score is None
            assert result.sample_count == i

    def test_z_score_appears_once_min_samples_reached(self, engine):
        for i in range(6):
            ev = _event(event_id=f"e{i}", numeric_signal=float(i))
            result = _run(engine.score(ev, _no_dlp(), _allowed_policy()))
        # On the 6th call (i=5), window had 5 samples [0,1,2,3,4]
        # before scoring, so z_score should be defined.
        assert result.z_score is not None
        assert result.sample_count == 5

    def test_z_score_arithmetic_matches_statistics_module(self, engine):
        values = [10.0, 12.0, 11.0, 13.0, 10.5, 11.5]
        last_assessment = None
        for i, v in enumerate(values):
            ev = _event(event_id=f"e{i}", numeric_signal=v)
            last_assessment = _run(engine.score(ev, _no_dlp(), _allowed_policy()))

        baseline = values[:-1]
        expected_mean = statistics.mean(baseline)
        expected_stdev = statistics.pstdev(baseline)
        expected_z = (values[-1] - expected_mean) / expected_stdev

        assert last_assessment.z_score == pytest.approx(expected_z, rel=1e-9)

    def test_constant_window_yields_zero_z(self, engine):
        for i in range(6):
            ev = _event(event_id=f"e{i}", numeric_signal=42.0)
            result = _run(engine.score(ev, _no_dlp(), _allowed_policy()))
        assert result.z_score == 0.0
        assert result.statistical_score == 0.5

    def test_window_evicts_oldest_at_maxlen(self):
        eng = RiskEngine(window_size=3, min_samples=2)
        for i, v in enumerate([100.0, 100.0, 100.0]):
            _run(eng.score(_event(event_id=f"a{i}", numeric_signal=v),
                           _no_dlp(), _allowed_policy()))

        # Burst of zero-valued events evicts the 100s; eventually
        # the window holds [0,0,0] -> stdev 0 -> z = 0.
        for i in range(5):
            result = _run(eng.score(
                _event(event_id=f"b{i}", numeric_signal=0.0),
                _no_dlp(),
                _allowed_policy(),
            ))
            assert result.window_size == 3

        assert result.z_score == 0.0


# --------------------------------------------------------------------------- #
# Per-actor isolation
# --------------------------------------------------------------------------- #


class TestPerActorIsolation:
    def test_actors_have_independent_windows(self, engine):
        for i in range(6):
            _run(engine.score(
                _event(event_id=f"a{i}", actor_id="alice", numeric_signal=10.0),
                _no_dlp(),
                _allowed_policy(),
            ))

        # Bob's first event sees neutral stats --- no window yet.
        bob = _run(engine.score(
            _event(event_id="b1", actor_id="bob", numeric_signal=10000.0),
            _no_dlp(),
            _allowed_policy(),
        ))
        assert bob.statistical_score == 0.5
        assert bob.z_score is None
        assert bob.sample_count == 0

    def test_reset_actor_clears_only_that_actor(self, engine):
        for i in range(6):
            _run(engine.score(
                _event(event_id=f"a{i}", actor_id="alice", numeric_signal=1.0),
                _no_dlp(),
                _allowed_policy(),
            ))
            _run(engine.score(
                _event(event_id=f"b{i}", actor_id="bob", numeric_signal=2.0),
                _no_dlp(),
                _allowed_policy(),
            ))

        engine.reset_actor("alice")

        alice = _run(engine.score(
            _event(event_id="ax", actor_id="alice", numeric_signal=1.0),
            _no_dlp(),
            _allowed_policy(),
        ))
        bob = _run(engine.score(
            _event(event_id="bx", actor_id="bob", numeric_signal=2.0),
            _no_dlp(),
            _allowed_policy(),
        ))
        assert alice.sample_count == 0
        assert bob.sample_count == 6  # bob untouched

    def test_reset_clears_all_actors(self, engine):
        for i in range(6):
            _run(engine.score(
                _event(event_id=f"a{i}", actor_id="alice", numeric_signal=1.0),
                _no_dlp(),
                _allowed_policy(),
            ))
            _run(engine.score(
                _event(event_id=f"b{i}", actor_id="bob", numeric_signal=2.0),
                _no_dlp(),
                _allowed_policy(),
            ))

        engine.reset()

        alice = _run(engine.score(
            _event(event_id="ax", actor_id="alice", numeric_signal=1.0),
            _no_dlp(),
            _allowed_policy(),
        ))
        bob = _run(engine.score(
            _event(event_id="bx", actor_id="bob", numeric_signal=2.0),
            _no_dlp(),
            _allowed_policy(),
        ))
        assert alice.sample_count == 0
        assert bob.sample_count == 0


# --------------------------------------------------------------------------- #
# Confidence weighting (REQ-RE-4 / engine confidence, distinct from SA-002)
# --------------------------------------------------------------------------- #


class TestEngineConfidence:
    def test_confidence_starts_at_zero(self, engine):
        result = _run(engine.score(_event(), _no_dlp(), _allowed_policy()))
        assert result.confidence == 0.0

    def test_confidence_grows_linearly_with_sample_count(self):
        eng = RiskEngine(window_size=10, min_samples=2)
        confidences: list[float] = []
        for i in range(10):
            result = _run(eng.score(
                _event(event_id=f"e{i}", numeric_signal=1.0),
                _no_dlp(),
                _allowed_policy(),
            ))
            confidences.append(result.confidence)
        # confidence at step i is i / window_size (samples BEFORE event)
        assert confidences == [pytest.approx(i / 10) for i in range(10)]

    def test_confidence_caps_at_one(self):
        eng = RiskEngine(window_size=5, min_samples=2)
        for i in range(20):
            result = _run(eng.score(
                _event(event_id=f"e{i}", numeric_signal=1.0),
                _no_dlp(),
                _allowed_policy(),
            ))
        assert result.confidence == 1.0

    def test_low_confidence_attenuates_statistical_contribution(self):
        """With confidence 0 (fresh engine), the statistical
        contribution collapses to 0.5 (neutral). Final score on the
        0-100 scale: 100 * (0.6*0 + 0.4*0.5) = 20."""
        eng = RiskEngine(det_weight=0.6, stat_weight=0.4)
        result = _run(eng.score(_event(), _no_dlp(), _allowed_policy()))
        assert result.score == pytest.approx(20.0)

    def test_final_score_blends_weights_when_confidence_is_full(self):
        """After window fills with constant samples, stat=0.5 (stdev=0)
        and conf=1.0. A critical event then scores
        100 * (0.6*1.0 + 0.4*0.5) = 80."""
        eng = RiskEngine(
            window_size=5, min_samples=2,
            det_weight=0.6, stat_weight=0.4,
        )
        for i in range(5):
            _run(eng.score(
                _event(event_id=f"warm{i}", numeric_signal=7.0),
                _no_dlp(),
                _allowed_policy(),
            ))
        result = _run(eng.score(
            _event(event_id="x", severity="critical", numeric_signal=7.0),
            _no_dlp(),
            _allowed_policy(),
        ))
        assert result.confidence == 1.0
        assert result.score == pytest.approx(80.0)


# --------------------------------------------------------------------------- #
# Allowlist / blocklist
# --------------------------------------------------------------------------- #


class TestAllowAndBlockLists:
    def test_allowlisted_actor_short_circuits_to_zero(self):
        eng = RiskEngine(actor_allowlist={"trusted_bot"})
        dlp = DLPResult(findings=(DLPFinding("ZA_ID", "critical", 1.0),))
        result = _run(eng.score(
            _event(actor_id="trusted_bot", severity="critical"),
            dlp,
            PolicyResult(allowed=False),
        ))
        assert result.score == 0.0
        assert result.rule_hits == ("actor_allowlist",)

    def test_blocklisted_actor_short_circuits_to_one_hundred(self):
        eng = RiskEngine(actor_blocklist={"banned"})
        result = _run(eng.score(
            _event(actor_id="banned", severity="low"),
            _no_dlp(),
            _allowed_policy(),
        ))
        assert result.score == 100.0
        assert result.rule_hits == ("actor_blocklist",)


# --------------------------------------------------------------------------- #
# Output contract
# --------------------------------------------------------------------------- #


class TestAssessmentOutput:
    def test_returns_risk_assessment_instance(self, engine):
        result = _run(engine.score(_event(), _no_dlp(), _allowed_policy()))
        assert isinstance(result, RiskAssessment)

    def test_score_is_in_0_to_100_range(self, engine):
        """Canonical spec section 8 consumes risk.score on a 0-100
        scale. Verify the engine never emits outside that range
        even when every input is at its extreme."""
        ev = _event(severity="critical")
        dlp = DLPResult(findings=(DLPFinding("ZA_ID", "critical", 1.0),))
        result = _run(engine.score(ev, dlp, PolicyResult(allowed=False)))
        assert 0.0 <= result.score <= 100.0

    def test_assessment_exposes_score_attribute_per_spec_section_8(self, engine):
        """Canonical spec section 8 reads ``risk.score`` (not
        ``risk.risk_score``). The output type must expose the right
        attribute name so the Decision Engine can be implemented
        verbatim from the spec."""
        result = _run(engine.score(_event(), _no_dlp(), _allowed_policy()))
        assert hasattr(result, "score")
        assert isinstance(result.score, float)

    def test_risk_inputs_payload_shape(self, engine):
        result = _run(engine.score(
            _event(severity="medium"),
            _no_dlp(),
            _allowed_policy(),
        ))
        inputs = result.risk_inputs
        for key in (
            "deterministic_score",
            "statistical_score",
            "confidence",
            "z_score",
            "rule_hits",
            "sample_count",
            "window_size",
        ):
            assert key in inputs

    def test_assessment_carries_event_and_actor_ids(self, engine):
        result = _run(engine.score(
            _event(event_id="abc-123", actor_id="charlie"),
            _no_dlp(),
            _allowed_policy(),
        ))
        assert result.event_id == "abc-123"
        assert result.actor_id == "charlie"


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #


class TestDeterminism:
    def test_two_fresh_engines_produce_identical_sequences(self):
        """REQ-RE-1: same construction params + same input sequence
        from a fresh state --- identical output sequence."""
        events = [
            _event(event_id=f"e{i}", numeric_signal=float(i % 7))
            for i in range(15)
        ]

        def run_sequence() -> list[float]:
            eng = RiskEngine()
            return [
                _run(eng.score(e, _no_dlp(), _allowed_policy())).score
                for e in events
            ]

        assert run_sequence() == run_sequence()

    def test_reset_restores_to_fresh_state(self, engine):
        events = [
            _event(event_id=f"e{i}", numeric_signal=float(i))
            for i in range(8)
        ]
        first_pass = [
            _run(engine.score(e, _no_dlp(), _allowed_policy())).score
            for e in events
        ]
        engine.reset()
        second_pass = [
            _run(engine.score(e, _no_dlp(), _allowed_policy())).score
            for e in events
        ]
        assert first_pass == second_pass

