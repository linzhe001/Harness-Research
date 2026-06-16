# WF10: Structured Experiment Iteration

Use this skill only for WF10 experiment-loop state. It owns
`iteration_log.json`; it never writes `PROJECT_STATE.json` or `.auto_iterate/**`.
The auto-iterate controller may invoke these phases, but only `/iterate` writes
iteration records.

## Read First

- `iteration_log.json`; create it from `templates/iteration-log-schema.json`
  only if missing.
- `CLAUDE.md` `## Entry Scripts` for Train/Eval commands.
- `PROJECT_STATE.json` for read-only project and baseline context.
- `docs/10_contract/Evaluation_Contract.md` or protocol docs when present.
- Shared rules: `code-style.md`, `language-policy.md`,
  `documentation-evidence-rule.md`, `documentation-style.md`,
  `contract-gating-rule.md`, `run-artifact-contract.md`, and
  `lesson-quality-rule.md`.

## State Rules

- Append new experiment records; do not delete or rewrite completed entries.
- Keep `.claude/iterations/iter{N}/context.json` for sub-skill context.
- Use `.claude/current_iteration.json` only as a temporary symlink; remove it
  after `/code-debug` or `/evaluate` returns.
- If startup finds a stale current-iteration symlink, clean it: rollback
  `coding` to `planned`, leave `running`/`training` unchanged, remove symlink.
- `project_map.json` is stable code structure. Code-writing sub-steps must keep
  it current when stable files or interfaces change.

## Context Budget

Load active iteration plus 5 most recent summaries; reference full
`iteration_log.json` and Gate ledger by path. Include at most 5 Gate ledger
summaries in prompts or status context.

## Preflight And Next Action

Before recommending or executing a sub-command, resolve the latest iteration
from `iteration_log.json`: `id`, `status`, `decision`,
`config_diff.planned_command`, target script existence, `git_commit`,
`run_manifest`, and metrics/report availability.

Recommend exactly one immediate command unless the operator asks for a full
playbook. Map state to action: `planned` with missing code -> `code`;
`training` with committed code and runnable command -> `run`; `running` with
run artifacts -> `eval`; `completed` with `NEXT_ROUND` or `DEBUG` -> `plan`.
Do not recommend `code` for `training`, `run` for a missing planned command
target, or `eval` before run artifacts exist.

If a run-local script is reused for another slice, training route, or follow-up
iteration, recommend `/change classify` to promote it into stable `src/`,
`scripts`, `tests`, and `project_map.json` surfaces instead of cloning more
`runs/wf10/iter*/` scripts.

## Commands

### `plan [hypothesis]`

Read current and completed iterations. Refuse to start a new ordinary iteration
while any iteration is `coding` or `running`. Assign the next ID, run the lesson
dedup guard against previous failed lessons, and design a bounded change plan:
files, `config_diff`, expected effect, and screening recommendation. Always
attempt Codex MCP review when available; otherwise record
`codex_review: "unavailable"`. Write status `planned`.

### `code [description]`

Select the latest `planned` iteration, set status `coding`, write persistent
context, create the symlink, apply the shared code-style checklist, then invoke
`/code-debug`. Remove the symlink afterward. Require a real git commit hash and
message before advancing to `training`; if no commit exists, keep `coding` and
report the blocker.

### `run [config_path]`

Select the latest `training` iteration. Resolve Train/Eval scripts from
`CLAUDE.md`, infer or use the config path, and build the command from
`config_diff`. If `config_diff.planned_command` exists, run that exact command;
do not substitute a generic training dry-run, preflight-only command, or
unrelated smoke command for a planned run/eval command. Before launching it, verify any
`config_diff.run_local_config` path and any `--config` path; materialize a
missing run-local config only when `config_diff` includes enough `base_config`
plus override content, otherwise record `planned_command_not_runnable` without
launching an unrelated command. Record `run_manifest` with run artifact bundle
paths, `training_trace`, checkpoint path, duration, exit code, and only metrics
defined by the active evaluation protocol. For screening runs, store the bundle
in `screening.run_manifest` and mirror it in top-level `run_manifest` until a
full run replaces the top-level bundle. On successful eval, set status
`running`.
For OOM, NaN, crash, or missing checkpoint, keep status `training` and report
the concrete error. If `--manual` or cluster execution is required, register the
command and expected outputs without inventing metrics.

### `eval [log_path]`

Select the latest `running` or `training` iteration. Write/update context, call
`/evaluate` when available, and compare protocol metrics against baseline,
previous best, and previous iteration. Record metrics, at least one lesson,
slice/drift observations when relevant, `decision`, and status `completed`.
Include vertical slice boundary notes and complexity and boundary observations
when the iteration changes stable code surfaces.
Allowed decisions are `NEXT_ROUND`, `DEBUG`, `CONTINUE`, `PIVOT`, and `ABORT`.
Never update `PROJECT_STATE.json`; recommend the next `/iterate` or
`/orchestrator` command instead. Report a Gate ledger or `NOT_RUN` for
workflow-state checks near WF10 handoff points; use `check_workflow_state.py`
when checking workflow state.

### `ablate BASE --components "name:override,..."`

Require BASE to exist and be `completed`. Parse component overrides only from
the argument or existing iteration history. Create idempotent sub-iterations,
run/evaluate each component when possible, skip already completed components,
record failures without stopping the whole batch, and update the parent
`ablation_summary`.

### `status`

Show current in-progress iteration, five most recent iterations, best iteration,
baseline comparison, and recommended next command.

### `log`

Render the full iteration history as a compact table with ID, primary metric,
status, decision, and key change.

## Hard Constraints

- One unfinished ordinary iteration at a time unless an explicit ablation
  command creates sub-iterations.
- Every completed iteration needs metrics or a documented failure, a decision,
  and at least one lesson.
- Every completed metric-bearing iteration needs a run artifact bundle. If
  pieces are missing, report `NOT_RUN` and keep the iteration incomplete.
- Compare against baseline and previous best during eval.
- `git_commit` is required after `code` completes.
- The recommended next command must be singular unless a full playbook was
  explicitly requested.
- Core training/evaluation logic must stay in `CLAUDE.md` Entry Scripts;
  auxiliary scripts may support but not replace them.
- Do not promote raw observations to `MEMORY.md`; follow lesson-quality rules.

## Durable Docs Render

After stable Markdown outputs are finalized, invoke `/docs-site` or report
`docs_site_boundary_report`. Do not render for temporary drafts.
