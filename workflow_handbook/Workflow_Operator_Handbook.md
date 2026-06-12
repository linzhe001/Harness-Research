# Workflow Operator Handbook

这是 Harness workflow 的人类入口页。它只保留日常操作需要先知道的内容：
现在想推进哪类工作、应该从哪个 human-facing mode 启动、怎么看状态、
什么时候必须停下来让人决策。

内部执行细节不属于第一层界面。只有当你需要追踪 artifact ownership、
Skill Contract、Gate 条件或失败恢复时，再打开 detailed reference。

Markdown source 仍是 source of truth，`docs/_site/workflow_handbook/**` 只是渲染视图。

## Start Here

如果你只想运行 workflow，按这个顺序读：

- 当前页：理解 Harness 的操作模型。
- [[page:operator_task_index|Operator Action Index]]：按“我想做什么”选择顶层入口、supervisor action、状态命令和停点。
- [[page:workflow_supervisor_model|Workflow Supervisor Model]]：理解 Grill 和 Execution Supervisor 的边界。
- [[page:evidence_approval_model|Evidence And Approval Model]]：确认什么是 Gate Evidence，什么才是 Human Approval。
- [[page:auto_iterate_model|Auto-Iterate Model]]：只有进入 WF10 loop 或 delegated iteration 时再读。
- [[page:workflow_layers|Detailed Workflow Map]]、[[page:stage_cards|Stage Reference]] 和 [[page:skill_reference|Skill Reference]]：只在需要细查内部 artifact、Skill 或 Gate 时打开。

## Quick Action Index

| 你现在想做什么 | 顶层入口 | 具体动作 | 先看哪里 |
| --- | --- | --- | --- |
| 把粗糙 idea 问清楚 | Grill | `harness grill` / `$grill` | Research Intent Draft、Grill Round Log |
| 准备数据集和 baseline | Execution Supervisor | `$prepare` / `prepare --complete` | Dataset Stats、Baseline Report、Review Packet |
| 判断能否进入执行 | Execution Supervisor | `$prepare` / `prepare --dry-run` | readiness preflight、Review Packet |
| 推进 build / validate | Execution Supervisor | `$build` / `build --auto` 或 `build --worker-command ...` | worker result JSON、Gate ledger、Validate Run Report |
| 跑多轮实验 | Execution Supervisor | `$run`，必要时接 `$analyze` | `auto_iterate_ctl.sh status --json`、`iteration_log.json` |
| 处理成熟代码库的新需求 | Execution Supervisor | `$change` | Change Request JSON、route confidence |
| 写论文、文档或 release claim gate | Execution Supervisor | `$write` / scoped release action | paper artifacts、WF12 Review Packet、Claim Boundary |
| 排查内部失败 | Detailed Reference | Stage / Skill lookup | Stage Reference、Skill Reference |

完整索引见 [[page:operator_task_index|Operator Action Index]]。

## Top-Level Modes

日常使用先选两个顶层入口之一：

```text
Intent
  -> Grill or Execution Supervisor
  -> supervisor action / typed request / worker result / Gate ledger
  -> Human Approval or next safe action
```

| Top-level mode | 什么时候用 | 包含什么 | 它不会做什么 |
| --- | --- | --- |
| `harness grill` / `$grill` | 研究意图还不清楚，需要追问、挑战、收敛 Research Intent | grill rounds、Research Intent Draft、Execution Readiness candidate | 不批准 contract，不宣称 WF1-WF3 完成 |
| visible aliases `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change` | intent 已经能进入执行、验证、迭代、写作，或成熟代码库出现新需求 | prepare/build/run/analyze/write/change modes, routed to internal supervisor or Skill Contracts | 不绕过 Gate，不信任 worker prose，不替人批准 contract / claim / release |

更完整的边界见 [[page:workflow_supervisor_model|Workflow Supervisor Model]]。

## Daily Run Shape

一个正常 turn 应该长这样：

```text
operator request
  -> choose Grill or Execution Supervisor
  -> read relevant source artifacts
  -> run or inspect the owning tool
  -> produce structured Gate ledger / pending request / worker result
  -> ask for Human Approval only when required
  -> report next safe action
```

`$prepare` / `prepare --complete` 会在输入明确时验证或获取数据集、clone 或采用
baseline、生成 protocol / Review Packet，并在没有缺失输入、policy blocker、
worker failure 或 gate failure 时流畅完成到 `prepare_complete`。远端数据下载和
baseline clone 必须显式加 `--allow-external-downloads`，或在 Grill readiness 中明确
`external_download_policy: allow` / `allow_external_downloads: true`。
更窄的自动化范围应写入 `approved_datasets`、`approved_baselines`、
`target_paths`、`unknowns` 和 `operator_approved_at`。
当 full prepare 从对话启动时，supervisor 会读取 `.workflow_supervisor/readiness.json`、
`docs/Execution_Readiness_Packet.md`、`docs/Research_Intent_Draft.md` 和
`docs/Grill_Round_Log.md`，把结构化 dataset / baseline 输入桥接到 prepare。
Redacted 或 ambiguous 值不会被猜测，会变成 typed pending request。

`$build` / `build --auto` 或 `build --worker-command ...` 会按 build registry 推进
implementation / validation nodes。它只有在 validate-run postconditions 通过、
产物可跑通时才记录 `build_ready_for_iterate`；缺输入、worker 失败或验证失败都会
变成 typed pending request 或失败记录。Worker prompt 会带 node postconditions
和 allowed write patterns；worker 必须运行真实检查并写 Gate ledger，不能只写
prose success。

不要把 generated HTML、hover card、Review Packet 或 hook notice 当成批准。它们只是
阅读视图、decision input 或 guardrail signal。

## Stop Points

必须暂停或请求 Human Approval 的常见情况：

- contract acceptance、Claim Boundary、release decision 或 high-risk transition。
- Review Packet 要求 approve/revise/reject。
- supervisor 创建 `pending_request.json`。
- auto-iterate 返回 `manual_action_required` 或 operator pause。
- change intake 分类不确定，或影响 evaluation/claim boundary。

`workflow_ctl approve` 只作用于一个 pending request。它必须保留
`approval_source`，不能变成 “approve all”。

## Gate And Approval

常见边界：

- Gate Evidence 证明命令、测试、validator 或 review 是否执行以及结果。
- Conclusion Evidence 支持事实、claim、protocol choice 或 research conclusion。
- Approval Evidence 只能来自明确的人类批准或可审计批准 artifact。
- Review Packet 是决策输入，不是批准。

更详细的边界见 [[page:evidence_approval_model|Evidence And Approval Model]]。

## Detailed Reference

这些页给 agent、maintainer 或正在排查失败的人使用。普通 operator 不需要先读：

- [[page:workflow_layers|Detailed Workflow Map]]：Intent、顶层入口、内部 Stage/Skill/Gate 的关系。
- [[page:stage_cards|Stage Reference]]：WF0-WF12 内部 artifact 和 Stage Skill 索引。
- [[page:skill_reference|Skill Reference]]：Skill Contract 的 read/write/gate 细节。
- [[page:hooks_permissions_model|Hooks And Permissions Model]]：为什么某些写入会被拦。
- [[page:workflow_terms|Workflow Terms]]：Top-level mode、Pending Request、Gate Evidence 等术语。
- [[page:markdown_to_html_preview_chain|Markdown To HTML Preview Chain]]：source Markdown 到 HTML view 的生成链路。

不要再在 `workflow_handbook/` 下新增平行叙事文档；新增稳定内容应放进
`workflow_handbook/pages/**`，并接入 `workflow_handbook/config/navigation.json`。

## Generated Views

`workflow_handbook/**` 是 source Markdown。HTML 通过 tooling 生成：

```text
workflow_handbook/**/*.md
  -> docs/_views/workflow_handbook_reference_index.json
  -> docs/_site/workflow_handbook/**
```

hover card 是 preview；链接本身应该能跳转到 stage、skill、page、term 或 source reference。
生成链路见 [[page:markdown_to_html_preview_chain|Markdown To HTML Preview Chain]]。

## Currentness

本手册的 source of truth 是当前仓库里的 Markdown、schemas、Skill Contracts 和
tooling source。外部网页和长篇设计文档只作为设计背景；在做实现或发布判断前，
必须重新读当前 source artifacts，并用 validator / tests / Gate ledger 证明结果。
