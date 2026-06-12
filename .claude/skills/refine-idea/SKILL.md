# WF3: Refine Idea

Use this skill after WF1 survey and WF2 idea debate.

Read first:
- `PROJECT_STATE.json` if it exists
- `OPERATOR_CONTEXT.md` if it exists
- `docs/Feasibility_Report.md` if it exists
- `docs/Idea_Debate.md` if it exists
- `docs/30_evidence/Evidence_Index.md` if it exists
- `docs/35_protocol/Research_Protocol.md` if it exists
- `templates/refined-idea.md`
- `../../shared/context-layering-policy.md`
- `../../shared/research-invariants.md`
- `../../shared/ubiquitous-language.md`
- `../../shared/documentation-evidence-rule.md`
- `../../shared/documentation-style.md`
- `../../shared/language-policy.md`

Required work:
1. Use WF1 Grill records as intent inputs. Do not rerun a full Grill here; only ask blocking questions that affect success criteria, kill criteria, pivot triggers, or Contract readiness.
2. Identify the selected idea or variant and record why alternatives were rejected or deferred.
3. Define problem statement, target task, data assumptions, candidate baselines, target metrics, success criteria, minimum viable experiment, kill criteria, pivot triggers, and candidate vocabulary signals for WF6/WF7 to use when generating or refining `docs/20_facts/Project_Glossary.md`.
4. Record open questions that must be resolved by WF4 data-prep or WF5 baseline-repro.
5. When dynamic context is enabled, refresh draft protocol assumptions or run `/protocol-compiler` if evidence tables changed.
6. Write `docs/Refined_Idea.md`.
7. Update `PROJECT_STATE.json` when stage synchronization is required.

Do not write architecture, module plans, file trees, or implementation roadmaps. Architecture design belongs to WF6 after data and baseline evidence exist.

## Durable Docs Render

After stable Markdown outputs for this skill are finalized, invoke `/docs-site` or report `docs_site_boundary_report`. Do not render after temporary draft edits; Markdown remains the source of truth.

## Durable Docs Render

After stable Markdown is finalized, invoke `/docs-site` or report
`docs_site_boundary_report` / `docs_site_render_or_NOT_RUN`. Do not render for
temporary drafts.
