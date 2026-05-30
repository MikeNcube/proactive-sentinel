"""Decision Engine package.

Implements the ``decision`` dependency of the SOCPipeline contract
declared in canonical spec section 5.2 (``docs/AI_OS_v3_SPEC.md``):

    decision = self.decision.decide(
        event=event,
        policy=policy_result,
        risk=risk_result,
        manifest=current_manifest(),
    )

Behaviour is the spec section 8 mapping, implemented as a pure
function (no I/O, no state, no clocks, no randoms).

Public surface
--------------
- :class:`DecisionEngine`    --- the engine itself
- :class:`DecisionRecord`    --- engine output (carries ``action``,
                                  ``reason``, ``risk_score``,
                                  ``risk_inputs``, etc. per spec
                                  section 5.3 A4)
- :class:`Action`            --- ALLOW / MONITOR / REQUIRE_APPROVAL / BLOCK
- :class:`Manifest`          --- subset of MANIFEST.yaml the engine reads
- :class:`ApprovalConfig`    --- the ``approvals`` sub-tree
"""

from soc.decision.engine import DecisionEngine
from soc.decision.types import (
    Action,
    ApprovalConfig,
    DecisionRecord,
    Manifest,
)

__all__ = [
    "Action",
    "ApprovalConfig",
    "DecisionEngine",
    "DecisionRecord",
    "Manifest",
]

