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
This is Stage 4 of the 10-stage CV research workflow.
Input: Sanity_Check_Log.md (GO decision) from WF3.
Output: Data_Pipeline_Script.py, Dataset_Stats.md, subset config.
On success → WF5 (baseline-repro). On failure → requires human intervention for data issues.

Note: WF4 itself must ensure dataset paths are written into `CLAUDE.md`; do not leave this as a best-effort downstream refresh.

First, read PROJECT_STATE.json to get dataset_name and codebase_path.
For the output format, see [templates/dataset-stats.md](templates/dataset-stats.md).
For language behavior, see [../../shared/language-policy.md](../../shared/language-policy.md).
</context>

<instructions>
1. **Parse Input**

   Obtain from PROJECT_STATE.json and $ARGUMENTS:
   - `dataset_name`: Dataset name
   - `dataset_path`: Dataset storage path
   - `subset_strategy`: Subset strategy (optional, auto-inferred)

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

   Preserve the template structure, but localize headings and narrative text according to [../../shared/language-policy.md](../../shared/language-policy.md) unless a field is explicitly marked English-only.

7. **Update Project State**

   Update PROJECT_STATE.json:
   - `current_stage.status` → "completed"
   - `artifacts.data_pipeline_script` → script path
   - `artifacts.dataset_stats` → statistics report path
   - `dataset_paths` → normalized dataset paths
   - `history` append completion record

8. **Sync CLAUDE.md**

   Before WF4 concludes, trigger `/init-project update` or an equivalent section-safe update
   to ensure `CLAUDE.md`'s `### Dataset Paths` is consistent with `PROJECT_STATE.json.dataset_paths`.
</instructions>

<constraints>
- ALWAYS auto-detect data format before applying any strategy
- NEVER randomly drop views from NVS/3DGS datasets — use resolution scaling or scene selection instead
- For detection datasets, NEVER use pure random sampling without stratification
- ALWAYS save subset/scaling config to JSON for reproducibility
- ALWAYS set random seed for all sampling operations
- For detection datasets, ALWAYS verify subset distribution matches full dataset within 5% deviation
</constraints>
