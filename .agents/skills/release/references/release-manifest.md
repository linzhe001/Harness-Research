# Release Manifest Rules

Use this reference instead of a helper packaging script.

## State File Placement

- Read `PROJECT_STATE.json` from the repository root.
- Read `iteration_log.json` from the repository root.
- Write submission assets under `submission/` at the repository root.

## Manifest Content

Create `submission/manifest.json` with:

- `project`
  - from `PROJECT_STATE.json.project_name`, fallback to iteration log project name
- `best_iteration`
  - from `iteration_log.json.best_iteration`
- `target_venue`
  - from `PROJECT_STATE.json.target_venue`
- `dataset_paths`
  - from `PROJECT_STATE.json.dataset_paths`
- `entry_scripts`
  - `train`: `scripts/train_smoke.py` when present
  - `eval`: `scripts/eval_smoke.py` when present
  - `multi_scene`: `scripts/train_all_scenes.py` when present
- `scenes`
  - one object per chosen result from `PROJECT_STATE.json.best_results`
  - each object should include:
    - `label`
    - `iteration`
    - `scene`
    - `checkpoint`
    - `resolution`
    - `peak_psnr`
    - `final_psnr`

## Validation Checklist

For a first-pass submission check:

- `submission/` exists
- `submission/README.md` exists
- files use allowed extensions required by the competition
- filenames follow the competition format
- per-scene outputs are complete
- expected image resolution is correct
