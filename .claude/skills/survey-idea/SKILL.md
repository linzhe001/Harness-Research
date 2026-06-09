---
name: survey-idea
description: WF1 inspiration survey and gap analysis. Takes the user's research idea, performs literature search, gap analysis, competitor analysis, and feasibility scoring, then outputs Feasibility_Report.md.
argument-hint: "[idea description]"
disable-model-invocation: true
allowed-tools: WebSearch, WebFetch, Read, Write, Bash, Glob
---

# WF1: Inspiration Survey and Gap Analysis

Use this Skill for literature-backed feasibility assessment of a new research
idea. Output is `docs/Feasibility_Report.md` and related evidence tables. WF1
does not approve contracts.

## Read First

- `PROJECT_STATE.json` when present
- `templates/feasibility-report.md`
- shared language, documentation evidence, documentation style,
  context-layering, research-invariants, and ubiquitous-language rules
- current evidence tables when enabled

## Required Work

1. Parse idea description, keywords, target venue, and search window. Ask only
   for essential missing inputs.
2. Run an Explore Intake Grill before broad research when motivation, task,
   data, success shape, non-goals, resources, preferences, or known concerns
   are missing. Questions should map to survey keywords, competitor search,
   baseline candidates, metric candidates, or open questions.
3. Analyze the idea before scoring: contribution, problem type, dependencies,
   core assumption, hard constraints, and risk points.
4. Use WebSearch/WebFetch for multiple search rounds; do not rely on memory.
   Collect at least 10 relevant papers when available, including failure or
   limitation evidence.
5. After collecting Source Artifacts, run an Explore Synthesis Grill when
   evidence conflicts or baseline choices, metrics, Claim Boundary, first
   vertical slice, or pivot/abort conditions remain unclear.
6. Build gap matrix, Top 5 competitor analysis, feasibility scores,
   prerequisites, risks, and recommendation.
7. Write `docs/Feasibility_Report.md` using the template:
   feasibility score, gap matrix, competitor analysis, prerequisites, risk
   assessment, and `PROCEED` / `PIVOT` / `ABANDON` recommendation.
8. Refresh `docs/30_evidence/**` when enabled; keep Grill notes as intent/open
   questions, not Gate Evidence or Human Approval.
9. Update `PROJECT_STATE.json` with WF1 completion only when the report and
   required Gate ledger exist.

## Context Budget

- Use 8-12 source artifacts by default; store extra candidates by path.
- Limit competitor analysis to Top 5 and Grill rounds to 3-5 questions.

## Constraints

- Never give score above 8 without at least 3 supporting papers.
- Never recommend `PROCEED` when technical feasibility score is below 6.
- Always include at least one failed-attempt reference when found.
- Preserve decision vocabulary and template structure; localize prose according
  to language policy.
- After stable Markdown is finalized, invoke `/docs-site` or report
  `docs_site_render_or_NOT_RUN`.
