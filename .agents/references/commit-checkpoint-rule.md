# Commit Checkpoint Rule

## Purpose

Keep long build/run loops fast while preventing large unreviewable worktrees.
Routine workflow actions should run only the checks needed for that action.
Validation-heavy checks move to automatic commit checkpoints.

## Checkpoint Triggers

An agent should create a commit checkpoint when:

- a completed implementation or docs slice is ready
- `$iterate code` is about to mark an iteration `ready_to_run`
- `$iterate eval` or `$evaluate` writes iteration/discovery/lesson artifacts
- non-tool-owned dirty paths span more than one ownership domain
- non-tool-owned dirty paths exceed eight files
- the next action is a long run, external/manual run registration, or handoff

Do not stage unrelated user changes.

## Validation Profiles

- `slice`: default profile for ordinary code/docs slices. Run modified Python
  `py_compile`, `ruff check --select=E,F,I`, and the smallest focused test or
  record `NOT_RUN`.
- `guardrail`: hook, schema, skill contract, routing, permission, or supervisor
  policy changes. Run `check_contracts.py`, focused hook/contract tests, and
  Python lint/compile for modified Python.
- `docs`: template, handbook, or workflow prose changes. Run focused dynamic
  context/template tests. Run docchain tooling only for current
  contract/fact/protocol/release docs.
- `experiment`: WF10 run-local or iteration evidence changes. Validate
  `iteration_log.json`, run artifact manifests, and discovery ledger updates;
  do not run framework-wide tests by default.
- `release`: approval, claim boundary, WF11/WF12, or release package changes.
  Run dynamic-context gates, docchain gates, and release checks.

## Required Behavior

Before each agent-created commit:

1. Inspect `git status --short` and staged changes.
2. Identify exactly one Commit Slice.
3. Select the validation profile from the slice owner and risk.
4. Run the profile checks or record `NOT_RUN` reasons.
5. Stage only that slice.
6. Commit with a semantic subject that explains what changed and why.
7. Report the commit hash, subject, profile, and Gate ledger.

Hooks may remind about checkpoints, but hooks are not Gate Evidence.
