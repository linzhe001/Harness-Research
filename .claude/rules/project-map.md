---
description: project_map.json maintenance rules — must sync updates when files are added or removed
globs:
  - "src/**/*.py"
  - "baselines/**/*"
  - "configs/**/*.yaml"
  - "configs/**/*.yml"
  - "configs/**/*.json"
  - "scripts/**/*.py"
  - "scripts/**/*.sh"
  - "tests/**/*.py"
---

# project_map.json Maintenance Rules

## Stable vs Volatile Layering

project_map.json only tracks **stable architecture files** (long-lived files that define module interfaces).
**Volatile experiment assets** (per-iteration configs, ablation scripts, one-off utilities) do not need to be maintained in project_map.json.

### Stable (must track)
- `src/**/*.py` — main research code (models, data, losses, utils)
- `baselines/` — each baseline subdirectory (brief level)
- Core entry scripts listed in CLAUDE.md `## Entry Scripts`
- Core config files referenced in CLAUDE.md

### Volatile (no need to track)
- `scripts/run_*.sh` — per-iteration training scripts
- `scripts/run_ablation_*.py` — ablation experiment scripts
- Temporary experiment configs under `configs/`
- Everything under `experiments/`

Rule of thumb: if a file is only used in 1-2 iterations, it is volatile.

## Correct Way to Modify Code
- **Non-trivial code changes** (logic, interfaces, losses, new modules, etc.) → must invoke `/code-debug`
- **Trivial changes** (typos, comments, import order) → can edit directly, but must still run these checks:
  1. `python -m py_compile <file>`
  2. `ruff check --select=E,F,I <file>`
  3. If interface changes are involved → update project_map.json (see rules below)

## When to Update project_map.json
- **New stable file added** → add a node under the corresponding directory in project_map.json
- **Stable file deleted** → remove the corresponding node
- **Interface changed** (function signature, tensor shape changes) → update the corresponding fields
- Internal implementation changes only, no interface changes — no update needed
- **Volatile file added/deleted** → no update to project_map.json needed

## Description Detail Level by Directory

### src/ — detailed (main research code)
Each file must include:
- `exports`: list of exported class/function names
- `io`: input/output tensor shapes (for model-related files)
- `dependencies`: paths to other project-internal modules it depends on

### baselines/ — brief (reproduced comparison methods)
Each baseline subdirectory only needs:
- `description`: one-line summary
- `source`: code source URL
- `paper`: paper citation (author + venue + year)
- `status`: verified / untested / modified / broken / partial
- `entry_point`: training entry file
Do not list exports or tensor shapes for files inside baselines.

### configs/, scripts/, docs/ — medium (stable files only)
Each stable file only needs `description` (purpose, 1-2 sentences).

### experiments/ — minimal
Only record subdirectory purposes and storage rules; do not list specific log/checkpoint/result files.
