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
summary: "Explains how the WF10 auto-iterate controller fits into the workflow."
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

Auto-iterate 减少 WF10 多轮实验的手工摩擦，但不替代 operator 的 claim、contract 或 release 决策。

## Model

```text
$auto-iterate-goal
  -> controller preflight
  -> plan/code/run/eval phases
  -> iteration_log.json remains experiment source of truth
```

## Boundaries

- `.auto_iterate/**` 是 controller-owned runtime state。
- `docs/auto_iterate_goal.md` 是 operator-facing goal source。
- Human Approval 仍然控制 contracts、Claim Boundary、release readiness 和高风险转向。

## Common Confusions

- Controller logs 不是 approval。
- Auto mode 失败后要从 state 和 logs 恢复，不能补写成功记录。
- WF10 决策词仍然是 NEXT_ROUND、DEBUG、CONTINUE、PIVOT、ABORT。

## Related Pages

- [[stage:WF10]]
- [[skill:auto-iterate-goal]]
- [[skill:iterate]]
- [[term:Human Approval]]

