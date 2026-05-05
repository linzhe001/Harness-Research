---
name: idea-debate
description: Codex wrapper for WF2 idea debate. Use after WF1 feasibility to stress-test candidate research directions before WF3 refine-idea and before any architecture design.
---

# Idea Debate

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/research-invariants.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `../../../.agents/references/reviewer-independence.md`
- `../../../.agents/references/review-tracing.md`
- `./references/idea-debate-report.md`
- `../../../PROJECT_STATE.json` if it exists
- `../../../docs/Feasibility_Report.md` if it exists
- `../../../docs/30_evidence/Evidence_Index.md` if it exists
- `../../../docs/35_protocol/Research_Protocol.md` if it exists

## When To Use

Use this skill for WF2 after WF1 survey.

For new projects this is a numbered required stage. Legacy projects that predate
WF2 idea-debate may warn instead of failing, but new dynamic-context projects
should not skip from WF1 directly to architecture design.

## Required Work

1. Re-read `docs/Feasibility_Report.md`, existing project state, relevant local code/docs, and any user-provided idea notes.
2. Extract 2-6 candidate ideas or variants. If only one idea exists, create conservative/balanced/aggressive variants.
3. For each candidate, document:
   - strongest objection
   - most likely failure mode
   - minimum viable experiment
   - kill criteria
   - estimated compute and implementation effort
   - fallback or pivot path
4. When an external reviewer is available, follow reviewer independence and tracing protocols for a fresh critique of the candidate artifacts.
5. When dynamic context is enabled, write or refresh `docs/35_protocol/Research_Protocol.md`, `docs/35_protocol/Protocol_Assumptions.md`, and `docs/35_protocol/Protocol_Changelog.md` with project-local protocol implications.
6. Write `docs/Idea_Debate.md` using the local template.
7. Update `PROJECT_STATE.json` when stage-state synchronization is requested or required by the orchestrator.

## Output Rules

- Use `./references/idea-debate-report.md`.
- Include `Evidence Sources` and separate verified facts from inferences.
- Protocol updates are drafts only; do not mark them as approved contracts.
- Keep the final recommendation explicit: `SELECT`, `PILOT_FIRST`, `MERGE`, `PIVOT`, or `ABANDON`.
- Report a Gate ledger when the debate report, protocol drafts, reviewer traces, or canonical state are written. If protocol compilation, drift checks, reviewer passes, or workflow-state checks are not run, mark them `NOT_RUN` with the reason.
- Treat template wording as structure-only; localize headings and narrative text according to `../../../.agents/references/language-policy.md` unless a field is explicitly English-only.

## Execution Rule

Use this skill to reduce idea risk before WF3 refine-idea. Do not turn it into another generic feasibility summary or an architecture design stage.
