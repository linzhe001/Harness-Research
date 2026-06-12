---
name: survey-idea
description: "Internal Harness instruction source for survey-idea. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Survey Idea

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/research-invariants.md`
- `../../../.agents/references/ubiquitous-language.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `./references/feasibility-report.md`
- `../../../PROJECT_STATE.json` if it exists

## When To Use

Use this skill for WF1 when the user wants to know whether a research idea is worth pursuing.

## Required Work

1. Extract the idea description, keywords, target venue, and time window.
2. Run an Explore Intake Grill before broad research when the user's goal,
   motivation, target task/data/user, success shape, non-goals, resource
   constraints, preferences, or known concerns are missing or ambiguous.
   Ask only the questions needed to map intent to survey keywords, competitor
   search, baseline candidates, metric candidates, and open questions.
3. Use web research to find recent related work, top competitors, and failure cases.
4. Run an Explore Synthesis Grill after collecting Source Artifacts when
   evidence conflicts, baseline choices, metrics, Claim Boundary, first
   vertical slice, or pivot/abort conditions remain unclear. Each question
   must name the downstream artifact it affects.
5. Build the canonical feasibility output:
   - weighted score
   - gap matrix
   - top competitor analysis
   - prerequisite checklist
   - risk table
   - final recommendation
6. When the project uses or requests the dynamic context layout, also write or refresh:
   - `docs/30_evidence/Evidence_Index.md`
   - `docs/30_evidence/Paper_Table.md`
   - `docs/30_evidence/Repo_Table.md`
   - `docs/30_evidence/Dataset_Table.md`
   - `docs/30_evidence/Baseline_Table.md`
   - `docs/30_evidence/Metric_Table.md`
   - `docs/30_evidence/Open_Questions.md`
7. Write `docs/Feasibility_Report.md` using the canonical template.
8. Update `PROJECT_STATE.json` if the user wants stage-state synchronization.

## Context Budget

- Use 8-12 source artifacts by default; store extra candidates by path instead
  of pasting full text.
- Limit competitor analysis to Top 5 and Grill rounds to 3-5 questions.

## Durable Docs Render

After stable Markdown outputs for this skill are finalized, invoke `$docs-site` or report `docs_site_boundary_report`. Do not render after temporary draft edits; Markdown remains the source of truth.

## Output Rules

- Use the template at `./references/feasibility-report.md`.
- Keep the `context_summary` block.
- Include evidence sources and separate verified facts from inferences.
- Keep the Grill sections as intent records and open-question routing, not as
  Gate Evidence or Human Approval.
- Treat `docs/30_evidence/**` as evidence tables only; do not turn findings into approved field rules.
- Use the canonical decision vocabulary: `PROCEED`, `PIVOT`, or `ABANDON`.
- Report a Gate ledger when evidence tables, protocol drafts, the feasibility report, or canonical state are written. If protocol compilation or workflow-state checks are not run, mark them `NOT_RUN` with the reason.
- Treat template wording as structure-only; localize headings and narrative text according to `../../../.agents/references/language-policy.md` unless a field is explicitly English-only.
- Route new projects to WF2 `$idea-debate` before WF3 refine-idea, even when one direction appears strongest. If only one idea exists, WF2 should compare conservative, balanced, and aggressive variants.

## Codex Adaptation

- Treat natural-language requests as the canonical `$survey-idea` invocation.
- Ask the user directly only if core idea details are missing.
- Preserve the original artifact path and state-update behavior.

## Execution Rule

Follow the local report template and language policy closely; do not replace the scoring or recommendation structure with a generic summary.

## Durable Docs Render

After stable Markdown is finalized, invoke `$docs-site` or report
`docs_site_boundary_report` / `docs_site_render_or_NOT_RUN`. Do not render for
temporary drafts.
