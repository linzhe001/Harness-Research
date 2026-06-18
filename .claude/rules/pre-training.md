---
description: Must git commit before meaningful training/evaluation + record git identity in run artifacts
globs:
  - "scripts/train*.py"
  - "scripts/run*.py"
  - "scripts/eval*.py"
  - "src/**/*.py"
  - "baselines/**/train*.py"
  - "baselines/**/run*.py"
  - "runs/wf10/**"
---

# Pre-Train / Pre-Eval Git & Tracking Rules

## 1. After Claude Modifies Code, Before Running Training Or Evaluation

Must execute git add + git commit for the relevant Commit Slice. Meaningful
training records this hash as `pre_train_commit`; meaningful evaluation records
`pre_eval_commit` or `pre_eval_commit_NOT_CHANGED` when the training commit
already covers the eval logic/configs. Commit message format:

- Research code: `train(research): {semantic description}`
  - Initial: `train(research): init — initial model implementation, backbone+neck+head`
  - Iteration: `train(research): replace MSE loss with SSIM+L1 hybrid loss`
- Baseline: `train(baseline/{name}): {semantic description}`
  - Example: `train(baseline/3dgs): reproduce official config, 30 epochs`
- Evaluation: `eval(research): {semantic description}`
- Claim support: `claim(evidence): {semantic description}`

Semantic description must explain **what was done and why**, not just list file names.

Run-local scripts and configs under `runs/wf10/<iter>/` are Source Artifacts
for the upcoming execution and must be committed before meaningful train/eval,
even when they will never merge back into stable code.

The run output directory itself is generated Execution Evidence and is normally
not committed before the run.

## 2. Training Scripts Must Integrate

All training scripts (research code and baselines) must call at the beginning of main():

```python
from src.utils.git_snapshot import git_snapshot

snapshot = git_snapshot(training_type="research")  # or "baseline/{name}"
```

git_snapshot responsibilities:
- Check and commit any missed unstaged changes (safety net, runs `ruff check --select=E,F` before commit)
- `git pull --rebase` then push (avoid merge conflicts)
- Return commit_hash, branch, commit_message, etc.
- wandb already auto-records git commit + uncommitted diff; git_snapshot info is supplementary
- The run directory must record the same commit identity in its run artifact
  bundle; see `../shared/run-artifact-contract.md`.
Evaluation entrypoints should record the same pre-train/pre-eval commit
identity when metrics will support conclusions or claims.

## 3. wandb Integration Requirements

```python
wandb.init(
    project=cfg.project_name,
    name=cfg.exp_name,
    config=asdict(cfg),
    tags=["initial" if snapshot["is_initial"] else "iteration", snapshot["training_type"]],
    notes=snapshot["commit_message"],
)
wandb.config.update({"git": snapshot})
# Note: wandb.init automatically records git commit hash and uncommitted diff
# snapshot info is supplementary, providing is_initial, training_type, and other extra fields
```

## 4. Checkpoints Must Include Git Info

```python
torch.save({
    "model": model.state_dict(),
    "optimizer": optimizer.state_dict(),
    "epoch": epoch,
    "git_commit": snapshot["commit_hash"],
    "git_message": snapshot["commit_message"],
}, path)
```

## 5. Run Artifact Bundle

Meaningful runs must produce or register the run artifact bundle from
`../shared/run-artifact-contract.md`: resolved config snapshot, console log,
git snapshot, eval metric artifacts when metrics are reported, and checkpoint
path when checkpointing is expected. Dirty smoke/debug runs may preserve a patch,
but they are not strong Conclusion Evidence until rerun from a semantic commit.
