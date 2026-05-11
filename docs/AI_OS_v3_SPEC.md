# AI OS v3 — Canonical Specification

**Document type:** Spec-driven development manifest for Claude Code, Cursor, Codex, and any compliant coding agent.
**Owner:** Simbarashe G. — AI Automation Engineer, Johannesburg.
**Primary deployment context:** Zororo-Phumulani Funeral Insurance (underwritten by KGA Life) — *enterprise tier*. Personal projects — *standard tier*.
**Status:** v3.0 — supersedes v2.3 and v2.5. Read this file end-to-end before generating any code.
**Last updated:** 2026-04-30

---

## 0. How agents must read this spec

This document is the **single source of truth**. When Claude Code (or any coding agent) is asked to build, review, or modify a project on this OS, it must:

1. Read this entire file before any plan or code is produced.
2. Read the project's `MANIFEST.yaml` (Section 2) to determine `compliance_tier`, `deployment_target`, and `data_classification`.
3. Resolve every component decision against the **Build / Adopt / Configure** matrix in Section 4. Do not reinvent components marked `[ADOPT]` or `[CONFIGURE]`.
4. Before writing code, present a plan back to the human (Maketekete) covering: files to create, libraries to adopt, IaC modules touched, and any decision the spec leaves ambiguous. **Wait for approval.**
5. Treat every section's *Acceptance Criteria* as testable assertions. If you cannot write a test for a criterion, ask before proceeding.
6. Never silently downgrade a control. If a tier-A control cannot be implemented in the chosen environment (e.g. Railway lacks KMS), surface the gap explicitly and propose either a compensating control or a deployment-target change.

**This is not a wishlist.** Every section below has been scoped to be implementable. Aspirational features are quarantined in Appendix B.

---

## 1. Why this exists

v2.3 and v2.5 had the right intuitions — event-driven SOC, POPIA-first thinking, MCP-style execution control — but were unbuildable as written. v3 collapses both into one architecture that:

- Is **executable by spec-driven coding agents** without ambiguity.
- Treats **Vercel/Railway as legitimate prototyping targets** with a clean promotion path to **AWS af-south-1** for production.
- Distinguishes **enterprise compliance posture** (Zororo-Phumulani / KGA Life) from **standard posture** (personal projects), via a single config flag.
- Marks every component as **[BUILD]**, **[ADOPT]**, or **[CONFIGURE]** so the agent knows when to write code and when to wire up something that already exists.
- Has a **threat model** (Appendix A) so each control has a defensible reason to exist.

---

## 2. Project Manifest (`MANIFEST.yaml`)

Every project on this OS has a `MANIFEST.yaml` at its root. The agent reads this *first*. Schema:

```yaml
project:
  name: zororo-claims-triage
  owner: maketekete
  description: "Funeral claim intake and triage assistant"

compliance_tier: enterprise   # enterprise | standard
data_classification: special  # special | personal | internal | public
                              # 'special' = POPIA s.26 (health, religion, biometric)

deployment:
  prototype_target: railway   # vercel | railway | local
  production_target: aws-af-south-1
  data_residency: za-only     # za-only | za-preferred | global

llm:
  primary_provider: anthropic
  primary_model: claude-opus-4-7
  governance_role: claude     # claude reviews/approves sensitive decisions
  fallback_provider: none     # explicit; no silent fallback
  human_in_loop: required     # required | sampling | none

storage:
  vector_db: pgvector         # pgvector | qdrant | pinecone-eu
  relational: postgres
  object: s3-af-south-1

integrations:
  - name: kga-policy-system
    direction: read-only
    auth: oauth2-client-credentials
    pii_in_scope: true

approvals:
  required_for:
    - mcp.tool_execute
    - data.export
    - decision.claim_payout
    - decision.policy_decline
```

### Acceptance criteria (manifest)

- The system MUST refuse to start if `MANIFEST.yaml` is missing, malformed, or fails schema validation.
- The system MUST log the manifest hash on every startup so audit logs can be tied to a config version.
- Changing `compliance_tier` from `standard` to `enterprise` MUST require a documented review (a `CHANGELOG.md` entry referencing the change).

---

## 3. Architecture (canonical view)

```
                       ┌──────────────────────────────────────┐
                       │       MANIFEST.yaml (config)         │
                       └──────────────────────────────────────┘
                                       │
   ┌───────────────┐      ┌────────────▼────────────┐      ┌──────────────────┐
   │  User / API   │─────►│      Event Bus          │◄─────│  Agent Runtime    │
   │  (web/mobile) │      │   (NATS or SNS+SQS)     │      │  (LangGraph)      │
   └───────────────┘      └────────────┬────────────┘      └──────────────────┘
                                       │
                          ┌────────────▼────────────┐
                          │     SOC Pipeline        │
                          │  ┌───────────────────┐  │
                          │  │ 1. PII/DLP scan   │  │  Presidio + SA recognizers
                          │  │ 2. Policy eval    │  │  OPA (Rego policies)
                          │  │ 3. Risk score     │  │  Rules + sliding-window stats
                          │  │ 4. Decision       │  │  ALLOW | MONITOR | APPROVE | BLOCK
                          │  └─────────┬─────────┘  │
                          └────────────┼────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
   ┌──────────▼─────────┐  ┌───────────▼────────┐  ┌────────────▼────────┐
   │  MCP Gateway       │  │   RAG Layer        │  │   Audit Pipeline     │
   │  (capability       │  │   (pgvector +      │  │   (hash-chained →    │
   │   tokens, OAuth)   │  │   metadata filter) │  │   S3 Object Lock)    │
   └──────────┬─────────┘  └────────────────────┘  └─────────────────────┘
              │
   ┌──────────▼─────────┐
   │  Tool Execution    │  Each tool: scoped IAM role, KMS data key,
   │  (LLM, DB, Email,  │  rate limit, cost cap, timeout
   │   KGA API, etc.)   │
   └────────────────────┘
```

Key invariants:

- **Every action is an event.** No code path bypasses the SOC pipeline.
- **The SOC pipeline is synchronous on the critical path** for tier-A actions (those listed in `approvals.required_for`). Asynchronous "fire and check later" is forbidden for sensitive operations.
- **Decisions are explainable.** The decision engine emits a structured `decision_record` with the policy, risk inputs, and outcome. No black-box scoring.
- **Audit logs are tamper-evident.** Hash-chained, written to append-only storage.

---

## 4. Component Catalogue (Build / Adopt / Configure)

This is the table the agent must consult before writing any module.

| # | Component | Status | Implementation |
|---|---|---|---|
| 1 | Event Bus | `[ADOPT]` | NATS JetStream (dev/Railway), SNS+SQS (AWS prod). Wrap behind `events/bus.py` interface. |
| 2 | PII/DLP Scanner | `[ADOPT]` + `[BUILD]` | Microsoft Presidio (analyzer + anonymizer). **Build** SA-specific recognizers: SA ID (with Luhn-equivalent checksum), SA passport, SARS tax ref, medical aid number, CIPC company reg, KGA policy number format. |
| 3 | Policy Engine | `[ADOPT]` | Open Policy Agent (OPA) with Rego policies. Policies live in `policies/` and are version-controlled. |
| 4 | Risk Engine | `[BUILD]` | Hybrid: deterministic rules (fast path) + sliding-window anomaly stats per actor (z-score on request rate, novel-tool usage, off-hours activity). No ML in v3.0; ML is v3.1 (Appendix B). |
| 5 | Decision Engine | `[BUILD]` | Pure function: `(policy_result, risk_score, manifest) → decision_record`. Deterministic, fully unit-tested. |
| 6 | MCP Gateway | `[BUILD]` on top of `[ADOPT]` | Use the official MCP Python SDK. Build the **capability-token** layer: every tool call carries a short-lived JWT signed by the Decision Engine, scoped to one tool + one resource + one TTL. Gateway verifies before dispatch. |
| 7 | Encryption | `[CONFIGURE]` | AWS KMS (prod). For Railway/Vercel prototyping with non-special data, use envelope encryption with a key from a managed secret store (Doppler or Railway's secret manager). **Special data MUST NOT touch Railway/Vercel.** |
| 8 | Audit Logger | `[BUILD]` (thin) | Hash-chained JSONL: each record contains `prev_hash`. Local file in dev; ships to S3 with **Object Lock in compliance mode** in prod. CloudWatch Logs as a secondary index. |
| 9 | Observability | `[ADOPT]` | OpenTelemetry SDK; OTLP export to Grafana Cloud (dev) or AWS Managed Grafana + X-Ray (prod). Do not roll your own tracer. |
| 10 | Vector RAG Store | `[CONFIGURE]` | pgvector on RDS PostgreSQL (prod) or Railway Postgres (dev). Per-row encryption for embedded chunks containing PII. Metadata filter for tenant + classification. |
| 11 | Agent Runtime | `[ADOPT]` | LangGraph for orchestration (matches your skill set). Agents are nodes; the SOC pipeline is the edge guard. |
| 12 | Secrets | `[CONFIGURE]` | AWS Secrets Manager (prod), Doppler or Railway secrets (dev). Pre-commit hook with `gitleaks` and `detect-secrets` is mandatory. |
| 13 | Identity | `[CONFIGURE]` | AWS Cognito (prod) or Clerk (dev). All human approvals MUST be tied to a Cognito/Clerk identity, never a shared service account. |
| 14 | IaC | `[BUILD]` (Terraform modules) | One root per environment: `infra/terraform/{dev,staging,prod}/`. Reusable modules under `infra/terraform/modules/`. |

**Rule:** If a component is `[ADOPT]` or `[CONFIGURE]` and the agent proposes building it from scratch, the agent has misread the spec. Stop and reread.

---

## 5. The SOC Pipeline (canonical implementation contract)

The pipeline is the heart of v3. It MUST be implemented as a single composable chain so each step is independently testable.

### 5.1 Event schema

```python
# soc/events/schema.py
from pydantic import BaseModel
from typing import Literal, Any
from datetime import datetime

class Event(BaseModel):
    event_id: str                         # UUIDv7 (time-ordered)
    timestamp: datetime
    actor: dict                           # {id, type: human|agent|system, session_id}
    action: str                           # e.g. "rag.query", "mcp.tool_execute"
    resource: dict                        # {type, id, tenant}
    data: Any                             # payload (will be scanned for PII)
    context: dict                         # {ip, user_agent, manifest_hash, ...}
    classification: Literal["special", "personal", "internal", "public"]
```

### 5.2 Pipeline contract

```python
# soc/pipeline.py
class SOCPipeline:
    def __init__(self, dlp, policy, risk, decision, audit):
        self.dlp = dlp          # Presidio + SA recognizers
        self.policy = policy    # OPA client
        self.risk = risk        # rules + anomaly stats
        self.decision = decision
        self.audit = audit      # hash-chained logger

    async def evaluate(self, event: Event) -> DecisionRecord:
        await self.audit.log("EVENT_RECEIVED", event.event_id, event.summary())

        dlp_result = await self.dlp.scan(event.data, classification=event.classification)
        policy_result = await self.policy.evaluate(event, dlp_result)
        risk_result = await self.risk.score(event, dlp_result, policy_result)

        decision = self.decision.decide(
            event=event,
            policy=policy_result,
            risk=risk_result,
            manifest=current_manifest(),
        )

        await self.audit.log("DECISION", event.event_id, decision.to_record())
        return decision
```

### 5.3 Acceptance criteria (SOC pipeline)

- A1. Every method is `async` and non-blocking. Pipeline latency budget: **p95 < 150ms** for non-LLM events.
- A2. The pipeline is pure-function over its inputs *except* for `audit.log` (which is intentionally side-effecting). It MUST be unit-testable with mocked dependencies.
- A3. If any stage raises, the pipeline returns `decision = BLOCK` with `reason = "soc_failure"` and emits a high-severity audit record. **Failing open is forbidden.**
- A4. The decision record contains: event_id, manifest_hash, policy_version, dlp_findings (redacted), risk_inputs, risk_score, action, reason, required_approvers (if any).
- A5. PII findings logged to the audit trail MUST be redacted using Presidio's anonymizer. **Original PII never appears in audit logs.**

---

## 6. PII/DLP — Southern African customer document recognizers (BUILD spec)

Presidio handles the engine. You must extend it with these recognizers. Each one needs unit tests covering positive cases, false-positive traps, and edge cases.

**Role of the recognizer suite:** Detection and classification only — not document validity. The recognizer identifies what *type* of identifier is present and with what confidence. Trained Zororo staff determine whether the document is genuine, current, and matches the holder. See SA-002 and `docs/architecture/zororo-context.md` "ID verification model."

**Scope (v3.0):** SA ID, ZW National ID, SA asylum/refugee permits. ~80% of policyholders present Zimbabwean documentation — the recognizer suite must cover the full customer base, not only SA IDs. See MANIFEST.yaml `identifiers_supported`.

### 6.1 SA ID Number

Format: 13 digits, `YYMMDDSSSSCAZ` where:
- `YYMMDD` = date of birth
- `SSSS` = sequence (4000+ = female, <5000 = male — 5000 is the boundary)
- `C` = citizenship (0 = SA, 1 = permanent resident)
- `A` = legacy field (always 8 or 9 in modern IDs)
- `Z` = Luhn-style check digit

**Validation algorithm (the check digit):**
1. Sum the odd-position digits (positions 1,3,5,7,9,11) → `A`.
2. Concatenate the even-position digits (positions 2,4,6,8,10,12) into a 6-digit number, multiply by 2, sum the digits of the result → `B`.
3. `(A + B) mod 10`, then `(10 - that) mod 10` = expected check digit.

A regex match without checksum validation is **NOT a positive finding** — it logs as `low_confidence` only.

The recognizer must also **validate the date** (YYMMDD must be a real calendar date) to suppress false positives on receipt numbers and timestamps.

### 6.2 Other recognizers

| Identifier | Pattern hint | Validation |
|---|---|---|
| SA passport | `[A-Z]\d{8}` | None beyond pattern; flag as medium confidence |
| SARS tax ref | 10 digits, starts with 0/1/2/3/9 | Modulo-10 checksum (SARS publishes the algorithm) |
| KGA policy no. | (Confirm format with KGA — likely prefix + numeric) | Pattern + prefix whitelist |
| Medical aid no. | Scheme-specific; whitelist top 10 SA schemes' formats | Pattern + scheme prefix |
| Bank account | 9-11 digits | Branch code cross-check against SARB list |
| Phone | `(\+27|0)\d{9}` | Length + leading-digit validity |
| Email | RFC 5322 (use Presidio's built-in) | DNS MX optional in batch mode |

### 6.3 Acceptance criteria (DLP)

- B1. Test corpus of **at least 200 examples per recognizer** (mix of true positives, true negatives, near-misses).
- B2. False-positive rate on a held-out corpus of generic SA business text: **< 2%**.
- B3. Recognizer confidence expresses *recognition certainty* — how sure we are that we have correctly identified the *type* of identifier — not document validity (which is determined by trained Zororo staff, not the system). Confidence levels:
    - `high` — all available structural checks pass (pattern + checksum/date validation where applicable)
    - `medium` — pattern matches but no structural check is available or implemented for this format
    - `low` — partial or ambiguous pattern match
  All confidence levels trigger the same data-classification treatment (special or personal per the identifier type). Confidence affects the risk engine's weighting of the finding, not the classification itself. A `low`-confidence hit is still a POPIA-relevant finding and must not be suppressed.
- B4. The DLP module MUST run offline. No external API calls (this is a hard requirement for special data — it cannot leave the boundary for scanning).

---

## 7. Policy Engine (OPA / Rego)

Policies are code, version-controlled, and reviewed like code. Located in `policies/`.

### 7.1 Required base policies

```
policies/
├── base/
│   ├── data_classification.rego     # classification → allowed_actions
│   ├── popia_lawful_basis.rego      # actor must have a lawful basis for processing
│   ├── popia_purpose_limitation.rego # action must match the consent purpose
│   ├── popia_retention.rego         # data older than retention_days → access denied
│   └── tenant_isolation.rego        # cross-tenant access forbidden
├── zororo/
│   ├── claim_payout_authority.rego  # who can authorise payout, by amount band
│   ├── beneficiary_changes.rego     # cooling-off + dual-control
│   └── kga_data_egress.rego         # what can leave KGA's data perimeter
└── personal/
    └── relaxed.rego                 # standard tier defaults
```

### 7.2 Acceptance criteria (Policy)

- C1. Every policy file has a paired test file (`*_test.rego`) with passing/failing fixtures.
- C2. Policy evaluation is bounded: max 50ms or the call returns `policy_failure` (which is a BLOCK).
- C3. Policy bundles are signed; the runtime verifies the signature on load.
- C4. POPIA s.18 (consent) checks reference the `consent_record_id` from the event context. No consent record → BLOCK on personal/special data.

---

## 8. Decision Engine

```python
# soc/decision.py
class DecisionEngine:
    """
    Pure function. No I/O. No state. Trivially unit-testable.
    """
    def decide(self, event, policy, risk, manifest) -> DecisionRecord:
        if not policy.allowed:
            return DecisionRecord(action="BLOCK", reason=policy.deny_reason)

        if event.action in manifest.approvals.required_for:
            return DecisionRecord(
                action="REQUIRE_APPROVAL",
                required_approvers=self._approvers_for(event, manifest),
                reason="action_in_approval_list",
            )

        if risk.score >= 80:
            return DecisionRecord(action="REQUIRE_APPROVAL", reason="high_risk_score")

        if manifest.compliance_tier == "enterprise" and event.classification == "special":
            # POPIA s.26: special data on enterprise tier is monitored at ALL risk
            # levels, not just when risk >= 50. Evaluated before the elevated-risk
            # threshold so that a low-risk-score event involving health, biometric,
            # or children's data is never silently allowed.
            return DecisionRecord(action="MONITOR", reason="special_data_enterprise_tier")

        if risk.score >= 50:
            return DecisionRecord(action="MONITOR", reason=f"elevated_risk_score({risk.score})")

        return DecisionRecord(action="ALLOW", reason="default")
```

### 8.1 Acceptance criteria (Decision)

- D1. 100% branch coverage in unit tests.
- D2. Property-based test (Hypothesis): for any input, the function returns a valid `DecisionRecord` and never raises.
- D3. The function is deterministic: same inputs → same output, always. No clocks, no randoms, no I/O.

---

## 9. MCP Gateway with Capability Tokens

The v2.5 gateway trusted upstream code. v3 does not.

### 9.1 Capability token

When the Decision Engine returns `ALLOW` for an MCP action, it issues a JWT:

```json
{
  "sub": "actor_id",
  "aud": "mcp.gateway",
  "tool": "kga.policy.read",
  "resource": "policy/123456",
  "scope": "read",
  "exp": 1730000060,            // 60s TTL
  "jti": "uuid-v7",
  "decision_id": "dec_abc123"
}
```

Signed with a key the Gateway can verify (KMS-backed in prod). Single-use (`jti` recorded in a Redis/ElastiCache nonce store).

### 9.2 Gateway behaviour

```python
# mcp/gateway.py
class MCPGateway:
    async def execute(self, tool_call: ToolCall, capability_token: str):
        claims = self.verifier.verify(capability_token)  # signature, exp, aud
        if claims["tool"] != tool_call.tool:
            raise CapabilityMismatch()
        if claims["resource"] != tool_call.resource:
            raise CapabilityMismatch()
        if not await self.nonce_store.consume(claims["jti"]):
            raise CapabilityReplay()

        # at this point we trust the caller; dispatch
        return await self.tools[tool_call.tool].invoke(
            tool_call.args,
            scope=claims["scope"],
            actor=claims["sub"],
        )
```

### 9.3 Acceptance criteria (MCP)

- E1. Token replay attempts are rejected and audited.
- E2. Token forgery (modified claims) is rejected at signature verification.
- E3. Tool call without a token is rejected. There is no "trusted internal" bypass.
- E4. Each tool registers a manifest declaring required scopes; the gateway refuses to dispatch if the token's scope is insufficient.

---

## 10. Audit Logging (hash-chained, tamper-evident)

### 10.1 Record format

```json
{
  "seq": 142857,
  "timestamp": "2026-04-30T10:15:42.001Z",
  "manifest_hash": "sha256:abcd...",
  "event_type": "DECISION",
  "event_id": "ev_01H...",
  "payload_hash": "sha256:1234...",   // hash of (redacted) payload
  "payload_ref": "s3://audit/events/ev_01H...json",
  "prev_hash": "sha256:ffff...",      // hash of previous record (entire JSON)
  "this_hash": "sha256:5678..."        // hash of this record EXCLUDING this_hash field
}
```

### 10.2 Storage

- **Dev (Railway):** local JSONL file, rotated daily, `prev_hash` chain maintained.
- **Prod (AWS):** writes go to CloudWatch Logs (operational) AND S3 with **Object Lock in compliance mode** (legal). S3 is the legal record. Retention: 7 years for Zororo (FSCA + POPIA), configurable for personal projects.

### 10.3 Acceptance criteria (Audit)

- F1. A daily Lambda recomputes the chain over the prior day's records. A break triggers a P1 alert.
- F2. The first record of each day commits to the previous day's last record's hash, so days form a chain too.
- F3. PII redaction happens before write. A test corpus verifies no recognizer-detectable PII appears in any audit record.
- F4. The audit writer is the ONLY component with write permission to the audit S3 bucket; even the platform admin role cannot delete (Object Lock + bucket policy).

---

## 11. Deployment Path: Railway/Vercel → AWS af-south-1

### 11.1 What can run where

| Component | Railway/Vercel (dev/proto) | AWS af-south-1 (prod) |
|---|---|---|
| Frontend | Vercel | CloudFront + S3 |
| API runtime | Railway (Docker) | ECS Fargate or App Runner |
| Postgres + pgvector | Railway Postgres | RDS Postgres (Multi-AZ) |
| Object storage | Railway volumes | S3 + Object Lock |
| Secrets | Railway/Doppler | Secrets Manager |
| KMS | ❌ | KMS (per-environment CMK) |
| Audit log (legal record) | ❌ (dev-only chain) | S3 Object Lock |
| Special data (POPIA s.26) | ❌ **forbidden** | ✅ |

### 11.2 Hard rule for Zororo work

**No Zororo-Phumulani or KGA Life data of any kind — including dev fixtures, synthetic samples derived from real data, or screenshots of real records — may touch Vercel or Railway.** Use synthetic-only test data generated by a SA ID generator script (`scripts/synth_sa_data.py`).

For Zororo prototyping, use a **dedicated AWS dev account in af-south-1** behind SSO. The agent must refuse to scaffold Zororo projects pointing at Railway/Vercel runtimes.

### 11.3 Promotion checklist (the agent runs this)

When promoting a project from prototype to production, the agent generates and presents this checklist:

- [ ] All `[CONFIGURE]` components rebound to AWS equivalents
- [ ] KMS CMKs created per environment; data keys enveloped
- [ ] Secrets migrated from Doppler/Railway to Secrets Manager
- [ ] Audit log destination switched to S3 Object Lock bucket
- [ ] Terraform `prod` workspace plan reviewed and applied
- [ ] DPIA reviewed (enterprise tier; see Section 13)
- [ ] Penetration test scope updated
- [ ] DNS, TLS (ACM), WAF rules in place
- [ ] CloudWatch alarms for SOC failures, audit chain breaks, KMS errors
- [ ] Runbook drafted for top-5 incident scenarios

---

## 12. Terraform Layout

```
infra/terraform/
├── modules/
│   ├── network/             # VPC, private subnets, NAT, VPC endpoints
│   ├── data/                # RDS+pgvector, S3 audit bucket, KMS
│   ├── runtime/             # ECS Fargate service, ALB, autoscaling
│   ├── observability/       # CloudWatch, X-Ray, alarms
│   └── soc/                 # Lambdas (chain-verifier, anomaly-stats)
├── envs/
│   ├── dev/                 # cheap, single-AZ, no Object Lock
│   ├── staging/             # mirrors prod topology
│   └── prod/                # Multi-AZ, Object Lock, full alarms
└── policies/                # IAM policies as JSON, per role
```

### 12.1 Acceptance criteria (Terraform)

- G1. `terraform plan` is run in CI on every PR; non-empty plans require human approval before merge.
- G2. State stored in S3 with DynamoDB lock; no local state.
- G3. No resource is created without tags: `Owner`, `Project`, `Tier`, `DataClassification`, `CostCenter`.
- G4. KMS keys have rotation enabled; `deletion_window_in_days = 30`.
- G5. Production S3 buckets have Object Lock enabled at creation (cannot be added later).

---

## 13. POPIA Operating Model (enterprise tier — Zororo / KGA)

The architecture provides controls. Compliance also requires *processes*. The agent must scaffold these documents on first run of an enterprise-tier project:

| Document | Location | Trigger |
|---|---|---|
| Processing Register | `docs/popia/processing-register.md` | On project init |
| DPIA (Data Protection Impact Assessment) | `docs/popia/dpia.md` | When `data_classification = special` |
| Data Subject Request runbook | `docs/popia/dsr-runbook.md` | On project init |
| Sub-processor list | `docs/popia/sub-processors.md` | Every PR that adds an integration |
| Retention schedule | `docs/popia/retention.md` | On project init |
| Information Officer designation | `docs/popia/io.md` | On project init |
| Cross-border transfer log | `docs/popia/cross-border.md` | When LLM provider is non-ZA |

The cross-border transfer log is critical: every Anthropic API call is, technically, a cross-border processing event. POPIA s.72 requires a lawful basis. The default basis used by this OS is **s.72(1)(b) — adequate level of protection via contractual safeguards** (Anthropic's DPA). The log records: timestamp, data classification, lawful basis, safeguard reference. The agent emits this log automatically — the human just reviews it monthly.

---

## 14. Repository Layout (canonical)

```
project-root/
├── MANIFEST.yaml
├── README.md
├── CHANGELOG.md
├── docs/
│   ├── architecture.md
│   ├── threat-model.md
│   └── popia/                       # enterprise tier only
├── soc/
│   ├── events/
│   ├── pipeline.py
│   ├── dlp/
│   │   ├── presidio_setup.py
│   │   └── recognizers/             # SA-specific
│   ├── policy/                      # OPA client
│   ├── risk/
│   ├── decision.py
│   └── audit/
├── mcp/
│   ├── gateway.py
│   ├── capability.py                # token issuer + verifier
│   └── tools/                       # one file per tool
├── agents/
│   └── graphs/                      # LangGraph graphs
├── rag/
│   ├── ingest.py
│   ├── retriever.py
│   └── filters.py                   # tenant + classification filters
├── policies/                        # Rego
├── infra/terraform/
├── scripts/
│   ├── synth_sa_data.py
│   ├── audit_chain_verify.py
│   └── popia_dsr_handler.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── soc/                         # SOC-specific contract tests
│   └── corpus/                      # PII test corpus (synthetic only)
└── .github/workflows/               # CI: tests, gitleaks, terraform plan
```

---

## 15. Coding Agent Behaviour (Claude Code specifically)

When you (the agent) operate on this OS:

1. **Read the manifest first.** Refuse to act on projects without one.
2. **Plan before code.** Output a numbered plan covering files to create/modify, libraries to install, IaC modules touched, tests to write. Wait for human approval.
3. **Tests are not optional.** If a module has no test, the module is not done. Generate tests in the same pass.
4. **Refuse silent downgrades.** If you cannot implement a tier-A control on the current target, say so and propose alternatives.
5. **Cite the spec section.** When you make a non-obvious decision, link it to the section of this spec that justifies it (e.g. "Per §9.1, capability token TTL = 60s").
6. **Never invent a recognizer.** If a regulation, format, or API isn't documented, ask. Do not guess KGA's policy number format.
7. **Ask before broadening scope.** If a request implies changes beyond the stated task (e.g. "fix this bug" but the fix would touch the SOC pipeline), surface that and wait.
8. **Preserve audit-chain integrity in code edits.** Refactors of the audit module require regenerating chain-verification tests in the same change.

---

## Appendix A — Threat Model (STRIDE, abbreviated)

Trust boundaries: (1) public internet → API edge, (2) API → SOC pipeline, (3) SOC → MCP Gateway → tools, (4) Tools → external systems (KGA, LLM providers).

| Threat | Boundary | Control |
|---|---|---|
| **S**poof a human approver | (1)→(2) | Cognito MFA, capability tokens bound to `sub` |
| **T**amper with audit log | (3) post-write | S3 Object Lock + hash chain + daily verifier |
| **R**epudiate a decision | (2) | Decision record stored verbatim, signed |
| **I**nformation disclosure (PII leak via logs) | (2) | Presidio redaction before log write; unit-tested |
| **I**nformation disclosure (PII leak via LLM) | (3)→(4) | Pre-prompt DLP; post-response DLP; cross-border log |
| **D**oS via expensive tool calls | (3) | Per-actor cost cap, rate limit at gateway |
| **E**levation via MCP | (3) | Capability tokens, scope check, no internal bypass |
| Prompt injection via RAG content | (3) | Output schema validation; quarantine of low-trust sources; classifier on retrieved chunks |
| Cross-tenant data leak | (3) | Mandatory `tenant_id` filter on every retrieval; integration test enforces it |
| Key compromise | All | KMS-backed signing; rotation; short TTLs |

This is the *minimum* threat model. Each project's `docs/threat-model.md` extends it.

---

## Appendix B — Quarantined (v3.x) Roadmap

These are explicitly **not in v3.0**. They are listed so the agent does not get distracted into building them.

- ML-based anomaly detection (currently rules + sliding-window stats)
- Vector-based threat intelligence memory
- Automated penetration test agent
- Grafana dashboard UI (use AWS Managed Grafana for now)
- Multi-LLM routing (Claude is primary by spec)
- Real-time consent-receipt blockchain (overengineered)

If a request asks for these, the agent must answer: "This is in the v3.x roadmap, not v3.0. Adding it requires a spec amendment."

---

## Appendix C — Glossary

- **Special personal information** — POPIA s.26 categories: religion, race, health, sex life, biometric, criminal behaviour, children's data.
- **Lawful basis** — POPIA s.11: consent, contract, legal obligation, vital interest, public body function, legitimate interest.
- **DPIA** — Data Protection Impact Assessment, recommended by the Information Regulator for high-risk processing.
- **Information Officer** — POPIA s.55-56; for Zororo this is a designated role with statutory duties.
- **TCF** — Treating Customers Fairly, FSCA framework; relevant to KGA Life as an authorised FSP.

---

## End of Spec

If anything in this document is ambiguous, the agent must ask before acting. Ambiguity is not a license to choose; it is a signal to clarify.
