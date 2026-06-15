# Iterate Strong Constraints

These are mandatory behavior rules for `$iterate`.

## Scope

- These constraints apply whenever Codex is acting through `$iterate`.
- They are not generic repository-wide automation hooks.
- If the user bypasses `$iterate` and runs ad-hoc shell commands directly, these constraints are guidance, not an automatic trigger.

## Root-State Invariants

- `iteration_log.json` is the only experiment source of truth and must stay at the repository root.
- `PROJECT_STATE.json` must stay at the repository root and is read-only from `$iterate`.
- `project_map.json` must stay at the repository root and is updated whenever
  stable file presence or stable interfaces change through code work.
- `.agents/state/` is volatile local context only; never move canonical project state there.
- Keep `.agents/state/` as the reserved local context directory, but create context files inside it only when needed.

## Sub-command Obligations

### `plan`

- Must refuse to create a new iteration if there is a blocking unfinished iteration in `coding` or `running`.
- Must write a structured iteration entry before returning control.
- Must record at least:
  - `id`
  - `date`
  - `hypothesis`
  - `changes_summary`
  - `config_diff`
  - `status=planned`
  - `screening.recommended`
  - `codex_review`
- Must check prior `lessons` and warn when the new hypothesis repeats a known failed pattern.
- Must read accepted lessons from `MEMORY.md` and candidate/accepted lessons from `docs/50_memory/Lessons.md` when those files exist.

### `code`

- Must create both:
  - `.agents/state/iterations/<iter-id>/context.json`
  - `.agents/state/current_iteration.json`
- Must route implementation work through `$code-debug`.
- Must preserve the current vertical slice boundary from
  `docs/Implementation_Roadmap.md` when present.
- Must preserve `docs/20_facts/Project_Glossary.md` vocabulary when present.
- Must not move an iteration from `coding` to `training` without a semantic git commit.
- Must record `git_commit` and `git_message` into `iteration_log.json` before returning success.
- If no commit hash can be proven, the iteration must remain `coding`.

### `run`

- Must operate on the latest `training` iteration unless the user explicitly redirects.
- Must build the command from locked entry scripts in `CLAUDE.md` and the chosen config.
- If `config_diff.planned_command` exists, must run that exact command. Do not
  substitute a generic training dry-run, preflight-only command, or unrelated
  smoke command for a planned run/eval command.
- Before launching `config_diff.planned_command`, must verify every
  `config_diff.run_local_config` path and every `--config` path in the planned
  command. If a path is missing and `config_diff` includes enough `base_config`
  plus override content to materialize it, write the run-local config first.
  Otherwise record a `planned_command_not_runnable` failure and do not launch an
  unrelated command.
- Must resolve the tracked metrics from the baseline or evaluation protocol established in WF5.
- Must update `run_manifest` in `iteration_log.json` before returning.
- Must record, when available:
  - `artifact_contract_version`
  - `run_type`
  - `command`
  - `config_path`
  - `resolved_config_path`
  - `exp_dir`
  - `stdout_log_path`
  - `git_snapshot_path`
  - `git_commit`
  - `started_at`
  - `duration_seconds`
  - `exit_code`
  - `checkpoint_path`
  - `eval_artifact_paths`
  - `wandb_url`
  - `error`
- Completed metric-bearing runs must satisfy
  `.agents/references/run-artifact-contract.md`: semantic pre-run commit,
  resolved config snapshot, console log, git snapshot, and metric artifact
  paths in or under `exp_dir`.
- Must persist final evaluation metrics only for the tracked metric set defined by WF5.
- Must keep training-only traces in a separate structure such as `training_trace` instead of hard-coding project-specific metric keys.
- When the run is a screening/proxy run and `screening.status` is `passed` or
  `failed`, must record `screening.metrics` from the same tracked metric set and
  keep the screening artifact bundle in `screening.run_manifest`. Top-level
  `run_manifest` may mirror the screening bundle until a full run replaces it.
- Full runs must preserve `screening.run_manifest` before replacing top-level
  `run_manifest` with the full run bundle.
- When a screening/proxy run is the planned objective path and its primary
  metric already meets the WF10 target, auto-iterate may skip `run_full` and
  advance directly to `eval`; the screening bundle must remain in
  `screening.run_manifest` and top-level `run_manifest` until a real full run
  exists.
- Must end with one of:
  - `status=running` when metrics were collected and eval can proceed
  - `status=training` when the run failed and needs rerun or manual intervention
- Must output a concise run summary and the recommended next-step command.
- Must not silently finish without updating `iteration_log.json`.
- Must not perform opportunistic source-code edits during `run`.

### `eval`

- Must refresh active iteration context before analysis when context exists.
- Must compare the current results against:
  - baseline metrics
  - previous iteration
  - best iteration
- The comparison basis must come from the WF5 evaluation protocol, not from fixed assumptions about PSNR/SSIM/LPIPS or any other metric family.
- Must write back to `iteration_log.json`:
  - finalized `metrics`
  - exactly one `decision` from {NEXT_ROUND, DEBUG, CONTINUE, PIVOT, ABORT}
  - non-empty `lessons`
  - `lesson_candidates` when promotion-worthy findings are identified
  - `lesson_promotion_status` when a lesson is accepted or rejected
  - slice completion or drift observations when a planned slice changed scope
  - complexity and boundary observations when public APIs, dependencies, or
    naming changed during the iteration
  - `status=completed` when evaluation is complete
- Must not mark `status=completed` until the run artifact bundle exists. If
  pieces are missing, report `NOT_RUN` in the Gate ledger and keep the
  iteration incomplete.
- Must produce or refresh a per-iteration report at `docs/40_iterations/<iter-id>.md`
  for dynamic-context workflows. Legacy/report-directory workflows may also
  mirror `docs/iterations/<iter-id>.md`.
- Should produce or refresh `docs/40_iterations/latest.md` when the dynamic context layout is enabled.
- Should append or refresh candidate lessons in `docs/50_memory/Lessons.md`.
- Must append to `MEMORY.md` only for accepted lessons that satisfy the lesson quality rule; raw observations and auto-run findings must not enter `MEMORY.md` directly.
- Must output the recommended next-step command that matches the decision:
  - `NEXT_ROUND` -> `$iterate plan "..."` (ordinary improvement round)
  - `DEBUG` -> `$iterate plan "..." [debug-oriented]`
  - `CONTINUE` -> `$orchestrator next`
  - `PIVOT` -> `$orchestrator rollback 2`
  - `ABORT` -> `$orchestrator decision`

### `ablate`

- Must keep parent-child linkage through `parent_iteration` and `ablation_component`.
- Must summarize the final ablation outcome on the parent iteration entry.

### `status` and `log`

- Must report from `iteration_log.json` instead of inventing transient state.

## Commit Discipline

- Mandatory commit boundary:
  - `$iterate code` must end with a semantic commit before training can begin.
- Non-mandatory commit boundary:
  - `$iterate run` and `$iterate eval` primarily update tracked research records such as `iteration_log.json` and reports.
  - They should not create unrelated source edits.
  - If they do change tracked records in the current turn, Codex should leave those changes explicit in the worktree and may commit them only when the user asked for commit discipline on experiment bookkeeping.
- Never hide missing bookkeeping behind an absent commit. The state file update is mandatory even when no commit is made.

## Turn-End Output

Every `$iterate` sub-command response must make the state transition explicit:

- selected iteration id
- previous status
- new status
- files updated
- recommended next command
