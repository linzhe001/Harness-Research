# Workflow Operator Handbook

这是 Harness workflow 的人类入口页。它只保留日常操作需要先知道的内容：
现在想推进哪类工作、应该从哪个 human-facing mode 启动、怎么看状态、
什么时候必须停下来让人决策。

内部执行细节不属于第一层界面。只有当你需要追踪 artifact ownership、
Skill Contract、Gate 条件或失败恢复时，再打开 detailed reference。

Markdown source 仍是 source of truth，`docs/_site/workflow_handbook/**` 只是渲染视图。

> [!TIP] 读法
> 先按任务选择 visible alias，再看状态面和停点。只有当状态、Gate 或
> artifact ownership 不清楚时，再进入 detailed reference。

## Mental Model

Harness 的第一层不是 WF0-WF12 stage 选择器，而是 operator intent 到
visible alias 的路由面：

```text
operator intent
  -> visible alias
  -> internal runtime / Skill Contract source
  -> Gate Evidence, typed request, or generated view
  -> Human Approval or next safe action
```

生成后的 HTML 站点采用静态知识库视图：左侧导航用于跨页跳转，正文只保留当前任务
需要的信息，右侧页内目录用于长页定位，hover card 只提供 preview。链接本身仍应能
跳到 stage、skill、page、term 或 source reference。

## Start Here

如果你只想运行 workflow，按这个顺序读：

- 当前页：理解 Harness 的操作模型。
- [[page:operator_task_index|Operator Action Index]]：按“我想做什么”选择可见入口、内部 runtime、状态命令和停点。
- [[page:workflow_supervisor_model|Runtime Routing Model]]：理解 visible alias 如何路由到内部 runtime 或 Skill Contract source。
- [[page:evidence_approval_model|Evidence And Approval Model]]：确认什么是 Gate Evidence，什么才是 Human Approval。
- [[page:site_modes|Site Modes]]：确认 GitHub Pages/static HTML 和 localhost live service 的边界。
- [[page:auto_iterate_model|Auto-Iterate Model]]：只有进入 WF10 loop 或 delegated iteration 时再读。
- [[page:workflow_layers|Detailed Workflow Map]]、[[page:stage_cards|Stage Reference]] 和 [[page:skill_reference|Skill Reference]]：只在需要细查内部 artifact、Skill 或 Gate 时打开。

## Quick Action Index

| 你现在想做什么 | 可见入口 | 内部运行 | 先看哪里 |
| --- | --- | --- | --- |
| 把粗糙 idea 问清楚 | `$grill` | Grill drafting and readiness candidate capture | Research Intent Draft、Grill Round Log |
| 准备数据集和 baseline | `$prepare` | workflow-supervisor `prepare --complete` | Dataset Stats、Baseline Report、Review Packet |
| 判断能否进入执行 | `$prepare` | workflow-supervisor `prepare --dry-run` | readiness preflight、Review Packet |
| 推进 build / validate | `$build` | workflow-supervisor `build --auto` 或 `build --worker-command ...` | worker result JSON、Gate ledger、Validate Run Report |
| 跑多轮实验 | `$run`，必要时接 `$analyze` | iterate / auto-iterate, then evaluate | `auto_iterate_ctl.sh status --json`、`iteration_log.json` |
| 处理成熟代码库的新需求 | `$change` | change-intake route classification | Change Request JSON、route confidence |
| 写论文、文档或 release claim gate | `$write` | auto-paper / docs-site / scoped release gate | paper artifacts、WF12 Review Packet、Claim Boundary |
| 排查内部失败 | Detailed Reference | Stage / Skill lookup | Stage Reference、Skill Reference |

完整索引见 [[page:operator_task_index|Operator Action Index]]。

## Visible Aliases

日常使用先选一个可见入口：

```text
Intent
  -> visible alias
  -> internal runtime / typed request / worker result / Gate ledger
  -> Human Approval or next safe action
```

| Visible alias | 什么时候用 | 内部路由 | 它不会做什么 |
| --- | --- | --- |
| `$grill` | 研究意图还不清楚，需要追问、挑战、收敛 Research Intent | Grill drafts and readiness candidates | 不批准 contract，不宣称 WF1-WF3 完成 |
| `$prepare` / `$build` | intent 已经能进入数据、baseline、实现或验证 | internal workflow-supervisor runtime | 不绕过 Gate，不信任 worker prose，不替人批准 contract |
| `$run` / `$analyze` | 需要跑实验、调参、消融、可视化或解释结果 | iterate / auto-iterate / evaluate | 不扩大 claim，不替人决定 pivot 或 final claim |
| `$write` / `$change` | 需要写论文、文档、release gate，或成熟代码库出现新需求 | auto-paper / docs-site / release gate / change-intake | 不替人批准 claim、release 或高风险方向变更 |

更完整的边界见 [[page:workflow_supervisor_model|Runtime Routing Model]]。

## Site Modes

Handbook HTML 有两个不同的使用边界：

```text
static view
  -> generated HTML/CSS/JS
  -> GitHub Pages or local file
  -> read-only handbook and hover previews

local live view
  -> same generated HTML
  -> localhost service, if implemented
  -> optional rebuild or terminal APIs
```

当前 `docs/_site/workflow_handbook/**` 是 static view。它适合 GitHub Pages、
归档和 review，但不运行 tmux、PTY、Claude Code、Codex、secret resolver 或本地
写文件 API。若未来加入 browser terminal，它应属于单独的 localhost live service，
并且必须保留 origin check、local token、profile/env isolation 和 operator control。

详细边界见 [[page:site_modes|Site Modes]]。

## Daily Run Shape

一个正常 turn 应该保持这个形状：

```text
operator request
  -> choose one visible alias
  -> read relevant source artifacts
  -> run or inspect the owning tool
  -> produce structured Gate ledger / pending request / worker result
  -> ask for Human Approval only when required
  -> report next safe action
```

### Prepare

`$prepare` / `prepare --complete` 在输入明确时推进数据集、baseline、protocol 和
Review Packet 准备。

- 远端数据下载和 baseline clone 必须显式加 `--allow-external-downloads`，或在
  Grill readiness 中明确 `external_download_policy: allow` /
  `allow_external_downloads: true`。
- 更窄的自动化范围应写入 `approved_datasets`、`approved_baselines`、
  `target_paths`、`unknowns` 和 `operator_approved_at`。
- full prepare 从对话启动时，supervisor 会读取
  `.workflow_supervisor/readiness.json`、`docs/05_intake/Execution_Readiness_Packet.md`、
  `docs/05_intake/Research_Intent_Draft.md` 和 `docs/05_intake/Grill_Round_Log.md`，把结构化
  dataset / baseline 输入桥接到 prepare。
- Redacted 或 ambiguous 值不会被猜测，会变成 typed pending request。

### Build

`$build` / `build --auto` 或 `build --worker-command ...` 按 build registry 推进
implementation / validation nodes。

- 只有 validate-run postconditions 通过、产物可跑通时，才记录
  `build_ready_for_iterate`。
- 缺输入、worker 失败或验证失败会变成 typed pending request 或失败记录。
- Worker prompt 会带 node postconditions 和 allowed write patterns。
- Worker 必须运行真实检查并写 Gate ledger，不能只写 prose success。

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

- [[page:workflow_layers|Detailed Workflow Map]]：Intent、可见入口、内部 Stage/Skill/Gate 的关系。
- [[page:stage_cards|Stage Reference]]：WF0-WF12 内部 artifact 和 Stage Skill 索引。
- [[page:skill_reference|Skill Reference]]：Skill Contract 的 read/write/gate 细节。
- [[page:hooks_permissions_model|Hooks And Permissions Model]]：为什么某些写入会被拦。
- [[page:workflow_terms|Workflow Terms]]：Top-level mode、Pending Request、Gate Evidence 等术语。
- [[page:site_modes|Site Modes]]：GitHub Pages/static view 与 localhost live service 的边界。
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
这个 generated view 可以作为 GitHub Pages 上的只读 handbook，也可以被未来的本地
live service 复用；但 generated HTML 本身不拥有终端、文件写入或 approval 权限。
生成链路见 [[page:markdown_to_html_preview_chain|Markdown To HTML Preview Chain]]。

## Currentness

本手册的 source of truth 是当前仓库里的 Markdown、schemas、Skill Contracts 和
tooling source。外部网页和长篇设计文档只作为设计背景；在做实现或发布判断前，
必须重新读当前 source artifacts，并用 validator / tests / Gate ledger 证明结果。
