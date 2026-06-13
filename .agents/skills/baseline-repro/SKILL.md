---
name: baseline-repro
description: "Internal Harness instruction source for baseline-repro. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Baseline Repro

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/contract-gating-rule.md`
- `../../../.agents/references/pre-training-rule.md`
- `../../../.agents/references/run-artifact-contract.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `./references/baseline-report.md`
- `../../../PROJECT_STATE.json`
- `../../../docs/Refined_Idea.md` if it exists
- `../../../docs/30_evidence/Baseline_Table.md` if it exists
- `../../../docs/10_contract/Evaluation_Contract.md` if it exists
- `../../../docs/10_contract/Baseline_Contract.md` if it exists
- `../../../docs/35_protocol/Research_Protocol.md` if it exists

## When To Use

Use this skill for WF5 when the user wants baselines reproduced fairly before new method implementation.

## Required Work

1. Read the baseline candidates from `docs/Refined_Idea.md`, `docs/30_evidence/Baseline_Table.md`, and project state. For legacy projects, fall back to `docs/Technical_Spec.md` when no refined idea exists.
2. Create or refresh the first runnable project environment for the baselines and sync the `## Environment` section in `CLAUDE.md`.
3. Use `docs/Dataset_Stats.md` and project context to align data and evaluation conditions.
4. Resolve baseline inclusion/skipping rules from the approved Baseline Contract when present, and resolve the canonical evaluation protocol from the approved Evaluation Contract when present; otherwise derive drafts from reproduced baseline evidence and persist the tracked metric names for WF10.
5. Reproduce each requested baseline with minimal environment-specific changes.
6. Compare reproduced metrics against paper-reported metrics.
7. Record baseline run artifact bundle paths for reproduced metrics.
8. Write `docs/Baseline_Report.md` using the canonical template.
9. Create or refresh `docs/30_evidence/Baseline_Table.md` as the
   human-readable Conclusion Evidence table for baseline repos, papers,
   configs, reproduced metrics, logs, and skip reasons.
10. If `docs/20_facts/Codebase_Map.md` exists, keep it synchronized when
   baseline directories, scripts, configs, or durable entry points change.
11. Update:
   - `PROJECT_STATE.json` baseline metrics
   - `PROJECT_STATE.json` evaluation protocol or tracked metrics for later WF10 comparison
   - `project_map.json` baseline status and entry point
   - `CLAUDE.md` environment facts and baseline reference

## Durable Docs Render

After stable Markdown outputs for this skill are finalized, invoke `$docs-site` or report `docs_site_boundary_report`. Do not render after temporary draft edits; Markdown remains the source of truth.

## Output Rules

- Keep adaptation notes, training config notes, and reproduced-versus-paper comparison.
- Include evidence sources for reproduced metrics, commit hashes, configs, and any paper-reported values.
- Include run artifact bundle paths for reproduced metrics.
- Keep `docs/30_evidence/Baseline_Table.md` source-artifact oriented; it is
  human-readable Conclusion Evidence, not an `.evidence/**` Evidence Chain.
- If no approved Baseline or Evaluation Contract exists, write the affected baseline/evaluation protocol as draft/derived and surface the approval gap.
- WF5 is the first hard approval point for baseline/evaluation contracts in dynamic-context projects. Use protocol drift, context gates, docchain gates, and review packets when approval or explicit draft acceptance is needed.
- Treat environment creation here as part of the canonical WF5 gate, not as a separate pre-workflow step.
- Use the canonical pre-training commit rule for baseline code changes.
- Report a Gate ledger for baseline reproduction, contract readiness, protocol drift, dynamic-context gates, docchain checks, workflow-state checks, and semantic commits. Mark any skipped gate `NOT_RUN` with the reason.
- Treat template wording as structure-only; localize headings and narrative text according to `../../../.agents/references/language-policy.md` unless a field is explicitly English-only.

## Codex Adaptation

- Treat natural-language requests as the canonical `$baseline-repro` flow.
- Preserve the original expectations around faithful reproduction and minimal baseline edits.
- Use the Codex toolchain, but keep the canonical output files and state updates.

## Execution Rule

Follow the local prompt, baseline report template, and language policy instead of simplifying the reproduction stage.

## Durable Docs Render

After stable Markdown is finalized, invoke `$docs-site` or report
`docs_site_boundary_report` / `docs_site_render_or_NOT_RUN`. Do not render for
temporary drafts.
