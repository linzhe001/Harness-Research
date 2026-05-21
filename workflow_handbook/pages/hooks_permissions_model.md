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
summary: "Explains why Harness hooks block missing reads, out-of-scope writes, and missing ledgers."
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
  - "term:Write Scope"
  - "term:Gate Ledger"
  - "source:tooling/evidence/build_docs_site.py"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/hooks_permissions_model.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Hooks And Permissions Model

## Purpose

这页解释 hook 为什么会阻止某些写入，以及 operator 应该如何修复。

## Model

```text
UserPromptSubmit -> active Skill
PreToolUse       -> read/write boundary check
PostToolUse      -> pending Gate ledger marker
Stop             -> missing reads or missing Gate ledger check
```

## Boundaries

- 没有 active Skill 时，guardrail-sensitive paths fail closed。
- active Skill 只能写自己的 `write_scope.allowed_paths`。
- `.evidence/**`, `.auto_iterate/**`, `docs/_views/**`, `docs/_site/**` 是 tool-owned 或 controller-owned。

## Common Confusions

- Hook block 不是惩罚；它通常是在提醒缺少 Read Contract 或写入越界。
- Renderer 可以生成 `docs/_site/**`，但不要手写生成 HTML。
- 读过文件不代表 gate 已通过。

## Related Pages

- [[page:workflow_terms|Workflow Terms]]
- [[term:Read Contract]]
- [[term:Write Scope]]
- [[term:Gate Ledger]]

