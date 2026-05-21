# Workflow Operator Handbook

这是 Harness workflow 的人类入口页。它只保留日常操作需要先知道的内容：
现在处在哪个 Stage、应该启动哪个 Skill、完成后应看到什么产物、什么时候必须停下来让人决策。

深层 contract、hook、read/write scope、Evidence Chain 和 generated HTML 细节都放在链接页里。
Markdown source 仍是 source of truth，`docs/_site/workflow_handbook/**` 只是渲染视图。

## Start Here

如果你只想运行 workflow，按这个顺序读：

- 当前页：理解 Harness 的操作模型。
- [[page:stage_cards|Stage Details]]：快速查每个 WF Stage 怎么启动。
- 当前 Stage 的详情页：例如 [[stage:WF10|WF10 details]]。
- 需要理解分层时读 [[page:workflow_layers|Workflow Layers]]。
- 只有需要排查权限、Gate 或 Skill 边界时，再读 Skill detail 或 hook reference。

## The Four Layers

Harness 运行时可以按四层理解：

```text
Intent
  -> Stage
  -> Skill
  -> Gate
```

| Layer | 你要回答的问题 | 常见入口 |
| --- | --- | --- |
| Intent | 我现在想推进哪类工作？ | idea, data, baseline, code, validate, iterate, release |
| Stage | 当前属于 WF0-WF12 哪个阶段？ | Stage Details |
| Skill | 本轮应该激活哪个 Skill？ | `$survey-idea`, `$code-debug`, `$iterate` |
| Gate | 什么证据能证明可以继续？ | tests, validators, Gate ledger, Human Approval |

更完整的分层说明见 [[page:workflow_layers|Workflow Layers]]。

## Daily Run Shape

一个正常 turn 应该长这样：

```text
operator request
  -> pick active Stage / Skill
  -> read required source artifacts
  -> write only inside active write scope
  -> run narrow validation or report NOT_RUN
  -> report Gate ledger when a gate was touched
  -> ask for Human Approval only when the workflow requires it
```

不要把 generated HTML、hover card 或 hook notice 当成批准。它们只是阅读视图或 Gate Evidence 的一部分。

## Stage Details

[[page:stage_cards|Stage Details]] 是运行入口，不再单独维护额外地图页。
它按工作性质把 Stage 分成四组：

- Explore: WF0-WF4，建立 idea、Conclusion Evidence、data facts。
- Contract & Plan: WF5-WF7，建立 baseline、approved boundaries、implementation slices。
- Build & Validate: WF8-WF9，完成代码切片并验证。
- Iterate & Release: WF10-WF12，运行实验循环、final experiment、release。

每个 Stage 只给一句话、启动方式、完成效果和详情链接。具体 read/write scope、
required actions 和 Gate 条件在左侧 `Workflow Details` -> `Stage Details` 的子页面里。

## Gate And Approval

常见边界：

- Gate Evidence 证明命令、测试、validator 或 review 是否执行以及结果。
- Conclusion Evidence 支持事实、claim、protocol choice 或 research conclusion。
- Approval Evidence 只能来自明确的人类批准或可审计批准 artifact。
- Review Packet 是决策输入，不是批准。

更详细的边界见 [[page:evidence_approval_model|Evidence And Approval Model]]。

## Generated Views

`workflow_handbook/**` 是 source Markdown。HTML 通过 tooling 生成：

```text
workflow_handbook/**/*.md
  -> docs/_views/workflow_handbook_reference_index.json
  -> docs/_site/workflow_handbook/**
```

hover card 是 preview；链接本身应该能跳转到 stage、skill、page、term 或 source reference。
生成链路见 [[page:markdown_to_html_preview_chain|Markdown To HTML Preview Chain]]。
维护约束：不要再在 `workflow_handbook/` 下新增平行叙事文档；入口只保留当前页和
`Workflow_Stage_Cards.md`，深层内容放到 `workflow_handbook/pages/**`、`stages/**` 或
`skills/**`。

## Workflow Details

- [[page:stage_cards|Stage Details]]：WF0-WF12 的速查卡和 Stage detail 索引。
- [[page:workflow_layers|Workflow Layers]]：Intent、Stage、Skill、Gate 的关系。
- [[page:skill_reference|Skill Reference]]：所有 Skill 的 read/write/gate 细节。
- [[page:hooks_permissions_model|Hooks And Permissions Model]]：为什么某些写入会被拦。
- [[page:auto_iterate_model|Auto-Iterate Model]]：WF10 controller 怎么参与。
- [[page:workflow_terms|Workflow Terms]]：Stage、Skill、Gate Evidence、Human Approval 等术语。
