---
name: data-prep
description: WF4 Data engineering and subset generation. Analyzes dataset format and distribution, generates appropriate training subset strategies by project type, creates data pipeline scripts, and outputs dataset stats.
argument-hint: "[dataset_path] [subset_strategy]"
disable-model-invocation: true
allowed-tools: Read, Write, Bash, Glob, Grep
---

# WF4: Data Engineering and Subset Generation

Use this Skill for WF4 dataset analysis, subset strategy, and data-pipeline
preparation. WF4 must synchronize resolved dataset paths into `CLAUDE.md`; do
not leave that as best-effort downstream work.

## Read First

- `PROJECT_STATE.json`
- `CLAUDE.md`, and `AGENTS.md` when present
- `docs/Refined_Idea.md`
- `docs/20_facts/Execution_Contract.md` when present
- `docs/30_evidence/Dataset_Table.md` when present
- `templates/dataset-stats.md`
- shared language, documentation evidence, documentation style, and
  `docs/90_legacy/` rules

## Required Work

1. Before writing current WF4 Markdown, archive existing
   `docs/Dataset_Stats.md` or `docs/30_evidence/Dataset_Table.md` under
   `docs/90_legacy/<YYYY-MM-DD>/`; record
   `archive_existing_data_docs_or_NOT_RUN`.
2. Resolve dataset name, local path, remote source, and subset strategy from
   state, arguments, current docs, and the user request.
3. If local data is missing, invalid, or only remote metadata is known, run the
   Dataset Acquisition Gate before final statistics.
4. Auto-detect dataset format before choosing strategy:
   `transforms_*.json`, COCO `instances_*.json`, YOLO images/labels,
   point-cloud/image layouts, COLMAP `sparse/`, or custom/unknown.
5. Produce task-specific stats and subset strategy. For NVS/3DGS, prefer
   resolution scaling, scene selection, or point-cloud downsampling; never
   random view dropping. For detection, use stratified sampling and verify
   distribution drift.
6. Write `docs/Dataset_Stats.md`,
   `docs/30_evidence/Dataset_Table.md`, subset config JSON, expected data
   pipeline script, `PROJECT_STATE.json`, and `CLAUDE.md` dataset paths as
   appropriate.
7. Keep `AGENTS.md` stable; it should point to `CLAUDE.md` for volatile dataset
   and environment paths.

## Dataset Acquisition Gate

When the local dataset root cannot be verified, do not stop with blocked stats
as the first response. First run Remote Repository Selection, then ask only for
the missing download/mount choice and target directory, archive/slice choice,
and approval for network, runtime, or disk use.

If target path and approval are already unambiguous, proceed without another
question. Otherwise ask before large transfers or writing data outside the
repo. Record `dataset_acquisition_decision_request_or_NOT_RUN`.

Record `dataset_acquisition_or_NOT_RUN` with Gate Evidence: source URL, target
path, command, result, observed bytes/checksum when available, extraction path,
and follow-up stat command. With multiple Grill/supervisor candidates, log
failed/skipped entries and try the next executable `candidate`; entries marked
`rejected`, `deferred`, or `requires_approval` are `NOT_RUN` unless separately
approved.

## Remote Repository Selection

Inspect source-native listings before download: dataset APIs, repository trees,
manifests, README files, HTTP metadata, or file-list commands. For Hugging Face
datasets, check API and relevant `tree/main/...` listings.

Build a small candidate matrix before approval:
- remote path/archive
- content role such as `smoke`, `dehaze`, clean reference, depth, COLMAP,
  point cloud, or metadata
- resolution/layout, size/checksum when known
- required/optional/excluded status for `docs/Refined_Idea.md` or the
  Execution Contract
- selection or exclusion rationale

Do not silently fall back to full data, unrelated conditions, or high-resolution
archives when a smaller task-valid slice is enough.

## Output Rules

- Use the dataset-stats template structure.
- Separate verified facts from inferred properties.
- Keep `Dataset_Table.md` concise and source-artifact oriented; never hand-edit
  `.evidence/**`.
- Treat template wording as structure-only; localize narrative according to
  language policy.
- Report Gate ledger for acquisition, stats, configs, scripts, guidance, and
  state writes.
- After stable Markdown is finalized, invoke `/docs-site` or report
  `docs_site_boundary_report`.
