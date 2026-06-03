---
schema_version: "0.1"
page_id: "hooks_permissions_model"
title: "Hooks And Permissions Model"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/hooks_permissions_model.md"
source_of_truth: true
status: "current"
summary: "Explains how Harness hooks provide route hints, notices, and narrow boundary blocks."
nav:
  section: "reference"
  position: 20
canonical_sources:
  - path: "tooling/codex_hooks/README.md"
    role: "hook_source"
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
references:
  - "term:Read Contract"
  - "term:Gate Ledger"
  - "source:tooling/evidence/build_docs_site.py"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/hooks_permissions_model.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Hooks And Permissions Model

## Purpose

这页解释 hook 如何在不重型阻断流程的前提下提供 route hint、上下文提醒和少量硬边界。

## Model

```text
UserPromptSubmit -> route hint and workspace capsule
PreToolUse       -> one-time notices plus narrow boundary checks
PostToolUse      -> read/write/pending metadata
Stop             -> pending cleanup; no default read/Gate block
```

## Boundaries

- Missing recommended reads produce a notice rather than a block.
- Mixed-owner writes or commits produce a notice rather than a block.
- `.evidence/**`, `.auto_iterate/**`, `docs/_views/**`, `docs/_site/**` 是 tool-owned 或 controller-owned。
- Direct external model review must go through the Harness wrapper.

## Common Confusions

- Hook notice 是上下文提示；不是 approval，也不是 Gate Evidence。
- Hook block 只用于具体的 controlled-state 边界。
- Renderer 可以生成 `docs/_site/**`，但不要手写生成 HTML。
- 读过文件不代表 gate 已通过。

## Related Pages

- [[page:workflow_terms|Workflow Terms]]
- [[term:Read Contract]]
- [[term:Gate Ledger]]
