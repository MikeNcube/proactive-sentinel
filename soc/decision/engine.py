"""Decision Engine implementation.

Pure function over (event, policy, risk, manifest) -> DecisionRecord
per canonical spec section 8. The branch order is fixed by the spec
and MUST NOT be reordered:

    1. policy denied                          --> BLOCK
    2. event.action in manifest.approvals.required_for
                                              --> REQUIRE_APPROVAL
    3. risk.score >= 80                       --> REQUIRE_APPROVAL
    4. enterprise tier AND classification == "special"
                                              --> MONITOR
                                              (POPIA s.26 safeguard;
                                              must come before the
                                              >= 50 band)
    5. risk.score >= 50                       --> MONITOR
    6. default                                --> ALLOW

Acceptance criteria (canonical spec section 8.1):

    D1. 100% branch coverage in unit tests.
    D2. For any input, the function returns a valid DecisionRecord
        and never raises.
    D3. Deterministic: same inputs --> same output, always. No clocks,
        no randoms, no I/O.

Implementation rules enforced here:

    - No I/O. No filesystem, no network, no logging.
    - No state. The engine instance carries no mutable attributes.
    - No clocks. ``datetime.now`` is not called.
    - No randoms. ``random`` module is not imported.
"""

from __future__ import annotations

from soc.decision.types import Action, DecisionRecord, Manifest
from soc.risk.types import PolicyResult, RiskAssessment, SecurityEvent


class DecisionEngine:
    """Pure-function decision mapper.

    The engine is instantiated without arguments and exposes a single
    public method, :meth:`decide`. All branching logic follows the
    canonical spec section 8 verbatim.
    """

    def decide(
        self,
        *,
        event: SecurityEvent,
        policy: PolicyResult,
        risk: RiskAssessment,
        manifest: Manifest,
    ) -> DecisionRecord:
        """Map inputs onto a :class:`DecisionRecord`.

        See module docstring for the branch order. The function is
        deterministic and never raises for well-typed inputs --- a
        malformed input would surface at attribute-access time, not
        as a custom DecisionEngine exception.
        """
        # Branch 1: policy denial. First guard per spec section 8.
        if not policy.allowed:
            return self._record(
                event=event,
                manifest=manifest,
                risk=risk,
                action=Action.BLOCK,
                reason=policy.deny_reason or "policy_denied",
            )

        # Branch 2: action listed in manifest.approvals.required_for.
        if event.action in manifest.approvals.required_for:
            return self._record(
                event=event,
                manifest=manifest,
                risk=risk,
                action=Action.REQUIRE_APPROVAL,
                reason="action_in_approval_list",
                required_approvers=self._approvers_for(event, manifest),
            )

        # Branch 3: high risk score (>= 80).
        if risk.score >= 80:
            return self._record(
                event=event,
                manifest=manifest,
                risk=risk,
                action=Action.REQUIRE_APPROVAL,
                reason="high_risk_score",
            )

        # Branch 4: POPIA s.26 special-data MONITOR override.
        # MUST come before the >= 50 branch so a low-risk-score event
        # involving health, biometric, or children's data is never
        # silently allowed on enterprise tier (canonical spec section
        # 8 inline comment).
        if (
            manifest.compliance_tier == "enterprise"
            and event.classification == "special"
        ):
            return self._record(
                event=event,
                manifest=manifest,
                risk=risk,
                action=Action.MONITOR,
                reason="special_data_enterprise_tier",
            )

        # Branch 5: elevated risk score (50 <= score < 80).
        if risk.score >= 50:
            return self._record(
                event=event,
                manifest=manifest,
                risk=risk,
                action=Action.MONITOR,
                reason=f"elevated_risk_score({risk.score})",
            )

        # Branch 6: default.
        return self._record(
            event=event,
            manifest=manifest,
            risk=risk,
            action=Action.ALLOW,
            reason="default",
        )

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def _record(
        *,
        event: SecurityEvent,
        manifest: Manifest,
        risk: RiskAssessment,
        action: Action,
        reason: str,
        required_approvers: tuple[str, ...] = (),
    ) -> DecisionRecord:
        """Build a DecisionRecord with the always-same provenance
        fields (event id, manifest hash, policy version, risk inputs,
        risk score) populated from the inputs.

        ``dlp_findings`` is currently an empty tuple --- the canonical
        spec section 6 DLP scanner is not yet implemented (see
        ``soc/dlp/__init__.py``). When that lands, the pipeline will
        thread the scanner's output through here.
        """
        return DecisionRecord(
            event_id=event.event_id,
            manifest_hash=manifest.manifest_hash,
            policy_version=manifest.policy_version,
            dlp_findings=(),  # TODO: populate from soc.dlp output when present
            risk_inputs=dict(risk.risk_inputs),
            risk_score=risk.score,
            action=action,
            reason=reason,
            required_approvers=required_approvers,
        )

    @staticmethod
    def _approvers_for(
        event: SecurityEvent,
        manifest: Manifest,
    ) -> tuple[str, ...]:
        """Resolve the approver list for an approval-gated action.

        Full resolution belongs to the MCP Gateway (canonical spec
        section 9 capability tokens) plus a future approver-registry
        component. Until those exist, we return a single explicit
        placeholder so the action is correctly gated and the approver
        identity is visible and replaceable in audit logs.
        """
        # event and manifest are accepted so the signature is stable
        # once a real registry lookup is wired in; both are unused
        # right now.
        del event, manifest
        return ("designated_approver",)

