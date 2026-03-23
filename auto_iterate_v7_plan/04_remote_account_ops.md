# 04. Remote / Account / Ops 计划

本文件定义 V1 的远控与账号边界。重点不是把一切自动化做到最强，而是先让 local-first controller 有一个稳定、可包装、可观察的 operator surface。

## 1. remote 设计原则

### 1.1 local-first

V1 的 source of truth 仍然是本地命令：

- `tooling/auto_iterate/scripts/auto_iterate_ctl.sh start ...`
- `tooling/auto_iterate/scripts/auto_iterate_ctl.sh status`
- `tooling/auto_iterate/scripts/auto_iterate_ctl.sh pause`
- `tooling/auto_iterate/scripts/auto_iterate_ctl.sh stop`
- `tooling/auto_iterate/scripts/auto_iterate_ctl.sh resume`
- `tooling/auto_iterate/scripts/auto_iterate_ctl.sh tail`
- `tooling/auto_iterate/scripts/auto_iterate_ctl.sh override ...`

remote layer 只包装这些命令，不直接修改 runtime state 文件。

### 1.2 remote layer 不拥有 workflow 语义

remote layer 负责：

- transport
- auth
- operator routing
- notification delivery

remote layer 不负责：

- 改 `iteration_log.json`
- 改 `.auto_iterate/state.json`
- 推断是否应该继续下一轮
- 推断 account 是否应该切换

## 2. 与 `cc-connect` 的衔接方式

`cc-connect` 是 v7 指定的 primary remote layer，因此 controller 的命令面必须先为它稳定下来。

### 2.1 V1 集成方式

V1 不要求直接在本仓实现 `cc-connect` 插件，只要求给它一个足够稳定的命令面：

| 远程动作 | 本地命令 |
|---|---|
| 启动 loop | `tooling/auto_iterate/scripts/auto_iterate_ctl.sh start --tool codex --goal docs/auto_iterate_goal.md` |
| 查看状态 | `tooling/auto_iterate/scripts/auto_iterate_ctl.sh status --json` |
| 暂停 | `tooling/auto_iterate/scripts/auto_iterate_ctl.sh pause` |
| 停止 | `tooling/auto_iterate/scripts/auto_iterate_ctl.sh stop` |
| 恢复 | `tooling/auto_iterate/scripts/auto_iterate_ctl.sh resume` |
| 查看事件尾部 | `tooling/auto_iterate/scripts/auto_iterate_ctl.sh tail --jsonl --lines 50` |
| staged goal update | `tooling/auto_iterate/scripts/auto_iterate_ctl.sh override --goal docs/auto_iterate_goal.md` |

### 2.2 为什么先稳 CLI，再谈 chat command

参考 `Reference_tool_repo/cc-connect` 的经验：

- 它最适合包装“明确的本地命令面”
- 不适合包装“聊天里随意修改状态文件”
- 有 webhook / management API / session 管理能力，但这些都应该建立在稳定的本地 entrypoint 之上

因此 V1 的优先级是：

1. 先保证本地 CLI 完整
2. 再写 `tooling/auto_iterate/docs/remote_control_guide.md`
3. 最后才在后续版本中接 `cc-connect` webhook/management API

## 3. V1 远控的 operator 语义

### 3.1 `status`

V1 必须区分 human mode 和 machine mode：

- 默认 `status` 可以是人类可读摘要
- `status --json` 必须是 stable operator contract
- remote wrapper 只能依赖 `--json`，不应解析 prose

`status --json` 至少要稳定输出这几个字段：

- `status`
- `halt_reason`
- `current_round_index`
- `current_phase_key`
- `current_iteration_id`
- `selected_account_id`
- `best.primary_metric`
- `budget.completed_rounds / max_rounds`
- `llm_budget.used_calls / max_calls`
- `last_decision`
- `last_failure`

### 3.2 `tail`

V1 应该基于 `events.jsonl`，不要再单独发明一个 operator log summary 文件。

建议支持：

- 默认尾部 `20` 行
- `--lines N`
- `--jsonl` 直接输出 parseable event lines，供 remote wrapper 直接消费
- 简洁摘要模式如果提供，也只能是 human convenience，不是 remote contract

### 3.3 `pause`

V1 只做 safe boundary pause，不能尝试打断中间的 skill 语义然后“靠猜测恢复”。

### 3.4 `stop`

同上，V1 只做 safe boundary graceful stop。

### 3.5 `override`

V1 远程 override 只允许：

- staged goal update
- 明确的 policy override（如果后续决定开放）

不允许任意 JSON patch。

### 3.6 exit code 与错误处理

remote wrapper 也必须把 exit code 当稳定接口，而不是看 stderr prose 猜原因。

最低要按下面方式消费：

- `0`：命令成功
- `102`：live lock conflict
- `105`：manual action required
- `106`：budget exhausted
- `107`：waiting for account
- `108`：operator pause / resumable interruption
- `109`：fatal controller error

如果 wrapper 需要更细粒度的原因，先读 `status --json`，不要扩展一套聊天内私有状态解释。

## 4. account registry 设计

这里参考 `openclaw-cliproxy-kit` 和 `codex-account-manager`，但不照抄它们的运行方式。

### 4.1 推荐的 `tooling/auto_iterate/config/auto_iterate_accounts.example.yaml`

建议结构：

```yaml
accounts:
  - id: codex_acc1
    codex_home: /home/user/.codex-acc1
    enabled: true
    priority: 100
    cooldown_sec: 1800
    tags: [local, primary]
  - id: codex_acc2
    codex_home: /home/user/.codex-acc2
    enabled: true
    priority: 90
    cooldown_sec: 1800
    tags: [local, backup]
```

可选字段：

- `max_calls_hint`
- `notes`
- `provider`
- `base_url`

但 V1 核心逻辑不应依赖这些可选字段。

### 4.2 为什么不用“全局切号”

`Reference_tool_repo/codex-account-manager` 里的 `switch_account.py` 适合人工切换当前系统账号，但不适合作为 controller V1 的运行中切换方案。原因：

1. 它会写系统级 auth 文件。
2. 它是“切当前环境”，不是“给某个 phase 挑运行账号”。
3. 它不适合并发或多个项目同时跑。

因此 controller 只能做：

- 选择 `account_id`
- 把它映射到 `CODEX_HOME`
- 在子进程环境里运行

### 4.3 quota / rate limit 处理

当 runtime result 给出 `quota_or_rate_limit` 时：

1. controller 标记当前 account cooldown
2. 重新 inspect repository state
3. 先走 phase-specific recovery
4. 确认需要重跑时，再选别的 ready account

绝不能直接换号后“认为上一个 phase 一定没写完”。

## 5. `openclaw-cliproxy-kit` 的借鉴边界

能借鉴的点：

- auth 文件与运行凭证分离
- quota/rate-limit 后切 route 的 operator 思路
- dashboard / logs / config 脱敏视角

V1 不采纳的点：

- 不把 proxy server 设为 controller 必要依赖
- 不把 round-robin 作为默认 routing strategy
- 不把 `cliproxyapi` 的 request-retry 直接搬进 controller phase retry

一句话：V1 只借鉴“账号池管理思维”，不借鉴“统一 API proxy 架构”。

## 6. `codex-account-manager` 的借鉴边界

能借鉴的点：

- 账号 registry 的目录/元信息组织方式
- usage cache 是 operator insight，不是 runtime source of truth
- 项目态与系统态配置分离的思路

V1 不采纳的点：

- 不使用交互式切号
- 不依赖 Web GUI
- 不把缓存用量直接当成 controller budget 依据

controller 的预算 source of truth 仍然是：

- 本轮 runtime invocation 产生的 usage/call 增量
- `state.json.llm_budget`
- `state.json.accounts.by_account[*].used_calls`

## 7. notification 设计

参考 ARIS 和 `cc-connect`，V1 通知策略建议保守：

- 通知失败永远 non-fatal
- 通知只作为 event sink，不回写状态
- 推荐通知节点：
  - loop started
  - round completed
  - new best
  - manual action required
  - loop paused/stopped/failed

V1 不强制实现某个具体通知 provider，但 `tooling/auto_iterate/docs/remote_control_guide.md` 应预留：

- `cc-connect`
- Feishu / Telegram / Slack 这类包装层

## 8. operator runbook 需要覆盖的内容

`tooling/auto_iterate/docs/remote_control_guide.md` 最终至少要讲清楚：

1. 如何启动
2. 如何查看状态
3. 如何暂停与停止
4. 如何 staged 更新 goal
5. 如何在 lock conflict 时判断是 live loop 还是 stale lock
6. 如何在 `waiting_for_account` 时恢复
7. 如何查看 stdout/stderr logs
8. 如何解读 `events.jsonl`

## 9. 未来版本边界

### 9.1 V1 之后可以做的事

- `cc-connect` management API 的直接集成
- 远程 slash command 到 controller subcommand 的原生映射
- dashboard 读取 `.auto_iterate/state.json` 与 `events.jsonl`
- proxy-backed account pool
- 多 provider 选择

### 9.2 V1 明确不做的事

- async pending job adoption
- 远程直接编辑 controller JSON
- cluster scheduler 集成
- mid-phase remote mutation
- 自动跨机器恢复正在运行的外部任务

## 10. 完成判定

remote/account/ops 这一块完成的最低标准：

1. 本地 CLI 足够稳定，远程系统只需包它。
2. `CODEX_HOME` per-process account selection 可配置。
3. quota/rate-limit 后 account cooldown + retry 行为明确。
4. `tooling/auto_iterate/docs/remote_control_guide.md` 足够让后续 AI 或 operator 接 `cc-connect`。
5. 整个 remote/account 方案没有破坏 controller 的 single-writer rule。
