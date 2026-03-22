# Iterate Strong Constraints

These are mandatory behavior rules for `$iterate`.

## Scope

- These constraints apply whenever Codex is acting through `$iterate`.
- They are not generic repository-wide automation hooks.
- If the user bypasses `$iterate` and runs ad-hoc shell commands directly, these constraints are guidance, not an automatic trigger.

## Root-State Invariants

- `iteration_log.json` is the only experiment source of truth and must stay at the repository root.
- `PROJECT_STATE.json` must stay at the repository root and is read-only from `$iterate`.
- `project_map.json` must stay at the repository root and is updated only when stable interfaces change through code work.
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
  - `codex_review`
- Must check prior `lessons` and warn when the new hypothesis repeats a known failed pattern.

### `code`

- Must create both:
  - `.agents/state/iterations/<iter-id>/context.json`
  - `.agents/state/current_iteration.json`
- Must route implementation work through `$code-debug`.
- Must not move an iteration from `coding` to `training` without a semantic git commit.
- Must record `git_commit` and `git_message` into `iteration_log.json` before returning success.
- If no commit hash can be proven, the iteration must remain `coding`.

### `run`

- Must operate on the latest `training` iteration unless the user explicitly redirects.
- Must build the command from locked entry scripts in `CLAUDE.md` and the chosen config.
- Must resolve the tracked metrics from the baseline or evaluation protocol established in WF5.
- Must update `run_manifest` in `iteration_log.json` before returning.
- Must record, when available:
  - `command`
  - `config_path`
  - `exp_dir`
  - `started_at`
  - `duration_seconds`
  - `exit_code`
  - `checkpoint_path`
  - `wandb_url`
  - `error`
- Must persist final evaluation metrics only for the tracked metric set defined by WF5.
- Must keep training-only traces in a separate structure such as `training_trace` instead of hard-coding project-specific metric keys.
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
  - `status=completed` when evaluation is complete
- Must produce or refresh the per-iteration report under `docs/iterations/` when the workflow uses those reports.
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
