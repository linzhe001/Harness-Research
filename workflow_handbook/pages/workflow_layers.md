---
schema_version: "0.1"
page_id: "workflow_layers"
title: "Workflow Layers"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/workflow_layers.md"
source_of_truth: true
status: "current"
summary: "Explains the Intent -> Stage -> Skill -> Gate model."
nav:
  section: "details"
  position: 30
canonical_sources:
  - path: "workflow_handbook/Workflow_Operator_Handbook.md"
    role: "aggregate_source"
  - path: ".agents/references/ubiquitous-language.md"
    role: "framework_rule"
references:
  - "term:Stage"
  - "term:Skill"
  - "term:Skill Contract"
  - "term:Gate Evidence"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/workflow_layers.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Workflow Layers

## Purpose

这页解释 operator 如何把一句自然语言请求落到正确的 Stage、Skill 和 Gate。

## Model

```text
Intent
  -> Stage
  -> Skill
  -> Gate Evidence / Human Approval
```

- Intent 是人的目标，例如“验证这次实现”。
- Stage 是 workflow phase，例如 [[stage:WF9]]。
- Skill 是 agent 行为边界，例如 [[skill:validate-run]]。
- Gate 是继续前必须能报告的检查，例如 [[term:Gate Evidence]]。

## Boundaries

- Stage 决定工作性质，不等于权限自动放开。
- Skill Contract 决定 recommended reads、declared paths 和 required actions。
- Gate ledger 只报告命令和结果，不替代 Human Approval。

## Common Confusions

- Review Packet 是人类决策输入，不是 Approval Evidence。
- HTML view 是阅读视图，不是 source of truth。
- Hook notice 是 guardrail，不是 workflow gate 本身。

## Related Pages

- [[page:stage_cards|Stage Details]]
- [[page:layer_explore|Explore Layer]]
- [[page:layer_contract_plan|Contract And Plan Layer]]
- [[page:layer_build_validate|Build And Validate Layer]]
- [[page:layer_iterate_release|Iterate And Release Layer]]
- [[page:evidence_approval_model|Evidence And Approval Model]]
- [[page:hooks_permissions_model|Hooks And Permissions Model]]
