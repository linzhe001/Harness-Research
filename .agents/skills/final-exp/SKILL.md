---
name: final-exp
description: "Internal Harness instruction source for final-exp. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Final Exp

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/contract-gating-rule.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `./references/experiment-matrix.md`
- `../../../iteration_log.json`
- `../../../PROJECT_STATE.json`
- `../../../docs/10_contract/Project_Contract.md` if it exists
- `../../../docs/10_contract/Evaluation_Contract.md` if it exists
- `../../../docs/10_contract/Baseline_Contract.md` if it exists
- `../../../docs/10_contract/Claim_Boundary.md` if it exists

## When To Use

Use this skill for WF11 when the user wants the final validation matrix after the main approach is stable.

## Required Work

1. Read the best iteration, available iteration reports, and the contract set.
   Dynamic-context projects must cite the current Project Contract, Evaluation
   Contract, and Claim Boundary, or record the fallback evidence/policy reason
   when operating under an Automation Policy.
2. Design canonical ablations that isolate major component contributions.
3. Define hyperparameter search, robustness tests, and cross-dataset evaluation.
4. Estimate compute budget and execution order.
5. Ensure the matrix respects the Evaluation Contract and Claim Boundary. Record
   Claim Delta Evidence when the matrix narrows, removes, or changes a claim
   implication. In legacy or standard projects without dynamic contracts,
   report the fallback evidence source instead of treating missing contracts as
   approval.
6. Before metric-bearing final experiment evaluation, create or verify
   `pre_eval_commit`, or record `pre_eval_commit_NOT_CHANGED`.
7. Write `docs/Final_Experiment_Matrix.md` using the canonical template.
8. Update `PROJECT_STATE.json` when appropriate.

## Durable Docs Render

After stable Markdown outputs for this skill are finalized, invoke `$docs-site` or report `docs_site_boundary_report`. Do not render after temporary draft edits; Markdown remains the source of truth.

## Codex Adaptation

- Treat natural-language requests as the canonical `$final-exp` flow.
- Preserve the original emphasis on ablation isolation, reviewer expectations, and compute budgeting.
- Keep the canonical output path and state updates.
- Include evidence sources for selected iterations, component definitions, metrics, and compute estimates.
- Report a Gate ledger for dynamic-context readiness, protocol drift, experiment-matrix writes, and workflow-state checks. Mark skipped checks `NOT_RUN` with the reason.
- Treat template wording as structure-only; localize headings and narrative text according to `../../../.agents/references/language-policy.md` unless a field is explicitly English-only.

## Execution Rule

Follow the local planning prompt, experiment-matrix template, and language policy rather than replacing them with a generic experiment checklist.

## Durable Docs Render

After stable Markdown is finalized, invoke `$docs-site` or report
`docs_site_boundary_report` / `docs_site_render_or_NOT_RUN`. Do not render for
temporary drafts.
