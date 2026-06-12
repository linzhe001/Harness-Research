---
schema_version: "0.1"
page_id: "cli"
title: "CLI"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/cli.md"
source_of_truth: true
status: "current"
summary: "Top-level command and runtime entry surface for Harness workflow operations."
nav:
  section: "topbar"
  position: 20
canonical_sources:
  - path: "workflow_handbook/pages/workflow_supervisor_model.md"
    role: "aggregate_source"
  - path: "tooling/workflow_supervisor/scripts/workflow_ctl.sh"
    role: "tooling"
references:
  - "page:workflow_supervisor_model"
  - "page:operator_task_index"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/cli.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# CLI

## Purpose

这个入口是静态 handbook 里的 web terminal 面板，和 `Overview`、
`Codebase`、`Handbook` 平行。它把常用 workflow supervisor 命令做成可切换
模板，方便 operator 识别当前要运行的 route；详细 runtime 解释仍然保留在
handbook 内部 reference 页。

## Model

```text
web terminal surface
  -> command template
  -> example output preview
  -> real local shell run
  -> Gate ledger | generated artifact | operator approval
```

页面内的输出是静态示例，用来说明 command shape、runtime state ownership 和
approval 边界。真实命令输出必须来自本地 shell 或 supervisor runtime。

## Boundaries

- CLI 页面不执行本机 shell，也不写 `.workflow_supervisor/**`。
- web terminal 中的 output preview 不替代 Gate Evidence。
- `.workflow_supervisor/**` 是 runtime state；用 CLI 或 controller 写，不手改。
- `.auto_iterate/**` 仍由 WF10 auto-iterate controller 拥有。
- 需要解释 route model 时，进入 [[page:workflow_supervisor_model|Runtime Routing Model]]。

## Common Confusions

- `status --json` 显示状态，不等于 approve。
- `--dry-run` 可验证 plumbing，但不产生完整 prepare 结果。
- worker result JSON 必须被 supervisor 验证采用，不能用 prose completion 替代。

## Related Pages

- [[page:workflow_supervisor_model|Runtime Routing Model]]
- [[page:operator_task_index|Action Index]]
