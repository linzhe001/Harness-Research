---
name: iterate
description: "Internal Harness instruction source for iterate. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Iterate

Use this only for WF10 experiment-loop state. It owns `iteration_log.json`; it
never writes stage transitions into `PROJECT_STATE.json` or `.auto_iterate/**`.

## Read First
- Workflow, context, contract, lesson, code-style, review, language, docs, and
  commit checkpoint rules under `../../../.agents/references/`
- Research supervision assets:
  `research-supervision-patterns.md`,
  `research-supervision/experiment-and-build-canvas.md`, and
  `research-supervision/ai-assisted-research-workflow.md`
- `../../../.agents/references/run-artifact-contract.md`
- `./references/iteration-log-schema.json`,
  `./references/iteration-context.md`,
  `./references/iteration-constraints.md`
- `iteration_log.json`, `PROJECT_STATE.json`, `CLAUDE.md`, evaluation/baseline
  contracts, glossary, and lessons when present

## State Rules
- `iteration_log.json` is the experiment source of truth.
- New or migrated logs use `schema_version: "2"` with per-iteration
  `action_state` and `implementation`.
- `$orchestrator` owns `PROJECT_STATE.json` transitions.
- Stable file/interface changes sync `project_map.json` when present.
- Auto-iterate may invoke phases through a runtime adapter, but it only reads
  `iteration_log.json` postconditions.
- Active context belongs in `.agents/state/iterations/<iter-id>/context.json`
  plus `.agents/state/current_iteration.json` only when needed.

## Preflight
Load active iteration plus 5 recent summaries; reference full history and Gate
ledger by path. Resolve latest `id`, `status`, `decision`,
`config_diff.planned_command`, target script, `git_commit`, `run_manifest`, and
metrics/report availability.

Scan `auto_paper_output/*/run_request_register.{json,md}` and fold the highest
priority unclosed request into planning unless a higher-priority WF10 blocker
exists.

Recommend exactly one next command unless asked for a playbook. Prefer
`action_state.next_action`; migrate legacy logs with
`tooling/evidence/migrate_iteration_log_v2.py` or map status:
`planned|coding -> code`, `ready_to_run -> run_screening|run_full`,
`running|ready_to_eval -> eval`, `needs_debug -> debug`,
`needs_more_evidence -> compare`, `candidate_for_promotion|promoting -> promote`,
`completed/NEXT_ROUND -> plan`, terminal -> `stop`.

If run-local code becomes reusable, recommend `$iterate promote` or
`$change classify` before merging into stable `src/`, `scripts`, `tests`, or
`project_map.json`.

## Commands
- `next`: execute one `action_state.next_action`, update `last_action`,
  `next_action`, `reason`, and `blocked_by`, then stop.
- `plan`: refuse ordinary new work while an iteration is `coding` or `running`;
  allocate ID; check lessons; record hypothesis, files, `config_diff`, expected
  effect, screening recommendation, dominant improvement axis, falsifier,
  assurance axis, minimum artifact, claim/figure implication, canonical
  `codex_review`, and implementation scope: `config_only`, `run_local_code`,
  `stable_candidate`, or `delegated_build`. Read
  `docs/context/experiments.md` when present and consume one queued item or
  explain the priority choice. Use legacy
  `docs/40_iterations/Experiment_Queue.md` only when the project has not
  migrated to dynamic-context-v2.
- `code`: select latest planned iteration, write context, apply code-style
  checklist, preserve slice/glossary boundaries, route implementation through
  `$code-debug`, and run a `slice` or `experiment` commit checkpoint before
  status `ready_to_run`. For `run_local_code` or `stable_candidate`, write
  `runs/wf10/<iter>/code_manifest.json`.
- `run_screening` / `run_full`: select latest `ready_to_run`; resolve Train/Eval
  scripts from `CLAUDE.md`; run `config_diff.planned_command` exactly when
  present; verify run-local config paths; create or verify a Semantic Execution
  Commit covering stable code, configs, eval logic, and run-local code/configs;
  record `run_manifest`, `pre_train_commit`, artifacts, screening result when
  relevant, and protocol metrics. Set `ready_to_eval`, `needs_debug`, or
  `needs_more_evidence`; never invent metrics.
- `register`: record externally executed/manual run paths and expected outputs
  without inventing metrics; set `ready_to_eval` only when the bundle is
  complete.
- `debug`, `compare`, `ablate`: operate inside the same iteration unless an
  explicit ablation command creates sub-iterations; update `action_state`.
- `eval`: refresh context; invoke `$evaluate` when useful; compare baseline,
  previous, and best metrics; create or verify `pre_eval_commit`, or record
  `pre_eval_commit_NOT_CHANGED`; record metrics or documented failure, decision,
  lessons, assurance axis, claim delta evidence, slice/drift/complexity notes,
  reports, and completion state. Write mutable observations to
  `docs/context/experiments.md`, including concrete next experiments, mutable
  observations, and stable searchable findings, or report `NOT_RUN`. Legacy
  `docs/45_discoveries/Discovery_Ledger.md`,
  `docs/40_iterations/Experiment_Queue.md`, and
  `docs/45_discoveries/Research_Wiki.md` may be updated only for
  not-yet-migrated projects. Refresh the light Evidence layer with
  `tooling/evidence/build_light_evidence_index.py`;
  run `tooling/evidence/build_experiment_evidence_index.py` only when detailed
  claim/writing evidence is needed, or report `NOT_RUN`.
- `promote`: read `implementation.code_manifest_path`, write/verify
  `implementation.promotion.plan_path`, run acceptance commands or report
  `NOT_RUN`, merge only approved candidate code into stable surfaces, and update
  `project_map.json` / `Codebase_Map.md` when stable structure changes.
- `discard`, `status`, `log`: preserve canonical schema and history behavior.

## Lesson And Gate Rules
- Append `MEMORY.md` only for accepted lessons satisfying
  `lesson-quality-rule.md`; raw observations stay in iteration reports or
  `docs/context/experiments.md`; candidates may be promoted into
  `docs/context/memory.md`.
- When `iteration_log.json`, lesson files, accepted memory, reports, queue/wiki
  docs, claim delta evidence, or evidence indexes change, report a Gate ledger.
- Run `check_workflow_state.py` near WF10 handoff points; for routine in-loop
  updates, report whether it was run or deferred.
- After Grill establishes an Automation Policy, WF10 auto-proceeds within that
  policy. Do not ask for human approval during run/eval loops unless the action
  would leave the policy, run an explicit approval tool, or perform an
  irreversible external submission.
- Use commit hashes, Gate ledgers, Claim Delta Evidence, Experiment Queue, and
  Research Wiki updates for traceability.

## Durable Docs Render
After stable Markdown is finalized, invoke `$docs-site` or report
`docs_site_boundary_report` / `docs_site_render_or_NOT_RUN`; do not render
temporary drafts.
