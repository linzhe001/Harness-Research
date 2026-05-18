# Sliced Commit Rule

## Type

- `always_on` when an agent is preparing a `git commit`
- `skill_scoped` for `$build-plan`, `$code-expert`, and `$code-debug`

## Purpose

Keep implementation history reviewable, reversible, and traceable by committing
one completed functional slice at a time instead of bundling unrelated changes.

A `Commit Slice` is the smallest coherent set of files that delivers one
reviewable behavior, workflow rule, bug fix, roadmap slice, or validation
artifact. It should have its own validation result or an explicit `NOT_RUN`
reason.

## Scope

Apply this rule before any agent-created commit, including:

- WF8 code generation after WF7 planning
- `$iterate code` and `$code-debug` changes
- ordinary daily bug fixes or documentation/tooling updates
- Harness framework maintenance commits

This rule complements `pre-training-rule.md`: training-related changes still
need the canonical `train(...)` commit prefixes and must be committed before
meaningful training runs.

## Required Behavior

Before committing:

1. Inspect the worktree and staged changes:
   - `git status --short`
   - `git diff --name-only`
   - `git diff --cached --name-only` when anything is staged
2. Identify independent commit slices by one or more of:
   - roadmap `slice_id`
   - active skill or workflow Stage
   - subsystem or stable interface boundary
   - one bug fix, one behavior change, one docs update, or one guardrail change
   - validation command that proves that slice
3. Commit exactly one completed slice at a time.
4. Stage only the files or hunks that belong to the current slice.
5. Validate the slice before committing, or record why validation is `NOT_RUN`.
6. Use a semantic commit message that explains both what changed and why.
7. Repeat for the next completed slice.

## Commit Message Guidance

Use the project or workflow convention already active. The message should name
the slice when practical:

```text
feat(slice/<slice_id>): add dataset loader smoke path for WF8 bootstrap
fix(slice/<slice_id>): align metric parser with Evaluation Contract
docs(workflow): add sliced commit rule for daily git commits
train(research): implement slice s2 loss wiring for smoke restoration
```

Training-related commits keep the `pre-training-rule.md` prefixes:

```text
train(research): {what changed and why}
train(baseline/{name}): {what changed and why}
```

## Forbidden Actions

- Do not create one broad "all changes" commit when independent slices can be
  separated.
- Do not stage unrelated user changes unless the user explicitly asks for them.
- Do not mix framework guardrail edits with research implementation edits.
- Do not mix code behavior changes with unrelated formatting churn.
- Do not continue to training from uncommitted training-related changes.

## Cross-Cutting Changes

Some changes are intentionally atomic across files. A cross-cutting commit is
acceptable only when splitting it would leave the repository in a broken or
misleading state. Record the reason in the handoff summary.

Examples:

- one interface signature change plus all direct callers
- one schema update plus the validator and focused tests
- one hook policy update plus its contract and regression test

## Verification

A sliced commit is ready when:

- the staged file set matches one slice
- the slice has a validation command, smoke command, or documented `NOT_RUN`
  reason
- stable interface changes are reflected in `project_map.json`
- the commit message states what changed and why
