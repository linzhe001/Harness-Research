# Stage Gate Checks

Use these checks when validating `PROJECT_STATE.json` progress.

## State File Placement

- `PROJECT_STATE.json` must live at the repository root.
- `iteration_log.json` must live at the repository root.
- `project_map.json` must live at the repository root.
- `.agents/` may keep local references and volatile context only; it must not become the canonical home for project state.

## Required Paths By Stage

- `survey_idea`
  - `docs/Feasibility_Report.md`
- `refine_arch`
  - `docs/Technical_Spec.md`
- `deep_check`
  - `docs/Sanity_Check_Log.md`
- `data_prep`
  - `docs/Dataset_Stats.md`
- `baseline_repro`
  - `docs/Baseline_Report.md`
  - populated `baseline_metrics` in `PROJECT_STATE.json`
  - evaluation protocol or tracked metric names recorded for later WF8 comparison
- `build_plan`
  - `docs/Implementation_Roadmap.md`
  - `project_map.json`
- `code_expert`
  - prefer `artifacts.code_modules` from `PROJECT_STATE.json`
  - fallback: `src/`, `scripts/train_smoke.py`, `scripts/eval_smoke.py`
- `validate_run`
  - `project_map.json`
  - `docs/Implementation_Roadmap.md`
  - `scripts/train_smoke.py`
  - `scripts/eval_smoke.py`
  - `scripts/train_all_scenes.py` when the project uses it
  - pass/fail evidence is usually in stage history or logs, not a dedicated file
- `iterate`
  - `iteration_log.json`
  - `PROJECT_STATE.json.current_stage.latest_iteration` synchronized with the latest iteration record
  - `CLAUDE.md` current-stage summary synchronized with iteration progress
  - WF8 → WF9 gate: only a `decision=CONTINUE` on the latest completed iteration allows advancing to WF9. `NEXT_ROUND` and `DEBUG` keep the project in WF8. `PIVOT` triggers rollback to WF2. `ABORT` terminates.
  - If auto-iterate is active, `.auto_iterate/state.json` may be read for loop status (read-only; orchestrator must not write to `.auto_iterate/`)
- `final_exp`
  - `docs/Final_Experiment_Matrix.md`
- `release`
  - `submission/`
  - `submission/README.md`
  - `submission/manifest.json`

## Output Format

When checking a stage, report:

- current workflow id or name
- current status
- `missing_artifacts`
- a `checks` list with per-check:
  - `name`
  - `ok`
  - `required`
  - `present`
  - `missing`
  - optional `detail`
