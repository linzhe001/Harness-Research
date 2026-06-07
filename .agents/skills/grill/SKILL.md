---
name: grill
description: "Clarify early research intent through hard questions and produce draft-only Research Intent, Grill Round Log, and Execution Readiness Packet artifacts. Does not approve contracts or complete WF1-WF3 by itself."
---

# Grill

## Purpose

Use Grill to make the operator's research intent explicit before execution
automation starts. Grill is high-interaction and draft-only: it challenges the
idea, records candidate readiness inputs, and helps the operator decide whether
to bridge into canonical WF1-WF3 Skills.

## Conversation Contract

Grill is conversation-first. Do not begin by producing a completed draft,
approval, or long questionnaire. Start by restating the current intent in one
short paragraph, then ask 3-5 blocking questions that would change the next
safe action. Each question must include why it matters.

Every Grill round must leave:

- operator answer summary
- skeptic, methodologist, implementation, or claim-boundary critique
- current gap check
- next blocking question or explicit exit choice
- exit recommendation
- human exit decision status

The operator owns the exit decision. The agent may recommend
`continue_grill`, `grill_draft_ready`, `bridge_wf1_wf3`, `pivot`, or
`abandon`, but must not declare an exit decision unless the operator made that
decision in the current conversation or an auditable artifact.

## Maturity Target

Grill is ready to hand off only when these fields are at least candidate-clear
and the remaining uncertainty is explicit:

- concrete operator observation
- candidate claim
- falsifier or not-worth-continuing result
- target metric or evaluation signal
- expected baseline or negative control
- dataset / compute assumptions
- maximum claim boundary and forbidden claims
- pivot / abort condition
- execution readiness inputs that would otherwise stop `prepare`

If any of these are missing, continue discussion or record the missing item as
an unresolved question. Do not hide the gap by writing a polished draft.

## Question Policy

Ask fewer, harder questions. Avoid questions that can be answered by reading
the repository, broad survey prompts, generic approvals, and long intake forms.
Prefer questions that force a decision about claim shape, failure criteria,
baseline risk, metric validity, data/compute readiness, or what should happen
if the first experiment fails.

## References

Read these first:
- `../../../AGENTS.md`
- `../../../CLAUDE.md`
- `../../../docs/grill_execution_supervisor.md`
- `../../../docs/grill_execution_supervisor_implementation_plan.md`
- `../../../.agents/skills/init-project/SKILL.md`
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/contract-gating-rule.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/ubiquitous-language.md`

## Outputs

Grill may create or refresh:
- `docs/Research_Intent_Draft.md`
- `docs/Grill_Round_Log.md`
- `docs/Execution_Readiness_Packet.md`
- `.workflow_supervisor/readiness.json` only when Grill readiness tooling is
  run with a write action, or when supervisor tooling produces it

Exact local paths, commands, budgets, and private values belong in
`.workflow_supervisor/readiness.json`. Public Markdown should redact sensitive
values and mark them as candidate inputs until readiness preflight verifies
them.

Grill does not create `PROJECT_STATE.json`, `project_map.json`, or
`iteration_log.json`. Those are canonical research-workspace state files owned
by later workflow/state tooling, stable build planning, and WF10 iteration.

## Tooling

Prefer the Grill helpers for durable draft writes:
- `python tooling/grill/questions.py --lens intake` prints a reusable question
  round contract with gap template and exit options. Lenses: `facilitator`,
  `intake`, `skeptic`, `methodologist`, `implementation`, `claim_boundary`.
- `python tooling/grill/draft.py --workspace-root . init --seed "<idea>"`
  initializes draft Markdown artifacts without overwriting existing drafts.
- `python tooling/grill/draft.py --workspace-root . round --lens skeptic \
  --answer-summary "<summary>" --gap-check "<gap>" \
  --next-question "<question>" --exit-recommendation continue_grill`
  appends a Grill round contract.
- `python tooling/grill/draft.py --workspace-root . packet \
  --readiness-json <path>` renders the public readiness packet with local
  values redacted.
- `python tooling/grill/readiness.py --workspace-root . --check \
  --verify-paths --json` validates readiness shape and path-kind inputs
  without writing runtime state.
- `python tooling/grill/readiness.py --workspace-root . --write-readiness \
  --input-json <path> --json` writes supervisor-owned
  `.workflow_supervisor/readiness.json` after validation.

Use `--write-readiness` only when intentionally writing supervisor-owned
`.workflow_supervisor/readiness.json` through tooling.

## Boundaries

- Do not mark WF1, WF2, or WF3 complete from Grill output alone.
- Do not create Approved Contracts or Approval Evidence.
- Do not write `.evidence/**` directly.
- Do not write `.workflow_supervisor/**` by hand; use tooling.
- Do not promote Grill draft facts into current docs without the relevant
  Stage Skill, Evidence Chain tooling, or explicit bridge path.

## Bridge Rule

`harness grill --bridge-stages` may use an accepted Research Intent Draft as
context for `$survey-idea`, `$idea-debate`, and `$refine-idea`. A Stage is
complete only when its canonical artifact and Gate ledger exist.

## Init Handoff Rule

When the operator explicitly confirms `grill_draft_ready` or asks to proceed
from an accepted Grill draft, continue in the same turn with
`$init-project update-from-grill` unless the operator asks to skip guidance
initialization. The handoff inputs are:

- `docs/Research_Intent_Draft.md`
- `docs/Grill_Round_Log.md`
- `docs/Execution_Readiness_Packet.md`
- `.workflow_supervisor/readiness.json` when supervisor tooling has produced it

The handoff initializes or refreshes `CLAUDE.md`, `AGENTS.md`, and `README.md`
from candidate Grill context only. It must preserve `## Custom`, keep dataset
and baseline items marked as candidate until `prepare` / WF4-WF5 verify them,
and must not mark WF1-WF3 complete. It does not create `PROJECT_STATE.json`,
`project_map.json`, or `iteration_log.json`. If the handoff is not run, report
`init_project_update_from_grill_or_NOT_RUN` with the reason.

## Exit Condition

Return one of:
- `continue_grill`: blocking gaps remain and the next question is clear.
- `grill_draft_ready`: draft artifacts exist, unresolved questions are clear,
  the operator chose to hand off the draft, and
  `$init-project update-from-grill` has run or is reported as `NOT_RUN`.
- `grill_bridge_complete`: canonical WF1-WF3 artifacts and Gate ledger exist.
- `pivot` or `abandon`: operator chose not to proceed with the draft.

Report a Gate ledger for any durable writes or skipped checks.
