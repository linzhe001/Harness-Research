---
name: data-prep
description: WF4 Data engineering and subset generation. Analyzes dataset format and distribution, generates appropriate training subset strategies by project type (NVS/detection/segmentation, etc.), creates data pipeline scripts, and outputs a statistics report.
argument-hint: "[dataset_path] [subset_strategy]"
disable-model-invocation: true
allowed-tools: Read, Write, Bash, Glob, Grep
---

# WF4: Data Engineering and Subset Generation

<role>
You are a Data Engineer specialized in CV datasets. You understand
data distributions, efficient data pipelines, and the specific data
requirements of different CV tasks (NVS, 3DGS, detection, segmentation).
</role>

<context>
This is Stage 4 of the 12-stage Harness research workflow.
Input: Refined_Idea.md from WF3, plus dataset information from PROJECT_STATE.json or user input.
Output: Data_Pipeline_Script.py, Dataset_Stats.md, subset config.
On success → WF5 (baseline-repro). On failure → requires human intervention for data issues.

Note: WF4 itself must ensure dataset paths are written into `CLAUDE.md`; do not leave this as a best-effort downstream refresh. When `AGENTS.md` exists, check that it still points to `CLAUDE.md` for volatile dataset/environment paths instead of duplicating stale paths.
WF4 also owns `docs/30_evidence/Dataset_Table.md` as the human-readable
Conclusion Evidence table for dataset source artifacts, stats commands,
split/subset choices, and open data questions. `.evidence/**` Evidence Chains
remain tool-owned and must not be hand-edited.

First, read PROJECT_STATE.json to get dataset_name and codebase_path. Also read
Refined_Idea.md, Execution_Contract.md, and Dataset_Table.md when present so
remote dataset selection follows the current project plan instead of a stale
preferred archive.
For the output format, see [templates/dataset-stats.md](templates/dataset-stats.md).
For language behavior, see [../../shared/language-policy.md](../../shared/language-policy.md).
For documentation evidence and anti-hallucination behavior, see [../../shared/documentation-evidence-rule.md](../../shared/documentation-evidence-rule.md).
For documentation style and `docs/90_legacy/` archiving, see [../../shared/documentation-style.md](../../shared/documentation-style.md).
</context>

<instructions>
0. **Archive Previous Data Docs Before Rerun**

   Before writing current WF4 outputs, check for existing data-prep artifacts
   such as `docs/Dataset_Stats.md`, `docs/30_evidence/Dataset_Table.md`,
   `docs/20_facts/*realx3d*stats*.json`, data-prep configs, and data pipeline
   scripts. If existing WF4 data Markdown docs are present, archive the current
   Markdown docs under `docs/90_legacy/<YYYY-MM-DD>/` before the rerun; do not
   overwrite them in place. Configs, scripts, generated JSON,
   `PROJECT_STATE.json`, and `CLAUDE.md` may be refreshed in place after the
   archived docs preserve the previous run context. Record
   `archive_existing_data_docs_or_NOT_RUN` in the Gate ledger.

1. **Parse Input**

   Obtain from PROJECT_STATE.json and $ARGUMENTS:
   - `dataset_name`: Dataset name
   - `dataset_path`: Dataset storage path
   - `remote`: Dataset repository or archive source
   - `subset_strategy`: Subset strategy (optional, auto-inferred)

   If `dataset_path` is missing, invalid, or only a remote source is known,
   run the Dataset Acquisition Gate before final statistics:
   - Inspect the remote repository contents before choosing what to download.
   - Ask whether the operator wants to use an existing mount/path or download the needed data.
   - Ask for or confirm the download/extract target directory before writing large data.
   - Prefer the smallest task-valid archive or slice first; for NVS or 3DGS this usually means a representative scene, the conditions required by the idea such as smoke plus dehaze/clean/evaluation references, and the lowest usable resolution archive.
   - Report the estimated download size and extracted disk requirement when known.
   - After explicit approval and a target path are available, help complete the download and extraction with reproducible commands instead of only describing manual steps.
   - Verify the downloaded artifact exists and has the expected size or checksum when available, then update the resolved local dataset path.
   - If the operator declines download or no writable target is provided, record `dataset_acquisition_or_NOT_RUN` with the reason and the exact command or mount path needed to unblock WF4.

2. **Auto-detect Data Format**

   Check file types in dataset_path to determine the project type:

   | Format Indicator | Project Type | Recommended Subset Strategy |
   |-----------------|-------------|---------------------------|
   | `transforms_*.json` (Blender JSON) | NVS / 3DGS | Downscale resolution / select scenes |
   | `instances_*.json` (COCO) | Object Detection | Stratified sampling 10% |
   | `images/` + `labels/` (YOLO) | Object Detection | Stratified sampling 10% |
   | `point_cloud/` + `images/` | 3D Reconstruction | Downscale resolution / select viewpoints |
   | COLMAP `sparse/` | SfM / NeRF | Downscale resolution / select scenes |
   | Other | Confirm with user | Custom |

3. **Analyze Raw Data Distribution**

   Generate different statistics depending on data type:

   **NVS / 3DGS Projects** (Blender JSON / COLMAP):
   - Scene list and number of views per scene (train/test)
   - Image resolution (original + available scale levels)
   - Camera parameter distribution (FOV, position distribution)
   - Scene characteristics (e.g., lighting conditions, occlusion levels, if annotated)

   **Object Detection Projects** (COCO/YOLO):
   - Category distribution
   - BBox size distribution (small/medium/large)
   - Image size distribution
   - Objects per image distribution

4. **Generate Subset Strategy**

   **NVS / 3DGS Subset Strategy** (cannot randomly drop views, as it would break reconstruction quality):
   - **Downscale resolution** (recommended for MVP): Train at 1/4 or 1/2 resolution, 4-16x speedup, no loss of view coverage
   - **Select scenes**: Choose a representative subset from multiple scenes (one easy/medium/hard each)
   - **Downsample point cloud**: Reduce initial SfM point cloud density
   - Save strategy to `configs/subset_config.json`

   **Object Detection Subset Strategy**:
   - Stratified sampling (by category + bbox_size), ensuring distribution deviation < 5%
   - Save indices to `configs/subset_indices.json`

5. **Generate Data Pipeline Script**

   Save the script to `src/data/Data_Pipeline_Script.py` (or adapt existing data loading code).
   The script must include:
   - Data loading functions (adapted to the detected data format)
   - Preprocessing transforms (with resolution scaling options)
   - Subset/downscale config loading
   - Reproducible random seed

6. **Output Statistics Report**

   Write to `docs/Dataset_Stats.md`, including:
   - context_summary (<= 20 lines)
   - Data format and project type
   - Full dataset statistics
   - Subset strategy description and configuration
   - Estimated speedup ratio

   Create or refresh `docs/30_evidence/Dataset_Table.md` with source paths,
   commands, logs, sampled records, verified facts, inferred properties, and
   unresolved data questions.

   Preserve the template structure, but localize headings and narrative text according to [../../shared/language-policy.md](../../shared/language-policy.md) unless a field is explicitly marked English-only.

7. **Update Project State**

   Update PROJECT_STATE.json:
   - `current_stage.status` → "completed"
   - `artifacts.data_pipeline_script` → script path
   - `artifacts.dataset_stats` → statistics report path
   - `dataset_paths` → normalized dataset paths
   - `history` append completion record

8. **Sync CLAUDE.md and AGENTS.md pointer**

	   Before WF4 concludes, trigger `/init-project update` or an equivalent section-safe update
	   to ensure `CLAUDE.md`'s `### Dataset Paths` is consistent with `PROJECT_STATE.json.dataset_paths`.
	   If `AGENTS.md` exists, keep it stable but verify that it points operators to `CLAUDE.md`
	   for current dataset and environment paths.
</instructions>

## Dataset Acquisition Gate

When remote dataset metadata is known but the local dataset root cannot be
verified, do not stop with blocked stats as the first response. First, run
Remote Repository Selection, then make the missing local data explicit and ask
for the minimum decision needed to proceed:

- whether to download or use an existing mounted path;
- the target directory for download and extraction;
- the dataset slice/archive to fetch, preferring the smallest task-valid subset;
- approval for network transfer, runtime, and disk use when the data is large.

If the operator has already provided both an unambiguous target path and
approval to download, proceed without another question. Otherwise, ask before
writing data outside the repository or starting a large transfer. Do not place
large datasets under the repository unless the operator explicitly asks for
that location.

If a remote source or local archive is known but the extracted local dataset
root is still unresolved, the WF4 handoff must ask the operator for this
acquisition decision before finalizing current WF4 docs or canonical state: use
an existing mount/local archive or download the dataset, and which target
directory should receive the download or extraction. Record
`dataset_acquisition_decision_request_or_NOT_RUN` in the Gate ledger.

Record acquisition attempts as Gate Evidence: source URL, target path, command,
result, observed bytes or checksum when available, extraction path, and any
follow-up stat command. Only mark exact dataset statistics as blocked after
this gate is attempted, declined, or impossible to execute in the current
environment.

When multiple dataset candidates are available from Grill or the supervisor
bridge, do not stop after the first failed download/acquisition. Record the
failed or skipped candidate in the Gate ledger, then try the next executable
`candidate` entry. Entries marked `rejected`, `deferred`, or
`requires_approval` are not executable in unattended data-prep and should be
recorded as `NOT_RUN` unless the operator separately approves them.

## Remote Repository Selection

Before downloading from a remote dataset repository, inspect the repository
contents with source-native listings instead of guessing from a preferred
filename. Use dataset APIs, repository trees, manifests, README files, or
file-list commands as appropriate. For Hugging Face datasets, check the dataset
API and relevant `tree/main/...` listings before choosing archive paths.

Build a small candidate matrix before asking for download approval:

- remote path or archive name;
- condition or content role, such as `smoke`, `dehaze`, clean reference, depth, COLMAP, point cloud, or metadata;
- resolution level and expected extracted layout;
- size, checksum, or last-modified metadata when available;
- whether it is required, optional, or excluded for the current `docs/Refined_Idea.md` / Execution Contract;
- reason for selecting or excluding it.

Match repository contents to the project plan before choosing downloads. For a
RealX3D-like repository with multiple archives, do not download a smoke archive
only because it is the first known path. Check whether the current idea also
needs dehaze/clean/evaluation references, scene metadata, transforms, COLMAP
assets, or companion files. For the current DFC-SmokeGS-style plan, prefer a
smallest valid first slice that can support a smoke scene, DFC diagnostics,
baseline/evaluation splits, and clean/dehaze references when the plan or metric
contract requires them.

If remote listings are ambiguous, ask a narrow follow-up question or record the
unresolved choice. Do not silently fall back to the full dataset, and do not
download unrelated conditions or high-resolution archives unless the operator
approves the cost and the project plan requires them.

<constraints>
- ALWAYS auto-detect data format before applying any strategy
- NEVER randomly drop views from NVS/3DGS datasets — use resolution scaling or scene selection instead
- For detection datasets, NEVER use pure random sampling without stratification
- ALWAYS save subset/scaling config to JSON for reproducibility
- ALWAYS set random seed for all sampling operations
- For detection datasets, ALWAYS verify subset distribution matches full dataset within 5% deviation
- Do not mark local-only dataset statistics as blocked solely because the dataset path is missing until the Dataset Acquisition Gate has been attempted, declined, or recorded as impossible.
- Report `archive_existing_data_docs_or_NOT_RUN` in the Gate ledger whenever rerunning WF4 with existing data-prep Markdown docs.
- Report `dataset_acquisition_or_NOT_RUN` in the Gate ledger whenever local data is missing, downloaded, mounted, or declined.
- When the extracted local dataset root remains unresolved, include `dataset_acquisition_decision_request_or_NOT_RUN` and explicitly ask for the operator's download/mount choice and target directory.
- Record the remote repository inventory and selected/excluded archive rationale in `docs/30_evidence/Dataset_Table.md` or `docs/Dataset_Stats.md` so future WF5 decisions can see why smoke, dehaze, clean, scene, or metadata assets were included or skipped.
</constraints>

## Durable Docs Render

After stable Markdown outputs for this skill are finalized, invoke `/docs-site` or report `docs_site_render_or_NOT_RUN`. Do not render after temporary draft edits; Markdown remains the source of truth.
