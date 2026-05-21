---
schema_version: "0.1"
page_id: "layer_contract_plan"
title: "Contract And Plan Layer"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/layer_contract_plan.md"
source_of_truth: true
status: "current"
summary: "How WF5-WF7 establish baseline, boundaries, architecture, and slices."
nav:
  section: "details"
  position: 20
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
references:
  - "stage:WF5"
  - "stage:WF6"
  - "stage:WF7"
  - "term:Human Approval"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/layer_contract_plan.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Contract And Plan Layer

## Purpose

WF5-WF7 建立 baseline、human-approved boundaries、architecture 和 implementation slices。

## Model

```text
WF5 baseline / contracts -> WF6 architecture -> WF7 implementation roadmap
```

## Boundaries

- Contracts 只有在 Human Approval 后才是 approved。
- WF6 不能越过 approved evaluation 或 claim boundary。
- WF7 负责切片计划，不应重新做架构决策。

## Common Confusions

- Review Packet 不是 approval。
- Technical Spec 不是 implementation commit。
- Roadmap 不是代码实现。

## Related Pages

- [[stage:WF5]]
- [[stage:WF6]]
- [[stage:WF7]]
- [[term:Human Approval]]
