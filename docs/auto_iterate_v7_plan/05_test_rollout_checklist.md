# 05. 测试、Rollout 与验收清单

本文件把 v7 的 contract test matrix 转成可执行的测试与 rollout 计划。目标不是“把测试写多”，而是确保不会出现看起来能跑、实际把 workflow 语义打穿的实现。

## 1. 测试资产布局建议

建议新增：

```text
tests/
  fixtures/
    auto_iterate/
      contracts/
      project_minimal/
      project_screening_failed/
      project_recoverable_failed/
      project_goal_pending/
  test_auto_iterate_contracts.py
  test_auto_iterate_goal_parser.py
  test_auto_iterate_controller_fsm.py
  test_auto_iterate_recovery.py
  test_auto_iterate_runtime_adapter.py
```

### 1.1 fixture project root 至少需要什么

每个 fixture project root 建议最少包含：

- `CLAUDE.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `docs/`
- `scripts/`（可以是 fake train/eval）
- `.agents/` / `.claude/` 最小必要子集，或通过测试逻辑 mock 掉

目的不是模拟完整研究项目，而是给 postcondition validator / recovery engine 一个真实 filesystem 语境。

## 2. 单元测试层

### 2.1 contract / schema

必须测试：

1. brief schema version reject
2. result schema valid/invalid
3. state schema valid/invalid
4. lock schema valid/invalid
5. goal parser duplicate/conflict reject

### 2.2 parser / helper

必须测试：

1. `current_iteration_id` 绑定
2. `recent_lessons` flatten + dedupe
3. `failed_hypotheses` insertion conditions
4. atomic write helper 不会留下 partial file
5. event rotation helper

### 2.3 decision / transition

必须测试：

1. `NEXT_ROUND` -> `status=running`
2. `DEBUG` -> `status=running`
3. `CONTINUE` -> `status=stopped`, `halt_reason=workflow_continue`
4. `PIVOT` -> `status=stopped`, `halt_reason=workflow_pivot`
5. `ABORT` -> `status=stopped`, `halt_reason=workflow_abort`

## 3. 集成测试层

这里对应 v7 明写的 contract test matrix，需要逐条映射到测试。

### 3.1 runtime / brief 契约

| 测试项 | 说明 |
|---|---|
| adapter rejects inconsistent `phase_key` vs `run_type` | 如 `phase_key=run_full` 但 `run_type=screening` |
| adapter rejects incompatible `schema_version` | brief schema version 非 1 |
| runtime result file is atomic | 不能读到半写 JSON |

### 3.2 controller / repo postcondition 契约

| 测试项 | 说明 |
|---|---|
| controller accepts valid postcondition for each phase | `plan/code/run_screening/run_full/eval` 全部覆盖 |
| controller rejects runtime success when postcondition missing | stdout 成功但 repo state 不成立 |
| screening-bypassed phase order correct | `run_screening` 被跳过时 event 与 phase order 正确 |

### 3.3 recovery / stale lock / retry

| 测试项 | 说明 |
|---|---|
| stale lock detection and cleanup | 过期 heartbeat 可以清理 |
| resume reconstructs state after crash during each phase | 每个 phase 各测一例 |
| retry ceiling on `recoverable_failed` | 超 ceiling 后 pause 为 `manual_action_required` |
| heartbeat worker death escalates to fatal controller error | 主进程仍活着但 heartbeat worker 死掉 |

### 3.4 goal / budget / manual action

| 测试项 | 说明 |
|---|---|
| staged goal activates only at round boundary | 中途 override 不影响当前 round |
| goal activation fails on metric identity change | name/direction 变化 |
| LLM budget exhaustion stops with correct halt reason | 下一 phase 会超预算 |
| `MANUAL_ACTION_REQUIRED` pause + resume path | pause 后 resume 能继续 |
| `WF7.5 PASS` auto-triggers goal readiness flow | `check/init/refresh` 链路正确，不靠用户手动记忆 |
| existing goal is not silently overwritten by refresh hook | 人工修改过的目标约束不会被无提示覆盖 |

### 3.5 CLI / operator contract

| 测试项 | 说明 |
|---|---|
| `status --json` returns stable machine-readable fields | remote wrapper 不需要解析 prose |
| `tail --jsonl --lines N` returns parseable event lines | 直接复用 `events.jsonl` contract |
| controller exit codes stay mapped to documented meanings | 至少覆盖 `101/102/105/106/107/108/109` |

## 4. 手工 smoke 测试层

自动测试之外，后续 AI 完成实现后，至少还要做下面这些手工 smoke：

1. `start --goal ...` 在最小 fixture 上跑通。
2. `WF7.5 PASS` 后若缺 goal，会自动生成合法的 `docs/auto_iterate_goal.md`。
3. `WF7.5 PASS` 后若 goal 已合法，不会重复覆盖。
4. `status` 返回字段完整且可读。
5. `tail` 能看到 event 增长。
6. `pause` 在下一个 phase boundary 生效。
7. `stop` 在下一个 phase boundary 生效。
8. `override --goal` 生成 `goal.next.md`，但当前 round 不受影响。
9. 人工 kill controller 后 `resume` 成功。
10. 模拟 quota/rate-limit 后切到备用 account。

## 5. chaos-ish 测试建议

V1 不需要复杂 chaos framework，但至少要模拟这几类“脏情况”：

1. 写一半的 result 临时文件存在，但最终 result 文件不存在。
2. `lock.json` 存在但 pid 已死。
3. `events.jsonl` 超阈值，需要 rotation。
4. `goal.next.md` 存在，但内容不合法。
5. runtime stdout 很大，stderr 为空。
6. `full_run.status=recoverable_failed` 连续两次。
7. heartbeat worker 被显式终止。

## 6. rollout 阶段设计

### Gate 0：文档与 fixture freeze

必须完成：

- 本目录 5 份计划文档
- contract fixture 初版
- file inventory 与变更范围确认

没过 Gate 0，不准写 main controller loop。

### Gate 1：controller primitives 可测

必须完成：

- atomic write helper
- lock manager
- event logger
- goal parser
- brief/result schema validator

过 Gate 1 的标准：

- unit tests 通过
- 没有业务逻辑耦合到 shell wrapper

### Gate 2：dry_run 可跑

必须完成：

- CLI + state machine 骨架
- fake runtime / dry_run
- status/pause/stop/override 基本面

过 Gate 2 的标准：

- 不需要真实 Codex 即可走完整控制流

### Gate 3：真实 Codex phase smoke

必须完成：

- runtime adapter
- timeout supervision
- postcondition validator
- phase transition

过 Gate 3 的标准：

- 至少一个 local fixture/real sample 项目能跑一轮

### Gate 4：recovery / retry / account

必须完成：

- resume
- stale lock cleanup
- retry ceiling
- account cooldown / switching

过 Gate 4 的标准：

- 中途 kill + resume 成功
- recoverable failure 行为符合预期

### Gate 5：skill / template / guide sync

必须完成：

- `.agents`
- `.claude`
- template
- README / docs sync
- `auto-iterate-goal`

过 Gate 5 的标准：

- 已执行 grep/rg 验证，覆盖 `.agents`、`.claude`、template、guide、stage-report 等高风险文本面
- 仓库中再搜索不到旧 WF8 核心误导文案，或剩余命中已明确标记为历史对比/废弃说明
- `NEXT_ROUND` 已出现在 iterate/evaluate/orchestrator/schema/template 的全部必要位置

### Gate 6：remote-ready

必须完成：

- `remote_control_guide.md`
- local CLI 完整
- event/log/operator 输出稳定

过 Gate 6 的标准：

- `cc-connect` 或其他包装层不需要直接写 state 文件

## 7. 验收 checklist

后续 AI 在准备结束这次改造时，建议逐条勾选：

- [ ] `iteration_log.json` 仍然只由 `iterate` 写
- [ ] `PROJECT_STATE.json` 仍然不被 controller 写
- [ ] `.auto_iterate/state.json` / `lock.json` / runtime result 都是原子写
- [ ] `NEXT_ROUND` 已成为 canonical WF8 decision
- [ ] `DEBUG` 不再承担普通继续迭代语义
- [ ] `CONTINUE` 明确只表示 handoff 给 orchestrator
- [ ] `run_screening` / `run_full` 被显式表示为同 iteration 下的两类 run
- [ ] goal staged activation 已实现
- [ ] goal metric identity change 会阻止激活
- [ ] `resume` 不依赖 chat history
- [ ] stale lock cleanup 已实现
- [ ] heartbeat worker 已实现
- [ ] timeout supervision 已实现
- [ ] retry ceiling 已实现
- [ ] account switching 使用 `CODEX_HOME` per-process
- [ ] remote layer 不直接改 state 文件
- [ ] `.agents` 与 `.claude` 的 WF8 vocabulary 已同步
- [ ] `WF7.5 PASS -> auto-iterate-goal check/init/refresh` 已形成稳定 bridge
- [ ] template 已更新到新 WF8 summary
- [ ] `status --json` / `tail --jsonl` 已形成稳定 operator contract
- [ ] tests 覆盖 contract matrix 的关键项
- [ ] `remote_control_guide.md` 足够支持后续接 `cc-connect`

## 8. 回滚策略

如果 rollout 过程中发现实现有问题，回滚原则如下：

1. 优先关闭 auto-iterate 入口，而不是回滚已有手动 WF8 能力。
2. 保持旧手动 `/iterate` 流程仍然可用。
3. 不回滚 `.agents` / `.claude` 的单写者约束。
4. 如果 controller 尚不稳定，可以暂时不启用 `start` / `resume`，但不应留下半同步的 decision vocabulary。

换句话说，最坏情况允许“controller 暂时不可用”，不允许“workflow 语义半新半旧”。

## 9. 最终交付标准

本次 v7 改造可以视为真正完成，当且仅当：

1. 文档、skill、schema、script、tests 五个层面都同步到同一套 vocabulary。
2. 本地 Codex V1 可运行、可恢复、可暂停、可停止。
3. 远控包装层只需调用稳定 CLI，不需要理解内部状态细节。
4. 后续 AI 不需要再回头读 v2-v7 历史设计文档，就能基于本计划继续实现和维护。
