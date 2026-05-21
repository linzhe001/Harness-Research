---
schema_version: "0.1"
page_id: "layer_explore"
title: "Explore Layer"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/layer_explore.md"
source_of_truth: true
status: "current"
summary: "How WF0-WF4 move from idea to data facts."
nav:
  section: "details"
  position: 10
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
references:
  - "stage:WF0"
  - "stage:WF1"
  - "stage:WF2"
  - "stage:WF3"
  - "stage:WF4"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/layer_explore.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Explore Layer

## Purpose

WF0-WF4 把初始 idea 变成可执行的 research target 和数据事实。

## Model

```text
WF0 init -> WF1 survey -> WF2 debate -> WF3 refine -> WF4 data
```

## Boundaries

- 这里可以收集 Conclusion Evidence，但不能提前声明 approved contracts。
- Protocol Draft 可以出现，但它不是 Approved Contract。
- Data facts 必须来自 artifacts、logs、configs 或明确记录。

## Common Confusions

- Survey 不是替研究者发明 idea。
- Debate 不是 approval。
- Data-prep 的输出是事实面，不是 final metric claim。

## Related Pages

- [[stage:WF0]]
- [[stage:WF1]]
- [[stage:WF2]]
- [[stage:WF3]]
- [[stage:WF4]]
