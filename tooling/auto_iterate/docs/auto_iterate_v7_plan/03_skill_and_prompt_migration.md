# 03. `.agents` / `.claude` / Template 迁移计划

本文件解决一个常见漏项：很多实现会把 controller 写出来，但不把现有 workflow 文本、schema、template、guide 同步，最后仓库里留下三套 WF8 语义。

这一步必须和 controller 实现并行推进，不是收尾装饰。

## 1. 迁移原则

### 1.1 双基石同步原则

- `.agents`：V1 Codex runtime 的实际语义基底，必须优先完成。
- `.claude`：V1 虽不提供 runtime adapter，但 vocabulary、state ownership、WF8 loop summary 必须同步。

### 1.2 语义统一，能力分阶段

必须区分两件事：

1. **语义统一**：`NEXT_ROUND`、`auto_mode`、`.auto_iterate/`、screening/full_run、halt_reason 等 vocabulary 必须在 `.agents` 和 `.claude` 同步。
2. **执行能力**：V1 只把 Codex runtime 跑通；Claude runtime 只做“contract alignment”，不宣称可执行 parity。

### 1.3 不允许的迁移方式

- 只更新 `.agents`，不更新 `.claude`
- 只更新 `.claude/Workflow_Guide.md`，不更新 skill schema
- 只更新 `docs/auto_iterate_and_remote_v7.md`，不更新实际 prompt/template
- 在 README 或 template 里继续保留旧的 `CONTINUE→repeat` 之类文案

## 2. 必改文件矩阵

### 2.1 must-change：WF8 核心 skill

| 路径 | 变更级别 | 必改内容 |
|---|---|---|
| `.agents/skills/auto-iterate-goal/SKILL.md` | 高 | 生成 / 校验 / 刷新 `docs/auto_iterate_goal.md`，并明确它是 WF7.5 PASS 后的 bridge skill |
| `.claude/skills/auto-iterate-goal/SKILL.md` | 高 | 同上，但不宣称和 Codex runtime 完全同构 |
| `.agents/skills/iterate/SKILL.md` | 高 | 对齐 v7 phase model、decision enum、auto_mode、screening/full_run 表达、controller coexistence |
| `.claude/skills/iterate/SKILL.md` | 高 | 同上，但需显式声明 Claude runtime parity 不在 V1 范围 |
| `.agents/skills/evaluate/SKILL.md` | 高 | decision recommendation 改成 `NEXT_ROUND | DEBUG | CONTINUE | PIVOT | ABORT` |
| `.claude/skills/evaluate/SKILL.md` | 高 | 同上，并明确 `NEXT_ROUND` 与 `DEBUG` 的边界 |
| `.agents/skills/orchestrator/SKILL.md` | 高 | 识别 `NEXT_ROUND` 为“继续停留 WF8”，不是“进入 WF9” |
| `.claude/skills/orchestrator/SKILL.md` | 高 | 同上；保持 `CONTINUE` 才能进入 WF9 |
| `.claude/skills/init-project/SKILL.md` | 中 | 更新内嵌 WF8 loop summary，避免新项目初始化后继续写出旧 decision 语义 |

### 2.2 must-change：WF8 schema / reference

| 路径 | 变更级别 | 必改内容 |
|---|---|---|
| `.agents/skills/auto-iterate-goal/references/goal-template.md` | 高 | 提供 machine-readable goal 模板，与 controller goal parser 的字段完全对齐 |
| `.claude/skills/auto-iterate-goal/templates/goal-template.md` | 高 | 同上 |
| `.agents/skills/iterate/references/iteration-log-schema.json` | 高 | 加入 `NEXT_ROUND`、`screening.status`、`full_run.status` 新 vocab |
| `.claude/skills/iterate/templates/iteration-log-schema.json` | 高 | 同步 schema |
| `.agents/skills/iterate/references/iteration-context.md` | 中 | 说明 controller 不写 `.agents/state/**`，只读 recovery；保留 local context 行为 |
| `.agents/skills/iterate/references/iteration-constraints.md` | 高 | 用 v7 decision/postcondition vocabulary 重写 obligations |
| `.agents/skills/evaluate/references/stage-report.md` | 高 | recommendation 模板、Next Step 文案、decision matrix 必须支持 `NEXT_ROUND` |
| `.claude/skills/evaluate/templates/stage-report.md` | 高 | 同上，并移除把 `CONTINUE` 当普通继续迭代的暗示 |
| `.agents/skills/orchestrator/references/stage-gates.md` | 中 | WF8 gate 需要解释 `NEXT_ROUND` / `DEBUG` / `CONTINUE` 分流 |

### 2.3 must-change：workflow guide / template / repo-facing docs

| 路径 | 变更级别 | 必改内容 |
|---|---|---|
| `.agents/references/workflow-guide.md` | 高 | WF8 流程图、decision 表、state ownership、controller coexistence |
| `.claude/Workflow_Guide.md` | 高 | 同步 WF8 新语义 |
| `AGENTS.md.template` | 中 | 增加 `.auto_iterate/` controller-owned runtime state 说明 |
| `CLAUDE.md.template` | 中 | 更新 WF8 loop summary，避免旧 decision 误导 |
| `.agents/skills/init-project/references/claude-md-template.md` | 中 | 更新内嵌 WF8 loop summary |
| `.claude/skills/init-project/templates/claude-md-template.md` | 中 | 同上 |

### 2.4 should-change：repo 顶层说明

| 路径 | 变更级别 | 建议内容 |
|---|---|---|
| `README.md` | 中 | 在 workflow capability / roadmap / file ownership 一节加入 auto-iterate v7 的 controller 说明 |
| `docs/feature_plan_auto_iterate_and_remote.md` | 低 | 追加 deprecation note，指向 `tooling/auto_iterate/docs/auto_iterate_v7_plan/` |
| `.agents/skills/final-exp/references/experiment-matrix.md` | 低 | 确认其前置条件文案仍只把 `CONTINUE` 解释为 handoff 到 WF9，不残留“普通继续迭代”语义 |
| `.claude/skills/final-exp/templates/experiment-matrix.md` | 低 | 同上 |

## 3. `iterate` skill 需要怎么改

### 3.1 `.agents/skills/iterate/SKILL.md`

当前问题：

- 还是 wrapper 视角，尚未明确 controller/runtime coexistence。
- `run` 仍是单一子命令语义，未充分映射 `run_screening` / `run_full`。
- `eval` 的 decision 语义还是老四元组。

目标改法：

1. 在 skill 顶部明确：
   - `iteration_log.json` 继续单写者
   - controller 只通过 runtime prompt 间接驱动 `$iterate`
   - controller 不写 `.agents/state/**`
2. 在 `plan` 中加入：
   - `screening.recommended` 的明确写法
   - `round_type` / hypothesis presence 对 controller memory 的支持
3. 在 `run` 中明确：
   - controller 侧 phase key 虽分 `run_screening` / `run_full`，但 skill 表面仍是 canonical `$iterate run`
   - skill 需要根据 prompt/brief 上下文知道自己当前是在跑 screening 还是 full
4. 在 `eval` 中改 decision vocabulary：
   - `NEXT_ROUND`：普通继续下一轮
   - `DEBUG`：问题主要是 bug / stability / failed run
   - `CONTINUE`：退出 WF8，交还 orchestrator
5. 在输出建议命令时：
   - `NEXT_ROUND` -> `Recommended: $iterate plan "..."`
   - `DEBUG` -> `Recommended: $iterate plan "..."`
   - `CONTINUE` -> `Recommended: $orchestrator next`

### 3.2 `.claude/skills/iterate/SKILL.md`

当前问题：

- 文本很完整，但仍是旧 decision 语义。
- 强依赖 Claude 当前交互方式，没有为 v7 的 non-blocking `auto_mode` 留出明确边界。
- 对 V1 scope 的表述会误导实现者以为 Claude runtime 也要一起落地。

目标改法：

1. 保留 manual invocation 能力，但在 `<context>` / `<instructions>` 中新增：
   - v7 decision enum
   - controller coexistence
   - `.auto_iterate/` is controller-owned
   - Claude runtime parity not in V1
2. 把旧的“总是等待用户确认”逻辑改成：
   - `auto_mode=true` 时不允许阻塞提问
   - `MANUAL_ACTION_REQUIRED` 仅用于真正歧义或危险动作
3. 保留 `.claude/current_iteration.json` / `.claude/iterations/**` 的现有兼容行为，但避免把它说成 controller state。

## 3A. `auto-iterate-goal` skill 需要怎么加

这是一个新增 bridge skill，位置不在 controller 里，也不应硬塞进 `validate-run` 本体。

推荐定位：

- 逻辑上位于 `WF7.5 PASS` 之后、`WF8 auto-iterate start` 之前
- 物理上作为独立 skill 存在，供 orchestrator 自动触发
- 产物是 operator-facing source goal：`docs/auto_iterate_goal.md`

推荐子命令：

- `init`
- `refresh`
- `check`

职责边界：

1. 读取已有 workflow 产物：
   - `WF5` baseline / evaluation protocol
   - `WF7.5` validate-run 输出
   - 现有 `docs/auto_iterate_goal.md`（如果存在）
2. 生成或校验 goal 的结构化字段
3. 保持字段与 controller goal parser 完全一致
4. 输出 operator-facing goal 文件，但不直接启动 controller

它不应该：

- 直接写 `.auto_iterate/goal.md`
- 直接写 `.auto_iterate/state.json`
- 直接决定当前 loop 的 resume / stop / pause

默认行为建议：

- `check`：只校验，不改文件
- `init`：当 goal 不存在时生成 `docs/auto_iterate_goal.md`
- `refresh`：当 goal 已存在但需要补字段或更新上下文时生成新版本或 draft；默认不应静默覆盖人工改过的关键目标

推荐字段来源：

- `objective.primary_metric.*`：来自 WF5 protocol / 当前项目 metric 定义
- `screening_policy.*`：来自现有 iterate / validate-run 经验和项目默认值
- `budget.*` / `patience.*`：来自 controller policy defaults + 当前项目阶段约束

一句话：它负责“把 workflow 上下文变成合法 goal 输入”，controller 才负责“消费这个 goal 并驱动 loop”。

## 4. `evaluate` skill 需要怎么改

这是最容易漏改的地方，因为当前很多旧文案直接把 `CONTINUE` 当作“继续迭代”。

### 4.1 决策建议语义重写

后续 AI 在改 `.agents/skills/evaluate/SKILL.md` 和 `.claude/skills/evaluate/SKILL.md` 时，应明确：

- `NEXT_ROUND`
  - 当前 round 有结果，但尚未到 handoff 给 WF9 的时机
  - 适用于普通调参与局部改进
- `DEBUG`
  - 主要问题是实现、稳定性、训练崩溃、评估异常、pipeline 失真
  - 下一轮应优先 debug-oriented
- `CONTINUE`
  - 当前结果已经达到进入 WF9 的条件，或局部 loop 应停止并交还 orchestrator

### 4.2 报告模板影响

per-iteration 报告不一定要改结构，但至少要：

- 在“recommendation”部分支持 `NEXT_ROUND`
- 解释为什么是 ordinary next round 而不是 debug round
- 明确 `CONTINUE` 是 workflow handoff，不是“继续做下一次 iterate”

这条不能只改 skill 主文案，至少要同步：

- `.agents/skills/evaluate/references/stage-report.md`
- `.claude/skills/evaluate/templates/stage-report.md`

## 5. `orchestrator` 需要怎么改

### 5.1 `.agents/skills/orchestrator/SKILL.md`

必须把 WF8 decision gating 改成：

- `CONTINUE` -> 可进 WF9
- `PIVOT` -> rollback WF2
- `ABORT` -> terminate
- `NEXT_ROUND` / `DEBUG` -> 仍留在 WF8，不推进 stage

### 5.2 `.claude/skills/orchestrator/SKILL.md`

当前文件里有大量关于 `CONTINUE / DEBUG / PIVOT / ABORT` 的固定解释，需要统一替换。重点是：

- `DEBUG` 不再是“通用继续迭代”
- `NEXT_ROUND` 才是默认的 local continuation
- `status` 命令在 WF8 时最好能感知 `.auto_iterate/state.json`（如果存在），但仍不能写它

### 5.3 stage gate reference

`stage-gates.md` 需要补充：

- 如果 auto-iterate 正在运行，orchestrator 的 `status` 应报告 loop 状态，但不接管它
- WF8 -> WF9 的 gate 仍然只认最新 completed iteration 的 `decision=CONTINUE`

### 5.4 WF7.5 PASS hook

这是这次新增的关键自动化，不应让用户自己记忆“PASS 之后还要补 goal”。

推荐行为：

```text
WF7.5 validate-run PASS
  -> orchestrator 自动调用 $auto-iterate-goal check
     -> goal 已存在且合法：no-op
     -> goal 不存在：调用 $auto-iterate-goal init
     -> goal 存在但无效/缺字段：调用 $auto-iterate-goal refresh
```

额外建议：

- `refresh` 默认生成更新版或 draft，不要静默覆盖人工改过的目标约束
- orchestrator 可以把状态报告为：
  - `WF8 goal_missing`
  - `WF8 goal_ready`
  - `WF8 auto_iterate_running`
- 是否在 goal ready 后自动执行 `start --goal ...`，应做成显式 policy/config，而不是隐藏副作用

V1 推荐默认：

- 自动 `check/init/refresh`
- 自动把项目推进到 `goal_ready`
- `auto_start_after_goal_ready` 作为可选配置，默认可关闭

## 6. workflow guide 需要怎么改

`.agents/references/workflow-guide.md` 与 `.claude/Workflow_Guide.md` 必须一起更新，不允许一个写 v7 一个写旧 WF8。

最少要改：

1. WF8 流程图：
   - 加 `NEXT_ROUND`
   - 区分 local continuation 与 orchestrator handoff
2. state ownership：
   - 补 `.auto_iterate/` controller-owned runtime state
   - 强调 controller 不写 `iteration_log.json`
3. `run`：
   - 引入 screening/full run under one iteration 的表达
4. recovery：
   - 简要说明 controller resume 来自 `.auto_iterate/state.json` + repo inspection
5. WF7.5 -> WF8 bridge：
   - `validate-run PASS` 后自动执行 goal readiness check
   - `auto-iterate-goal` 负责准备 `docs/auto_iterate_goal.md`
   - `iterate` 仍然是 WF8 core，不改 stage 编号

## 7. `init-project` 与模板需要怎么改

### 7.1 模板中的 WF8 loop summary

下面这些模板里的 WF8 loop summary 必须同步：

- `AGENTS.md.template`
- `CLAUDE.md.template`
- `.agents/skills/init-project/references/claude-md-template.md`
- `.claude/skills/init-project/templates/claude-md-template.md`
- `.claude/skills/init-project/SKILL.md` 中任何直接内嵌的 workflow summary

旧文案：

```text
WF8 iteration loop: ... (CONTINUE->WF9 | DEBUG->repeat | PIVOT->WF2)
```

目标文案应改成类似：

```text
WF8 iteration loop: ... (NEXT_ROUND->repeat | DEBUG->debug round | CONTINUE->WF9 | PIVOT->WF2 | ABORT->stop)
```

### 7.2 `.auto_iterate/` 说明

模板里不需要放很多 runtime 细节，但建议补一条简短说明：

- 如果启用 auto-iterate，`.auto_iterate/` 是 controller-owned runtime state，不要手改。

## 8. 推荐新增的 reference 文档

为了降低 skill 文本继续膨胀，建议在 `.agents` 侧新增 1-2 个 reference note：

- `.agents/skills/iterate/references/auto-iterate-v7-note.md`
  - 说明 controller coexistence
  - 说明 `NEXT_ROUND`
  - 说明 `screening` / `full_run`
- `.agents/skills/evaluate/references/decision-v7-note.md`
  - 解释 `NEXT_ROUND` vs `DEBUG` vs `CONTINUE`

`.claude` 侧不一定要新增对应文件，但至少要在 skill 内部或 template 中同步同一语义。

## 9. 迁移顺序建议

### 顺序 A：先 schema，后 skill

先改：

- `iteration-log-schema.json`
- template / guide 中的 decision vocabulary

再改：

- iterate / evaluate / orchestrator skill 主体

原因：

- 否则 skill 文本会引用一个尚未存在的 schema

### 顺序 B：先 `.agents`，后 `.claude`

Codex V1 先跑通 `.agents` 侧，再做 `.claude` mirror。

但注意：

- `.claude` 的同步不能拖到最后一个提交之后
- 最迟在 controller 本地 loop 跑通后立刻同步 `.claude`

### 顺序 C：每轮改动后跑仓库级搜索验证

这一步不是收尾 polish，而是防止 file matrix 漏项的最低保障。每次完成一批迁移后，至少要跑一次面向仓库的 grep/rg 验证，确认没有残留旧 WF8 核心误导文案。

最低检查面应覆盖：

- `.agents/**`
- `.claude/**`
- `AGENTS.md.template`
- `CLAUDE.md.template`
- 与 WF8 决策直接相连的 stage report / workflow guide / init-project 模板

最低检查模式应覆盖：

- 旧四元 decision enum：`CONTINUE / DEBUG / PIVOT / ABORT`
- 把 `CONTINUE` 写成“继续下一轮”或把 `DEBUG` 写成“默认普通继续迭代”的文案
- iteration-log schema 中仍缺 `NEXT_ROUND`
- stage report / template 中仍缺 `NEXT_ROUND`

允许保留的命中必须是语义正确的场景，例如：

- `CONTINUE` 作为 WF8 -> WF9 handoff
- 历史设计文档或变更说明中的旧文案对比
- 明确在解释“旧语义已废弃”的文本

## 10. 迁移完成判定

只有同时满足下面条件，才算 skill / prompt migration 完成：

1. 仓库中所有 WF8 核心文本都不再把 `CONTINUE` 当作“普通继续迭代”。
2. `.agents` 和 `.claude` 都认识 `NEXT_ROUND`。
3. iterate / evaluate / orchestrator 的语义能彼此闭环。
4. template 中已经向未来项目暴露新的 WF8 vocabulary。
5. 没有任何文档暗示 controller 会写 `iteration_log.json` 或 `PROJECT_STATE.json`。
6. grep/rg 验证已经覆盖 skill、reference、template、guide，且所有残留命中都被人工判定为“历史对比或语义正确引用”，而不是漏改。
7. `WF7.5 PASS -> auto-iterate-goal check/init/refresh -> WF8 goal_ready` 这条桥接链已经在 orchestrator / workflow guide / template 中同步。
