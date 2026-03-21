---
description: Must git commit (semantic message) before training + training scripts must integrate git_snapshot and wandb
globs:
  - "scripts/train*.py"
  - "scripts/run*.py"
  - "src/**/*.py"
  - "baselines/**/train*.py"
  - "baselines/**/run*.py"
---

# Pre-Training Git & Tracking Rules

## 1. After Claude Modifies Code, Before Running Training

Must execute git add + git commit. Commit message format:

- Research code: `train(research): {semantic description}`
  - Initial: `train(research): init — initial model implementation, backbone+neck+head`
  - Iteration: `train(research): replace MSE loss with SSIM+L1 hybrid loss`
- Baseline: `train(baseline/{name}): {semantic description}`
  - Example: `train(baseline/3dgs): reproduce official config, 30 epochs`

Semantic description must explain **what was done and why**, not just list file names.

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
