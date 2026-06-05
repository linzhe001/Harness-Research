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

## References

Read these first:
- `../../../AGENTS.md`
- `../../../CLAUDE.md`
- `../../../docs/grill_execution_supervisor.md`
- `../../../docs/grill_execution_supervisor_implementation_plan.md`
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
- `.workflow_supervisor/readiness.json` through Grill or supervisor tooling

Exact local paths, commands, budgets, and private values belong in
`.workflow_supervisor/readiness.json`. Public Markdown should redact sensitive
values and mark them as candidate inputs until readiness preflight verifies
them.

## Tooling

Prefer the Grill helpers for durable draft writes:
- `python tooling/grill/questions.py --lens intake` prints a reusable question
  round. Lenses: `intake`, `skeptic`, `methodologist`, `implementation`.
- `python tooling/grill/draft.py --workspace-root . init --seed "<idea>"`
  initializes draft Markdown artifacts without overwriting existing drafts.
- `python tooling/grill/draft.py --workspace-root . round --lens skeptic \
  --answer-summary "<summary>" --risk "<risk>"` appends a Grill round.
- `python tooling/grill/draft.py --workspace-root . packet \
  --readiness-json <path>` renders the public readiness packet with local
  values redacted.
- `python tooling/grill/readiness.py --workspace-root . --check \
  --verify-paths --json` validates readiness shape and path-kind inputs
  without writing runtime state.

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

## Exit Condition

Return one of:
- `grill_draft_ready`: draft artifacts exist and unresolved questions are clear.
- `grill_bridge_complete`: canonical WF1-WF3 artifacts and Gate ledger exist.
- `pivot` or `abandon`: operator chose not to proceed with the draft.

Report a Gate ledger for any durable writes or skipped checks.
