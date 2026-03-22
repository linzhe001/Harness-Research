---
name: evaluate
description: Codex wrapper for experiment analysis and decision-making. Use when the user wants metrics interpreted, a stage or iteration report written, and a NEXT_ROUND, DEBUG, CONTINUE, PIVOT, or ABORT recommendation.
---

# Evaluate

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/language-policy.md`
- `./references/stage-report.md`
- `../../../iteration_log.json`
- `../../../PROJECT_STATE.json`

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
5. Recommend exactly one of:
   - `NEXT_ROUND` — ordinary improvement round, stay in WF8
   - `DEBUG` — fixable technical issue, stay in WF8
   - `CONTINUE` — handoff to orchestrator/WF9, not continue iterating
   - `PIVOT`
   - `ABORT`
6. If invoked from `$iterate`, do not take over stage-transition ownership.

## Codex Adaptation

- Treat natural-language requests as the canonical `$evaluate` flow or the evaluation sub-step of `$iterate`.
- Use `.agents/state/current_iteration.json` as the active iteration context path.
- Preserve the original decision vocabulary (NEXT_ROUND / DEBUG / CONTINUE / PIVOT / ABORT) and per-iteration reporting behavior, but do not assume a fixed metric family.
- Use `../../../.agents/references/language-policy.md` for reply language and for localizing natural-language report sections; keep protocol keys and decision tokens in English.

## Execution Rule

Follow the local evaluation prompt, stage-report template, and language policy rather than collapsing this into a brief metrics summary.
