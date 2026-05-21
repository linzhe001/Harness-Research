---
schema_version: "0.1"
page_id: "layer_iterate_release"
title: "Iterate And Release Layer"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/layer_iterate_release.md"
source_of_truth: true
status: "current"
summary: "How WF10-WF12 run iterations, final experiment, and release."
nav:
  section: "details"
  position: 40
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
references:
  - "stage:WF10"
  - "stage:WF11"
  - "stage:WF12"
  - "skill:iterate"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/layer_iterate_release.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Iterate And Release Layer

## Purpose

WF10-WF12 处理多轮实验、final experiment 和 release claim 边界。

## Model

```text
WF10 iterate -> WF11 final experiment -> WF12 release
```

## Boundaries

- `iteration_log.json` 是 experiment source of truth。
- Final experiment 必须服从 approved contracts 和 Claim Boundary。
- Release claim 不能超出 Human Approval 和 Evidence Chain 支持。

## Common Confusions

- Auto-iterate controller 不替代 Human Approval。
- NEXT_ROUND、DEBUG、CONTINUE、PIVOT、ABORT 是决策词，不是自由文本标签。
- Release readiness 不等于 explicit submit request。

## Related Pages

- [[stage:WF10]]
- [[stage:WF11]]
- [[stage:WF12]]
- [[skill:iterate]]
