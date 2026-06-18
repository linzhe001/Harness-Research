# Pre-Train / Pre-Eval Tracking Rule

## Type

- `always_on` for training-related and meaningful evaluation-related code changes
- `skill_scoped` for `$baseline-repro` and `$code-debug`

## Purpose

Ensure every meaningful training or evaluation run is traceable to semantic git
commits and that tracking metadata is carried into logs, checkpoints, metrics,
claim-support records, and the run artifact bundle.

## Scope

Apply this rule when preparing to run training from:

- `scripts/train*.py`
- `scripts/run*.py`
- `src/**/*.py` when the changes affect training behavior
- `baselines/**/train*.py`
- `baselines/**/run*.py`
- `runs/wf10/<iter>/**` when it contains run-local code or configs
- `scripts/eval*.py`
- evaluation helpers, metric scripts, and release-validation scripts when their
  outputs will support claims

## Trigger

Apply this rule after training-related code changes and before launching a real
training run. Apply the same rule after meaningful eval/claim-support changes
and before launching a real evaluation, WF11 matrix run, or release validation.

This rule is about run traceability, not about every trivial text edit.

## Required Actions

1. Before training, create a semantic git commit for the training-related code
   changes and record it as `pre_train_commit`.
2. Before evaluation, create a semantic git commit for evaluation-related code,
   config, run-local helpers, and claim-support changes, or record
   `pre_eval_commit_NOT_CHANGED` when the pre-train commit already covers them.
3. Use commit messages that explain both:
   - what changed
   - why it changed
4. Follow the canonical commit prefixes:
   - research code: `train(research): {what changed and why}`
   - baseline code: `train(baseline/{name}): {what changed and why}`
   - evaluation code: `eval(research): {what changed and why}`
   - claim-support docs or release validation: `claim(evidence): {what changed and why}`
5. Ensure training/evaluation entry scripts carry git and tracking metadata:
   - call `src.utils.git_snapshot.git_snapshot(...)` at startup when that utility is part of the project design
   - initialize tracking such as wandb with commit-aware metadata when enabled
   - include git identifiers in checkpoints when the training pipeline saves checkpoints
6. Write or register the run artifact bundle defined in
   `.agents/references/run-artifact-contract.md`.
7. Keep experiment bookkeeping consistent with the active workflow records.

## Recommended Patterns

### Commit Messages

- `train(research): initialize ASM-integrated dehaze model for MVP smoke restoration`
- `train(research): replace pure MSE with SSIM plus L1 to improve texture fidelity`
- `train(baseline/3dgs): reproduce official config under project dataset layout`
- `eval(research): add seed-sweep aggregation before robustness evaluation`
- `claim(evidence): record ablation-supported boundary for draft paper claim`

### Training Startup Metadata

Typical startup metadata should include:

- training type
- commit hash
- pre-train and pre-eval commit hashes
- commit message
- branch
- run name
- config snapshot
- run output directory

### Checkpoint Metadata

Typical checkpoints should include:

- model state
- optimizer state
- step or epoch
- `git_commit`
- `git_message`

### Run Artifact Bundle

Typical run output should include:

- resolved config snapshot
- console log
- git snapshot under the run directory
- eval metric artifacts when metrics are reported
- checkpoint path when checkpointing is expected

## Forbidden Actions

- Do not launch a meaningful training run from uncommitted training-code changes when this rule applies.
- Do not launch a meaningful evaluation from uncommitted eval/config/run-local
  changes when this rule applies.
- Do not use non-semantic commit messages that only list filenames or vague placeholders.
- Do not drop git metadata from the training trace when the pipeline is expected to support it.
- Do not treat dirty smoke/debug runs as strong Conclusion Evidence unless the
  preserved patch and limitation are reported and a clean committed rerun is not
  required by the active gate.

## Verification

This rule is satisfied when:

- semantic commits or explicit `NOT_CHANGED` records exist before the run/eval
- the training/evaluation pipeline can point back to the commits used for the run
- tracking metadata and checkpoints include the expected git information when supported by the project
- `iteration_log.json` or the relevant report points to the run artifact bundle
  with the same commit identity

## Escalation

- If there is no semantic commit, the training run should be treated as not ready.
- If the code path cannot capture git metadata yet, that gap should be surfaced explicitly rather than ignored.
