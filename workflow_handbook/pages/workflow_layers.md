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
summary: "Explains the visible-alias-first operating model and where internal Stage references fit."
nav:
  section: "detailed_reference"
  position: 40
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

这页解释 operator 如何把一句自然语言请求落到正确的可见入口和 Gate。
WF0-WF12 nodes 和 Skill 是内部执行参考，不是第一层用户界面。

## Model

```text
Intent
  -> visible alias: grill | prepare | build | run | analyze | write | change
  -> Runtime / Skill worker / Evidence tooling
  -> Internal process assets when relevant
  -> Gate Evidence / Pending Request / Human Approval
  -> Next safe action
```

- Intent 是人的目标，例如“验证这次实现”。
- Visible aliases 只有 `$grill`, `$prepare`, `$build`, `$run`, `$analyze`,
  `$write`, `$change`。它们路由到内部 runtime 或 Skill Contract source，
  不创建新的 stage ownership。
- Internal skills such as `workflow-supervisor`, `iterate`, `evaluate`,
  `auto-paper`, and `change-intake` are detailed references and hook route
  targets, not autocomplete entries.
- Runtime / worker / tooling 是执行层，例如 supervisor、auto-iterate、
  evidence tooling 或某个 Skill worker。
- Internal process assets 是被吸收到 Harness 的 `research-supervision`
  参考层。它们塑造 Grill pressure tests、experiment canvas、paper/figure
  layout 和 harden checklist，但不是 Conclusion Evidence。
- Gate 是继续前必须能报告的检查，例如 [[term:Gate Evidence]]、Pending
  Request 或 [[term:Human Approval]]。
- Stage / Skill 是 detailed reference。只有在需要定位 artifact、contract、
  postcondition 或失败恢复时才展开。

## Boundaries

- 可见入口只决定运行语义，不替代 Stage artifact、Gate Evidence 或
  Human Approval。
- Stage 决定内部 artifact map，不等于用户必须先选择 Stage。
- Skill Contract 决定 recommended reads、declared paths 和 required actions。
- Gate ledger 只报告命令和结果，不替代 Human Approval。
- `research-supervision` assets 不授权下载、clone、claim、approval 或 stage
  transition；如果它们影响当前项目 claim，仍需要 Source Artifacts 和
  Conclusion Evidence。

## Common Confusions

- Review Packet 是人类决策输入，不是 Approval Evidence。
- HTML view 是阅读视图，不是 source of truth。
- Hook notice 是 guardrail，不是 workflow gate 本身。
- `coverage-matrix.md` 没有 runtime skill route 是有意设计；它只帮助
  maintainer 审计资产是否被匿名化吸收。

## Related Pages

- [[page:workflow_supervisor_model|Runtime Routing Model]]
- [[page:stage_cards|Stage Reference]]
- [[page:research_supervision_assets|Research Supervision Assets]]
- [[page:layer_explore|Explore Layer]]
- [[page:layer_contract_plan|Contract And Plan Layer]]
- [[page:layer_build_validate|Build And Validate Layer]]
- [[page:layer_iterate_release|Iterate And Release Layer]]
- [[page:evidence_approval_model|Evidence And Approval Model]]
- [[page:hooks_permissions_model|Hooks And Permissions Model]]
