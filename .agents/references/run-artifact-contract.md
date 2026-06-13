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

## Pre-Run Commit Rule

Before any meaningful run:

1. Commit training-related code, stable entry scripts, eval logic, and durable
   configs with a semantic commit message.
2. Use that commit as the run identity.
3. Treat dirty-worktree runs as debug or smoke only unless the dirty patch is
   explicitly preserved and the limitation is reported.

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
- `checkpoint_path`
- `eval_artifact_paths`
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

- `$iterate run` may register manual or cluster runs before artifacts exist, but
  `$iterate eval` must not mark an iteration `completed` until the artifact
  bundle exists. If pieces are missing, report `NOT_RUN` and keep the iteration
  incomplete.
- `check_workflow_state.py` should reject completed iterations that have no
  `exp_dir`, resolved config snapshot, console log, or git snapshot.
- Smoke/debug runs with preserved dirty patches may support debugging
  decisions, but final claims and release claims require clean committed runs
  unless a human-approved exception is recorded.
