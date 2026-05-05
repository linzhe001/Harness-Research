---
name: data-prep
description: Codex wrapper for WF4 data engineering. Use when the user wants dataset analysis, subset strategy selection, and `docs/Dataset_Stats.md` produced according to the original workflow.
---

# Data Prep

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `./references/dataset-stats.md`
- `../../../PROJECT_STATE.json`
- `../../../CLAUDE.md` if it exists
- `../../../AGENTS.md` if it exists

## When To Use

Use this skill for WF4 when the user wants dataset analysis, subset design, and data-pipeline preparation.

## Required Work

1. Resolve dataset name, dataset path, and optional subset strategy from `PROJECT_STATE.json` and the user request.
2. Auto-detect dataset format and infer task type.
3. Produce the canonical stats for the detected task family.
4. Generate a reproducible subset strategy:
   - NVS or 3DGS: resolution scaling, scene selection, or point-cloud downsampling
   - detection: stratified subset indices
5. Write `docs/Dataset_Stats.md` using the canonical template.
6. Write the expected config artifact, such as `configs/subset_config.json` or `configs/subset_indices.json`.
7. Create or update the data pipeline script path expected by the canonical prompt.
8. Update `PROJECT_STATE.json`, especially `dataset_paths`, when appropriate.
9. Refresh `CLAUDE.md` so `### Dataset Paths` reflects the resolved dataset addresses immediately after WF4.
10. Check `AGENTS.md` when it exists. Keep it stable, but ensure it points operators to `CLAUDE.md` for volatile dataset and environment paths instead of carrying stale duplicated paths.

## Output Rules

- Use `./references/dataset-stats.md`.
- Keep the `context_summary`, dataset format summary, full stats, subset strategy, and expected speedup.
- Include evidence sources and separate verified dataset facts from inferred dataset properties.
- Dataset path synchronization into `CLAUDE.md` is required WF4 output, not an optional downstream refresh.
- `AGENTS.md` synchronization means consistency of the stable pointer to `CLAUDE.md`; do not duplicate volatile dataset paths into `AGENTS.md` unless the user explicitly changes the project policy.
- Report a Gate ledger when dataset stats, configs, pipeline files, `CLAUDE.md`, `AGENTS.md`, or `PROJECT_STATE.json` are written. If docchain or workflow-state checks are not run, mark them `NOT_RUN` with the reason.
- Treat template wording as structure-only; localize headings and narrative text according to `../../../.agents/references/language-policy.md` unless a field is explicitly English-only.

## Codex Adaptation

- Treat natural-language requests as the canonical `$data-prep` flow.
- Preserve the original task-aware dataset logic, especially the NVS or 3DGS rule against random view dropping.
- Keep the original outputs and state-update behavior.

## Execution Rule

Follow the local prompt, template, and language policy closely, especially the data-format detection and subset-strategy rules.
