---
schema_version: "0.1"
page_id: "evidence_approval_model"
title: "Evidence And Approval Model"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/evidence_approval_model.md"
source_of_truth: true
status: "current"
summary: "Separates Conclusion Evidence, Gate Evidence, Evidence Chains, and approvals."
nav:
  section: "reference"
  position: 10
canonical_sources:
  - path: ".agents/references/ubiquitous-language.md"
    role: "framework_rule"
  - path: ".agents/references/evidence-chain-rule.md"
    role: "framework_rule"
references:
  - "term:Conclusion Evidence"
  - "term:Evidence Chain"
  - "term:Gate Evidence"
  - "term:Human Approval"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/evidence_approval_model.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Evidence And Approval Model

## Purpose

这页说明哪些 artifact 支持 claim，哪些 artifact 只证明 gate 被执行，以及什么时候必须人类批准。

## Model

```text
Conclusion Evidence -> Evidence Chain -> Review Packet -> Human Approval
Gate Evidence       -> Gate ledger
```

## Boundaries

- Conclusion Evidence 支持事实、claim、idea 或 protocol choice。
- Gate Evidence 证明检查执行和结果。
- Approval Evidence 只能来自明确的人类批准或可审计 approval artifact。

## Common Confusions

- Review Packet 不是 Human Approval。
- Gate ledger 不是 Evidence Chain。
- Hover preview 不是 source artifact。

## Related Pages

- [[page:workflow_terms|Workflow Terms]]
- [[term:Conclusion Evidence]]
- [[term:Evidence Chain]]
- [[term:Gate Evidence]]
- [[term:Human Approval]]

