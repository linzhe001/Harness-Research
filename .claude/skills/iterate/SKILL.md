# WF10: Structured Experiment Iteration

Use this skill only for WF10 experiment-loop state. It owns
`iteration_log.json`; it never writes `PROJECT_STATE.json` or `.auto_iterate/**`.
The auto-iterate controller may invoke phases, but only `/iterate` writes
iteration records.

## Read First

- `iteration_log.json`; create from `templates/iteration-log-schema.json` only if missing.
- `CLAUDE.md` `## Entry Scripts`; `PROJECT_STATE.json` read-only.
- `docs/context/contracts.md` and `docs/context/protocol.md` when present;
  legacy `docs/10_contract/Evaluation_Contract.md` is a fallback only before
  dynamic-context-v2 migration.
- Shared rules: `code-style.md`, `language-policy.md`,
  `documentation-evidence-rule.md`, `documentation-style.md`,
  `contract-gating-rule.md`, `run-artifact-contract.md`,
  `lesson-quality-rule.md`, `commit-checkpoint-rule.md`,
  `research-supervision-patterns.md`,
  `research-supervision/experiment-and-build-canvas.md`, and
  `research-supervision/ai-assisted-research-workflow.md`.

## State Rules

- Append records; do not delete or rewrite completed entries.
- New or migrated logs use `schema_version: "2"` with per-iteration
  `action_state` and `implementation`.
- Keep `.claude/iterations/iter{N}/context.json`; use
  `.claude/current_iteration.json` only as temporary sub-skill context.
- Clean stale current-iteration symlinks: rollback `coding` to `planned`, leave
  `running`/`ready_to_run`/`ready_to_eval` unchanged.
- `project_map.json` tracks stable code. Stable file/interface changes must
  update it and `Codebase_Map.md` when present.

## Preflight

Load active iteration plus 5 recent summaries; reference full
`iteration_log.json` and Gate ledger by path. Resolve latest `id`, `status`,
`decision`, `config_diff.planned_command`, target script, `git_commit`,
`run_manifest`, and metrics/report availability.

Scan `auto_paper_output/*/run_request_register.{json,md}`. Fold the highest
priority unclosed request into planning unless a higher-priority WF10 blocker
exists or the operator opts out.

Recommend one immediate command unless asked for a playbook. Prefer
`action_state.next_action`; migrate legacy logs with
`tooling/evidence/migrate_iteration_log_v2.py` or map status:
`planned|coding -> code`, `ready_to_run -> run_screening|run_full`,
`running|ready_to_eval -> eval`, `needs_debug -> debug`,
`needs_more_evidence -> compare`, `candidate_for_promotion|promoting -> promote`,
`completed/NEXT_ROUND -> plan`, terminal -> `stop`.

If run-local code becomes reusable, recommend `/iterate promote` or
`/change classify` before merging into stable `src/`, `scripts`, `tests`, or
`project_map.json`.

## Actions

- `next`: execute exactly one `action_state.next_action`, then update
  `last_action`, `next_action`, `reason`, and `blocked_by`.
- `plan`: refuse ordinary new work while an iteration is `coding` or `running`;
  allocate ID; check lessons; record hypothesis, files, `config_diff`, expected
  effect, screening recommendation, dominant improvement axis, falsifier,
  assurance axis, minimum artifact, claim/figure implication, Codex review
  status, and implementation scope: `config_only`, `run_local_code`,
  `stable_candidate`, or `delegated_build`. Read
  `docs/context/experiments.md` when it exists and either consume one queued
  item or explain the priority choice. Use legacy
  `docs/40_iterations/Experiment_Queue.md` only before dynamic-context-v2
  migration.
- `code`: select latest `planned`; set `coding`; write context; invoke
  `/code-debug`; run a `slice` or `experiment` commit checkpoint before
  `ready_to_run`; for `run_local_code` or `stable_candidate`, write
  `runs/wf10/<iter>/code_manifest.json`.
- `run_screening` / `run_full`: select latest `ready_to_run`; resolve
  Train/Eval scripts from `CLAUDE.md`; run `config_diff.planned_command`
  exactly when present; verify run-local config paths; create or verify a
  Semantic Execution Commit covering stable code, configs, eval logic, and
  run-local code/configs; record `run_manifest`, `pre_train_commit`,
  `training_trace`, checkpoints, duration, exit code, and protocol metrics.
  Use `register` for manual/cluster runs. Set `ready_to_eval`, `needs_debug`,
  or `needs_more_evidence`; never invent metrics.
- `register`: record externally executed/manual run paths and expected outputs;
  set `ready_to_eval` only when the artifact bundle is complete.
- `eval`: select latest `ready_to_eval` or `running`; call `/evaluate` when
  useful; compare against baseline, previous best, and previous iteration;
  create or verify `pre_eval_commit`, or record `pre_eval_commit_NOT_CHANGED`;
  record metrics or documented failure, assurance axis, claim delta evidence,
  lessons, decision, and completion.
  Include vertical slice boundary notes and complexity and boundary observations
  when stable code surfaces change. Record mutable observations, phenomena,
  findings, next-experiment hypotheses, concrete next experiments, and stable
  searchable findings in `docs/context/experiments.md`, or report `NOT_RUN`.
  Legacy `docs/45_discoveries/Discovery_Ledger.md`,
  `docs/40_iterations/Experiment_Queue.md`, and
  `docs/45_discoveries/Research_Wiki.md` are fallback paths only before
  dynamic-context-v2 migration. Refresh
  `.evidence/light/index.json` with
  `tooling/evidence/build_light_evidence_index.py`; run
  `tooling/evidence/build_experiment_evidence_index.py` only for detailed
  claim/writing evidence, or report `NOT_RUN`.
- `ablate`: create idempotent sub-iterations from explicit components or
  history; skip completed components; update parent `ablation_summary`.
- `debug` / `compare`: operate inside the same iteration and update
  `action_state`.
- `promote`: read `implementation.code_manifest_path`; write/verify
  `implementation.promotion.plan_path`; run acceptance commands or report
  `NOT_RUN`; merge only approved candidate code into stable surfaces; update
  `project_map.json` / `Codebase_Map.md` when structure changes.
- `discard`: preserve negative-result evidence and close the iteration without
  deleting history.
- `status` / `log`: show current, five recent iterations, best iteration,
  baseline comparison, and one recommended next command.

## Hard Constraints

- One unfinished ordinary iteration at a time unless explicit ablation creates
  sub-iterations.
- Completed iterations need metrics or documented failure, decision, and lesson.
- Metric-bearing completions need a run artifact bundle; missing pieces keep the
  iteration incomplete with `NOT_RUN`.
- Decisions are `NEXT_ROUND`, `DEBUG`, `CONTINUE`, `PIVOT`, `ABORT`.
- `git_commit` is required after `code`; do not update `PROJECT_STATE.json`.
- Meaningful run/eval commands require `pre_train_commit` and `pre_eval_commit`
  or explicit `pre_eval_commit_NOT_CHANGED`. Run-local code/configs under
  `runs/wf10/<iter>/` are part of this execution boundary even when they are
  never promoted into stable code.
- After Grill has established an Automation Policy, WF10 auto-proceeds within
  that policy. Do not ask for human approval during run/eval loops unless the
  action would leave the Automation Policy, run an explicit approval tool, or
  perform an irreversible external submission.
- Core train/eval logic stays in `CLAUDE.md` Entry Scripts.
- Do not promote raw observations to `MEMORY.md`; keep them in
  `docs/context/experiments.md` until lesson-quality rules promote them into
  `docs/context/memory.md`.
- Near WF10 handoff, report Gate ledger and run `check_workflow_state.py` or
  mark it `NOT_RUN`.

## Durable Docs Render

After stable Markdown outputs are finalized, invoke `/docs-site` or report
`docs_site_render_or_NOT_RUN`. Do not render for temporary drafts.
