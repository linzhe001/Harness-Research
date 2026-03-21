---
description: 训练前必须 git commit（语义化 message）+ 训练脚本必须集成 git_snapshot 和 wandb
globs:
  - "scripts/train*.py"
  - "scripts/run*.py"
  - "src/**/*.py"
  - "baselines/**/train*.py"
  - "baselines/**/run*.py"
---

# 训练前 Git 与 Tracking 规则

## 1. Claude 修改代码后、运行训练前

必须执行 git add + git commit，commit message 格式：

- 研究代码: `train(research): {语义描述}`
  - 初次: `train(research): init — 初始模型实现，backbone+neck+head`
  - 迭代: `train(research): 将 MSE loss 替换为 SSIM+L1 混合 loss`
- Baseline: `train(baseline/{name}): {语义描述}`
  - 例: `train(baseline/3dgs): 复现官方配置，30 epochs`

语义描述必须说明**做了什么、为什么做**，而非只列出文件名。

## 2. 训练脚本必须集成

所有训练脚本（研究代码和 baseline）必须在 main() 开头调用：

```python
from src.utils.git_snapshot import git_snapshot

snapshot = git_snapshot(training_type="research")  # or "baseline/{name}"
```

git_snapshot 职责：
- 检查并提交遗漏的未暂存更改（安全网，commit 前先跑 `ruff check --select=E,F`）
- `git pull --rebase` 后再 push（避免 merge conflict）
- 返回 commit_hash、branch、commit_message 等信息
- wandb 已自动记录 git commit + uncommitted diff，git_snapshot 的信息是补充

## 3. wandb 集成要求

```python
wandb.init(
    project=cfg.project_name,
    name=cfg.exp_name,
    config=asdict(cfg),
    tags=["initial" if snapshot["is_initial"] else "iteration", snapshot["training_type"]],
    notes=snapshot["commit_message"],
)
wandb.config.update({"git": snapshot})
# 注: wandb.init 会自动记录 git commit hash 和 uncommitted diff
# snapshot 信息是补充，提供 is_initial、training_type 等额外字段
```

## 4. Checkpoint 必须包含 git 信息

```python
torch.save({
    "model": model.state_dict(),
    "optimizer": optimizer.state_dict(),
    "epoch": epoch,
    "git_commit": snapshot["commit_hash"],
    "git_message": snapshot["commit_message"],
}, path)
```
