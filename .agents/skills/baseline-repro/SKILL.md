---
name: baseline-repro
description: Codex wrapper for WF5 baseline reproduction. Use when the user wants baseline adaptation, reproduction tracking, and `docs/Baseline_Report.md` following the original workflow contract.
---

# Baseline Repro

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/pre-training-rule.md`
- `../../../.agents/references/language-policy.md`
- `./references/baseline-report.md`
- `../../../PROJECT_STATE.json`

## When To Use

Use this skill for WF5 when the user wants baselines reproduced fairly before new method implementation.

## Required Work

1. Read the baseline list from `docs/Technical_Spec.md`.
2. Create or refresh the first runnable project environment for the baselines and sync the `## Environment` section in `CLAUDE.md`.
3. Use `docs/Dataset_Stats.md` and project context to align data and evaluation conditions.
4. Resolve the canonical evaluation protocol from the reproduced baselines and persist the tracked metric names for WF8.
5. Reproduce each requested baseline with minimal environment-specific changes.
6. Compare reproduced metrics against paper-reported metrics.
7. Write `docs/Baseline_Report.md` using the canonical template.
8. Update:
   - `PROJECT_STATE.json` baseline metrics
   - `PROJECT_STATE.json` evaluation protocol or tracked metrics for later WF8 comparison
   - `project_map.json` baseline status and entry point
   - `CLAUDE.md` environment facts and baseline reference

## Output Rules

- Keep adaptation notes, training config notes, and reproduced-versus-paper comparison.
- Treat environment creation here as part of the canonical WF5 gate, not as a separate pre-workflow step.
- Use the canonical pre-training commit rule for baseline code changes.
- Treat template wording as structure-only; localize headings and narrative text according to `../../../.agents/references/language-policy.md` unless a field is explicitly English-only.

## Codex Adaptation

- Treat natural-language requests as the canonical `$baseline-repro` flow.
- Preserve the original expectations around faithful reproduction and minimal baseline edits.
- Use the Codex toolchain, but keep the canonical output files and state updates.

## Execution Rule

Follow the local prompt, baseline report template, and language policy instead of simplifying the reproduction stage.
