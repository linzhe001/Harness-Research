---
name: iterate
description: "Internal Harness instruction source for iterate. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Iterate

Use this Skill only for WF10 experiment-loop state. It owns
`iteration_log.json`; it never writes stage transitions into
`PROJECT_STATE.json` and never writes `.auto_iterate/**`.

## Read First

- Workflow, context, contract, lesson, code-style, review, language, docs, and
  commit checkpoint rules under `../../../.agents/references/`
- `../../../.agents/references/commit-checkpoint-rule.md`
- `../../../.agents/references/run-artifact-contract.md`
- `./references/iteration-log-schema.json`
- `./references/iteration-context.md`
- `./references/iteration-constraints.md`
- `iteration_log.json`, `PROJECT_STATE.json`, `CLAUDE.md`
- Evaluation/Baseline contracts, glossary, and lessons when present

## State Rules

- `iteration_log.json` is the experiment source of truth.
- New or migrated logs must use `schema_version: "2"` with per-iteration
  `action_state` and `implementation`.
- `$orchestrator` owns `PROJECT_STATE.json` transitions.
- Code-writing substeps must sync `project_map.json` when stable files or
  interfaces change.
- Auto-iterate may invoke phases through a runtime adapter, but it only reads
  `iteration_log.json` postconditions.
- Active context belongs in `.agents/state/iterations/<iter-id>/context.json`
  plus `.agents/state/current_iteration.json` only when needed.

## Context Budget

- Load active iteration plus 5 most recent summaries; reference full
  `iteration_log.json` and Gate ledger by path.
- Include at most 5 Gate ledger summaries in prompts or status context.

## Preflight And Next Action

Before recommending or executing a sub-command, resolve the latest iteration
from `iteration_log.json`: `id`, `status`, `decision`,
`config_diff.planned_command`, target script existence, `git_commit`,
`run_manifest`, and metrics/report availability.

Also scan `auto_paper_output/*/run_request_register.{json,md}` for pending
requests. If present, include the highest-priority unclosed request as planning
context and make the next iteration answer its `needed_evidence` and
`acceptance_check`, unless a higher-priority WF10 blocker exists.

Recommend exactly one next command unless the operator explicitly asks for a
full playbook. Prefer `action_state.next_action` over status heuristics. If a
legacy record lacks `action_state`, migrate it with
`tooling/evidence/migrate_iteration_log_v2.py` or use this fallback:
`planned` -> `code`; `coding` -> `code`; `ready_to_run` -> `run_screening` or
`run_full`; `running`/`ready_to_eval` -> `eval`; `needs_debug` -> `debug`;
`needs_more_evidence` -> `compare`; `candidate_for_promotion`/`promoting` ->
`promote`; `completed` with `NEXT_ROUND` -> `plan`; terminal or abandoned ->
`stop`.

If a run-local script becomes reusable across another slice, training path, or
follow-up iteration, recommend `$iterate promote` or `$change classify` to
promote it into stable `src/`, `scripts/`, `tests`, and `project_map.json`
surfaces instead of cloning more `runs/wf10/iter*/` scripts.

## Commands

- `next`: read the active iteration's `action_state.next_action`, execute one
  matching action, update `action_state.last_action`, `action_state.next_action`,
  `reason`, and `blocked_by`, then stop.
- `plan`: ensure no blocking unfinished iteration, allocate ID, check accepted
  lessons and candidate lessons, record hypothesis, changes summary,
  `config_diff`, screening recommendation, and canonical `codex_review`
  behavior. Initialize `implementation` with scope `config_only`,
  `run_local_code`, `stable_candidate`, or `delegated_build`.
- `code`: select latest planned iteration, write context, apply code-style
  checklist, preserve slice/glossary boundaries, route implementation through
  `$code-debug`, and run a `slice` or `experiment` commit checkpoint before
  status `ready_to_run`.
  For `run_local_code` or `stable_candidate`, write
  `runs/wf10/<iter>/code_manifest.json`.
- `run_screening` / `run_full`: select latest `ready_to_run` iteration, resolve
  Train/Eval scripts from `CLAUDE.md`, run `config_diff.planned_command`
  exactly when present, verify
  or materialize run-local config paths before launch, use WF5 protocol metric
  keys, record `run_manifest` with run artifact bundle paths, tracked metrics,
  screening result when relevant, and canonical failure/manual-mode behavior.
  Set `ready_to_eval`, `needs_debug`, or `needs_more_evidence` rather than
  inventing metrics.
- `register`: record an externally executed/manual run and its expected or
  observed artifact paths without inventing metrics.
- `debug`, `compare`, `ablate`: operate inside the same iteration unless an
  explicit ablation command creates sub-iterations; update `action_state`.
- `eval`: refresh context, invoke `$evaluate` when needed, compare baseline,
  previous, and best metrics, record decision, lessons, slice/drift,
  complexity/boundary observations, reports, and completion state. Record
  mutable observations, phenomena, findings, and next-experiment hypotheses in
  `docs/45_discoveries/Discovery_Ledger.md` or report `NOT_RUN`; then refresh
  the light Evidence layer with `tooling/evidence/build_light_evidence_index.py`.
  Refresh
  `docs/30_evidence/Experiment_Evidence_Index.{json,md}` with
  `tooling/evidence/build_experiment_evidence_index.py` only when detailed
  claim/writing evidence is needed, or report `NOT_RUN` with the reason.
- `promote`: read `implementation.code_manifest_path`, write or verify
  `implementation.promotion.plan_path`, run acceptance commands or report
  `NOT_RUN`, then merge only approved candidate code into stable surfaces and
  update `project_map.json` / `Codebase_Map.md` when stable structure changes.
- `discard`, `status`, `log`: preserve canonical schema and history behavior.

## Lesson And Gate Rules

- Append `MEMORY.md` only for accepted lessons satisfying
  `lesson-quality-rule.md`; raw observations stay in iteration reports or
  `docs/45_discoveries/Discovery_Ledger.md`; lesson candidates may be promoted
  into `docs/50_memory/Lessons.md`.
- When `iteration_log.json`, lesson files, or accepted memory changed, report a
  Gate ledger.
- Run `check_workflow_state.py` near WF10 handoff points; for routine in-loop
  updates, report whether it was run or deferred.

## Durable Docs Render

After stable Markdown is finalized, invoke `$docs-site` or report
`docs_site_boundary_report` / `docs_site_render_or_NOT_RUN`. Do not render for
temporary drafts.
