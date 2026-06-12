---
schema_version: "0.1"
page_id: "codebase"
title: "Codebase"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/codebase.md"
source_of_truth: true
status: "current"
summary: "Where the framework code, workflow guidance, runtime state, and generated views live."
nav:
  section: "details"
  position: 35
canonical_sources:
  - path: "AGENTS.md"
    role: "framework_rule"
  - path: "CLAUDE.md"
    role: "framework_rule"
  - path: "tooling/codex_hooks/README.md"
    role: "hook_source"
references: []
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/codebase.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Codebase

## Purpose

这个页面是顶层 `Codebase` 入口。它只解释当前 framework checkout
里哪些区域承载 source of truth、哪些区域是 runtime state、哪些区域只是
generated view。

## Model

| Path | 作用 | 编辑方式 |
| --- | --- | --- |
| `.agents/` | Codex-facing skills、references、agent metadata | 修改 workflow 行为时同步考虑 `.claude/` |
| `.claude/` | Claude Code-facing skills、shared rules、templates | 和 `.agents/` 保持语义一致 |
| `tooling/evidence/` | docchain、protocol、review-packet、docs-site renderer | 改代码后跑 focused tests |
| `tooling/codex_hooks/` | Harness hook runtime、installer、policy checks | hook/contract 改动要跑 contract checks |
| `tooling/workflow_supervisor/` | prepare/build/change/release runtime controller | runtime state 由 controller 写 |
| `tooling/auto_iterate/` | WF10 auto-iterate controller | 不手写 `.auto_iterate/**` |
| `schemas/` | Skill Contracts、handbook、generated view schemas | schema 改动必须配测试 |
| `workflow_handbook/` | handbook Markdown source | source of truth |
| `docs/_views/**` | generated JSON indexes | 用 owning tool 生成 |
| `docs/_site/**` | generated HTML site | 用 docs-site renderer 生成 |

## Boundaries

- `workflow_handbook/**` 是本 handbook 的 Markdown source。
- `docs/_views/**` 和 `docs/_site/**` 是 generated view，不是 source of truth。
- `.evidence/**`、`.auto_iterate/**`、`.workflow_supervisor/**` 是 tool-owned
  runtime state；排查时可以读，不能手写修状态。
- Root state files such as `PROJECT_STATE.json`, `iteration_log.json`,
  `project_map.json`, `MEMORY.md`, and `OPERATOR_CONTEXT.md` normally belong
  to target research workspaces, not this framework repo.

## Common Confusions

- `docs/_site/**` 里能看到 HTML，不代表应该手改 HTML。
- hook notices 是 guardrail，不是 Gate Evidence。
- framework repo 里的 ignored runtime names 不等于当前研究项目状态。
- codebase map、contracts、Gate ledger 必须来自当前 workspace artifacts，不能从记忆补齐。

## Related Pages

- [[page:workflow_layers|Detailed Workflow Map]]
- [[page:markdown_to_html_preview_chain|HTML Preview Chain]]
- [[page:hooks_permissions_model|Hooks And Permissions]]
