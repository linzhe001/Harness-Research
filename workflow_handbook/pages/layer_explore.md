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
$grill
  -> draft-only intent and readiness candidates
  -> init-project update-from-grill after operator confirms grill_draft_ready
  -> WF1/WF2/WF3 stage skills only when canonical stage work is needed
  -> $prepare / WF4 data only after executable sources and policies are clear
```

`research-supervision-patterns.md`, `phd-research-primer.md`, and
`idea-evaluation.md` are the main absorbed assets here. They add problem type,
dominant improvement axis, fatal-flaw, capability-fit, falsifier, and reviewer
risk checks to Grill and new-direction triage.

## Boundaries

- 这里可以收集 Conclusion Evidence，但不能提前声明 approved contracts。
- Protocol Draft 可以出现，但它不是 Approved Contract。
- Data facts 必须来自 artifacts、logs、configs 或明确记录。
- Supervision assets can pressure-test an idea, but they are not project facts
  and do not prove dataset, baseline, metric, or access availability.

## Common Confusions

- Survey 不是替研究者发明 idea。
- Debate 不是 approval。
- Data-prep 的输出是事实面，不是 final metric claim。
- `grill_draft_ready` 不是 WF1-WF3 complete；它只说明 draft context 可以进入
  owning stage or supervisor path。

## Related Pages

- [[stage:WF0]]
- [[stage:WF1]]
- [[stage:WF2]]
- [[stage:WF3]]
- [[stage:WF4]]
- [[page:research_supervision_assets|Research Supervision Assets]]
