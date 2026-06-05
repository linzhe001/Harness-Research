---
schema_version: "0.1"
page_id: "operator_task_index"
title: "Operator Task Index"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/operator_task_index.md"
source_of_truth: true
status: "current"
summary: "Task-first index for choosing the right Harness top-level mode, supervisor action, status check, and detailed reference."
nav:
  section: "operate"
  position: 5
canonical_sources:
  - path: "workflow_handbook/Workflow_Operator_Handbook.md"
    role: "aggregate_source"
  - path: "docs/grill_execution_supervisor.md"
    role: "aggregate_source"
  - path: "tooling/auto_iterate/docs/cli_control_guide.md"
    role: "tooling"
references:
  - "skill:grill"
  - "skill:workflow-supervisor"
  - "skill:change-intake"
  - "term:Gate Evidence"
  - "term:Human Approval"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/operator_task_index.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Operator Task Index

## Purpose

当你知道自己想推进什么、但不确定该进入 Grill、Execution Supervisor，还是
detailed reference 时，从这里开始。

本页刻意按任务组织。内部 reference pages 仍然存在，但它们用于检查、恢复和
artifact ownership，不是普通用户的第一步选择。

## Model

```text
what you want
  -> top-level mode
  -> supervisor action, when applicable
  -> status / output / pause reason
  -> next safe action
```

| 我想做什么 | 顶层入口 | 具体动作 | 先看什么状态或产物 | 什么时候停下来 |
| --- | --- | --- | --- | --- |
| 澄清粗糙 research idea | Grill | `harness grill` 或 `$grill` | `docs/Research_Intent_Draft.md`, `docs/Grill_Round_Log.md`, `.workflow_supervisor/readiness.json` | operator 需要选择 continue、pivot、abandon 或 prepare |
| 判断能否进入执行 | Execution Supervisor | `prepare --dry-run` | Review Packet、readiness preflight、pending request JSON | 需要 contract、缺失事实或 approval decision |
| 处理 pending request | Execution Supervisor | `workflow_ctl status --json`，然后 `workflow_ctl approve ...` | `.workflow_supervisor/**/pending_request.json` 和 `approval_source` | request 不够 exact、scoped 或 auditable |
| 推进 planned slice 的 build / validate | Execution Supervisor | `build` | worker result JSON、Gate ledger、postcondition validation | worker prose 缺 artifact、Gate ledger 或 schema validity |
| 跑多轮实验 | Execution Supervisor | `$auto-iterate-goal check`，然后 `iterate` | `auto_iterate_ctl.sh status --json`、`tail --jsonl`、`iteration_log.json` | `manual_action_required`、PIVOT、ABORT、budget 或 goal change |
| 成熟代码库收到新需求 | Execution Supervisor | `change` | Change Request JSON 和 route confidence | route 影响 evaluation、claim boundary、architecture 或 new research direction |
| 准备 release / submit action | Execution Supervisor | `release --action validate|package|submit` | WF12 Review Packet、Claim Boundary、approved contracts | action 不精确、approval 缺失或 claim 超出证据 |
| 排查内部 node 失败 | Detailed Reference | Stage / Skill lookup | Stage page、Skill page、declared artifacts、Gate ledger | 失败需要 human steering 或 contract change |

常用状态命令：

```bash
tooling/workflow_supervisor/scripts/workflow_ctl.sh status --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh monitor-iterate --json
tooling/auto_iterate/scripts/auto_iterate_ctl.sh status --json
tooling/auto_iterate/scripts/auto_iterate_ctl.sh tail --jsonl --lines 50
```

## Boundaries

- 顶层入口只选择 operating mode；它不批准 contracts 或 claims。
- `prepare/build/iterate/release/change` 是 Execution Supervisor actions，
  不是额外的第一层入口。
- `status --json` 和 `tail --jsonl` 是稳定的 machine-readable surface；
  automation 不能解析 prose summary。
- Review Packet、HTML page、hover preview 和 hook notice 是 decision aids，
  不是 [[term:Human Approval]]。
- `.workflow_supervisor/**`, `.auto_iterate/**`, `.evidence/**`,
  `docs/_views/**`, and `docs/_site/**` are owned by tooling or controllers.

## Common Confusions

- `grill_draft_ready` 只表示 draft intent 存在，不表示 WF1-WF3 complete。
- `prepare_hitl_poc` 证明 approval plumbing，不表示完整 prepare completion。
- low-confidence change route 应暂停请求 steering，而不是直接 edit code。
- release readiness 不等于 package 或 submit approval。

## Related Pages

- [[page:workflow_supervisor_model|Workflow Supervisor Model]]
- [[page:evidence_approval_model|Evidence And Approval Model]]
- [[page:auto_iterate_model|Auto-Iterate Model]]
- [[page:workflow_layers|Detailed Workflow Map]]
- [[page:stage_cards|Stage Reference]]
- [[page:skill_reference|Skill Reference]]
