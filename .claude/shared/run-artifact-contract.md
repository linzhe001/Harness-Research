# Run Artifact Contract

## Purpose

Every meaningful training or evaluation run must be recoverable from current
Source Artifacts, not from memory or chat prose. The run directory is Execution
Evidence; `iteration_log.json` is the index that points to it.

## Scope

Apply this contract to:

- WF5 baseline reproduction runs
- WF9 smoke runs when they are used as WF10 readiness Gate Evidence
- WF10 screening and full runs
- WF11 final experiment runs

Ad-hoc debug commands may use a lighter record, but their results must not be
used as strong Conclusion Evidence until rerun from a semantic commit with a
complete artifact bundle.

## Pre-Train And Pre-Eval Commit Rule

Before any meaningful training run:

1. Commit training-related code, stable entry scripts, run-local code under
   `runs/wf10/<iter>/`, run-local configs, eval logic needed by the command,
   and durable configs with a semantic commit message.
2. Record that hash as `pre_train_commit` and use it as the training run
   identity.
3. Treat dirty-worktree runs as debug or smoke only unless the dirty patch is
   explicitly preserved and the limitation is reported.

Before any meaningful standalone evaluation, final matrix evaluation, or
release validation:

1. If eval logic, eval configs, metric scripts, run-local eval helpers, claim
   support docs, or release-validation code changed since the training commit,
   create a new semantic commit and record it as `pre_eval_commit`.
2. If nothing relevant changed, set `pre_eval_commit` to the same hash as
   `pre_train_commit` or record `pre_eval_commit_NOT_CHANGED`.
3. Never use an eval result as Conclusion Evidence without a committed source
   identity for the eval code/config that produced it.

The run output directory itself is normally a generated artifact and should not
be committed before the run.

## Required Run Bundle

Each completed run must create one unique `exp_dir` containing or pointing to:

| Artifact | Preferred path | Required when |
| --- | --- | --- |
| resolved config snapshot | `run_param.yaml` or `resolved_config.yaml` | always |
| console log | `stdout+stderr.log` | always |
| git snapshot | `git_status/commit.txt` or `git_status/git.json` | always |
| dirty patch | `git_status/dirty.patch` | dirty debug/smoke runs |
| eval metrics | `epochs/*/eval.jsonl`, `eval.json`, or protocol-specific metric file | metrics are reported |
| checkpoint | `checkpoints/**` or project-specific checkpoint path | model training produced a checkpoint |
| tracking logs | TensorBoard/W&B path or URL | tracking enabled |

For a committed run, `git_status/commit.txt` or `git_status/git.json` must
match the iteration `git_commit` recorded in `iteration_log.json`.

## Run Manifest Fields

For completed metric-bearing runs, the relevant run manifest must record:

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
- `checkpoint_path`
- `eval_artifact_paths`
- `run_local_code_manifest_path` when run-local code exists
- `claim_delta_evidence_paths` when claims or claim boundaries changed
- `wandb_url` or `tensorboard_log_dir` when enabled
- `started_at`, `duration_seconds`, `exit_code`, and `error`

Paths should be relative to the workspace root when possible. Missing optional
artifacts must be explained in the run report or Gate ledger.

For WF10 iterations with both screening and full runs:

- store the screening bundle in `screening.run_manifest`
- mirror the screening bundle in top-level `run_manifest` until a full run
  replaces it
- store the full run bundle in top-level `run_manifest`
- never overwrite `screening.run_manifest` with the full run bundle

## Gate Semantics

- `/iterate run` may register manual or cluster runs before artifacts exist, but
  `/iterate eval` must not mark an iteration `completed` until the artifact
  bundle exists. If pieces are missing, report `NOT_RUN` and keep the iteration
  incomplete.
- `/iterate run` and `/iterate eval` must record the pre-train/pre-eval commit
  hashes or explicit `NOT_CHANGED` / `NOT_RUN` explanations in the run
  manifest or Gate ledger.
- `check_workflow_state.py` should reject completed iterations that have no
  `exp_dir`, resolved config snapshot, console log, or git snapshot.
- Smoke/debug runs with preserved dirty patches may support debugging
  decisions, but final claims and release claims require clean committed runs
  unless the limitation is recorded as Claim Delta Evidence and accepted by the
  active Automation Policy.
