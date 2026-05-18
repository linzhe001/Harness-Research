# Sliced Commit Rule

## Purpose

Commit one completed functional slice at a time so project history stays
reviewable, reversible, and traceable.

A `Commit Slice` is the smallest coherent set of files that delivers one
reviewable behavior, workflow rule, bug fix, roadmap slice, or validation
artifact. It should have its own validation result or an explicit `NOT_RUN`
reason.

## Required Behavior

Before committing:

1. Inspect `git status --short`, `git diff --name-only`, and, when staged files
   exist, `git diff --cached --name-only`.
2. Identify independent slices by roadmap `slice_id`, active Stage, subsystem,
   one bug fix, one behavior change, one docs update, or one guardrail change.
3. Stage only the files or hunks for the current slice.
4. Validate that slice before committing, or record why validation is `NOT_RUN`.
5. Commit exactly one completed slice with a semantic message that explains
   what changed and why.
6. Repeat for the next completed slice.

Training-related commits still follow the prefixes from the pre-training rule:

```text
train(research): {what changed and why}
train(baseline/{name}): {what changed and why}
```

Do not bundle unrelated changes, do not stage unrelated user edits, and do not
mix framework guardrail edits with ordinary research implementation changes.
