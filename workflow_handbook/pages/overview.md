---
schema_version: "0.1"
page_id: "overview"
title: "Overview"
kind: "overview"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/overview.md"
source_of_truth: true
status: "current"
summary: "Top-level orientation for the static Harness workflow site."
nav:
  section: "topbar"
  position: 0
canonical_sources:
  - path: "workflow_handbook/Workflow_Operator_Handbook.md"
    role: "aggregate_source"
  - path: "workflow_handbook/pages/codebase.md"
    role: "aggregate_source"
  - path: "workflow_handbook/pages/cli.md"
    role: "aggregate_source"
references:
  - "page:operator_handbook"
  - "page:codebase"
  - "page:cli"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/overview.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Overview

## Purpose

这个入口只回答第一层问题：我现在应该看哪个区域。顶部导航的
`Overview`、`Codebase`、`CLI`、`Handbook` 是并列入口，不属于同一棵
handbook 左侧目录。

## Mental Model

```text
overview
  -> codebase: repository map and ownership boundaries
  -> cli: commands and runtime surfaces
  -> handbook: workflow operation and detailed references
```

`Overview` 是路由面；`Handbook` 才是操作手册。进入 `Handbook` 后左侧栏
显示 workflow handbook 的目录。进入 `Codebase` 或 `CLI` 时，左侧栏只保留
顶层区块关系，不展开 handbook 目录。

## Start Here

- 想知道仓库区域和 generated view 边界，打开 [[page:codebase|Codebase]]。
- 想找命令入口和 supervisor runtime，打开 [[page:cli|CLI]]。
- 想按任务推进 workflow，打开 [[page:operator_handbook|Handbook]]。

## Related Pages

- [[page:codebase|Codebase]]
- [[page:cli|CLI]]
- [[page:operator_handbook|Handbook]]
