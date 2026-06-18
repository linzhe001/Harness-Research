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

## Preflight And Recommendation Rules

Before any `$iterate` sub-command or WF10 command recommendation:

- Must resolve the latest iteration from `iteration_log.json`, including:
  - `id`
  - `status`
  - `decision`
  - `config_diff.planned_command`
  - planned command target script existence when a script path is present
  - `git_commit`
  - `run_manifest`
  - metrics and report availability
- Must recommend exactly one immediate next command unless the operator asks for
  a full playbook. A full playbook must still label the current command first.
- Must map state to action:
  - no active iteration, or latest `completed` with `NEXT_ROUND`/`DEBUG` -> `plan`
  - latest `planned` and implementation missing -> `code`
  - latest `training` with committed code and runnable planned command -> `run`
  - latest `running` with run artifacts -> `eval`
  - latest `completed` with `CONTINUE` -> orchestrator handoff, not another iteration command
- Must not recommend:
  - `code` when the latest iteration is already `training` or `running`
  - `run` when the planned command target script or required config path is missing
  - `eval` before a run artifact bundle or preserved manual-run registration exists
  - a multi-command chain as the current instruction unless explicitly requested

Run-local versus stable-code boundary:

- A single-iteration probe may live under `runs/wf10/<iter-id>/`.
- If the same run-local capability is reused for another slice, a training
  route, an adapter/reranker follow-up, or more than one future iteration, must
  recommend `$change classify` to promote it into stable `src/`, `scripts/`,
  `tests`, and `project_map.json` surfaces before further expansion.
- `$iterate code` must not become the default home for reusable architecture.
  Use `$change classify` for direction or architecture changes and `$code-debug`
  for stable implementation fixes.

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
  - `assurance_axis`
  - `status=planned`
  - `screening.recommended`
  - `codex_review`
- Must check `docs/40_iterations/Experiment_Queue.md` when it exists and
  either consume one queued item or explain why the selected hypothesis is
  higher priority.
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
  command. It must also verify the planned command target script when the
  command names a workspace script path. If a path is missing and `config_diff`
  includes enough `base_config` plus override content to materialize it, write
  the run-local config first. Otherwise record a
  `planned_command_not_runnable` failure and do not launch an unrelated command.
- Must resolve the tracked metrics from the baseline or evaluation protocol established in WF5.
- Before launching any meaningful train/screen/full command, must create or
  verify a Semantic Execution Commit covering stable entry scripts, eval logic
  used by the command, durable configs, run-local configs, and run-local code
  under `runs/wf10/<iter-id>/`. Record this hash as `pre_train_commit` in the
  run manifest or Gate ledger.
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
  - `pre_train_commit`
  - `pre_eval_commit` or `pre_eval_commit_NOT_CHANGED`
  - `run_local_code_manifest_path`
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
- Before running meaningful eval commands or using metric outputs as
  Conclusion Evidence, must create or verify `pre_eval_commit`. If eval logic,
  configs, run-local eval helpers, claim-support docs, and release-validation
  code are unchanged since `pre_train_commit`, record
  `pre_eval_commit_NOT_CHANGED`.
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
  - `assurance_axis`
  - `claim_delta_evidence` or `claim_delta_evidence_NOT_CHANGED`
  - `status=completed` when evaluation is complete
- Must not mark `status=completed` until the run artifact bundle exists. If
  pieces are missing, report `NOT_RUN` in the Gate ledger and keep the
  iteration incomplete.
- Must produce or refresh a per-iteration report at `docs/40_iterations/<iter-id>.md`
  for dynamic-context workflows. Legacy/report-directory workflows may also
  mirror `docs/iterations/<iter-id>.md`.
- Should produce or refresh `docs/40_iterations/latest.md` when the dynamic context layout is enabled.
- Should append or refresh candidate lessons in `docs/50_memory/Lessons.md`.
- Should append or refresh `docs/40_iterations/Experiment_Queue.md` when eval
  identifies a concrete next experiment, falsifier, assurance gap, or paper
  run request.
- Should append or refresh `docs/45_discoveries/Research_Wiki.md` for stable
  observations, method notes, open questions, and finding summaries that should
  remain searchable outside one iteration report.
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
- Mandatory train/eval execution boundary:
  - `$iterate run`, `run_screening`, and `run_full` must start from a Semantic
    Execution Commit recorded as `pre_train_commit`.
  - `$iterate eval` must start from a Semantic Execution Commit recorded as
    `pre_eval_commit`, or explicitly record `pre_eval_commit_NOT_CHANGED`.
  - Run-local code and configs under `runs/wf10/<iter-id>/` are included in
    this boundary even when they are not intended for stable promotion.
  - Claim or claim-boundary changes need Claim Delta Evidence, not a new human
    approval prompt, when they stay inside the active Automation Policy.
- Research bookkeeping boundary:
  - `$iterate run` and `$iterate eval` primarily update tracked research records
    such as `iteration_log.json`, reports, Experiment Queue, Discovery Ledger,
    and Research Wiki.
  - They should not create unrelated source edits.
  - If tracked research records or claim-support docs change before a long
    follow-up run or handoff, create an `experiment` commit checkpoint or
    report `NOT_RUN`.
- Never hide missing bookkeeping behind an absent commit. The state file update is mandatory even when no commit is made.

## Turn-End Output

Every `$iterate` sub-command response must make the state transition explicit:

- selected iteration id
- previous status
- new status
- files updated
- recommended next command

The recommended next command must be singular unless the operator explicitly
asked for a full playbook.
