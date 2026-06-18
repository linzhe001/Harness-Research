---
schema_version: "0.1"
page_id: "operator_task_index"
title: "Operator Action Index"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/operator_task_index.md"
source_of_truth: true
status: "current"
summary: "Action-first index for choosing the right Harness visible alias, internal runtime, status check, and detailed reference."
nav:
  section: "operate"
  position: 5
canonical_sources:
  - path: "workflow_handbook/Workflow_Operator_Handbook.md"
    role: "aggregate_source"
  - path: ".agents/references/workflow-supervisor-runtime.md"
    role: "framework_rule"
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

# Operator Action Index

## Purpose

当你知道自己想推进什么、但不确定该使用哪个 visible alias，还是需要打开
detailed reference 时，从这里开始。

本页刻意按操作意图组织。内部 reference pages 仍然存在，但它们用于检查、恢复和
artifact ownership，不是普通用户的第一步选择，也不是新的第一层入口。

## Model

```text
what you want
  -> visible alias
  -> internal runtime or Skill Contract source
  -> status / output / pause reason
  -> next safe action
```

| 我想做什么 | 可见入口 | 内部运行 | 先看什么状态或产物 | 什么时候停下来 |
| --- | --- | --- | --- | --- |
| 澄清粗糙 research idea | `$grill` | Grill drafting and readiness candidate capture | `docs/05_intake/Research_Intent_Draft.md`, `docs/05_intake/Grill_Round_Log.md`, `docs/05_intake/Execution_Readiness_Packet.md`, `.workflow_supervisor/readiness.json` | operator 需要选择 continue、pivot、abandon 或 prepare |
| 获取或验证数据集和 baseline | `$prepare` | workflow-supervisor `prepare --complete`，必要时加 explicit source/target | `grill_bridge.json`, `docs/Dataset_Stats.md`, `docs/Baseline_Report.md`, Review Packet | Grill 值 redacted/ambiguous、远端操作未授权、worker/gate failure |
| 判断能否进入执行 | `$prepare` | workflow-supervisor `prepare --dry-run` | readiness preflight 和 Gate ledger | readiness 输入缺失、无效或过期 |
| 处理 pending request | `$prepare` / `$build` / `$write` | `workflow_ctl status --json`，然后 scoped `workflow_ctl approve ...` 或 `resume ...` | `.workflow_supervisor/**/pending_request.json` 和 `approval_source` | request 不够 exact、scoped 或 auditable |
| 推进 planned slice 的 build / validate | `$build` | workflow-supervisor `build --auto` 或 `build --worker-command ...` | worker result JSON、Gate ledger、postcondition validation、Validate Run Report | 缺输入、worker 失败、Gate ledger 无效或 validate-run postconditions 未通过 |
| 跑多轮实验 | `$run` | iterate / auto-iterate | `auto_iterate_ctl.sh status --json`、`tail --jsonl`、`iteration_log.json` | `manual_action_required`、PIVOT、ABORT、budget/goal/policy change、缺 `pre_train_commit` / `pre_eval_commit` 记录 |
| 解释实验结果或决定下一轮 | `$analyze` | evaluate | Stage report、Discovery Ledger、Experiment Evidence Index、decision token | run artifact 缺失、claim support 不足、需要新 control 或 reviewer risk |
| 成熟代码库收到新需求 | `$change` | change-intake route classification | Change Request JSON 和 route confidence | route 影响 evaluation、claim boundary、architecture 或 new research direction |
| 写论文、完善 GitHub 或准备 release | `$write` | auto-paper / docs-site / scoped release gate | manuscript artifacts、WF12 Review Packet、Claim Boundary、approved contracts | action 不精确、claim 缺 Claim Delta Evidence、离开 Automation Policy、approval tool 或 external submit |
| 查 supervision 资产是否已吸收 | Detailed Reference | Research Supervision Assets | asset route table、coverage boundary、maintainer watchlist | 资产想进入 runtime 但没有 Skill Contract/read route |
| 旧 workspace 需要适配新 docs layout | `$change` | docs migration plus dynamic-context gates | `workflow_handbook/pages/legacy_docs_migration.md`、`docs/90_legacy/**`、Gate ledger | old approval 不可审计、Evidence Chain 缺 source、contract 需要重新批准 |
| 排查内部 node 失败 | Detailed Reference | Stage / Skill lookup | Stage page、Skill page、declared artifacts、Gate ledger | 失败需要 human steering 或 contract change |

常用状态命令：

Grill 中讨论过的数据下载、HF access、baseline clone 或跳过 gated source 的
意图，应先看 `docs/05_intake/Execution_Readiness_Packet.md` 的
`Execution Intent Ledger`。这些行只是 candidate readiness policy；真正执行时仍由
`$prepare` 的 workflow-supervisor runtime 验证并形成 Gate ledger。

```bash
tooling/workflow_supervisor/scripts/workflow_ctl.sh status --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh monitor-iterate --json
tooling/auto_iterate/scripts/auto_iterate_ctl.sh status --json
tooling/auto_iterate/scripts/auto_iterate_ctl.sh tail --jsonl --lines 50
```

## Boundaries

- visible alias 只选择 operating mode；它不批准 contracts 或 claims。
- Automation Policy 允许 non-Grill flows 自动推进，但不是 Approval Evidence。
- `$prepare/$build/$run/$analyze/$write/$change` 是 visible aliases；
  `workflow-supervisor`, `iterate`, `evaluate`, `auto-paper`, `change-intake`
  等是内部 Skill Contract source，不是 autocomplete 入口。
- Visible aliases 不会生成独立 Skill Contract pages；generated skill pages
  展示的是内部 route targets。
- `research-supervision` assets 已吸收到 `.agents/references/**` 和
  `.claude/shared/**`，runtime 不应指向 `ref/Supervisor-Skills`。
- `status --json` 和 `tail --jsonl` 是稳定的 machine-readable surface；
  automation 不能解析 prose summary。
- Review Packet、HTML page、hover preview 和 hook notice 是 decision aids，
  不是 [[term:Human Approval]]。
- `.workflow_supervisor/**`, `.auto_iterate/**`, `.evidence/**`,
  `docs/_views/**`, and `docs/_site/**` are owned by tooling or controllers.

## Common Confusions

- `grill_draft_ready` 只表示 draft intent 存在，不表示 WF1-WF3 complete。
- `prepare_hitl_poc` 证明 approval plumbing，不表示完整 prepare completion。
- `prepare_complete` 才表示数据、baseline、protocol / review-packet gate 和
  required gates/pending requests 已经走完。
- `build_ready_for_iterate` 才表示 build registry 已运行到 validate-run，并且可跑通的
  postconditions 通过。
- low-confidence change route 应暂停请求 steering，而不是直接 edit code。
- release readiness 不等于 package 或 submit approval。
- release validate/package 可以在 Automation Policy 内自动推进；submit 仍然
  是 explicit approval action。
- `coverage-matrix.md` 是 maintainer audit，不是 operator 每轮都要读的 asset。

## Related Pages

- [[page:workflow_supervisor_model|Runtime Routing Model]]
- `workflow_handbook/pages/legacy_docs_migration.md`
- [[page:evidence_approval_model|Evidence And Approval Model]]
- [[page:auto_iterate_model|Auto-Iterate Model]]
- [[page:research_supervision_assets|Research Supervision Assets]]
- [[page:workflow_layers|Detailed Workflow Map]]
- [[page:stage_cards|Stage Reference]]
- [[page:skill_reference|Skill Reference]]
