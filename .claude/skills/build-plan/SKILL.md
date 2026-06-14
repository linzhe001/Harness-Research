# WF7: Implementation Roadmap and Project Map

Use this Skill after WF6. WF7 translates the selected architecture into
implementation order, stable file structure, interfaces, tests,
`docs/Implementation_Roadmap.md`, `project_map.json`, and
`docs/20_facts/Codebase_Map.md`. It does not choose a new architecture.

## Read First

- `PROJECT_STATE.json`
- `docs/Technical_Spec.md`
- `docs/Refined_Idea.md`, `docs/Dataset_Stats.md`, `docs/Baseline_Report.md`
  when present
- Evaluation/Baseline contracts or protocol when present
- `docs/20_facts/Project_Glossary.md` and `docs/20_facts/Codebase_Map.md`
  when present
- shared code-style, project-map, sliced-commit, language, ubiquitous-language,
  run-artifact, documentation evidence, and documentation style rules
- `templates/implementation-roadmap.md`
- `templates/project-map-schema.json`

## Required Work

1. Read prerequisites and identify main research code versus reproduced
   baselines.
2. Create or refresh `docs/20_facts/Project_Glossary.md`; disputed names stay
   proposed.
3. Design a stable file tree driven by `docs/Technical_Spec.md`, not a fixed
   template. Keep research code, baselines, configs, scripts, tests,
   experiments, and docs separated.
4. Write `project_map.json` with tiered detail:
   - `src/`: exports, tensor shapes, dependencies
   - `configs/`, `scripts/`, `docs/`: purpose and key parameters
   - `baselines/`, `tests/`: source/status/entry or coverage scope
   - `experiments/`: storage rules only
5. Write `docs/20_facts/Codebase_Map.md` from the same stable tree; keep it
   synchronized with `project_map.json`.
6. Convert the WF6 first vertical slice into dependency-ordered slices. Each
   slice needs `Slice Trace`, acceptance checks, feedback command, downstream
   validation doc, Commit Slice boundary, semantic commit suggestion, and
   out-of-scope work.
   Also define an explicit `minimal_runnable_slice_set` that distinguishes
   foundation slices from the smallest runnable smoke/eval/training-ready path.
7. For planned `src/` files, define signatures, pseudocode, shape examples,
   dependencies, config keys, validation behavior, error conditions, and shared
   interfaces.
8. Include pseudocode for `src/utils/git_snapshot.py`:
   `git_snapshot(training_type, auto_push) -> dict` returning commit, branch,
   initial-state, training type, and timestamp metadata.
9. Define config schema with data/model/train/tracking/experiment sections.
10. Design training pipeline with `Smoke Test`, `Module Integration`, and
    `Full Training`; startup flow is git snapshot, tracking init, training
    loop, checkpoint with snapshot commit, and run artifact bundle.
11. Update `PROJECT_STATE.json` with roadmap, project-map, glossary, and
    codebase-map artifacts.

## Output Rules

- Preserve template schema and decision vocabulary; localize prose according to
  language policy.
- Include test plan, Red/Green/Refactor or smoke feedback, validation
  checkpoints, complexity budget, and commit slices.
- Mark foundation-only slices clearly. A foundation slice can be accepted as a
  Commit Slice, but it must not be described as enough for
  `build_ready_for_iterate` unless it also provides the canonical runnable
  smoke/eval/training entrypoint and run-artifact bundle required by WF9.
- Do not add architecture choices. If the roadmap needs a different
  architecture, stop and route back to WF6 or design review.
- Run workflow-state checks when `PROJECT_STATE.json` or `project_map.json`
  changed, or report `NOT_RUN`.
- After stable Markdown is finalized, invoke `/docs-site` or report
  `docs_site_boundary_report` / `docs_site_render_or_NOT_RUN`.
