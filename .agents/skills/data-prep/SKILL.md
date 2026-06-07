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
- `../../../docs/Refined_Idea.md` if it exists
- `../../../docs/20_facts/Execution_Contract.md` if it exists
- `../../../docs/30_evidence/Dataset_Table.md` if it exists

## When To Use

Use this skill for WF4 when the user wants dataset analysis, subset design, and data-pipeline preparation.

## Required Work

0. Before writing current WF4 outputs, check for existing data-prep artifacts such as `docs/Dataset_Stats.md`, `docs/30_evidence/Dataset_Table.md`, `docs/20_facts/*realx3d*stats*.json`, data-prep configs, and data pipeline scripts. If existing WF4 data Markdown docs are present, archive the current Markdown docs under `docs/90_legacy/<YYYY-MM-DD>/` before the rerun; do not overwrite them in place. Configs, scripts, generated JSON, `PROJECT_STATE.json`, and `CLAUDE.md` may be refreshed in place after the archived docs preserve the previous run context. Record `archive_existing_data_docs_or_NOT_RUN` in the Gate ledger.
1. Resolve dataset name, dataset path, remote source, and optional subset strategy from `PROJECT_STATE.json`, `docs/Refined_Idea.md` when present, `docs/20_facts/Execution_Contract.md` when present, the existing Dataset Table, and the user request.
2. If the local dataset path is missing, invalid, or only a remote source is known, run the Dataset Acquisition Gate before final stats:
   - Inspect the remote repository contents before choosing what to download.
   - Ask whether the operator wants to use an existing mount/path or download the needed data.
   - Ask for or confirm the download/extract target directory before writing large data.
   - Prefer the smallest task-valid archive or slice first; for NVS or 3DGS this usually means a representative scene, the conditions required by the idea such as smoke plus dehaze/clean/evaluation references, and the lowest usable resolution archive.
   - Report the estimated download size and extracted disk requirement when known.
   - After explicit approval and a target path are available, help complete the download and extraction with reproducible commands instead of only describing manual steps.
   - Verify the downloaded artifact exists and has the expected size or checksum when available, then update the resolved local dataset path.
   - If the operator declines download or no writable target is provided, record `dataset_acquisition_or_NOT_RUN` with the reason and the exact command or mount path needed to unblock WF4.
3. Auto-detect dataset format and infer task type.
4. Produce the canonical stats for the detected task family.
5. Generate a reproducible subset strategy:
   - NVS or 3DGS: resolution scaling, scene selection, or point-cloud downsampling
   - detection: stratified subset indices
6. Write `docs/Dataset_Stats.md` using the canonical template.
7. Create or refresh `docs/30_evidence/Dataset_Table.md` as the human-readable
   Conclusion Evidence table for dataset source artifacts, stats commands,
   split/subset choices, and unresolved data questions.
8. Write the expected config artifact, such as `configs/subset_config.json` or `configs/subset_indices.json`.
9. Create or update the data pipeline script path expected by the canonical prompt.
10. Update `PROJECT_STATE.json`, especially `dataset_paths`, when appropriate.
11. Refresh `CLAUDE.md` so `### Dataset Paths` reflects the resolved dataset addresses immediately after WF4.
12. Check `AGENTS.md` when it exists. Keep it stable, but ensure it points operators to `CLAUDE.md` for volatile dataset and environment paths instead of carrying stale duplicated paths.

## Dataset Acquisition Gate

When remote dataset metadata is known but the local dataset root cannot be verified, do not stop with blocked stats as the first response. First, run Remote Repository Selection, then make the missing local data explicit and ask for the minimum decision needed to proceed:

- whether to download or use an existing mounted path;
- the target directory for download and extraction;
- the dataset slice/archive to fetch, preferring the smallest task-valid subset;
- approval for network transfer, runtime, and disk use when the data is large.

If the operator has already provided both an unambiguous target path and approval to download, proceed without another question. Otherwise, ask before writing data outside the repository or starting a large transfer. Do not place large datasets under the repository unless the operator explicitly asks for that location.

If a remote source or local archive is known but the extracted local dataset root is still unresolved, the WF4 handoff must ask the operator for this acquisition decision before finalizing current WF4 docs or canonical state: use an existing mount/local archive or download the dataset, and which target directory should receive the download or extraction. Record `dataset_acquisition_decision_request_or_NOT_RUN` in the Gate ledger.

Record acquisition attempts as Gate Evidence: source URL, target path, command, result, observed bytes or checksum when available, extraction path, and any follow-up stat command. Only mark exact dataset statistics as blocked after this gate is attempted, declined, or impossible to execute in the current environment.

When multiple dataset candidates are available from Grill or the supervisor
bridge, do not stop after the first failed download/acquisition. Record the
failed or skipped candidate in the Gate ledger, then try the next executable
`candidate` entry. Entries marked `rejected`, `deferred`, or
`requires_approval` are not executable in unattended data-prep and should be
recorded as `NOT_RUN` unless the operator separately approves them.

## Remote Repository Selection

Before downloading from a remote dataset repository, inspect the repository contents with source-native listings instead of guessing from a preferred filename. Use dataset APIs, repository trees, manifests, README files, or file-list commands as appropriate. For Hugging Face datasets, check the dataset API and relevant `tree/main/...` listings before choosing archive paths.

Build a small candidate matrix before asking for download approval:

- remote path or archive name;
- condition or content role, such as `smoke`, `dehaze`, clean reference, depth, COLMAP, point cloud, or metadata;
- resolution level and expected extracted layout;
- size, checksum, or last-modified metadata when available;
- whether it is required, optional, or excluded for the current `docs/Refined_Idea.md` / Execution Contract;
- reason for selecting or excluding it.

Match repository contents to the project plan before choosing downloads. For a RealX3D-like repository with multiple archives, do not download a smoke archive only because it is the first known path. Check whether the current idea also needs dehaze/clean/evaluation references, scene metadata, transforms, COLMAP assets, or companion files. For the current DFC-SmokeGS-style plan, prefer a smallest valid first slice that can support a smoke scene, DFC diagnostics, baseline/evaluation splits, and clean/dehaze references when the plan or metric contract requires them.

If remote listings are ambiguous, ask a narrow follow-up question or record the unresolved choice. Do not silently fall back to the full dataset, and do not download unrelated conditions or high-resolution archives unless the operator approves the cost and the project plan requires them.

## Durable Docs Render

After stable Markdown outputs for this skill are finalized, invoke `$docs-site` or report `docs_site_render_or_NOT_RUN`. Do not render after temporary draft edits; Markdown remains the source of truth.

## Output Rules

- Use `./references/dataset-stats.md`.
- Keep the `context_summary`, dataset format summary, full stats, subset strategy, and expected speedup.
- Include evidence sources and separate verified dataset facts from inferred dataset properties.
- Do not mark local-only dataset statistics as blocked solely because the dataset path is missing until the Dataset Acquisition Gate has been attempted, declined, or recorded as impossible.
- Record the remote repository inventory and selected/excluded archive rationale in `docs/30_evidence/Dataset_Table.md` or `docs/Dataset_Stats.md` so future WF5 decisions can see why smoke, dehaze, clean, scene, or metadata assets were included or skipped.
- Keep `docs/30_evidence/Dataset_Table.md` concise and source-artifact oriented;
  `.evidence/**` Evidence Chains remain tool-owned and must not be hand-edited.
- Dataset path synchronization into `CLAUDE.md` is required WF4 output, not an optional downstream refresh.
- `AGENTS.md` synchronization means consistency of the stable pointer to `CLAUDE.md`; do not duplicate volatile dataset paths into `AGENTS.md` unless the user explicitly changes the project policy.
- Report a Gate ledger when dataset acquisition, dataset stats, configs, pipeline files, `CLAUDE.md`, `AGENTS.md`, or `PROJECT_STATE.json` are written or attempted. Include `archive_existing_data_docs_or_NOT_RUN` and `dataset_acquisition_or_NOT_RUN`; if docchain or workflow-state checks are not run, mark them `NOT_RUN` with the reason.
- When the extracted local dataset root remains unresolved, include `dataset_acquisition_decision_request_or_NOT_RUN` and explicitly ask for the operator's download/mount choice and target directory.
- Treat template wording as structure-only; localize headings and narrative text according to `../../../.agents/references/language-policy.md` unless a field is explicitly English-only.

## Codex Adaptation

- Treat natural-language requests as the canonical `$data-prep` flow.
- In Default mode, asking for download approval and a target directory is appropriate when local data is missing because large transfers consume disk, time, and network bandwidth.
- Preserve the original task-aware dataset logic, especially the NVS or 3DGS rule against random view dropping.
- Keep the original outputs and state-update behavior.

## Execution Rule

Follow the local prompt, template, and language policy closely, especially the data-format detection and subset-strategy rules.
