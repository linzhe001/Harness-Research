# Data Prep

Use this Skill for WF4 dataset analysis, subset design, and data-pipeline
preparation.

## Read First

- Workflow, language, and documentation rules under
  `../../../.agents/references/`
- `./references/dataset-stats.md`
- `PROJECT_STATE.json`, `CLAUDE.md`, `AGENTS.md` when present
- `docs/Refined_Idea.md`
- `docs/20_facts/Execution_Contract.md` when present
- `docs/30_evidence/Dataset_Table.md` when present

## Required Work

1. Before writing, check existing WF4 docs/artifacts. Archive current Markdown
   docs under `docs/90_legacy/<YYYY-MM-DD>/`; record
   `archive_existing_data_docs_or_NOT_RUN`.
2. Resolve dataset name, path, remote source, and subset strategy from state,
   `docs/Refined_Idea.md`, execution contract, existing Dataset Table, and the
   user request.
3. If local data is missing or only a remote source is known, run the Dataset
   Acquisition Gate before final stats.
4. Auto-detect dataset format and task type.
5. Produce canonical stats and reproducible subset strategy. For NVS/3DGS,
   preserve task-valid scene, resolution, point-cloud, smoke, dehaze/clean, and
   evaluation-reference needs.
6. Write `docs/Dataset_Stats.md` and concise
   `docs/30_evidence/Dataset_Table.md` as Conclusion Evidence.
7. Write expected config/script artifacts and update `PROJECT_STATE.json`,
   `CLAUDE.md` dataset paths, and stable `AGENTS.md` pointer when appropriate.

## Dataset Acquisition Gate

Do not stop at “dataset missing” as the first response. First perform Remote
Repository Selection, then ask for only the missing decision:
download/mount choice and target directory, target archive/slice, network/disk
approval, or existing local path.

If target path and approval are already unambiguous, proceed without another
question. Otherwise ask before large transfers or writing data outside the
repo. Record `dataset_acquisition_decision_request_or_NOT_RUN`.

Gate Evidence must include source URL, target path, command, result, observed
bytes/checksum when available, extraction path, and stats follow-up. With
multiple Grill/supervisor candidates, try the next executable `candidate`
after logging failures; skip `rejected`, `deferred`, or `requires_approval`
unless separately approved.

## Remote Repository Selection

Inspect source-native listings before download: API, repository tree,
manifest, README, HTTP metadata, or file-list command. For Hugging Face, check
dataset API and relevant `tree/main/...` listings.

Build a small candidate matrix with remote path/archive, content role
(`smoke`, `dehaze`, clean reference, depth, COLMAP, point cloud, metadata),
resolution/layout, size/checksum when known, required/optional/excluded status,
and selection rationale. Do not silently fall back to full data or unrelated
conditions.

## Output Rules

- Use `./references/dataset-stats.md`.
- Separate verified dataset facts from inferred properties.
- Keep `Dataset_Table.md` source-artifact oriented; do not hand-edit
  `.evidence/**`.
- Dataset path sync into `CLAUDE.md` is required WF4 output.
- `AGENTS.md` should point to `CLAUDE.md`, not duplicate volatile paths.
- Report Gate ledger for acquisition, stats, configs, pipeline files, guidance,
  and state writes, including `dataset_acquisition_or_NOT_RUN`.
- After stable Markdown is finalized, invoke `$docs-site` or report
  `docs_site_boundary_report`.

## Durable Docs Render

After stable Markdown is finalized, invoke `$docs-site` or report
`docs_site_boundary_report` / `docs_site_render_or_NOT_RUN`. Do not render for
temporary drafts.
