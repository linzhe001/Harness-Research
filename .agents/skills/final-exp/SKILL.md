---
name: final-exp
description: Codex wrapper for WF11 final experiment planning. Use when the user wants ablations, robustness tests, cross-dataset evaluation, and compute budgeting organized according to the original template.
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
- `../../../docs/10_contract/Claim_Boundary.md` if it exists

## When To Use

Use this skill for WF11 when the user wants the final validation matrix after the main approach is stable.

## Required Work

1. Read the best iteration, available iteration reports, and any approved contracts.
2. Design canonical ablations that isolate major component contributions.
3. Define hyperparameter search, robustness tests, and cross-dataset evaluation.
4. Estimate compute budget and execution order.
5. Ensure the matrix respects the Evaluation Contract and Claim Boundary when present.
6. Write `docs/Final_Experiment_Matrix.md` using the canonical template.
7. Update `PROJECT_STATE.json` when appropriate.

## Codex Adaptation

- Treat natural-language requests as the canonical `$final-exp` flow.
- Preserve the original emphasis on ablation isolation, reviewer expectations, and compute budgeting.
- Keep the canonical output path and state updates.
- Include evidence sources for selected iterations, component definitions, metrics, and compute estimates.
- Treat template wording as structure-only; localize headings and narrative text according to `../../../.agents/references/language-policy.md` unless a field is explicitly English-only.

## Execution Rule

Follow the local planning prompt, experiment-matrix template, and language policy rather than replacing them with a generic experiment checklist.
