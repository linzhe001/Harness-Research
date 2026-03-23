# 01. Contract Freeze

本文件定义后续实现前必须冻结的 contract。实现阶段不允许再靠口头理解补字段或改语义。

## 1. Freeze 的目标

v7 的核心不是“自动循环”本身，而是把下面几类边界一次性定死：

- 谁写什么文件
- 哪个 phase 成功靠什么 postcondition 判断
- 什么算 recoverable failure
- 什么情况下可以 resume / retry / stop / pause
- 目标文件、事件、brief、result 的 schema 长什么样
- `.agents` / `.claude` / controller / remote layer 共享什么 vocabulary

如果这些 contract 没冻结，后续 AI 很容易犯下面几类错误：

- 用 runtime stdout 猜 phase 是否成功
- 用“最新 iteration”代替 `current_iteration_id` 绑定
- 把 `CONTINUE` 同时当作“继续下一轮”与“退出 WF8”
- 让 remote wrapper 直接改 `state.json`
- 让 controller 在恢复时直接推断 `iteration_log.json` 的含义

## 2. 必须冻结的 artifact 清单

### 2.1 controller-owned runtime files

必须冻结以下文件的路径、writer、atomicity：

| 路径 | sole writer | 作用 | 是否必须原子替换 |
|---|---|---|---|
| `.auto_iterate/state.json` | running controller | durable loop state | 是 |
| `.auto_iterate/lock.json` | running controller | single-active-loop lock + heartbeat | 是 |
| `.auto_iterate/events.jsonl` | running controller | append-only event log | 否（按行 append），rotation 时必须原子 rename |
| `.auto_iterate/goal.md` | controller / `start` | active goal snapshot | 是 |
| `.auto_iterate/goal.next.md` | controller / `override` | staged goal snapshot | 是 |
| `.auto_iterate/runtime/*_brief.json` | running controller | controller->runtime normalized brief | 是 |
| `.auto_iterate/runtime/*_result.json` | runtime adapter | transport result metadata | 是 |
| `.auto_iterate/runtime/*.stdout.log` | runtime adapter | stdout log | 否 |
| `.auto_iterate/runtime/*.stderr.log` | runtime adapter | stderr log | 否 |
| `.auto_iterate/logs/controller.log` | running controller | controller operator log | 否 |

### 2.2 project-owned canonical files

这些文件只允许 controller 读，不允许 controller 写：

| 路径 | sole writer | controller 权限 |
|---|---|---|
| `iteration_log.json` | `iterate` | read-only |
| `PROJECT_STATE.json` | `orchestrator` + stage skill | read-only |
| `.agents/state/**` | Codex skill runtime | recovery inspection only |
| `.claude/**/current_iteration.json` / `.claude/iterations/**` | Claude skill runtime | V1 不写 |

## 3. v7 需要冻结的 vocabulary

### 3.1 phase family / phase key

必须统一使用下面两级枚举：

- `phase_family`: `plan | code | run | eval`
- `phase_key`: `plan | code | run_screening | run_full | eval`

所有 controller 文件必须写 `phase_key`，不能用旧的 `current_phase=run` 之类模糊值。

### 3.2 run type

当 `phase_family=run` 时，必须同时有：

- `run_type=screening`
- 或 `run_type=full`

`run_screening` 和 `run_full` 不是两个 iteration，它们是同一个 iteration 下的两类 run record。

### 3.3 WF8 decision enum

v7 的 canonical WF8 decision 必须冻结为：

- `NEXT_ROUND`
- `DEBUG`
- `CONTINUE`
- `PIVOT`
- `ABORT`

解释必须一起冻结：

- `NEXT_ROUND`：在当前 active goal 下进入下一轮普通改进
- `DEBUG`：进入下一轮，但下一轮默认 debug-oriented
- `CONTINUE`：结束 local loop，交还外层 orchestrator，进入 WF9
- `PIVOT`：结束 local loop，交还 orchestrator，回到 WF2
- `ABORT`：结束 local loop，终止项目方向

### 3.4 controller halt reason

WF8 decision 和 controller halt reason 不能混用。`halt_reason` 必须独立冻结为：

- `target_met`
- `max_rounds_reached`
- `patience_exhausted`
- `gpu_budget_exhausted`
- `llm_budget_exhausted`
- `manual_stop`
- `operator_pause`
- `waiting_for_account`
- `workflow_continue`
- `workflow_pivot`
- `workflow_abort`
- `manual_action_required`
- `fatal_controller_error`

## 4. `iteration_log.json` 的 v7 delta

`iteration_log.json` 仍然由 `iterate` 写，但后续 AI 在改 skill 和 schema 时必须同步到以下目标形态。

### 4.1 必须出现的 iteration-level 字段

最少要稳定存在：

- `id`
- `date`
- `hypothesis`
- `status`
- `screening`
- `full_run`
- `lessons`
- `decision`

### 4.2 `screening` contract

最少字段：

```json
{
  "recommended": true,
  "status": "passed"
}
```

冻结要求：

- `recommended` 由 `plan` 产生
- `status` 枚举为 `passed | failed | skipped`
- `run_screening` postcondition 只看 repository 里这个结构是否成立

### 4.3 `full_run` contract

最少字段：

```json
{
  "status": "completed",
  "resume_mode": "from_scratch",
  "metrics": {
    "primary_metric_name": 0.91
  }
}
```

冻结要求：

- `status` 枚举为 `completed | recoverable_failed | failed`
- `resume_mode` 是 repository-visible 字段，不是 controller 内存字段
- `metrics` 只放 protocol-defined tracked metrics

### 4.4 postcondition 的 phase 对应关系

| phase_key | 成功条件 |
|---|---|
| `plan` | 相比 pre-snapshot 恰好新增 1 个 `status=planned` 的 iteration，且包含 required plan fields |
| `code` | 同一 `current_iteration_id` 进入 `status=training`，且 `git_commit`、`git_message` 存在 |
| `run_screening` | `screening.status` 成为 `passed | failed | skipped` |
| `run_full` | `full_run.status` 成为 `completed | recoverable_failed | failed` |
| `eval` | `status=completed`，有 finalized metrics，恰好 1 个 WF8 decision，至少 1 条 lesson |

### 4.5 `current_iteration_id` 绑定算法

这个点必须独立冻结，因为它是 v7 专门要消灭的猜测源。

算法必须是：

1. `plan` 启动前读取 `iteration_log.json`，记下 `existing_ids`。
2. `plan` 结束后重新读取 `iteration_log.json`，生成 `new_ids = ids_after - existing_ids`。
3. `len(new_ids)` 必须等于 `1`，否则 `plan` 视为 `postcondition_failed`。
4. 这个唯一新增 id 就是 `current_iteration_id`。
5. controller 将其写入 `.auto_iterate/state.json`。
6. 后续 `code / run_screening / run_full / eval` 一律只围绕这个 id 验证，不允许“取最新一条”。

## 5. goal contract 必须冻结的部分

### 5.1 source goal 可接受的格式

只允许两类输入：

1. 推荐 markdown heading + structured field lines
2. embedded YAML / front matter machine-readable block

明确禁止：

- 从任意自然语言段落做 NLP 抽取
- 允许两个来源互相冲突还继续运行

### 5.2 extracted schema

goal parser 输出的 schema 必须冻结为至少包含：

- `objective.primary_metric.name`
- `objective.primary_metric.direction`
- `objective.primary_metric.target`
- `objective.constraints[]`
- `patience.max_no_improve_rounds`
- `patience.min_primary_delta`
- `budget.max_rounds`
- `budget.max_gpu_hours`（当启用 GPU budget）
- `screening_policy.enabled`
- `screening_policy.threshold_pct`
- `screening_policy.default_steps`

### 5.3 precedence

在 `start` 时冻结下面的优先级：

1. CLI overrides
2. validated source goal extracted schema
3. controller policy config
4. doc defaults
5. account registry（仅用于 account selection）

并且在 `start` 之后：

- 运行态一律读 `.auto_iterate/state.json`
- `resume` 不允许重新从原始 goal path 取值

### 5.4 staged activation

goal update 必须冻结为“两阶段提交”：

1. `override --goal <path>`：只写 `.auto_iterate/goal.next.md`
2. 下一轮边界、且下一次 `plan` 前：重新校验 `goal.next.md`
3. 校验通过后：
   - 覆盖 `.auto_iterate/goal.md`
   - 一次性更新所有 goal-derived frozen fields
4. 校验失败：
   - emit `GOAL_ACTIVATION_FAILED`
   - `status=paused`
   - `halt_reason=manual_action_required`

### 5.5 goal continuity

V1 必须冻结“不能跨 metric identity 激活”的规则：

- `objective.primary_metric.name` 不能变
- `objective.primary_metric.direction` 不能变

变了就 pause，不允许自动 reset best / patience。

## 6. round brief contract

后续 AI 在实现前应先把 valid / invalid brief fixture 落地。

必须稳定的字段：

- `schema_version`
- `loop_id`
- `round_index`
- `phase_family`
- `phase_key`
- `run_type`
- `tool`
- `auto_mode`
- `recovery_mode`
- `round_type`
- `objective`
- `current_best`
- `recent_lessons`
- `failed_hypotheses`
- `budget_status`
- `screening_policy`
- `timeouts`

### 6.1 `recovery_mode`

枚举必须冻结为：

- `normal`
- `retry`
- `resume`

### 6.2 version policy

- V1 只接受 `schema_version=1`
- adapter 遇到不兼容 brief version 必须 exit `200`
- controller 不做 auto-upgrade

### 6.3 Codex runtime invocation interface

这一层也要在实现前冻结，避免后续 AI 在 `codex` 调用方式上各写一套。

V1 的规范是：

- runtime adapter 必须调用 non-interactive 子命令 `codex exec`
- prompt 必须经 stdin 传入，而不是依赖 shell-escaped 单字符串参数
- adapter 必须显式指定 workspace root，而不是依赖调用时 cwd 猜测
- adapter 必须以 non-interactive approval policy 运行；不允许等待人工批准
- stdout/stderr 必须分别落到 runtime log 文件
- `--output-last-message` 之类的最终消息文件可以作为诊断产物，但不是 phase success proof
- `--json` 事件流如果使用，只能作为附加 observability；controller 不得把它当 repository postcondition

换句话说：V1 冻结的是“`codex exec` + stdin prompt + non-interactive policy + file-captured transport output”这一接口形态，而不是任由实现者选择交互式 `codex` 或不同 prompt transport。

## 7. runtime result contract

runtime result file 是 transport metadata，不是 phase success proof。

必须冻结的字段：

- `schema_version`
- `phase_family`
- `phase_key`
- `run_type`
- `account_id`
- `started_at`
- `finished_at`
- `duration_sec`
- `exit_code`
- `runtime_exit_class`
- `failure_reason`
- `timed_out`
- `stdout_path`
- `stderr_path`

### 7.1 `runtime_exit_class`

冻结为：

- `success`
- `quota_or_rate_limit`
- `auth_failure`
- `interactive_block`
- `timeout`
- `interrupted`
- `internal_error`

## 8. controller state / lock / events contract

### 8.1 `state.json`

必须至少冻结这些顶层字段：

- `schema_version`
- `loop_id`
- `status`
- `tool`
- `current_round_index`
- `current_phase_key`
- `current_iteration_id`
- `phase_attempt`
- `goal`
- `objective`
- `best`
- `patience`
- `budget`
- `llm_budget`
- `accounts`
- `last_decision`
- `halt_reason`
- `last_failure`

### 8.1.1 budget / account 子结构也必须冻结

至少要稳定到下面这个粒度：

- `budget.max_rounds`
- `budget.completed_rounds`
- `budget.gpu_count`
- `budget.max_gpu_hours`
- `budget.used_gpu_hours`
- `budget.tracking_method`
- `llm_budget.max_calls`
- `llm_budget.used_calls`
- `llm_budget.max_cost_usd`
- `llm_budget.used_cost_usd`
- `llm_budget.tracking_method`
- `accounts.selected_account_id`
- `accounts.by_account`

预算 source of truth 也要冻结：

- GPU budget 统一按 `wall_time_hours * gpu_count` 做 conservative accounting
- `gpu_count` 是 controller policy input，不从训练日志或外部平台回推
- LLM usage 如果拿不到精确 provider metadata，必须记录 estimate，并写清 `tracking_method`
- `llm_budget.used_calls` 必须等于 `accounts.by_account[*].used_calls` 之和
- controller 不应把 wandb、训练脚本 stdout、usage cache 等外部系统当作 budget durable source of truth

### 8.2 `lock.json`

最少要有：

- `schema_version`
- `loop_id`
- `pid`
- `host`
- `started_at`
- `heartbeat_at`
- `tool`
- `workspace_root`

stale lock 规则也要冻结：

- heartbeat 超过 policy threshold 即视为 stale candidate
- `resume` 负责清 stale lock 并发 `STALE_LOCK_CLEARED`
- live lock conflict 返回 exit `102`

### 8.3 `events.jsonl`

每行一个 JSON object，字段固定为：

- `v`
- `ts`
- `event`
- `loop_id`
- `status`
- optional `round_index`
- optional `phase_key`
- optional `payload`

最低事件集必须在实现前冻结完：

- `LOOP_STARTED`
- `LOOP_RESUMED`
- `ROUND_STARTED`
- `ROUND_COMPLETED`
- `PHASE_STARTED`
- `PHASE_COMPLETED`
- `PHASE_FAILED`
- `PHASE_TIMEOUT`
- `SCREENING_BYPASSED`
- `SCREENING_FAILED`
- `SCREENING_PASSED`
- `NEW_BEST`
- `BUDGET_WARNING`
- `MANUAL_ACTION_REQUIRED`
- `ACCOUNT_SWITCHED`
- `GOAL_STAGED`
- `GOAL_ACTIVATED`
- `GOAL_ACTIVATION_FAILED`
- `LOOP_PAUSED`
- `LOOP_STOPPED`
- `LOOP_FAILED`
- `RECOVERY_APPLIED`
- `STALE_LOCK_CLEARED`
- `EVENT_LOG_ROTATED`

rotation 规则也要一起冻结：

- rotation 只能发生在 round boundary，或 loop 当前不处于 `running`
- rotation archive path 必须稳定写入 `EVENT_LOG_ROTATED.payload`
- rotation rename 必须原子完成
- 如果 archive/rename 失败，但当前 `events.jsonl` 仍可继续 append，这次 rotation 视为 non-fatal warning，不能因此丢事件
- 如果 rotation 失败后连 active append 都无法保证 durable logging，才升级为 controller error

### 8.4 operator CLI surface contract

remote wrapper 不应解析 prose，因此 `status` 和 `tail` 的结构化模式必须冻结。

`status`：

- 必须支持 `status --json`
- 输出至少包含：
  - `schema_version`
  - `loop_id`
  - `status`
  - `halt_reason`
  - `current_round_index`
  - `current_phase_key`
  - `current_iteration_id`
  - `accounts.selected_account_id`
  - `objective.primary_metric.name`
  - `best.primary_metric`
  - `budget.completed_rounds`
  - `budget.max_rounds`
  - `llm_budget.used_calls`
  - `llm_budget.max_calls`
  - `last_decision`
  - `last_failure`
- human-readable 默认输出可以存在，但不是 remote contract

`tail`：

- 必须支持 `tail --jsonl`
- `tail --jsonl` 直接返回 `events.jsonl` 的尾部事件行，不重新包装第二套 schema
- 至少支持 `--lines N`
- 如果还提供简洁摘要模式，摘要只面向人类，不是 remote contract

### 8.5 CLI exit code contract

controller exit code space 必须冻结为：

- `0`：success
- `100`：invalid arguments
- `101`：invalid controller state
- `102`：lock conflict
- `103`：goal validation failed
- `104`：runtime invocation failed
- `105`：manual action required
- `106`：budget exhausted
- `107`：waiting for account
- `108`：resumable interruption or operator pause
- `109`：fatal controller error

额外规则：

- `paused` / `stopped` / `failed` 是 durable state，不等于进程 exit code
- remote wrapper 只能依赖这组冻结后的 exit code，不应从 stderr prose 猜状态

## 9. recovery contract 必须冻结的部分

### 9.1 phase boundary persistence

controller 必须在两个时刻持久化：

1. phase launch 前
2. phase postcondition validated 后

### 9.2 `phase_attempt`

规则必须固定：

- 同一 `phase_key` 每次 launch 前自增
- 切换到新 `phase_key` 后 reset 为 `1`
- 默认 `retry_policy.max_phase_attempts=2`
- 超上限则 pause 为 `manual_action_required`

### 9.3 phase-specific recovery

| phase_key | recovery rule |
|---|---|
| `plan` | 没有新 planned iteration 就 rerun；若恰好 1 个候选 planned iteration 已出现则 adopt |
| `code` | `planned` 或 `coding` 都 rerun；若已到 `training` 且 commit 完整则 adopt |
| `run_screening` | screening record 缺失且 iteration 仍 `training` 则 rerun；有 terminal screening 就 adopt |
| `run_full` | 无 `full_run` 且 iteration `training` 则 rerun；`recoverable_failed` 且未超 retry ceiling 则 rerun；`completed` 或 `failed` 则 adopt |
| `eval` | 无 decision / lesson 则 rerun；若 iteration 已 `completed` 则 adopt |

## 10. 原子写入矩阵

实现前必须明确所有 temp-write + atomic rename 范围：

| 文件类型 | 必须原子写 | 原因 |
|---|---|---|
| `state.json` | 是 | 避免 resume 读到半写状态 |
| `lock.json` | 是 | 避免 heartbeat / owner 信息损坏 |
| `goal.md` / `goal.next.md` | 是 | staged activation 不能看到半写 goal |
| `*_brief.json` | 是 | adapter 读取前必须完整 |
| `*_result.json` | 是 | controller 读取前必须完整 |
| `events.jsonl` active append | 否 | append-only 可接受；rotation rename 必须原子 |
| `stdout/stderr log` | 否 | 流式输出 |

## 11. Contract Freeze 输出物建议路径

后续 AI 应优先把下面这些 fixture 路径建立起来：

- `tests/fixtures/auto_iterate/contracts/state.valid.json`
- `tests/fixtures/auto_iterate/contracts/state.invalid.schema_version.json`
- `tests/fixtures/auto_iterate/contracts/lock.valid.json`
- `tests/fixtures/auto_iterate/contracts/brief.valid.plan.json`
- `tests/fixtures/auto_iterate/contracts/brief.invalid.run_type_mismatch.json`
- `tests/fixtures/auto_iterate/contracts/result.valid.success.json`
- `tests/fixtures/auto_iterate/contracts/goal.valid.md`
- `tests/fixtures/auto_iterate/contracts/goal.invalid_metric_change.md`
- `tests/fixtures/auto_iterate/contracts/events.sample.jsonl`
- `tests/fixtures/auto_iterate/contracts/IMPLEMENTER_NOTES.md`

## 12. Freeze 完成判定

只有满足下面条件，才能进入 controller 编码阶段：

1. 上述 schema 和 vocabulary 全部有 fixture 或明确文档落点。
2. `current_iteration_id` 绑定算法有单独 implementer note。
3. goal precedence、goal activation、atomic write 范围已写死。
4. `NEXT_ROUND` 与 `halt_reason` 的区别已在文档中说清。
5. `.agents` / `.claude` / controller 共享的 WF8 vocabulary 已统一。

如果这 5 条有任何一条没完成，controller 实现阶段就应该暂停。
