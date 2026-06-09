---
name: iterate
description: "WF10 structured experiment iteration. Manages the hypothesis->code->run->eval cycle, maintains iteration_log.json, with optional Codex cross-validation. Supported commands: plan, code, run, eval, ablate, status, log."
argument-hint: "[plan|code|run|eval|ablate|status|log] [details]"
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Skill, WebSearch
---

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
  `contract-gating-rule.md`, and `lesson-quality-rule.md`.

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
`CLAUDE.md`, infer or use the config path, build the command from `config_diff`,
and run training in the background when possible. Record `run_manifest`,
`training_trace`, checkpoint path, duration, exit code, and only metrics defined
by the active evaluation protocol. On successful eval, set status `running`.
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
- Compare against baseline and previous best during eval.
- `git_commit` is required after `code` completes.
- Core training/evaluation logic must stay in `CLAUDE.md` Entry Scripts;
  auxiliary scripts may support but not replace them.
- Do not promote raw observations to `MEMORY.md`; follow lesson-quality rules.

## Durable Docs Render

After stable Markdown outputs are finalized, invoke `/docs-site` or report
`docs_site_render_or_NOT_RUN`. Do not render for temporary drafts.
