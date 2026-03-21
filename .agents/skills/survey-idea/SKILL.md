---
name: survey-idea
description: Codex wrapper for WF1 idea survey and feasibility analysis. Use when the user wants literature-backed validation of a new research idea and a `docs/Feasibility_Report.md` outcome.
---

# Survey Idea

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `./references/feasibility-report.md`
- `../../../PROJECT_STATE.json` if it exists

## When To Use

Use this skill for WF1 when the user wants to know whether a research idea is worth pursuing.

## Required Work

1. Extract the idea description, keywords, target venue, and time window.
2. Use web research to find recent related work, top competitors, and failure cases.
3. Build the canonical feasibility output:
   - weighted score
   - gap matrix
   - top competitor analysis
   - prerequisite checklist
   - risk table
   - final recommendation
4. Write `docs/Feasibility_Report.md` using the canonical template.
5. Update `PROJECT_STATE.json` if the user wants stage-state synchronization.

## Output Rules

- Use the template at `./references/feasibility-report.md`.
- Keep the `context_summary` block.
- Use the canonical decision vocabulary: `PROCEED`, `PIVOT`, or `ABANDON`.

## Codex Adaptation

- Treat natural-language requests as the canonical `$survey-idea` invocation.
- Ask the user directly only if core idea details are missing.
- Preserve the original artifact path and state-update behavior.

## Execution Rule

Follow the local report template closely; do not replace the scoring or recommendation structure with a generic summary.
