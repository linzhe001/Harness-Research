# Commit Checkpoint Rule

## Purpose

Keep long build/run loops fast while preventing large unreviewable worktrees.
Routine workflow actions should run only the checks needed for that action.
Validation-heavy checks move to automatic commit checkpoints.

## Checkpoint Triggers

An agent should create a commit checkpoint when:

- a completed implementation or docs slice is ready
- `$iterate code` is about to mark an iteration `ready_to_run`
- `$iterate run`, `run_screening`, `run_full`, or any equivalent automation is
  about to launch meaningful training
- `$iterate eval`, `$evaluate`, WF11, or release validation is about to run
  meaningful metric-bearing evaluation after eval logic, configs, claims, or
  run-local code changed
- `$iterate eval` or `$evaluate` writes iteration/discovery/lesson artifacts
- a Claim Boundary, claim register, paper claim, release claim, or supported
  conclusion changes under an Automation Policy
- non-tool-owned dirty paths span more than one ownership domain
- non-tool-owned dirty paths exceed eight files
- the next action is a long run, external/manual run registration, or handoff

Do not stage unrelated user changes.

Meaningful train/eval checkpoints are mandatory, not best-effort. Run-local
code under `runs/wf10/<iter>/`, run-local configs, stable entry scripts, eval
logic, and durable claim-support docs are Source Artifacts for the upcoming
execution and must be covered by a semantic commit before the execution starts.
Dirty worktree executions remain debug/smoke only unless the dirty patch is
preserved and the limitation is reported.

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
- `release`: claim boundary, claim delta, WF11/WF12, or release package
  changes. Run dynamic-context gates, docchain gates, and release checks.

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

## Automation Policy

After `$grill` records an Automation Policy, non-Grill workflow actions should
auto-proceed within that policy instead of repeatedly asking for human approval.
The replacement for approval spam is evidence:

- every meaningful train/eval starts from a Semantic Execution Commit
- every run manifest records the commit hash used for execution
- every claim or claim-boundary delta records Claim Delta Evidence
- every stage transition records a Gate ledger or `NOT_RUN` reason

Human Approval remains required only for Grill exit/automation delegation and
for tools whose purpose is to record explicit approval, such as
`approve_contract.py`. Hooks may warn when a checkpoint seems missing; hooks do
not block ordinary flow just because a checkpoint or claim delta needs ledger
text.
