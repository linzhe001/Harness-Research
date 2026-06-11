---
name: evaluate
description: Codex wrapper for experiment analysis and decision-making. Use when the user wants metrics interpreted, a stage or iteration report written, and a NEXT_ROUND, DEBUG, CONTINUE, PIVOT, or ABORT recommendation.
---

# Evaluate

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/lesson-quality-rule.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `../../../.agents/references/reviewer-independence.md`
- `../../../.agents/references/review-tracing.md`
- `./references/stage-report.md`
- `../../../iteration_log.json`
- `../../../PROJECT_STATE.json`
- `../../../docs/10_contract/Evaluation_Contract.md` if it exists
- `../../../docs/50_memory/Lessons.md` if it exists

## When To Use

Use this skill when the user wants training or evaluation results interpreted and turned into a decision.

## Required Work

1. Parse the relevant logs, metrics, or checkpoint metadata.
2. Analyze:
   - training stability
   - convergence
   - overfitting
   - gradient and numerical issues
3. Resolve the tracked metric set from active iteration context or project state, and compare against baseline metrics and prior iterations using that protocol.
4. Produce the canonical report using `./references/stage-report.md`.
5. Write findings and lesson candidates to the iteration report and, when useful, `docs/50_memory/Lessons.md`.
6. Append or refresh `MEMORY.md` only when a lesson is accepted and satisfies `lesson-quality-rule.md`.
7. Recommend exactly one of:
   - `NEXT_ROUND` — ordinary improvement round, stay in WF10
   - `DEBUG` — fixable technical issue, stay in WF10
   - `CONTINUE` — handoff to orchestrator/WF11, not continue iterating
   - `PIVOT`
   - `ABORT`
8. If invoked from `$iterate`, do not take over stage-transition ownership.
9. Include evidence sources and keep unverifiable result interpretations under open questions.
10. Report a Gate ledger when iteration reports, stage reports, lesson files, `MEMORY.md`, or `iteration_log.json` are written. If lesson-quality or workflow-state checks are not run, mark them `NOT_RUN` with the reason.

## Context Budget

- Load active iteration plus 5 recent summaries; reference full history by path.
- Keep the report under 1200 words unless the operator requests a deep audit.

## Durable Docs Render

After stable Markdown outputs for this skill are finalized, invoke `$docs-site` or report `docs_site_boundary_report`. Do not render after temporary draft edits; Markdown remains the source of truth.

## Codex Adaptation

- Treat natural-language requests as the canonical `$evaluate` flow or the evaluation sub-step of `$iterate`.
- Use `.agents/state/current_iteration.json` as the active iteration context path.
- Preserve the original decision vocabulary (NEXT_ROUND / DEBUG / CONTINUE / PIVOT / ABORT) and per-iteration reporting behavior, but do not assume a fixed metric family.
- Use `../../../.agents/references/language-policy.md` for reply language and for localizing natural-language report sections; keep protocol keys and decision tokens in English.

## Execution Rule

Follow the local evaluation prompt, stage-report template, and language policy rather than collapsing this into a brief metrics summary.
