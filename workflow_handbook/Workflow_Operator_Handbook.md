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
- [[page:research_supervision_assets|Research Supervision Assets]]：确认从 local supervision material 吸收到 Harness 的匿名化资产、使用阶段和非证据边界。
- [[page:site_modes|Site Modes]]：确认 GitHub Pages/static HTML 和 localhost live service 的边界。
- [[page:auto_iterate_model|Auto-Iterate Model]]：只有进入 WF10 loop 或 delegated iteration 时再读。
- [[page:workflow_layers|Detailed Workflow Map]]、[[page:stage_cards|Stage Reference]] 和 [[page:skill_reference|Skill Reference]]：只在需要细查内部 artifact、Skill 或 Gate 时打开。

## Quick Action Index

| 你现在想做什么 | 可见入口 | 内部运行 | 先看哪里 |
| --- | --- | --- | --- |
| 把粗糙 idea 问清楚 | `$grill` | Grill drafting and readiness candidate capture | Research Intent Draft、Grill Round Log |
| 准备数据集和 baseline | `$prepare` | workflow-supervisor `prepare --complete` | Dataset Stats、Baseline Report、Review Packet |
| 判断 readiness 输入是否足够 | `$prepare` | workflow-supervisor `prepare --dry-run` | readiness preflight、Gate ledger |
| 推进 build / validate | `$build` | workflow-supervisor `build --auto` 或 `build --worker-command ...` | worker result JSON、Gate ledger、Validate Run Report |
| 跑多轮实验 | `$run` | iterate / auto-iterate | `auto_iterate_ctl.sh status --json`、`iteration_log.json` |
| 解释实验结果并决定下一轮 | `$analyze` | evaluate | Stage report、Discovery Ledger、Experiment Evidence Index |
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

| Visible alias | 内部路由 | 主要顺序或逻辑 | 它不会做什么 |
| --- | --- | --- | --- |
| `$grill` | `grill`，accepted draft 后接 `init-project update-from-grill` | 3-5 个 blocking questions -> draft intent/readiness artifacts -> operator exit decision | 不批准 contract，不宣称 WF1-WF3 完成 |
| `$prepare` | workflow-supervisor `prepare` | `--dry-run` 只做 readiness preflight；`--complete` 走 readiness -> acquisition plan -> data -> baseline -> protocol -> Review Packet | 不猜测 redacted/ambiguous 输入，不绕过 external-download policy |
| `$build` | workflow-supervisor `build` | `build_refine_arch -> build_plan -> build_code_expert -> build_validate_run`；`build_code_debug` 只在失败恢复时进入 | 不把 foundation-only slice 当成 `build_ready_for_iterate` |
| `$run` | `iterate` / auto-iterate bridge | 读取 `iteration_log.json` 的 `action_state.next_action`，执行一项 WF10 action，并记录 run artifact bundle | 不写 release claim，不替人 pivot |
| `$analyze` | `evaluate` | 解析 run artifacts，分离 metric movement、pipeline health、claim support 和 next experiment | 不把弱 `iteration_log.json` 信号升级成论文 claim |
| `$write` | `auto-paper`，必要时 `docs-site` 或 release gate | `auto-paper-research -> argument -> citation -> layout -> patch -> harden`；缺实验时写 `RUN_REQUEST` 给 `$run` | 不发明实验、citation、结果或超出 Claim Boundary 的 claim |
| `$change` | `change-intake` | 只分类 route：bugfix、experiment delta、architecture/evaluation/claim delta、new direction、harness guardrail 或 `STEER` | 不直接调用目标 Skill，不直接改 code/contracts |

更完整的边界见 [[page:workflow_supervisor_model|Runtime Routing Model]]。

## Research Supervision Asset Layer

`ref/Supervisor-Skills` 的可复用内容已经被吸收到 Harness 内部资产，而不是让
workflow 运行时指回 `ref/`。PDF、图片、个人身份、学校、logo、会议讲者和具体
case prose 没有复制；可复用方法被转成匿名 Markdown、ASCII/流程图、checklist 和
paper/figure patterns。

当前吸收后的路由是：

| Workflow area | Internalized asset use |
| --- | --- |
| `$grill` / `$change` | `phd-research-primer.md`, `idea-evaluation.md`, `research-supervision-patterns.md` 用于 problem type、fatal-flaw、dominant axis、falsifier 和 reviewer risk |
| `$build` / `$run` / `$analyze` | `experiment-and-build-canvas.md` 和 `ai-assisted-research-workflow.md` 用于小切片、first feedback command、experiment canvas 和分析拆分 |
| `$write` / `auto-paper-*` | `paper-writing-layouts.md`, `benchmark-evaluation-paper.md`, `paper-and-figure-system.md`, `scientific-plotting.md`, `pre-submission-review.md`, `case-patterns.md` 用于论文结构、图表 contract、caption claim map 和 harden checklist |
| Maintainer audit | `coverage-matrix.md` 只记录吸收覆盖与匿名化决策，不进入日常 runtime read set |

这些资产是 L1 process guidance。它们可以塑造问题、实验计划、写作结构和审查
checklist，但不能证明目标项目事实、metric、dataset availability、baseline strength
或 Human Approval。详细说明见
[[page:research_supervision_assets|Research Supervision Assets]]。

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
- [[page:research_supervision_assets|Research Supervision Assets]]：匿名化 supervision asset pack 的 stage routing 和 coverage boundary。
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

## Maintainer Watchlist

- visible aliases 仍只有 `$grill`, `$prepare`, `$build`, `$run`, `$analyze`,
  `$write`, `$change`；如果新增入口，必须同步 product policy、hook tests、
  handbook navigation 和 generated Stage/Skill pages。
- `workflow_handbook/skills/**`, `workflow_handbook/stages/**` 和
  `Workflow_Stage_Cards.md` 是 generated views；Skill Contract 或 skill body
  改动后必须重新运行 generator，不能手补 generated 页面。
- `prepare --dry-run`, legacy `prepare_hitl_poc`, and `prepare --complete`
  容易混淆：只有 `prepare_complete` 能作为后续 build/iterate 依赖。
- `coverage-matrix.md` 没有 runtime route 是有意设计；除它以外，新增
  supervision asset 若长期没有任何 Skill Contract 或 handbook route，应判定为未吸收。
- model weight approval 目前通过 `target_paths` 和 policy rows 表达；未来如果加入
  native `approved_weights` schema，需要同步 Grill、prepare tooling、contracts 和 handbook。
- `$write` -> `$run` 的 `RUN_REQUEST` 桥依赖
  `auto_paper_output/*/run_request_register.{json,md}`；`$run` preflight 必须继续扫描这些请求。
