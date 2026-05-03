# CLAUDE.md Maintenance Rules

Use these rules instead of helper scripts.

## State File Placement

- `PROJECT_STATE.json` stays at the repository root.
- `iteration_log.json` stays at the repository root.
- `project_map.json` stays at the repository root.
- `CLAUDE.md` stays at the repository root.
- `MEMORY.md` stays at the repository root.
- `OPERATOR_CONTEXT.md` stays at the repository root when used.
- `OPERATOR_CONTEXT.md` is written only from explicit operator-provided preferences or local constraints; do not infer it from project facts.
- `.evidence/` stays at the repository root when evidence-compiled docs are enabled.

## Section-Safe Editing

When updating `CLAUDE.md`:

1. Read the whole file first if it exists.
2. To replace a section:
   - locate the exact `## Section Name` header
   - replace content from that header until the next `## ` header
   - preserve all other sections byte-for-byte when possible
3. If the section does not exist, append it once at the end.
4. When updating the current-stage line:
   - replace the first line starting with `Current stage:`
   - append it only if it does not exist
5. Always preserve `## Custom`.

## Data-Backed Rendering

Render section bodies from project state rather than inventing new structure:

- `Environment`
  - keep runtime environment facts at the top of the section
  - keep `### Dataset Paths` inside the same section
  - render dataset addresses from `dataset_paths` when known
- `Current stage`
  - use `current_stage.workflow` or `workflow_id`
  - use `current_stage.name` or `workflow_name`
  - use `current_stage.status`
  - include iteration count if present
- `Core Artifacts`
  - prefer `PROJECT_STATE.json`
  - prefer `iteration_log.json`
  - prefer `project_map.json`
  - include `MEMORY.md` as the human-readable lessons bank when present or when initializing templates
  - include `OPERATOR_CONTEXT.md` as preference context when present
  - include `.evidence/` as evidence-chain storage when the dynamic context layout is enabled
  - include artifact paths recorded in `PROJECT_STATE.json`
- `Entry Scripts`
  - prefer:
    - `scripts/train_smoke.py`
    - `scripts/eval_smoke.py`
    - `scripts/train_all_scenes.py`
- `Project Structure`
  - summarize top-level stable directories only
- `Baseline reference`
  - render from `baseline_metrics`

## Refresh Scope

- `init` creates the minimal `CLAUDE.md`.
- `update` fills only sections whose source artifacts are known.
- WF4 dataset updates also check `AGENTS.md` for a stable pointer to `CLAUDE.md`; volatile dataset paths stay in `CLAUDE.md`.
- `deps-changed` updates only the runtime environment facts in `## Environment` and preserves `### Dataset Paths`.
