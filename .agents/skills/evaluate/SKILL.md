---
name: evaluate
description: "Internal Harness instruction source for evaluate. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Evaluate

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/commit-checkpoint-rule.md`
- `../../../.agents/references/lesson-quality-rule.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/run-artifact-contract.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `../../../.agents/references/research-supervision-patterns.md`
- `../../../.agents/references/research-supervision/experiment-and-build-canvas.md`
- `../../../.agents/references/research-supervision/ai-assisted-research-workflow.md`
- `../../../.agents/references/reviewer-independence.md`
- `../../../.agents/references/review-tracing.md`
- `./references/stage-report.md`
- `../../../iteration_log.json`
- `../../../PROJECT_STATE.json`
- `../../../docs/10_contract/Evaluation_Contract.md` if it exists
- `../../../docs/45_discoveries/Discovery_Ledger.md` if it exists
- `../../../docs/45_discoveries/Research_Wiki.md` if it exists
- `../../../docs/40_iterations/Experiment_Queue.md` if it exists
- `../../../docs/50_memory/Lessons.md` if it exists

## When To Use

Use this skill when the user wants training or evaluation results interpreted and turned into a decision.

## Required Work

1. Parse the relevant run artifact bundle, logs, metrics, or checkpoint metadata.
2. Analyze:
   - training stability
   - convergence
   - overfitting
   - gradient and numerical issues
3. Resolve the tracked metric set from active iteration context or project state, and compare against baseline metrics and prior iterations using that protocol.
4. Separate metric movement, training health, missing controls, claim support,
   and next-experiment implications.
5. Verify `pre_eval_commit` for meaningful eval work, or record
   `pre_eval_commit_NOT_CHANGED` when the committed training source already
   covers eval code/configs. Do not use eval output as Conclusion Evidence
   without a committed eval identity.
6. Produce the canonical report using `./references/stage-report.md`.
7. Write observations, phenomena, findings, hypotheses, and next-experiment
   hints to `docs/45_discoveries/Discovery_Ledger.md`; promote only qualified
   lesson candidates to `docs/50_memory/Lessons.md`.
8. Append or refresh `docs/40_iterations/Experiment_Queue.md` for concrete
   follow-up experiments, falsifiers, controls, assurance gaps, or paper-driven
   run requests; report `NOT_RUN` when no queue update is needed.
9. Append or refresh `docs/45_discoveries/Research_Wiki.md` for searchable
   stable observations, method notes, open questions, and finding summaries;
   report `NOT_RUN` when no wiki update is needed.
10. Record Claim Delta Evidence when a paper claim, release claim, or claim
   boundary implication changed; otherwise record
   `claim_delta_evidence_NOT_CHANGED`.
11. Append or refresh `MEMORY.md` only when a lesson is accepted and satisfies `lesson-quality-rule.md`.
12. Recommend exactly one of:
   - `NEXT_ROUND` — ordinary improvement round, stay in WF10
   - `DEBUG` — fixable technical issue, stay in WF10
   - `CONTINUE` — handoff to orchestrator/WF11, not continue iterating
   - `PIVOT`
   - `ABORT`
13. If invoked from `$iterate`, do not take over stage-transition ownership.
14. Include run artifact paths as Execution Evidence and keep unverifiable result interpretations under open questions.
15. Refresh `docs/30_evidence/Experiment_Evidence_Index.{json,md}` with
    `tooling/evidence/build_experiment_evidence_index.py` after completed run
    evidence is written, or report `NOT_RUN` with the reason.
16. Use an `experiment` commit checkpoint for completed evaluation/discovery
    slices before long follow-up runs or handoff.
17. Report a Gate ledger when iteration reports, stage reports, discovery
    ledgers, Research Wiki, Experiment Queue, lesson files, `MEMORY.md`,
    `iteration_log.json`, claim delta evidence, or the experiment evidence
    index are written. If lesson-quality or workflow-state checks are not run,
    mark them `NOT_RUN` with the reason.

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

## Durable Docs Render

After stable Markdown is finalized, invoke `$docs-site` or report
`docs_site_boundary_report` / `docs_site_render_or_NOT_RUN`. Do not render for
temporary drafts.
