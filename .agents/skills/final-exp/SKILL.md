---
name: final-exp
description: Codex wrapper for WF9 final experiment planning. Use when the user wants ablations, robustness tests, cross-dataset evaluation, and compute budgeting organized according to the original template.
---

# Final Exp

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `./references/experiment-matrix.md`
- `../../../iteration_log.json`
- `../../../PROJECT_STATE.json`

## When To Use

Use this skill for WF9 when the user wants the final validation matrix after the main approach is stable.

## Required Work

1. Read the best iteration and available iteration reports.
2. Design canonical ablations that isolate major component contributions.
3. Define hyperparameter search, robustness tests, and cross-dataset evaluation.
4. Estimate compute budget and execution order.
5. Write `docs/Final_Experiment_Matrix.md` using the canonical template.
6. Update `PROJECT_STATE.json` when appropriate.

## Codex Adaptation

- Treat natural-language requests as the canonical `$final-exp` flow.
- Preserve the original emphasis on ablation isolation, reviewer expectations, and compute budgeting.
- Keep the canonical output path and state updates.

## Execution Rule

Follow the local planning prompt and experiment-matrix template rather than replacing them with a generic experiment checklist.
