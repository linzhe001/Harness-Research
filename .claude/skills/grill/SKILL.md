---
name: grill
description: "Clarify early research intent through hard questions and produce draft-only Research Intent, Grill Round Log, and Execution Readiness Packet artifacts. Does not approve contracts or complete WF1-WF3 by itself."
argument-hint: "[seed idea or --bridge-stages]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Grill

Use `/grill` for high-interaction research intent clarification before
execution automation. It writes draft-only intent/readiness artifacts and must
not approve contracts or mark WF1-WF3 complete without the canonical Stage
artifacts and Gate ledger.

Read the mechanism and implementation plan, workflow guide, context layering,
contract gating, documentation rules, language policy, and ubiquitous language
before durable edits. Keep exact local/private values in
`.workflow_supervisor/readiness.json` through tooling; redact public Markdown.

Outputs:
- `docs/Research_Intent_Draft.md`
- `docs/Grill_Round_Log.md`
- `docs/Execution_Readiness_Packet.md`
- `.workflow_supervisor/readiness.json` through tooling

Prefer helper commands for durable draft writes:
- `python tooling/grill/questions.py --lens intake`
- `python tooling/grill/draft.py --workspace-root . init --seed "<idea>"`
- `python tooling/grill/draft.py --workspace-root . round --lens skeptic --answer-summary "<summary>" --risk "<risk>"`
- `python tooling/grill/draft.py --workspace-root . packet --readiness-json <path>`
- `python tooling/grill/readiness.py --workspace-root . --check --verify-paths --json`

Use `--write-readiness` only when intentionally writing supervisor-owned
`.workflow_supervisor/readiness.json` through tooling.

Exit with `grill_draft_ready`, `grill_bridge_complete`, `pivot`, or `abandon`,
and report Gate Evidence for durable writes or skipped checks.
