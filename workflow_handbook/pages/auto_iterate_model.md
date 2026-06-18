---
schema_version: "0.1"
page_id: "auto_iterate_model"
title: "Auto-Iterate Model"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/auto_iterate_model.md"
source_of_truth: true
status: "current"
summary: "Explains how the WF10 auto-iterate controller fits into the Automation Policy workflow."
nav:
  section: "reference"
  position: 30
canonical_sources:
  - path: "tooling/auto_iterate/docs/cli_control_guide.md"
    role: "tooling"
  - path: ".agents/skills/auto-iterate-goal/SKILL.md"
    role: "skill_source"
references:
  - "stage:WF10"
  - "skill:auto-iterate-goal"
  - "skill:iterate"
  - "term:Human Approval"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/auto_iterate_model.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Auto-Iterate Model

## Purpose

Auto-iterate 减少 WF10 多轮实验的手工摩擦。它在 Grill 记录的
Automation Policy 内自动推进 non-Grill loop，但不替代 explicit approval
tools、外部不可逆 submit，或离开 policy 的 steering 决策。

## Model

```text
$run
  -> internal auto-iterate goal preflight when delegated looping is requested
  -> plan/code/run/eval phases driven by iteration_log.json action_state
  -> pre_train_commit / pre_eval_commit or pre_eval_commit_NOT_CHANGED
  -> docs/context experiments, docs/context memory, and run manifests
  -> iteration_log.json remains experiment source of truth
```

## Boundaries

- `.auto_iterate/**` 是 controller-owned runtime state。
- `docs/auto_iterate_goal.md` 是 operator-facing goal source。
- `docs/context/experiments.md` 记录 next-run questions、falsifiers、
  controls、paper-driven run requests、Research Wiki findings 和 Assurance
  Axis 缺口。
- `docs/context/memory.md` 记录 promoted lessons；candidate lessons 留在
  experiments context，直到分析后被提升。
- Meaningful train/eval 必须记录 `pre_train_commit`、`pre_eval_commit` 或
  `pre_eval_commit_NOT_CHANGED`。
- Claim 或 claim-boundary 变化在 Automation Policy 内用 Claim Delta
  Evidence 和 Gate ledger 记录；离开 policy 时停下来请求 steering。
- Human Approval 只用于 Grill exit/delegation、approval-recording tools、
  policy 外动作和不可逆 external submit。

## Common Confusions

- Controller logs 不是 approval。
- Watchdog status 不是 notification 或 approval；它只是 pollable run health。
- Experiment Queue 和 Research Wiki 现在是 `docs/context/experiments.md`
  里的工作区段，不是 Gate Evidence 或 Approved Contract。
- Auto mode 失败后要从 state 和 logs 恢复，不能补写成功记录。
- WF10 决策词仍然是 NEXT_ROUND、DEBUG、CONTINUE、PIVOT、ABORT。

## Related Pages

- [[stage:WF10]]
- [[skill:auto-iterate-goal]]
- [[skill:iterate]]
- [[term:Human Approval]]
