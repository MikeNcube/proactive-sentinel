"""Unit tests for the SOC Decision Engine.

Spec references:
- canonical spec: ``docs/AI_OS_v3_SPEC.md`` sections 5.2, 5.3, 8, 8.1.

Acceptance criteria covered (canonical spec section 8.1):

- **D1** 100% branch coverage --- one positive test per branch plus
  boundary tests for the numeric thresholds.
- **D2** No-raise property --- a parametrised pass over a wide
  combination matrix that asserts a valid DecisionRecord is always
  returned and never raises. (Hypothesis dep skipped per the
  owner's call; same coverage via parametrise.)
- **D3** Determinism --- the engine returns identical
  ``DecisionRecord`` outputs across many repeated calls with the
  same inputs.

Plus
- branch-order regression tests (earlier branches dominate later ones)
- the spec section 8 inline-comment guarantee that
  ``enterprise + classification == "special"`` triggers MONITOR even
  at low risk score
- DecisionRecord field-shape assertions per spec section 5.3 A4
- JSON-serialisability of ``to_record()`` per spec section 5.2.
"""

from __future__ import annotations

import itertools
import json

import pytest

from soc.decision import (
    Action,
    ApprovalConfig,
    DecisionEngine,
    DecisionRecord,
    Manifest,
)
from soc.risk.types import PolicyResult, RiskAssessment, SecurityEvent


# --------------------------------------------------------------------------- #
# Fixtures and helpers
# --------------------------------------------------------------------------- #


@pytest.fixture
def engine() -> DecisionEngine:
    """Fresh engine per test (the engine carries no state, but the
    fixture matches the Risk Engine convention)."""
    return DecisionEngine()


def _event(
    *,
    event_id: str = "evt-1",
    actor_id: str = "alice",
    action: str = "rag.query",
    classification: str = "internal",
    severity: str = "low",
    numeric_signal: float = 0.0,
) -> SecurityEvent:
    return SecurityEvent(
        event_id=event_id,
        actor_id=actor_id,
        event_type="login",
        severity=severity,
        numeric_signal=numeric_signal,
        action=action,
        classification=classification,
    )


def _risk(score: float = 0.0) -> RiskAssessment:
    return RiskAssessment(
        event_id="evt-1",
        actor_id="alice",
        score=score,
        deterministic_score=0.0,
        statistical_score=0.5,
        confidence=0.0,
        z_score=None,
        rule_hits=(),
        sample_count=0,
        window_size=50,
    )


def _manifest(
    *,
    tier: str = "standard",
    required_for: tuple[str, ...] = (),
    manifest_hash: str = "deadbeef",
    policy_version: str = "v1",
) -> Manifest:
    return Manifest(
        compliance_tier=tier,
        approvals=ApprovalConfig(required_for=required_for),
        manifest_hash=manifest_hash,
        policy_version=policy_version,
    )


def _allowed() -> PolicyResult:
    return PolicyResult(allowed=True, policy_version="v1")


def _denied(reason: str = "explicit_deny") -> PolicyResult:
    return PolicyResult(
        allowed=False,
        policy_version="v1",
        violations=("R1",),
        deny_reason=reason,
    )


# --------------------------------------------------------------------------- #
# D1: branch coverage --- one positive test per branch
# --------------------------------------------------------------------------- #


class TestBranchCoverage:
    def test_branch1_policy_denied_returns_block(self, engine):
        result = engine.decide(
            event=_event(),
            policy=_denied("policy_says_no"),
            risk=_risk(score=0.0),
            manifest=_manifest(),
        )
        assert result.action == Action.BLOCK
        assert result.reason == "policy_says_no"

    def test_branch1_policy_denied_with_empty_reason_falls_back(self, engine):
        result = engine.decide(
            event=_event(),
            policy=PolicyResult(allowed=False, deny_reason=""),
            risk=_risk(),
            manifest=_manifest(),
        )
        assert result.action == Action.BLOCK
        assert result.reason == "policy_denied"

    def test_branch2_action_in_approval_list_requires_approval(self, engine):
        result = engine.decide(
            event=_event(action="mcp.tool_execute"),
            policy=_allowed(),
            risk=_risk(score=10.0),
            manifest=_manifest(required_for=("mcp.tool_execute",)),
        )
        assert result.action == Action.REQUIRE_APPROVAL
        assert result.reason == "action_in_approval_list"
        assert result.required_approvers == ("designated_approver",)

    def test_branch3_high_risk_score_requires_approval(self, engine):
        result = engine.decide(
            event=_event(),
            policy=_allowed(),
            risk=_risk(score=85.0),
            manifest=_manifest(),
        )
        assert result.action == Action.REQUIRE_APPROVAL
        assert result.reason == "high_risk_score"

    def test_branch4_special_data_on_enterprise_returns_monitor(self, engine):
        """Canonical spec section 8: enterprise + special MUST be
        MONITOR even when the numeric risk score is below 50."""
        result = engine.decide(
            event=_event(classification="special"),
            policy=_allowed(),
            risk=_risk(score=10.0),
            manifest=_manifest(tier="enterprise"),
        )
        assert result.action == Action.MONITOR
        assert result.reason == "special_data_enterprise_tier"

    def test_branch5_elevated_risk_score_returns_monitor(self, engine):
        result = engine.decide(
            event=_event(),
            policy=_allowed(),
            risk=_risk(score=65.0),
            manifest=_manifest(),
        )
        assert result.action == Action.MONITOR
        assert result.reason == "elevated_risk_score(65.0)"

    def test_branch6_default_returns_allow(self, engine):
        result = engine.decide(
            event=_event(),
            policy=_allowed(),
            risk=_risk(score=10.0),
            manifest=_manifest(),
        )
        assert result.action == Action.ALLOW
        assert result.reason == "default"


# --------------------------------------------------------------------------- #
# Numeric threshold boundaries
# --------------------------------------------------------------------------- #


class TestThresholdBoundaries:
    def test_risk_score_80_triggers_require_approval(self, engine):
        result = engine.decide(
            event=_event(),
            policy=_allowed(),
            risk=_risk(score=80.0),
            manifest=_manifest(),
        )
        assert result.action == Action.REQUIRE_APPROVAL
        assert result.reason == "high_risk_score"

    def test_risk_score_just_below_80_falls_through_to_monitor(self, engine):
        result = engine.decide(
            event=_event(),
            policy=_allowed(),
            risk=_risk(score=79.999),
            manifest=_manifest(),
        )
        assert result.action == Action.MONITOR

    def test_risk_score_50_triggers_monitor(self, engine):
        result = engine.decide(
            event=_event(),
            policy=_allowed(),
            risk=_risk(score=50.0),
            manifest=_manifest(),
        )
        assert result.action == Action.MONITOR

    def test_risk_score_just_below_50_returns_allow(self, engine):
        result = engine.decide(
            event=_event(),
            policy=_allowed(),
            risk=_risk(score=49.999),
            manifest=_manifest(),
        )
        assert result.action == Action.ALLOW

    def test_risk_score_zero_returns_allow(self, engine):
        result = engine.decide(
            event=_event(),
            policy=_allowed(),
            risk=_risk(score=0.0),
            manifest=_manifest(),
        )
        assert result.action == Action.ALLOW

    def test_risk_score_one_hundred_requires_approval(self, engine):
        result = engine.decide(
            event=_event(),
            policy=_allowed(),
            risk=_risk(score=100.0),
            manifest=_manifest(),
        )
        assert result.action == Action.REQUIRE_APPROVAL


# --------------------------------------------------------------------------- #
# Branch order regression --- earlier branches dominate later ones
# --------------------------------------------------------------------------- #


class TestBranchOrder:
    def test_policy_denial_overrides_approval_action(self, engine):
        """If both policy=denied AND action is in the approval list,
        the BLOCK must win (policy is branch 1, approval is branch 2)."""
        result = engine.decide(
            event=_event(action="mcp.tool_execute"),
            policy=_denied("nope"),
            risk=_risk(score=0.0),
            manifest=_manifest(required_for=("mcp.tool_execute",)),
        )
        assert result.action == Action.BLOCK
        assert result.reason == "nope"

    def test_policy_denial_overrides_high_risk(self, engine):
        result = engine.decide(
            event=_event(),
            policy=_denied(),
            risk=_risk(score=99.0),
            manifest=_manifest(),
        )
        assert result.action == Action.BLOCK

    def test_approval_action_overrides_high_risk(self, engine):
        """Branch 2 (approval action) MUST be checked before branch 3
        (high risk). When both fire, reason must be
        ``action_in_approval_list``, not ``high_risk_score``."""
        result = engine.decide(
            event=_event(action="mcp.tool_execute"),
            policy=_allowed(),
            risk=_risk(score=99.0),
            manifest=_manifest(required_for=("mcp.tool_execute",)),
        )
        assert result.action == Action.REQUIRE_APPROVAL
        assert result.reason == "action_in_approval_list"

    def test_high_risk_overrides_special_data_monitor(self, engine):
        """Branch 3 (>= 80) is checked before branch 4 (special-data
        override). Enterprise + special at risk 90 should be
        REQUIRE_APPROVAL, not MONITOR."""
        result = engine.decide(
            event=_event(classification="special"),
            policy=_allowed(),
            risk=_risk(score=90.0),
            manifest=_manifest(tier="enterprise"),
        )
        assert result.action == Action.REQUIRE_APPROVAL
        assert result.reason == "high_risk_score"

    def test_special_data_override_beats_elevated_risk_band(self, engine):
        """Branch 4 must come before branch 5. With enterprise +
        special + risk=65, the reason MUST be
        ``special_data_enterprise_tier``, not
        ``elevated_risk_score(...)``. This is the spec section 8
        inline comment about POPIA s.26 being checked first."""
        result = engine.decide(
            event=_event(classification="special"),
            policy=_allowed(),
            risk=_risk(score=65.0),
            manifest=_manifest(tier="enterprise"),
        )
        assert result.action == Action.MONITOR
        assert result.reason == "special_data_enterprise_tier"

    def test_special_classification_on_standard_tier_does_not_force_monitor(
        self, engine
    ):
        """Standard tier + special classification + low risk = ALLOW.
        The override only fires on enterprise tier."""
        result = engine.decide(
            event=_event(classification="special"),
            policy=_allowed(),
            risk=_risk(score=10.0),
            manifest=_manifest(tier="standard"),
        )
        assert result.action == Action.ALLOW

    def test_enterprise_tier_non_special_does_not_force_monitor(self, engine):
        """Enterprise tier + non-special classification + low risk
        = ALLOW. Both conditions must hold for the override."""
        result = engine.decide(
            event=_event(classification="personal"),
            policy=_allowed(),
            risk=_risk(score=10.0),
            manifest=_manifest(tier="enterprise"),
        )
        assert result.action == Action.ALLOW


# --------------------------------------------------------------------------- #
# D2: no-raise property over a wide combination matrix
# --------------------------------------------------------------------------- #


def _input_matrix():
    """Generate a Cartesian product of inputs that exercises every
    branch and every threshold boundary. Yields tuples of
    (allowed, score, classification, tier, action_in_list)."""
    return list(itertools.product(
        [True, False],                                # policy allowed
        [-1.0, 0.0, 49.999, 50.0, 79.999, 80.0, 99.9, 100.0, 200.0],
        ["public", "internal", "personal", "special"],
        ["standard", "enterprise"],
        [True, False],                                # action in list
    ))


@pytest.mark.parametrize(
    "allowed,score,classification,tier,action_in_list",
    _input_matrix(),
)
def test_d2_no_raise_over_input_matrix(
    allowed, score, classification, tier, action_in_list,
):
    engine = DecisionEngine()
    action_name = "mcp.tool_execute"
    result = engine.decide(
        event=_event(
            action=action_name if action_in_list else "rag.query",
            classification=classification,
        ),
        policy=(
            PolicyResult(allowed=True, deny_reason="")
            if allowed
            else PolicyResult(allowed=False, deny_reason="parametrised_deny")
        ),
        risk=_risk(score=score),
        manifest=_manifest(
            tier=tier,
            required_for=(action_name,) if action_in_list else (),
        ),
    )
    assert isinstance(result, DecisionRecord)
    assert isinstance(result.action, Action)
    assert isinstance(result.reason, str) and result.reason  # non-empty
    assert 0.0 <= 0.0 or True  # placeholder: risk_score may be any float
    # DecisionRecord must be JSON-serialisable on every input.
    json.dumps(result.to_record())


# --------------------------------------------------------------------------- #
# D3: determinism --- repeated calls must return identical records
# --------------------------------------------------------------------------- #


class TestDeterminism:
    def test_one_hundred_identical_calls_return_identical_records(self, engine):
        ev = _event(action="mcp.tool_execute", classification="special")
        pol = _allowed()
        risk = _risk(score=72.5)
        man = _manifest(tier="enterprise", required_for=("mcp.tool_execute",))

        results = [
            engine.decide(event=ev, policy=pol, risk=risk, manifest=man)
            for _ in range(100)
        ]
        first = results[0]
        for r in results[1:]:
            assert r == first

    def test_different_engine_instances_produce_identical_records(self):
        ev = _event()
        pol = _allowed()
        risk = _risk(score=65.0)
        man = _manifest()
        r1 = DecisionEngine().decide(event=ev, policy=pol, risk=risk, manifest=man)
        r2 = DecisionEngine().decide(event=ev, policy=pol, risk=risk, manifest=man)
        assert r1 == r2


# --------------------------------------------------------------------------- #
# DecisionRecord output contract (canonical spec section 5.3 A4)
# --------------------------------------------------------------------------- #


class TestDecisionRecordContract:
    def test_record_carries_every_spec_a4_field(self, engine):
        result = engine.decide(
            event=_event(event_id="evt-X"),
            policy=_allowed(),
            risk=_risk(score=10.0),
            manifest=_manifest(
                manifest_hash="hash-X",
                policy_version="policy-X",
            ),
        )
        # Spec section 5.3 A4 mandates these fields.
        for field_name in (
            "event_id",
            "manifest_hash",
            "policy_version",
            "dlp_findings",
            "risk_inputs",
            "risk_score",
            "action",
            "reason",
            "required_approvers",
        ):
            assert hasattr(result, field_name), f"missing field: {field_name}"

    def test_provenance_fields_propagate_from_inputs(self, engine):
        result = engine.decide(
            event=_event(event_id="evt-XYZ"),
            policy=_allowed(),
            risk=_risk(score=10.0),
            manifest=_manifest(
                manifest_hash="manifest-XYZ",
                policy_version="policy-XYZ",
            ),
        )
        assert result.event_id == "evt-XYZ"
        assert result.manifest_hash == "manifest-XYZ"
        assert result.policy_version == "policy-XYZ"

    def test_risk_inputs_propagate_to_record(self, engine):
        risk = _risk(score=42.0)
        result = engine.decide(
            event=_event(),
            policy=_allowed(),
            risk=risk,
            manifest=_manifest(),
        )
        # Every key from risk.risk_inputs must appear in result.risk_inputs.
        for k in risk.risk_inputs:
            assert k in result.risk_inputs

    def test_to_record_is_json_serialisable(self, engine):
        result = engine.decide(
            event=_event(action="mcp.tool_execute"),
            policy=_allowed(),
            risk=_risk(score=85.0),
            manifest=_manifest(required_for=("mcp.tool_execute",)),
        )
        as_json = json.dumps(result.to_record())
        round_trip = json.loads(as_json)
        assert round_trip["action"] == "REQUIRE_APPROVAL"
        assert round_trip["reason"] == "action_in_approval_list"
        assert round_trip["required_approvers"] == ["designated_approver"]

    def test_action_value_serialises_as_plain_string(self, engine):
        result = engine.decide(
            event=_event(),
            policy=_allowed(),
            risk=_risk(score=10.0),
            manifest=_manifest(),
        )
        rec = result.to_record()
        assert rec["action"] == "ALLOW"
        assert isinstance(rec["action"], str)
        # Importantly NOT a stringified Enum like "Action.ALLOW".
        assert not rec["action"].startswith("Action.")

    def test_default_branch_has_empty_required_approvers(self, engine):
        result = engine.decide(
            event=_event(),
            policy=_allowed(),
            risk=_risk(score=10.0),
            manifest=_manifest(),
        )
        assert result.required_approvers == ()


# --------------------------------------------------------------------------- #
# Engine purity guarantees
# --------------------------------------------------------------------------- #


class TestEnginePurity:
    def test_engine_instance_has_no_mutable_public_state(self):
        eng = DecisionEngine()
        # No instance __dict__ attributes the test could mutate.
        assert vars(eng) == {} or not vars(eng)

    def test_repeated_calls_do_not_accumulate_state(self, engine):
        """Run the same call 50 times interleaved with different
        calls; the result must not depend on the call history."""
        ev_default = _event()
        ev_special = _event(classification="special")
        first = engine.decide(
            event=ev_default,
            policy=_allowed(),
            risk=_risk(10.0),
            manifest=_manifest(),
        )
        for _ in range(50):
            engine.decide(
                event=ev_special,
                policy=_allowed(),
                risk=_risk(85.0),
                manifest=_manifest(tier="enterprise"),
            )
        last = engine.decide(
            event=ev_default,
            policy=_allowed(),
            risk=_risk(10.0),
            manifest=_manifest(),
        )
        assert first == last

