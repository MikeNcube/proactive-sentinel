"""Decision Engine types.

Implements the data shapes referenced by canonical spec section 8 and
the DecisionRecord field list in section 5.3 A4. Frozen dataclasses
across the board so engine inputs and outputs are hashable, comparable
in tests, and safe to log without mutation surprises.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping


class Action(str, Enum):
    """Action a Decision Record can carry.

    The four values mirror canonical spec section 3 ("ALLOW | MONITOR
    | APPROVE | BLOCK") and section 8 (``REQUIRE_APPROVAL`` is the
    full name used by the decide() implementation). Sub-classing
    ``str`` so ``json.dumps`` serialises the value cleanly without a
    custom encoder.
    """

    ALLOW = "ALLOW"
    MONITOR = "MONITOR"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ApprovalConfig:
    """The ``approvals`` sub-tree of the project manifest.

    Mirrors canonical spec section 2 (``MANIFEST.yaml`` schema):

        approvals:
          required_for:
            - mcp.tool_execute
            - data.export
            - decision.claim_payout
            - decision.policy_decline
    """

    required_for: tuple[str, ...] = ()


@dataclass(frozen=True)
class Manifest:
    """Subset of MANIFEST.yaml the Decision Engine actually reads.

    The Decision Engine only consumes the fields canonical spec
    section 8 references. Other manifest contents (storage,
    integrations, llm provider, etc.) are out of scope for this stage.
    """

    compliance_tier: str  # "enterprise" | "standard"
    approvals: ApprovalConfig = field(default_factory=ApprovalConfig)
    manifest_hash: str = ""
    policy_version: str = "unversioned"


@dataclass(frozen=True)
class DecisionRecord:
    """Decision Engine output.

    Field list is exactly the one canonical spec section 5.3 A4
    mandates:

        event_id, manifest_hash, policy_version, dlp_findings
        (redacted), risk_inputs, risk_score, action, reason,
        required_approvers (if any).
    """

    event_id: str
    manifest_hash: str
    policy_version: str
    dlp_findings: tuple[Mapping[str, Any], ...]
    risk_inputs: Mapping[str, Any]
    risk_score: float
    action: Action
    reason: str
    required_approvers: tuple[str, ...] = ()

    def to_record(self) -> Mapping[str, Any]:
        """JSON-serialisable plain-dict view of the decision.

        Referenced by canonical spec section 5.2:

            await self.audit.log("DECISION", event.event_id,
                                 decision.to_record())

        Returns a dict whose values are JSON-native (str, float, list,
        dict, None, bool). The ``action`` enum is reduced to its
        string value explicitly so callers do not have to know about
        Python's str-Enum coercion quirks.
        """
        record = asdict(self)
        record["action"] = self.action.value
        # asdict turns tuples into lists already; nothing else to do.
        return record
