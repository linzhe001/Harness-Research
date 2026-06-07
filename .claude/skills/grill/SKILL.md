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

Grill is conversation-first. Start by restating the current intent in one short
paragraph, then ask 3-5 blocking questions that would change the next safe
action. Each question must include why it matters. Do not begin with a polished
draft, approval, or long questionnaire.

Every Grill round must leave an operator answer summary, critique lens,
current gap check, next blocking question or explicit exit choice, exit
recommendation, and human exit decision status. The operator owns the exit
decision. You may recommend `continue_grill`, `grill_draft_ready`,
`bridge_wf1_wf3`, `pivot`, or `abandon`, but must not declare the decision
unless the operator made it in the current conversation or an auditable
artifact.

The handoff target is candidate-clear intent: concrete observation, candidate
claim, falsifier, metric/evaluation signal, baseline or negative control,
dataset/compute assumptions, maximum claim boundary, forbidden claims,
pivot/abort condition, and execution readiness inputs that would otherwise
stop `prepare`. Missing items stay as unresolved questions.

Read the mechanism and implementation plan, workflow guide, context layering,
contract gating, documentation rules, language policy, and ubiquitous language
before durable edits. Keep exact local/private values in
`.workflow_supervisor/readiness.json` through tooling; redact public Markdown.

Outputs:
- `docs/Research_Intent_Draft.md`
- `docs/Grill_Round_Log.md`
- `docs/Execution_Readiness_Packet.md`
- `.workflow_supervisor/readiness.json` only when Grill readiness tooling is
  run with a write action, or when supervisor tooling produces it

Prefer helper commands for durable draft writes:
- `python tooling/grill/questions.py --lens intake`
- `python tooling/grill/draft.py --workspace-root . init --seed "<idea>"`
- `python tooling/grill/draft.py --workspace-root . round --lens skeptic --answer-summary "<summary>" --gap-check "<gap>" --next-question "<question>" --exit-recommendation continue_grill`
- `python tooling/grill/draft.py --workspace-root . packet --readiness-json <path>`
- `python tooling/grill/readiness.py --workspace-root . --check --verify-paths --json`
- `python tooling/grill/readiness.py --workspace-root . --write-readiness --input-json <path> --json`

Use `--write-readiness` only when intentionally writing supervisor-owned
`.workflow_supervisor/readiness.json` through tooling.
Grill does not create `PROJECT_STATE.json`, `project_map.json`, or
`iteration_log.json`; those are owned by later workflow/state tooling, stable
build planning, and WF10 iteration.

When the operator explicitly confirms `grill_draft_ready` or asks to proceed
from an accepted Grill draft, continue in the same turn with
`/init-project update-from-grill` unless the operator asks to skip guidance
initialization. The handoff reads `docs/Research_Intent_Draft.md`,
`docs/Grill_Round_Log.md`, `docs/Execution_Readiness_Packet.md`, and
`.workflow_supervisor/readiness.json` when supervisor tooling has produced it.
It initializes or refreshes `CLAUDE.md`, `AGENTS.md`, and `README.md` from
candidate Grill context only; dataset and baseline items remain candidate
until `prepare` / WF4-WF5 verify them. Do not mark WF1-WF3 complete from this
handoff, and do not create `PROJECT_STATE.json`, `project_map.json`, or
`iteration_log.json`. If the handoff is skipped, report
`init_project_update_from_grill_or_NOT_RUN` with the reason.

Exit with `grill_draft_ready`, `grill_bridge_complete`, `pivot`, or `abandon`,
and report Gate Evidence for durable writes or skipped checks. A
`grill_draft_ready` exit requires `/init-project update-from-grill` to have run
or to be reported as `NOT_RUN`.
