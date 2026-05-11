# Risk Engine — sub-contract for `docs/AI_OS_v3_SPEC.md`

**Status:** DRAFT — supplements the canonical spec. Not a replacement.

The canonical spec (`docs/AI_OS_v3_SPEC.md`) describes the Risk Engine
at three places only:

- §4 (Component Catalogue, row 4) — high-level: "deterministic rules
  (fast path) + sliding-window anomaly stats per actor (z-score on
  request rate, novel-tool usage, off-hours activity). No ML in v3.0."
- §5.2 (Pipeline contract) — call signature only:
  ``risk_result = await self.risk.score(event, dlp_result, policy_result)``
- §6.3 B3 (DLP acceptance criteria, "SA-002") — confidence policy:
  "Confidence affects the risk engine's weighting of the finding, not
  the classification itself. A `low`-confidence hit is still a
  POPIA-relevant finding and must not be suppressed."
- §8 (Decision Engine) — the implicit contract on the OUTPUT of the
  risk engine, since the Decision Engine reads ``risk.score >= 80`` /
  ``risk.score >= 50``. This pins the **score scale to 0–100** and
  the **attribute name to ``score``**.

This document fills in the implementation details left open by the
canonical spec. If anything here contradicts `docs/AI_OS_v3_SPEC.md`,
the canonical spec wins.

---

## 1. Public interface

```python
class RiskEngine:
    async def score(
        self,
        event: SecurityEvent,
        dlp_result: DLPResult,
        policy_result: PolicyResult,
    ) -> RiskAssessment: ...

    def reset(self) -> None: ...
    def reset_actor(self, actor_id: str) -> None: ...
```

``RiskAssessment`` exposes:

- ``score: float`` in ``[0.0, 100.0]`` — matches the scale used by the
  Decision Engine in canonical spec §8.
- ``deterministic_score: float`` in ``[0.0, 1.0]`` — fast-path sub-score
  (internal scale; before the 0–100 rescale).
- ``statistical_score: float`` in ``[0.0, 1.0]`` — window-derived
  sub-score (internal scale).
- ``confidence: float`` in ``[0.0, 1.0]`` — engine confidence in its
  statistical sub-score, rises with sample count.
- ``z_score: Optional[float]`` — ``None`` until ``min_samples`` reached.
- ``rule_hits: tuple[str, ...]`` — deterministic rule IDs that fired.
- ``sample_count: int`` — samples PRESENT BEFORE this event (the event
  being scored is not part of its own baseline).
- ``window_size: int``
- ``risk_inputs: Mapping[str, Any]`` — explainability payload, safe to
  log (no raw PII). Maps onto ``DecisionRecord.risk_inputs`` per
  canonical spec §5.3 A4.

## 2. Determinism contract (REQ-RE-1)

The engine is **stateful but reproducible**: given the same
construction parameters and the same ordered sequence of ``score()``
calls from a fresh state (after ``__init__`` or ``reset()``), it
produces an identical ordered sequence of ``RiskAssessment`` outputs.
Tests MUST instantiate a fresh ``RiskEngine()`` per test or call
``engine.reset()`` in setUp. The pytest fixtures provided default to
per-test scope.

## 3. Deterministic fast-path rules (REQ-RE-2)

The engine maintains an ordered list of
``(rule_id, predicate, base_score, selector)`` 4-tuples. On each
``score()`` call the list is scanned in order. Multiple rules MAY
match; the deterministic sub-score is the ``max()`` of all firing
rules' contributions, and every firing rule's ID is appended to
``rule_hits``. A single rule firing is enough to escalate; non-matching
rules do not depress the score.

The ``selector`` field is optional. When present, it identifies the
DLP findings the rule "owns" so SA-002 confidence weighting can be
applied. When ``None``, the rule contributes its ``base_score``
unchanged (used for event-severity and policy rules that do not depend
on DLP).

The default rule table:

| rule_id            | trigger                              | base score | DLP-weighted |
|--------------------|--------------------------------------|------------|--------------|
| `severity_critical`| `event.severity == "critical"`       | 1.00       | no           |
| `severity_high`    | `event.severity == "high"`           | 0.75       | no           |
| `severity_medium`  | `event.severity == "medium"`         | 0.40       | no           |
| `policy_denied`    | `policy_result.allowed is False`     | 1.00       | no           |
| `dlp_pii_critical` | DLP finding with severity `critical` | 0.90       | yes          |
| `dlp_pii_high`     | DLP finding with severity `high`     | 0.65       | yes          |
| `dlp_pii_any`      | any DLP finding present              | 0.30       | yes          |

For rules where "DLP-weighted" is `yes`, the rule's contribution is
``base_score * max(f.score for f in owned_findings)``. See §4 (SA-002).

### 3.1 Engine-level short-circuits (evaluated before the rule table)

The actor allowlist and blocklist are NOT entries in the
``fast_path_rules`` table. They are checked directly by ``score()``
before the rule table is consulted, and they bypass all other
computation:

| short-circuit     | trigger                          | effect                         |
|-------------------|----------------------------------|--------------------------------|
| `actor_allowlist` | `event.actor_id` in allowlist    | `score = 0.0`, `rule_hits = ("actor_allowlist",)` |
| `actor_blocklist` | `event.actor_id` in blocklist    | `score = 100.0`, `rule_hits = ("actor_blocklist",)` |

The Risk Engine produces only a numeric score; the Decision Engine
(canonical spec §8) maps that score to ALLOW / MONITOR /
REQUIRE_APPROVAL / BLOCK.

## 4. DLP confidence weighting (REQ-RE-5 / SA-002)

Each DLP fast-path rule predicate identifies a SUBSET of findings it
"owns" (e.g. ``dlp_pii_critical`` owns all findings whose severity is
``critical``). The rule's contribution to the deterministic sub-score
is:

```text
contribution = base_score * max(f.score for f in matching_findings)
```

This honours §6.3 B3: a low-confidence finding is not suppressed (its
contribution is `base_score * 0.something`, still > 0), but a
high-confidence finding pulls the rule's contribution toward its full
base score. The finding's **classification** is unchanged — that
happens in the DLP stage upstream of the Risk Engine.

If a rule's ``selector`` is ``None``, or the selector returns no
findings, the rule contributes its ``base_score`` unchanged. Only
rules with a non-empty owned slice are confidence-weighted. This keeps
non-DLP rules (event-severity, policy) immune to DLP confidence.

## 5. Sliding-window z-score (REQ-RE-3)

Per actor, the engine maintains a ``collections.deque`` of the most
recent ``numeric_signal`` values, bounded by ``window_size`` (default
50). The deque evicts the oldest entry on overflow.

```text
n = len(window)                       # samples BEFORE this event
if n < min_samples:                   # default min_samples = 5
    statistical_score = 0.5           # neutral
    z_score           = None
else:
    mean  = statistics.mean(window)
    stdev = statistics.pstdev(window)
    if stdev == 0:
        z_score          = 0.0
        statistical_score = 0.5
    else:
        z_score          = (event.numeric_signal - mean) / stdev
        statistical_score = sigmoid(z_score, k=1.0)
```

The event's own ``numeric_signal`` is appended to the window AFTER the
score for this event has been computed, so the event being scored is
not part of its own baseline.

> **Note on `pstdev` vs `stdev`:** the engine uses ``statistics.pstdev``
> (population standard deviation) rather than ``statistics.stdev``
> (sample standard deviation with Bessel's correction). With a bounded
> sliding window we treat the window as the **full population of
> recent activity for that actor**, not a sample from an infinite
> distribution. This avoids the small-sample bias correction
> (``/ (n-1)``) inflating the z-score's denominator when the window
> is short.

## 6. Confidence weighting (REQ-RE-4)

Engine confidence rises linearly with sample count:

```text
confidence = min(1.0, n / window_size)
```

The statistical contribution is attenuated by confidence so a fresh
engine does not over-react to a tiny baseline:

```text
stat_blended = statistical_score * confidence + 0.5 * (1.0 - confidence)
final_unit   = clamp_unit(det_weight * deterministic_score
                          + stat_weight * stat_blended)
score        = 100.0 * final_unit       # 0-100 scale per spec §8
```

Defaults: ``det_weight = 0.6``, ``stat_weight = 0.4``. Weights must sum
to 1.0 (validated at construction).

## 7. Sigmoid normalisation

```text
sigmoid(z, k) = 1.0 / (1.0 + exp(-k * z))
```

Maps an unbounded z-score onto ``[0, 1]`` so the statistical sub-score
composes cleanly with the deterministic sub-score before the 0–100
rescale. ``k = 1.0`` by default.

## 8. Constraints

- **No I/O** in the engine. No network, no filesystem, no logging
  side-effects.
- **No new dependencies**. Uses only ``collections``, ``dataclasses``,
  ``statistics``, ``math``, ``datetime``, ``typing`` from stdlib.
- **Latency budget**: p95 < 5 ms (the canonical spec §5.3 A1's 150 ms
  budget covers the whole pipeline; the engine is well inside that).
- **Concurrency**: a single ``RiskEngine`` instance is not guaranteed
  thread-safe; callers must serialise or shard per actor. Async-safe
  within a single event loop because all internals are synchronous.

## 9. Decision banding (informative, not normative)

The Risk Engine does NOT decide ALLOW / MONITOR / REQUIRE_APPROVAL /
BLOCK — that is the Decision Engine's job per canonical spec §8. The
engine only emits ``score`` and the explainability payload. For
reference, the canonical Decision Engine maps the numeric ranges:

| ``risk.score``  | typical action       |
|-----------------|----------------------|
| ``>= 80``       | REQUIRE_APPROVAL     |
| ``50 – 79``     | MONITOR              |
| ``< 50``        | ALLOW                |

The actor-level short-circuits described in §3.1 pin
``score = 0.0`` (allowlist) or ``score = 100.0`` (blocklist) and
therefore land in the ALLOW or REQUIRE_APPROVAL bands respectively.

> **The table above is not the complete decision logic.** Canonical
> spec §8 also forces ``action = MONITOR`` when
> ``manifest.compliance_tier == "enterprise"`` **and**
> ``event.classification == "special"``, regardless of
> ``risk.score`` (POPIA s.26 special data on enterprise tier is
> monitored at every risk level). This override is the Decision
> Engine's responsibility — the Risk Engine does not encode it and
> must not be relied upon to enforce it.

## 10. Test plan (implemented under tests/unit/test_risk_engine.py)

- Fresh engine + ``n < min_samples`` → neutral statistical sub-score,
  ``z_score is None``.
- Fast-path ``severity == "critical"`` pins deterministic sub-score
  to 1.00 regardless of window state.
- Z-score arithmetic verified against ``statistics``-computed
  reference values.
- Sliding window evicts at ``maxlen``.
- Per-actor isolation: actor A's history does not influence actor B.
- Engine confidence grows from ``0`` to ``1.0`` over ``window_size``
  calls.
- Weights ``(0.6, 0.4)`` honoured exactly when sub-scores are fixed.
- Blocklist short-circuits to ``score = 100``; allowlist short-circuits
  to ``score = 0``.
- DLP rule contribution scales with finding confidence (SA-002).
- ``reset()`` clears all actor windows; ``reset_actor()`` clears one.
- Construction validation: weights sum to 1.0; ``window_size > 0``;
  ``1 <= min_samples <= window_size``.
- Determinism: two fresh engines + identical input sequence →
  identical output sequence.

---

Simbarashe G. | AI Automation Engineer
