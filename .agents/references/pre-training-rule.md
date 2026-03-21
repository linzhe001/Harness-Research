# Pre-Training Tracking Rule

## Type

- `always_on` for training-related code changes
- `skill_scoped` for `$baseline-repro` and `$code-debug`

## Purpose

Ensure every meaningful training run is traceable to a semantic git commit and that tracking metadata is carried into logs and checkpoints.

## Scope

Apply this rule when preparing to run training from:

- `scripts/train*.py`
- `scripts/run*.py`
- `src/**/*.py` when the changes affect training behavior
- `baselines/**/train*.py`
- `baselines/**/run*.py`

## Trigger

Apply this rule after training-related code changes and before launching a real training run.

This rule is about run traceability, not about every trivial text edit.

## Required Actions

1. Before training, create a semantic git commit for the training-related code changes.
2. Use commit messages that explain both:
   - what changed
   - why it changed
3. Follow the canonical commit prefixes:
   - research code: `train(research): {what changed and why}`
   - baseline code: `train(baseline/{name}): {what changed and why}`
4. Ensure training entry scripts carry git and tracking metadata:
   - call `src.utils.git_snapshot.git_snapshot(...)` at startup when that utility is part of the project design
   - initialize tracking such as wandb with commit-aware metadata when enabled
   - include git identifiers in checkpoints when the training pipeline saves checkpoints
5. Keep experiment bookkeeping consistent with the active workflow records.

## Recommended Patterns

### Commit Messages

- `train(research): initialize ASM-integrated dehaze model for MVP smoke restoration`
- `train(research): replace pure MSE with SSIM plus L1 to improve texture fidelity`
- `train(baseline/3dgs): reproduce official config under project dataset layout`

### Training Startup Metadata

Typical startup metadata should include:

- training type
- commit hash
- commit message
- branch
- run name
- config snapshot

### Checkpoint Metadata

Typical checkpoints should include:

- model state
- optimizer state
- step or epoch
- `git_commit`
- `git_message`

## Forbidden Actions

- Do not launch a meaningful training run from uncommitted training-code changes when this rule applies.
- Do not use non-semantic commit messages that only list filenames or vague placeholders.
- Do not drop git metadata from the training trace when the pipeline is expected to support it.

## Verification

This rule is satisfied when:

- a semantic commit exists before the run
- the training pipeline can point back to the commit used for the run
- tracking metadata and checkpoints include the expected git information when supported by the project

## Escalation

- If there is no semantic commit, the training run should be treated as not ready.
- If the code path cannot capture git metadata yet, that gap should be surfaced explicitly rather than ignored.
