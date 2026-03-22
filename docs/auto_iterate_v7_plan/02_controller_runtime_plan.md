# 02. Controller / Runtime 实施计划

本文件只讨论脚本与运行态实现，不再重新定义 contract。凡是字段或语义问题，回 `01_contract_freeze.md`。

## 1. 目标产物

V1 必须新增以下文件：

```text
scripts/
  auto_iterate_ctl.sh
  auto_iterate_ctl.py
  auto_iterate_controller.py
  auto_iterate_runtime_codex.sh
  auto_iterate_runtime_codex.py

config/
  auto_iterate_controller.example.yaml
  auto_iterate_accounts.example.yaml

docs/
  auto_iterate_goal_template.md
  remote_control_guide.md
```

另外建议新增：

```text
scripts/
  auto_iterate/
    __init__.py
    controller.py
    state.py
    lock.py
    events.py
    goal.py
    policy.py
    accounts.py
    postcondition.py
    recovery.py
    runtime.py

tests/
  fixtures/auto_iterate/
  test_auto_iterate_*.py
```

## 2. 文件职责拆分

### 2.1 `scripts/auto_iterate_ctl.sh`

职责只保留三件事：

1. 稳定外部入口，供 shell / remote wrapper / `cc-connect` 调用。
2. 定位 repo root、Python 解释器、脚本路径。
3. 把参数原样转发给 `auto_iterate_ctl.py`。

不要把业务逻辑写进 `.sh`。否则测试、重构、remote 包装都会变差。

### 2.2 `scripts/auto_iterate_ctl.py`

这是 CLI 前门，不是完整状态机本体。

建议职责：

- argparse / subcommand parsing
- config loading bootstrap
- repo root / workspace root normalization
- dry_run 开关解析
- 调用 `auto_iterate_controller.py` 暴露的 API
- 统一 exit code 映射
- `status --json` / `tail --jsonl` 这种 operator contract 的模式开关解析

建议子命令：

- `start`
- `status`
- `pause`
- `stop`
- `resume`
- `tail`
- `override`

可选但有价值：

- hidden/test-only `--workspace-root`
- hidden/test-only `--dry-run`

### 2.3 `scripts/auto_iterate_controller.py`

这是 V1 的核心状态机，但不建议把全部实现永久堆在单文件里。

建议从第一版就把真实逻辑放进 `scripts/auto_iterate/` 包；`scripts/auto_iterate_controller.py` 保留为薄兼容入口或 import shim。这样做的原因很简单：lock / events / goal / recovery / postcondition 都是天然可测的 primitives，不值得先耦合进一个 1500+ 行的大文件再拆。

建议的包内逻辑对象映射：

- `LoopController`
- `StateStore`
- `LockManager`
- `EventLogger`
- `GoalManager`
- `PolicyConfig`
- `AccountRegistry`
- `PostconditionValidator`
- `RecoveryEngine`
- `HeartbeatWorker`
- `PhaseSupervisor`

建议最小方法面：

- `start_loop()`
- `resume_loop()`
- `pause_loop()`
- `stop_loop()`
- `status()`
- `stage_goal_override()`
- `tail_events()`
- `run_main_loop()`
- `run_one_phase()`
- `advance_after_phase()`
- `apply_decision_transition()`
- `check_stop_conditions()`
- `check_operator_signals()`
- `activate_pending_goal_if_needed()`
- `select_account_for_phase()`
- `record_runtime_usage()`
- `handle_phase_failure()`
- `recover_from_state()`

### 2.4 `scripts/auto_iterate_runtime_codex.sh`

仍然只做 thin wrapper：

- 接受 canonical args：`--phase-key --brief --account --result`
- 导出必要 env（如 `CODEX_HOME`）
- 调用 `auto_iterate_runtime_codex.py`

### 2.5 `scripts/auto_iterate_runtime_codex.py`

职责：

1. 读取 brief
2. 校验 brief schema/version
3. 渲染 phase prompt
4. 以 non-interactive 方式启动 Codex
5. 采集 stdout/stderr/exit/timestamps
6. 写 result file

它不应该：

- 直接写 `.auto_iterate/state.json`
- 直接写 `iteration_log.json`
- 自己判断 repository postcondition

### 2.5.1 Codex invocation freeze

这一块不要留到实现中“边试边定”。V1 直接冻结为：

- 调用非交互入口 `codex exec`
- prompt 通过 stdin 传入
- 明确指定 workspace root
- approval policy 必须是 non-interactive，不允许卡在人工批准
- stdout/stderr 分别重定向到 runtime log
- 可选写出 final message 文件，但 controller 不依赖它判成功

推荐调用形态应接近：

```text
codex [global non-interactive approval flags] exec \
  --cd <workspace_root> \
  --sandbox workspace-write \
  --output-last-message <final_message_path> \
  -
```

实现注意点：

- 不要调用裸 `codex` 进入交互式 TUI
- 不要把长 prompt 作为单个 shell 参数传进去
- 不要把 `--json` 事件流当成 success oracle；它最多是 observability 辅助
- 如果本机 CLI 需要用全局 flag 而不是 subcommand flag 指定 approval policy，也必须保持这一冻结语义不变

## 3. 推荐的内部实现顺序

### Phase 1A：底座 primitives

先实现这些无业务猜测的基础设施：

- JSON 原子写 helper
- file lock / stale lock helper
- event append / rotation helper
- timestamp / duration helper
- temp file path helper
- `state.json` load / validate / save
- `lock.json` load / validate / save

交付判定：

- 能独立测试 atomic write
- 能独立测试 lock acquire / stale cleanup / conflict
- 能独立测试 event append / rotation
- 能独立测试 `status --json` / `tail --jsonl` 的最小 schema

### Phase 1B：goal 与 policy bootstrapping

第二步实现：

- goal parser
- goal validator
- goal snapshot copier
- goal staged activation
- controller policy config loader
- accounts registry loader

交付判定：

- `start --goal` 能冻结 active goal 到 `.auto_iterate/goal.md`
- `override --goal` 能只写 `.auto_iterate/goal.next.md`
- metric identity 变更会被阻止

### Phase 1C：runtime adapter

第三步实现：

- brief renderer
- prompt renderer
- Codex invocation wrapper
- runtime result writer
- timeout-aware supervisor 接口

交付判定：

- `run_screening` / `run_full` brief 结构正确
- adapter 会拒绝 invalid brief
- result file 原子写成立
- `codex exec` 调用约定已被 fixture / 测试固定，不再依赖实现者口头约定

### Phase 1D：main loop / phase machine

第四步实现：

- `ROUND_STARTED` / `PHASE_STARTED`
- phase launch 前持久化
- postcondition validator
- phase 结束后 transition
- retry / recoverable failure
- WF8 decision mapping

交付判定：

- dry_run 能跑通一轮 phase sequence
- `NEXT_ROUND` / `DEBUG` / `CONTINUE` / `PIVOT` / `ABORT` 行为正确

### Phase 1E：resume / stale lock / retry ceiling

第五步实现：

- `resume`
- phase-specific recovery
- stale lock cleanup
- retry ceiling
- `MANUAL_ACTION_REQUIRED`

交付判定：

- 中途 kill 后可以 `resume`
- 超 retry ceiling 会 pause，不会 silent loop

### Phase 1F：operator surface

最后补：

- `status`
- `tail`
- `pause`
- `stop`
- `override`
- `waiting_for_account`

交付判定：

- local operator 面完整
- remote wrapper 可直接复用

## 4. loop 执行骨架

建议后续 AI 严格实现为下面这个骨架，而不是边写边拼：

```text
start/resume
  -> acquire lock
  -> load/freeze state
  -> start heartbeat worker
  -> emit LOOP_STARTED / LOOP_RESUMED
  -> while status == running:
       -> if at round boundary:
            -> check stop/pause signals
            -> activate pending goal if any
            -> enforce budget/account preconditions
            -> emit ROUND_STARTED
       -> persist state before phase launch
       -> build brief
       -> select account
       -> launch runtime with timeout supervision
       -> inspect runtime result (transport only)
       -> validate repository postcondition
       -> update state / budgets / events
       -> transition to next phase or stop/pause/fail
  -> persist terminal state
  -> release lock
```

## 5. phase 顺序与 branching

### 5.1 canonical round sequence

固定顺序：

1. `plan`
2. `code`
3. optional `run_screening`
4. optional `run_full`
5. `eval`

### 5.2 screening bypass 规则

必须在 controller 层执行，而不是 runtime adapter 层执行：

- `screening_policy.enabled=false` -> 直接跳 `run_full`
- `screening_policy.enabled=true` 但 plan 写出 `screening.recommended=false` -> 直接跳 `run_full`
- bypass 时 emit `SCREENING_BYPASSED`

### 5.3 full run 失败分类

controller 对 `run_full` 的后处理必须分清：

- `completed` -> 进入 `eval`
- `recoverable_failed` -> 先走 retry/recovery policy
- `failed` -> 仍然进入 `eval`

## 6. postcondition validator 设计

postcondition validator 不应混在 CLI 或 runtime adapter 里，建议做成独立组件。

### 6.1 validator 的输入

- pre-phase state snapshot
- current `.auto_iterate/state.json`
- current `iteration_log.json`
- current `PROJECT_STATE.json`（只读）
- latest runtime result（可选，仅 transport diagnosis）

### 6.2 validator 的输出

建议统一输出结构：

```json
{
  "ok": true,
  "phase_key": "run_full",
  "classification": "completed",
  "iteration_id": "iter8",
  "payload": {
    "full_run_status": "completed"
  }
}
```

或

```json
{
  "ok": false,
  "phase_key": "code",
  "classification": "postcondition_failed",
  "iteration_id": "iter8",
  "payload": {
    "missing_fields": ["git_commit"]
  }
}
```

这样 controller 才能统一处理 `PHASE_FAILED`、retry、manual action required。

## 7. timeout 与 heartbeat 设计

### 7.1 timeout ownership

timeout 明确属于 controller，不属于 runtime。

默认值直接使用 v7：

- `plan=1800`
- `code=3600`
- `run_screening=14400`
- `run_full=28800`
- `eval=1800`

### 7.2 terminate sequence

必须按这个顺序：

1. timeout 到达
2. 发 graceful interrupt
3. 等 `terminate_grace_sec`
4. 仍存活则强制 terminate
5. emit `PHASE_TIMEOUT`
6. 按 phase failure 路径分类

### 7.3 heartbeat worker

必须单独实现，不要依赖“每轮都会刷新所以够了”：

- 至少每 30s 刷一次 `heartbeat_at`
- phase launch 前立即刷
- phase validated 后立即刷
- phase wait 期间持续刷

如果 heartbeat worker 死掉而主 controller 还活着：

- 立即 `status=failed`
- `halt_reason=fatal_controller_error`
- emit `LOOP_FAILED`

## 8. account 选择逻辑

账号逻辑属于 controller，不属于 runtime adapter。

### 8.1 V1 选择原则

V1 只做 deterministic safe selection：

1. 先看 `selected_account_id` 是否仍 `ready`
2. 否则从 enabled account 中选一个：
   - 未 cooldown
   - 未被标记 auth_failure
   - `used_calls` 相对更少
3. 切换后写入 `state.json.accounts.selected_account_id`
4. emit `ACCOUNT_SWITCHED`

### 8.2 绝对不要做的事

- 不改全局 `~/.codex/auth.json`
- 不在 phase 中途切账号再“接着跑”
- 不把 openclaw / cliproxy 的 round-robin 当成 V1 默认策略

## 9. `start` / `resume` / `pause` / `stop` / `override` 细化

### 9.1 `start`

必须做：

1. 校验 lock 冲突
2. 校验 goal
3. 冻结 policy + objective + budgets + screening_policy
4. 创建 `.auto_iterate/`
5. 写 `state.json`
6. 写 `goal.md`
7. 创建 lock
8. 进入 loop

### 9.2 `resume`

必须做：

1. 读 `state.json` / `lock.json`
2. 判断 live lock conflict 还是 stale lock
3. stale 时清 lock 并 emit `STALE_LOCK_CLEARED`
4. 做 phase-specific recovery
5. 重新 acquire lock
6. `status` 回到 `running`
7. emit `LOOP_RESUMED`

### 9.3 `pause`

V1 只做 graceful boundary pause：

- 写 `.auto_iterate_pause`
- running controller 在 safe phase boundary 消费它
- 更新 `status=paused`
- `halt_reason=operator_pause`

### 9.4 `stop`

V1 只做 graceful boundary stop：

- 写 `.auto_iterate_stop`
- running controller 在 safe phase boundary 消费它
- 更新 `status=stopped`
- `halt_reason=manual_stop`

### 9.5 `override`

`override` 只允许做两类事：

- staged goal update
- policy override（如果 CLI 允许）

不允许：

- 直接改 `current_phase_key`
- 直接改 `current_iteration_id`
- 直接改 `best`

## 10. prompt renderer 设计

runtime adapter 的 prompt 不要散落在 shell 里。建议放在 `auto_iterate_runtime_codex.py` 里的固定模板函数中。

每个 prompt 必须显式包含：

- 当前 canonical `$iterate <phase_family>` 语义
- 当前 `phase_key`
- `iteration_log.json` 是 source of truth
- `auto_mode=true` 时不可阻塞提问
- postcondition 必须满足后才能声称成功

额外建议：

- prompt 中嵌入 brief 的结构化摘要，而不是全文 dump
- 对 `run_screening` / `run_full` 使用不同模板
- `eval` prompt 要明确区分 `NEXT_ROUND` vs `DEBUG` vs `CONTINUE`

## 11. `dry_run` 的定义

`dry_run` 不是“假装成功”，而是“不调用真实 Codex，但完整走 controller 状态迁移与验证壳”。

V1 的 `dry_run` 应该做到：

- 校验参数
- 校验 goal / policy / account registry
- 创建 lock
- 写 state / event
- 构造 brief
- 调用 fake runtime / stub result
- 跑 postcondition validator 的测试壳
- 验证 pause / stop / override / stale lock 行为

`dry_run` 不应该：

- 写 `iteration_log.json`
- 写 `PROJECT_STATE.json`
- 发真实训练或真实 Codex 会话

## 12. 需要先落地的配置样例

### 12.1 `config/auto_iterate_controller.example.yaml`

至少包含：

- `llm_budget.max_cost_usd`
- `llm_budget.max_calls`
- `budget.gpu_count`
- `timeouts.*`
- `retry_policy.max_phase_attempts`
- `terminate_grace_sec`
- `event_log.rotate_bytes`

### 12.2 `config/auto_iterate_accounts.example.yaml`

至少包含：

- `accounts[].id`
- `accounts[].codex_home`
- `accounts[].enabled`
- `accounts[].priority`
- `accounts[].cooldown_sec`
- `accounts[].tags`

## 13. 完成判定

controller/runtime 实现完成的最低标准：

1. `start` 能在 fixture project 上跑通一轮完整 phase 序列。
2. `resume` 能从 mid-phase kill 恢复。
3. `run_full.status=recoverable_failed` 能触发 retry ceiling。
4. `pause` / `stop` / `override` 都通过边界生效，不直接改 state。
5. timeout、heartbeat、stale lock、event rotation 有测试覆盖。

少任何一项，都还不能进入“远控已完成”的叙述。
