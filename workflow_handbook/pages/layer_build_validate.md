---
schema_version: "0.1"
page_id: "layer_build_validate"
title: "Build And Validate Layer"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/layer_build_validate.md"
source_of_truth: true
status: "current"
summary: "How WF8-WF9 implement and validate bounded code slices."
nav:
  section: "details"
  position: 30
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
references:
  - "stage:WF8"
  - "stage:WF9"
  - "skill:code-debug"
  - "skill:validate-run"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/layer_build_validate.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Build And Validate Layer

## Purpose

WF8-WF9 把 plan 中的一个 bounded slice 实现出来，并用 Gate Evidence 验证。

## Model

```text
WF8 code -> focused checks -> WF9 validate -> PASS | REVIEW | FAIL
```

## Boundaries

- 代码实现必须服从 roadmap、contracts、project map 和 codebase map。
- Validation 只能报告 PASS、REVIEW、FAIL 或 NOT_RUN。
- Generated HTML 可以刷新，但不能替代 source Markdown 或 tests。

## Common Confusions

- `$code-debug` 不负责改 hooks 或 skill contracts。
- 通过语法检查不等于 semantic validation。
- Validation report 不自动推进 WF10。

## Related Pages

- [[stage:WF8]]
- [[stage:WF9]]
- [[skill:code-debug]]
- [[skill:validate-run]]
