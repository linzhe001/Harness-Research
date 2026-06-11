---
description: project_map.json and Codebase_Map.md maintenance rules — sync when stable files or stable interfaces change
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

# project_map.json and Codebase_Map.md Maintenance Rules

## Stable vs Volatile Layering

project_map.json tracks **stable implementation files** (long-lived files that define module interfaces). It describes file layout and interfaces; it does not replace the WF6 architecture decision in `docs/Technical_Spec.md`.
When `docs/20_facts/Codebase_Map.md` exists, keep it synchronized as the operator-facing current fact document for the same stable codebase structure. `project_map.json` remains the machine-readable source; `Codebase_Map.md` is for fast human orientation.
**Volatile experiment assets** (per-iteration configs, ablation scripts, one-off utilities) do not need to be maintained in `project_map.json` or `Codebase_Map.md`.

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
  3. If stable interface changes are involved → update `project_map.json` and, when present, `docs/20_facts/Codebase_Map.md` (see rules below)

## When to Update project_map.json and Codebase_Map.md
- **New stable file added** → add a node under the corresponding directory in `project_map.json`; update `Codebase_Map.md` if it exists
- **Stable file deleted** → remove the corresponding node
- **Stable file renamed** → update the old and new paths
- **Stable interface changed** (exports, function signature, tensor shape, durable config schema, responsibilities, dependencies) → update the corresponding fields
- Internal implementation changes only, no stable interface changes — no update needed
- **Operator-facing map drift** → if `Codebase_Map.md` exists and stable codebase structure, responsibilities, public interfaces, entry points, or dependencies changed, update it in the same Commit Slice
- **Operator-facing map evidence** → if `Codebase_Map.md` changed, run
  `python tooling/evidence/compile_doc.py --workspace-root . --doc docs/20_facts/Codebase_Map.md --source project_map.json`
  plus any explicit stable source files needed to support the changed facts, or
  report `compile_doc_or_NOT_RUN`; do not hand-edit `.evidence/**`
- **Human docs view** → after the Markdown is finalized for the current slice,
  invoke `/docs-site` or report `docs_site_boundary_report`; do not render
  after temporary draft edits
- **Volatile file added/deleted/renamed** → no update to `project_map.json` or `Codebase_Map.md` needed

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
