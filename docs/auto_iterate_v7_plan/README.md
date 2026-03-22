# Auto-Iterate V7 详细实施计划

> 状态：planning artifact
> 基线文档：`docs/auto_iterate_and_remote_v7.md`
> 目标：把当前 Harness workflow 改造成 v7 定义的 controller-driven auto-iterate + remote-ready workflow

## 1. 这套计划的定位

这不是一份“功能想法清单”，而是一份给后续 AI 实施者使用的改造执行蓝图。它要解决两个问题：

1. 把 `docs/auto_iterate_and_remote_v7.md` 里的契约、状态机、恢复语义、远控边界，拆成可以逐步落地的工程任务。
2. 避免后续 AI 在实现时重新做架构猜测，尤其避免在 `.agents`、`.claude`、`iteration_log.json`、`PROJECT_STATE.json`、`.auto_iterate/` 的职责边界上再次分叉。

这份计划默认把当前仓库视为“workflow 模板仓库”，不是某个具体研究项目本身。也就是说：

- 本仓库负责产出 skill、template、controller script、config example、测试夹具。
- 真实项目中的 `PROJECT_STATE.json`、`iteration_log.json`、`CLAUDE.md`、`.auto_iterate/` 将由这些模板和脚本在项目根目录中工作。
- 因为当前仓库根目录并没有一个真实运行中的研究项目状态，所以所有 controller 测试都必须基于 fixture project root，而不是依赖当前仓库现状。

### 1.1 语言约定

本目录可以继续用中文叙述工程计划，但下面这些内容一律保持英文 canonical form，不做中英混写：

- schema field / JSON key
- enum value
- file / command / flag 名称
- workflow ID（如 `WF8`、`NEXT_ROUND`、`halt_reason`）

如果后续需要补英文版 guide，也应复用同一套英文 canonical identifiers，而不是重新翻译字段名或决策名。

## 2. 文档阅读顺序

后续 AI 建议严格按下面顺序阅读和执行：

1. `README.md`：总览、基线差距、参考仓库映射、总 workstream。
2. `01_contract_freeze.md`：先冻结所有 schema、ownership、event、goal、decision contract。
3. `02_controller_runtime_plan.md`：再实现 controller / runtime / CLI / recovery / timeout / budget。
4. `03_skill_and_prompt_migration.md`：然后同步 `.agents`、`.claude`、template、schema、guide。
5. `04_remote_account_ops.md`：最后接远控、账号、proxy-ready 边界。
6. `05_test_rollout_checklist.md`：按测试矩阵和 rollout gate 收尾。

不建议跳着做。v7 最大风险不是代码量，而是“先写出能跑的壳，再补契约”，那样最容易回到 v6 之前的语义漂移。

## 3. 当前基线与缺口

### 3.1 当前仓库已经具备的基础

- `.agents/`：Codex 侧 workflow skill、reference spec、local context 约束。
- `.claude/`：Claude Code 侧 skill、rules、shared references、stage template。
- `docs/auto_iterate_and_remote_v2..v7.md`：auto-iterate 设计迭代历史。
- `docs/feature_plan_auto_iterate_and_remote.md`：更早期的粗粒度 feature 草案，但还不是 v7 级别的 implementer plan。
- 现有 WF8 skill 已经有：
  - iteration context 文件
  - `iteration_log.json` 单写者约束
  - `screening` 概念
  - `run_manifest` / `training_trace`
  - `evaluate` / `code-debug` 协同

### 3.2 当前仓库缺失的核心能力

- 没有 `scripts/auto_iterate_ctl.sh` / `.py` / controller / runtime adapter。
- 没有 `.auto_iterate/` runtime state contract 的任何实现。
- 没有 v7 要求的 `state.json` / `lock.json` / `events.jsonl` schema fixture。
- 没有 `goal.md` / `goal.next.md` staged activation 机制。
- 没有 controller-owned budget / account / timeout / retry / heartbeat worker。
- 没有远控命令面与 `cc-connect` 的稳定映射。
- 没有账号 registry / `CODEX_HOME` per-process 选择。
- 没有 contract tests / dry_run 测试壳。
- `.agents` / `.claude` / template / guide 中大量内容仍停留在旧 WF8 语义：
  - 决策枚举只有 `CONTINUE / DEBUG / PIVOT / ABORT`
  - 没有 `NEXT_ROUND`
  - 没有 controller 状态与 `.auto_iterate/` 语义
  - 没有 `full_run.status=recoverable_failed|failed`
  - 没有 `auto_mode` canonical transport

### 3.3 已经确认的受影响文件面

必须进入改造范围的文件面包括：

- 新增脚本与配置：
  - `scripts/auto_iterate_ctl.sh`
  - `scripts/auto_iterate_ctl.py`
  - `scripts/auto_iterate_controller.py`
  - `scripts/auto_iterate_runtime_codex.sh`
  - `scripts/auto_iterate_runtime_codex.py`
  - `scripts/auto_iterate/**`（推荐从第一版开始承载可测 primitives，而不是把核心逻辑永久塞进单文件）
  - `config/auto_iterate_controller.example.yaml`
  - `config/auto_iterate_accounts.example.yaml`
  - `docs/auto_iterate_goal_template.md`
  - `docs/remote_control_guide.md`
- 必改 skill / schema / guide：
  - `.agents/skills/auto-iterate-goal/**`
  - `.claude/skills/auto-iterate-goal/**`
  - `.agents/skills/iterate/**`
  - `.claude/skills/iterate/**`
  - `.agents/skills/evaluate/**`
  - `.claude/skills/evaluate/**`
  - `.agents/skills/orchestrator/**`
  - `.claude/skills/orchestrator/**`
  - `.agents/skills/evaluate/references/stage-report.md`
  - `.claude/skills/evaluate/templates/stage-report.md`
  - `.agents/references/workflow-guide.md`
  - `.claude/Workflow_Guide.md`
  - `.claude/skills/init-project/SKILL.md`
  - `.agents/skills/init-project/references/claude-md-template.md`
  - `.claude/skills/init-project/templates/claude-md-template.md`
  - `AGENTS.md.template`
  - `CLAUDE.md.template`
- 必增测试资产：
  - `tests/fixtures/auto_iterate/**`
  - `tests/test_auto_iterate_*.py`

## 4. 不可打破的总约束

后续实现必须同时满足下面约束；任何一条被破坏，都意味着 plan 没被正确执行：

1. `iteration_log.json` 继续只由 `iterate` 写。
2. `PROJECT_STATE.json` 继续只由 `orchestrator` 和 stage skill 写。
3. controller 只写 `.auto_iterate/**`。
4. V1 只支持 Codex runtime，不宣称 Claude runtime parity。
5. 每个 phase 必须 fresh process，不允许单 session 长时间累积上下文。
6. phase success 只能靠 repository postcondition 验证，不能靠 chat prose、stdout 文案或 runtime metadata 推断。
7. 不能伪造一个“真正存在的 `$iterate` shell CLI”；controller 调的是 runtime adapter，adapter 再以 prompt 方式执行 canonical `$iterate <phase>` 语义。
8. 不能通过切换全局 `~/.codex/auth.json` 做账号切换；只能用 per-process `CODEX_HOME`。
9. 不能让 remote layer 直接改 `.auto_iterate/state.json`。
10. 不能把 `.agents` 和 `.claude` 维护成两套语义不同的 workflow 文档。

## 5. `.agents` 与 `.claude` 的基石地位

本次改造里，`.agents` 和 `.claude` 不是“附带文档”，而是 workflow 的双基石：

- `.agents`：
  - 是 Codex-first V1 的实际 prompt / reference / skill contract 基础层。
  - controller 在 V1 的 runtime 行为，必须和 `.agents` 中的 WF8 语义一致。
- `.claude`：
  - 虽然 v7 明确说 Claude runtime 不属于 V1 实装范围，但 `.claude` 仍然必须同步 vocabulary、state ownership、WF8 decision 语义。
  - 否则未来补 `auto_iterate_runtime_claude.*` 时会出现第二次大迁移。

一句话：V1 的“执行权”在 `.agents`，V1 的“语义一致性责任”同时在 `.agents` 和 `.claude`。

## 6. 参考仓库映射

| 参考源 | 借鉴点 | 在本项目中的采纳方式 | 明确不采纳的部分 |
|---|---|---|---|
| `Reference_tool_repo/ralph` | fresh context、每轮独立进程、append-only progress、简单 shell 入口 | phase 级 fresh process；`events.jsonl` 作为 append-only loop log；shell wrapper 只做 thin entrypoint | 不照搬“单 bash loop + prompt file”作为主逻辑，不用 branch 驱动 |
| `Reference_tool_repo/Auto-claude-code-research-in-sleep` | state file recovery、cross-model review、阶段化 pipeline、可选通知、AUTO_PROCEED 思维 | `.auto_iterate/state.json` + recovery；controller-owned event/state；`auto_mode` 无阻塞执行；可选 remote notify | 不把长流程逻辑塞回单 skill 文本里，不依赖 session compact 自恢复 |
| `Reference_tool_repo/cc-connect` | 远控命令面、multi-project、session 管理、webhook / management API、memory 操作 | 先稳定本地 CLI，再把 `start/status/stop/pause/resume/tail/override` 映射给 `cc-connect` | V1 不直接把 controller 状态暴露为聊天内任意写入 |
| `Reference_tool_repo/openclaw-cliproxy-kit` | 多账号会话、quota failover、auth sync、dashboard/operator 视角 | 设计 `auto_iterate_accounts.yaml`；账号 cooldown；quota/rate failure 后切账号 | V1 不引入 cliproxy 作为硬依赖，不做 pooled routing |
| `Reference_tool_repo/codex-account-manager` | 账号 registry、usage cache、项目/系统模式意识、显式切换工具 | 参考其 registry / usage snapshot 思维，为 controller 设计 account metadata | 不使用“覆盖全局 auth 文件”模式驱动运行中切换 |
| `.agents` / `.claude` 本仓已有资产 | 单写者规则、WF1-WF10 流程、WF8 结构化 iteration、template layering | 作为改造基底；controller 只是上层 orchestration，不重写 workflow core | 不允许 controller 自己发明第三套 stage 语义 |

## 7. 总 workstream

### Workstream A：Contract Freeze

目标：先把所有 contract 固定下来，再写代码。

输出物：

- v7 controller schema fixtures
- valid / invalid goal fixtures
- event / lock / round brief / runtime result fixtures
- implementer note（`current_iteration_id`、goal precedence、atomic write 范围）

对应文档：`01_contract_freeze.md`

### Workstream B：Controller + Runtime

目标：落地 Python state machine、runtime adapter、CLI 和 dry_run。

输出物：

- `scripts/auto_iterate_*`
- `scripts/auto_iterate/**`
- `config/*.example.yaml`
- `docs/auto_iterate_goal_template.md`
- `docs/remote_control_guide.md`

对应文档：`02_controller_runtime_plan.md`

### Workstream C：Skill / Prompt / Template Migration

目标：把 `.agents` / `.claude` / template / guide 全部同步到 v7 vocabulary 与 state boundary。

输出物：

- `auto-iterate-goal` skill 与 template
- iterate / evaluate / orchestrator / init-project 同步更新
- stage-report / workflow summary / template carrier 同步更新
- workflow guide 同步更新
- schema / template / README 同步更新

对应文档：`03_skill_and_prompt_migration.md`

### Workstream D：Remote / Account / Ops

目标：定义 V1 的 local-first remote surface、账号 registry、quota/cooldown 行为、后续 proxy 扩展边界。

输出物：

- `config/auto_iterate_accounts.example.yaml`
- `docs/remote_control_guide.md`
- cc-connect mapping note

对应文档：`04_remote_account_ops.md`

### Workstream E：Test / Rollout / Acceptance

目标：建立可重复验证的 contract test matrix 与 rollout gate。

输出物：

- fixture project roots
- unit + integration + chaos-ish tests
- rollout checklist

对应文档：`05_test_rollout_checklist.md`

## 8. 推荐实施顺序

1. 先新增计划中要求的 fixtures 与文档框架，不写 controller 主逻辑。
2. 先把 parser / schema / decision / event / lock / CLI operator surface 的“纯数据契约”做完并测过。
3. 再实现 controller 的 IO primitives、atomic write helper、lock、event logger；这里就应把 event rotation helper 一起做掉，不要拖到最后。
4. 再实现 goal parser、account registry、policy config loader。
5. 再实现 runtime adapter 与 timeout supervision，并冻结 `codex exec` 调用约定。
6. 再实现 repository postcondition validator 与 recovery engine。
7. 从第 2 步之后就并行推进 `.agents` / `.claude` / template 的 vocabulary 同步；不要等 controller 全部完成后才开始。
8. 在 controller 本地 loop 跑通后，做一次仓库级 skill/template/guide semantic sweep，确保 grep/rg 不再命中旧 WF8 核心误导文案。
9. 最后再收 remote guide、account cooldown 策略说明、剩余 docs sync 与 rollout checklist。

## 9. 后续 AI 的执行规约

后续 AI 落地时建议遵守下面的工作方式：

1. 每次只完成一个 workstream 内部的相邻子任务，不要同时重写 controller 和 skill 文案。
2. 任意时候只要需要“猜测” `iteration_log.json` 或 `PROJECT_STATE.json` 的新字段，就回到 `01_contract_freeze.md`，先补 contract 再实现。
3. 在 Codex V1 跑通之前，不要写任何 `auto_iterate_runtime_claude.*` 文件。
4. 在 tests 没有覆盖 `resume`、stale lock、goal activation 之前，不要声称“自动恢复已完成”。
5. 文档同步不能拖到最后一笔提交之后；至少 `.agents` / `.claude` / template 中的 WF8 vocabulary 必须和代码一起更新。
6. remote-ready 不等于 prose-ready；给 wrapper 用的 `status --json`、`tail --jsonl`、exit code 必须在实现期就固定下来并纳入测试。

## 10. 这套计划完成后的定义

如果后续 AI 严格执行完本目录下 5 份子计划，最终应当得到：

- 一套可在项目根目录运行的 Codex-first auto-iterate controller。
- 一套与 controller 一致的 `.agents` / `.claude` WF8 语义层。
- 一套可 resume、可 pause/stop、可 remote-wrap、可 account-switch 的 V1 实现。
- 一套能证明“没有破坏单写者边界”的 contract tests。

剩余历史设计文档（`docs/auto_iterate_and_remote_v2..v7.md`）继续保留为设计演进记录；真正的实施 source of truth 从这一目录开始。
