---
name: survey-idea
description: Codex wrapper for WF1 idea survey and feasibility analysis. Use when the user wants literature-backed validation of a new research idea and a `docs/Feasibility_Report.md` outcome.
---

# Survey Idea

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/research-invariants.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
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
4. When the project uses or requests the dynamic context layout, also write or refresh:
   - `docs/30_evidence/Evidence_Index.md`
   - `docs/30_evidence/Paper_Table.md`
   - `docs/30_evidence/Repo_Table.md`
   - `docs/30_evidence/Dataset_Table.md`
   - `docs/30_evidence/Baseline_Table.md`
   - `docs/30_evidence/Metric_Table.md`
   - `docs/30_evidence/Open_Questions.md`
5. Write `docs/Feasibility_Report.md` using the canonical template.
6. Update `PROJECT_STATE.json` if the user wants stage-state synchronization.

## Output Rules

- Use the template at `./references/feasibility-report.md`.
- Keep the `context_summary` block.
- Include evidence sources and separate verified facts from inferences.
- Treat `docs/30_evidence/**` as evidence tables only; do not turn findings into approved field rules.
- Use the canonical decision vocabulary: `PROCEED`, `PIVOT`, or `ABANDON`.
- Treat template wording as structure-only; localize headings and narrative text according to `../../../.agents/references/language-policy.md` unless a field is explicitly English-only.
- Route new projects to WF2 `$idea-debate` before WF3 refine-idea, even when one direction appears strongest. If only one idea exists, WF2 should compare conservative, balanced, and aggressive variants.

## Codex Adaptation

- Treat natural-language requests as the canonical `$survey-idea` invocation.
- Ask the user directly only if core idea details are missing.
- Preserve the original artifact path and state-update behavior.

## Execution Rule

Follow the local report template and language policy closely; do not replace the scoring or recommendation structure with a generic summary.
