# Proactive Sentinel - Roadmap

## Phase 1 - Core SOC Service (Complete)
- Flask application factory with tenant auth
- AES-256-GCM column encryption
- PII masking layer
- Rule-based detection engine
- SHA-256 alert fingerprinting in Redis
- MITRE ATT&CK attack chain correlation
- Per-IP and per-unit velocity detection with auto-ban
- OpenTelemetry instrumentation
- Docker Compose packaging
- pytest suites for auth, PII masking, detection, tenant isolation

## Phase 2 - Hardening (Current)
- Full tenant isolation regression test suite
- Manual unban UI or CLI for every auto-ban mechanism
- Detection rule tuning per tenant without code changes
- Alert data retention policy per tenant
- Redis TTL explicitly set on all fingerprint keys

## Phase 3 - Operations
- Tenant management dashboard
- Alert export and reporting per tenant
- Detection rule configuration interface per tenant

## Phase 4 - AI Enhancement (Future - requires Agent 4 review)
- LLM-based threat summarisation (masked telemetry only)
- Human-in-the-loop gate required before any LLM touches alert data
- Separate constitution required before this phase begins

## Rule
Tenant isolation test suite must pass before every phase completes.
No phase begins without Mike's approval.

---

## MIKE - HUMAN IN THE LOOP (NON-NEGOTIABLE - CANNOT BE BYPASSED)

Mike Ncube is the sole human decision maker in this system.
No agent, model, or automated process has authority to override Mike.
Every agent exists to serve Mike's intent - not to replace his judgment.

### MIKE MUST APPROVE BEFORE ANY OF THESE HAPPEN

Code and Development:
- Any code is written beyond a planning or spec draft
- Any file is created, modified, renamed, or deleted in a project
- Any dependency is added, upgraded, or removed
- Any refactor that touches more than one file
- Any database migration or schema change
- Any new API endpoint or change to an existing endpoint

Infrastructure and Deployment:
- Any deployment to any environment (dev, staging, production)
- Any Railway, Vercel, or AWS configuration change
- Any Docker or Docker Compose change that affects running services
- Any Terraform plan is applied
- Any new cloud resource is created or destroyed

Cost and Models:
- Any premium model is used (Codex, Claude Opus, Grok, Claude Opus
  high thinking)
- Any task estimated to cost more than R50 in a single run
- Monthly spend crosses R500 (Yellow status)
- Monthly spend crosses R800 (Red status - full stop)

Security and Compliance:
- Any change to authentication, encryption, or PII handling
- Any change to rate limiting or auto-ban logic
- Any change to audit trail structure
- For Zororo: any change that could affect FSP48558 licence compliance
- For Sentinel: any change to tenant isolation or MITRE ATT&CK mappings

AI and Agents:
- Any new agent or LLM component is introduced to a project
- Any prompt template is modified in production
- Any change to agent handoff or fallback logic
- Any LLM component is given access to unmasked PII

### HOW MIKE GIVES APPROVAL

Mike approves by typing one of these exact responses:
- CONFIRMED - proceed exactly as planned
- CONFIRMED WITH CHANGES - proceed but apply the changes Mike specifies
- STOP - do not proceed, reassess and re-present the plan
- SKIP - skip this specific check but continue the session
- ABORT - stop everything and return to session start

No agent interprets silence as approval.
No agent interprets a partial response as approval.
If Mike's response is unclear, Agent 6 asks for clarification before
any action is taken.

### WHAT AGENTS MUST SHOW MIKE BEFORE ASKING FOR APPROVAL

Before every approval request, the requesting agent must show Mike:

1. What is about to happen - plain English description, no jargon
2. Why it is happening - which part of the spec or plan requires this
3. What files or systems will be affected - specific list
4. What the rollback plan is if something goes wrong
5. Estimated cost in ZAR if a premium model or cloud resource is involved
6. Risk level - Low / Medium / High with one sentence explanation

Format every approval request like this:

---APPROVAL REQUIRED---
Action:       [what is about to happen in plain English]
Reason:       [why this is needed - reference to spec or plan]
Affects:      [specific files, services, or systems]
Rollback:     [how to undo this if it goes wrong]
Cost:         [R amount or ZERO if no cost]
Risk:         [Low / Medium / High - one sentence reason]
Token status: [current GREEN / YELLOW / RED and monthly spend]

Type CONFIRMED to proceed or STOP to cancel.
-----------------------

### MIKE CAN PAUSE OR STOP ANYTHING AT ANY TIME

At any point in any session Mike can type:
- PAUSE - agents stop immediately and wait for Mike to resume
- EXPLAIN - agents stop and explain what they were about to do before
  continuing
- SHOW PLAN - agents display the full remaining plan for Mike to review
  before any further action
- ROLLBACK - agents immediately revert the last completed action
- ABORT SESSION - all agents stop, all pending actions are cancelled,
  session ends cleanly

These commands work at any point - mid-task, mid-deployment, mid-debate.
No agent continues past one of these commands without Mike explicitly
resuming.

### MIKE IS NEVER RUSHED

No agent uses language that creates urgency or pressure.
No agent says things like "we should do this quickly" or "time is critical".
No agent presents a single option as the only option.
No agent makes a decision feel irreversible before Mike has confirmed.

Every decision has time for Mike to think.
Every plan can be paused and resumed.
Every action can be rolled back.

### END OF SESSION

At the end of every session Agent 6 asks Mike:
"Before we close - is there anything you want me to remember for next
session, any decisions you want documented, or any spec files that need
updating based on what we built today?"

Agent 9 then displays the full session summary:

---SESSION SUMMARY---
Date:              [date]
Project:           [project name]
Goal achieved:     YES / PARTIAL / NO
Actions taken:     [list of every action Mike approved]
Actions skipped:   [list of anything Mike stopped or skipped]
Files changed:     [list of every file created or modified]
Models used:       [list of models used this session]
Session cost:      R[amount]
Monthly spend:     R[amount] of R1000
Budget remaining:  R[amount]
Risks to monitor:  [any risks identified during the session]
Next steps:        [what was agreed for next session]
---------------------

Mike reviews and types CONFIRMED to close the session cleanly or
HOLD to keep the session open for follow-up actions.
