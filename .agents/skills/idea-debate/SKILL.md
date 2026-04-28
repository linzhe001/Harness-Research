---
name: idea-debate
description: Codex workflow for debating and stress-testing candidate research ideas after WF1 feasibility and before WF2 architecture design. Use when the user wants idea debate, devil's-advocate critique, minimum viable experiments, kill criteria, compute estimates, or `docs/Idea_Debate.md`.
---

# Idea Debate

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `../../../.agents/references/reviewer-independence.md`
- `../../../.agents/references/review-tracing.md`
- `./references/idea-debate-report.md`
- `../../../PROJECT_STATE.json` if it exists
- `../../../docs/Feasibility_Report.md` if it exists

## When To Use

Use this skill after WF1 when there are multiple plausible directions or when the chosen idea needs a skeptical debate before WF2.

This is a recommended gate, not a numbered workflow stage. Missing `docs/Idea_Debate.md` should warn but not break older projects.

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
5. Write `docs/Idea_Debate.md` using the local template.
6. Update `PROJECT_STATE.json` only if the user wants stage-state synchronization.

## Output Rules

- Use `./references/idea-debate-report.md`.
- Include `Evidence Sources` and separate verified facts from inferences.
- Keep the final recommendation explicit: `SELECT`, `PILOT_FIRST`, `MERGE`, `PIVOT`, or `ABANDON`.
- Treat template wording as structure-only; localize headings and narrative text according to `../../../.agents/references/language-policy.md` unless a field is explicitly English-only.

## Execution Rule

Use this skill to reduce idea risk before architecture design. Do not turn it into another generic feasibility summary.
