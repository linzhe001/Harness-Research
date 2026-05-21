# Stage Permission Elevation Guide

本文说明 Harness Codex hooks 中的 Stage 权限提升模型: 为什么要这样做、这次具体改了哪些文件、执行链路如何流动、每个 skill 的写入边界是什么、后续新增或修改 Stage 权限时应该如何检查。

当前采用方案 B:

```text
ordinary implementation code
  -> $code-debug
  -> src/, scripts/, configs/, project_map.json

Harness guardrails
  -> $harness-maintenance
  -> hooks, skill contracts, skill routing/triggers, permission docs/tests
```

也就是说, `$code-debug` 不再承担 hook、skill、contract 或 permission policy
维护职责。这些 guardrail 变更统一进入 `$harness-maintenance`。

术语遵循 `.agents/references/ubiquitous-language.md`。特别是 `Evidence`
不能再作为单一概念使用:

```text
Conclusion Evidence -> 支持 claim / fact / idea / protocol choice 的来源链
Gate Evidence       -> 支持 command / review / approval check / gate 的执行结果
```

## 目标

旧的解释容易把 `docs/10_contract/**`, `docs/20_facts/**`, `docs/30_evidence/**` 等 docs 层当作权限入口。更准确的模型是:

```text
Stage / skill 激活
  |
  v
获得该 Stage 的临时写入权限
  |
  v
只允许写入这个 Stage 声明的 write scope
  |
  v
required reads, forbidden actions, Gate ledger, human approval 继续约束
```

也就是说, `docs/**` 不是永久可写或永久不可写。某个 Stage 进入 active contract 后, 才临时获得一组窄写入面。
这里的 `forbidden actions` 和 `required actions` 是 contract / gate 义务,
不是通用动作解释器。Hook runtime 只硬编码执行一部分边界, 例如 required
read set、tool-owned path block、`code-review` review-only 和 path-aware
write scope。

## 修改摘要

本次改动涉及以下几类文件:

| 文件 | 作用 |
| --- | --- |
| `schemas/skill_contracts.json` | 给每个 skill contract 显式声明 `write_scope.allowed_paths` |
| `schemas/skill_contracts.schema.json` | 要求 skill contract 包含 `write_scope.allowed_paths` 字段 |
| `tooling/codex_hooks/harness_contracts.py` | 在 `PreToolUse` 中执行 Stage 写入 scope 检查, 并把 hook/skill/permission 修改请求推断到 `$harness-maintenance` |
| `tooling/.tests/test_codex_hooks_contracts.py` | 覆盖 scope 内允许、scope 外阻止、缺失 `write_scope` fail-closed、`code-debug` 不能写 hooks、`harness-maintenance` 可以写 guardrails |
| `.agents/skills/harness-maintenance/` | Codex 侧 guardrail 维护 skill |
| `.claude/skills/harness-maintenance/` | Claude Code 侧语义对齐的 guardrail 维护 skill |
| `.agents/references/ubiquitous-language.md` | workflow skill 的通用语言 |
| `workflow_handbook/Workflow_Operator_Handbook.md` | operator 低负担入口 |
| `tooling/codex_hooks/generate_stage_cards.py` | 从 `schemas/skill_contracts.json` 生成 Stage Cards；版本化 operator 快照保存在 `workflow_handbook/Workflow_Stage_Cards.md` |
| `tooling/codex_hooks/README.md` | 记录 Stage permission elevation、方案 B 路由和 operator-facing 解释 |

## 数据结构

本仓库里的每个 contract 必须声明:

```json
{
  "skill": "validate-run",
  "write_scope": {
    "allowed_paths": [
      "docs/Validate_Run_Report.md",
      "PROJECT_STATE.json"
    ]
  }
}
```

当前仓库规则:

```text
schema / check_contracts
  -> 要求每个 contract 都有 write_scope.allowed_paths
  -> 要求每个 contract 声明 artifact_outputs

PreToolUse
  -> 对可解析写入路径使用 write_scope.allowed_paths 作为 Stage 写入面
```

运行时代码不再使用 `sensitive_paths` 作为 `write_scope` fallback。缺失
`write_scope.allowed_paths` 是 contract 错误; 对 path-aware writes, hook 会
fail closed, 而不是临时退回到 `sensitive_paths`。

`artifact_outputs` 是输出落点语义, 不是权限提升:

```json
{
  "artifact_outputs": [
    {
      "kind": "current_doc",
      "paths": ["docs/40_iterations/"],
      "owner": "iterate",
      "is_final": true,
      "requires_tool": false
    }
  ]
}
```

这层元数据把 final docs、canonical state、tool traces、review traces、
implementation files、guidance 和 release packages 分开。Stage Cards 会把
`Final outputs` 和 `Can write` 分开展示。权限仍只来自 hard `active_skill`
和 `write_scope.allowed_paths`; `artifact_outputs` 不授予 Write Scope。

当前 prompt intent 模型也把上下文提示和硬合约分开:

```text
active_skill    -> hard Skill Contract, 可在 Read Contract 完成后使用 Write Scope
candidate_skill -> advisory context, 不授予 Write Scope
```

`enforcement_mode` 取值:

| Mode | 含义 |
| --- | --- |
| `none` | 没有 workflow Skill |
| `context_only` | 讨论/解释/设计问题, 只保留候选上下文 |
| `active_read` | status/review/read-mode hard contract, 只能写声明的 read-mode artifact |
| `active_write` | 明确执行或写入请求, 按 Read Contract 和 Write Scope 执行 |

裸 `WF<N>` 和 `DEBUG`/`PIVOT`/`CONTINUE` 等 Decision vocabulary 是
action-gated trigger。问题句不会激活 hard contract; Stage lifecycle 语言路由到
`$orchestrator`; WF10 loop action 才路由到 `$iterate`。

## 执行链路

```text
User prompt
  |
  v
UserPromptSubmit
  |
  +-- detect active skill / Stage
  +-- write .harness_hooks/session.json
  |
  v
Tool call
  |
  v
PreToolUse
  |
  +-- reject direct external review scripts
  +-- reject untrusted .evidence/** or .auto_iterate/** manual writes
  +-- load active contract
  +-- require active contract read set before writes
  +-- apply code-review review-only boundary
  +-- apply Stage write scope boundary to path-aware writes
      (missing write_scope => fail closed)
  |
  v
Tool executes only if not denied
  |
  v
PostToolUse
  |
  +-- record reads
  +-- record mutating tool activity
  +-- mark sensitive changed paths as pending Gate ledger
  |
  v
Stop
  |
  +-- require missing read set if needed
  +-- require Gate ledger if sensitive workflow files changed
```

## Enforcement 规则

### 1. Path-aware writes are checked

这些写入会被 Stage scope 精确检查:

- `apply_patch`
- `Edit`
- `Write`
- external review wrapper 的可解析 output path

准确地说, `write_scope.allowed_paths` 是可解析写入路径的硬边界。它不是
OS 级 sandbox, 也不能证明不可解析 Bash mutation 没有写出边界。

示例:

```text
active skill: validate-run
allowed scope:
  - docs/Validate_Run_Report.md
  - PROJECT_STATE.json

attempt:
  - README.md

result:
  PreToolUse deny
```

`Edit` / `Write` 如果直接指向 `.evidence/**` 或 `.auto_iterate/**`, 会在
Stage scope 检查之前被阻止。这两个目录是工具或 controller 托管路径, 不能用
普通编辑工具手工写入。

### 2. Complex Bash is not treated as fully scoped

复杂 Bash mutation 可能无法可靠解析目标路径, 例如:

```bash
python -c "open(dynamic_path, 'w').write(...)"
find docs -name '*.md' -exec sh -c '...' \;
cmd_a && cmd_b > maybe_path
```

这类命令不应该被误认为已经由 Stage scope 精确保护。当前策略是:

- 继续阻止明显的 `.evidence/**` / `.auto_iterate/**` 手工写入。
- 如果实际变更命中 active contract 的 `sensitive_paths`, 继续通过
  `PostToolUse` / `Stop` 要求 Gate ledger。
- 不把不可解析 Bash 当作 path-aware proof。

## Stage 权限矩阵

这张表是 operator 视角的简表。对可解析写入路径的精确执行以
`schemas/skill_contracts.json` 中每个 skill 的
`write_scope.allowed_paths` 为准; 对不可解析 Bash, 它是 contract 语义边界,
不是完整的路径证明。

| Stage / skill | 临时写入面 | 主要边界 |
| --- | --- | --- |
| `init-project` / WF0 | `CLAUDE.md`, `AGENTS.md`, `OPERATOR_CONTEXT.md`, `PROJECT_STATE.json`, `docs/**`, `.evidence/**` scaffold | 不能推断 operator preferences; `.evidence/**` 应由 `tooling/evidence/init_context.py` 等工具生成 |
| `survey-idea` / WF1 | `docs/30_evidence/**`, `docs/Feasibility_Report.md`, `docs/35_protocol/**` | Conclusion Evidence 不是 approved contract; protocol draft 需要 review |
| `idea-debate` / WF2 | `docs/Idea_Debate.md`, `docs/35_protocol/**` | reviewer independence, protocol drift |
| `refine-idea` / WF3 | `docs/Refined_Idea.md`, `docs/35_protocol/**` | 不提前写 architecture decision |
| `data-prep` / WF4 | `docs/Dataset_Stats.md`, `docs/20_facts/**`, `docs/30_evidence/Dataset_Table.md`, `configs/**`, `src/**`, `CLAUDE.md`, `AGENTS.md` | dataset facts 必须来自 artifacts/commands |
| `baseline-repro` / WF5 | `docs/Baseline_Report.md`, `docs/30_evidence/Baseline_Table.md`, `docs/10_contract/**`, `docs/20_facts/Codebase_Map.md`, `baselines/**`, `configs/**`, `scripts/**`, `src/**` | semantic commit, dynamic gates, codebase map sync when baseline layout changes, contract human approval |
| `refine-arch` / WF6 | `docs/Technical_Spec.md`, `docs/20_facts/Project_Glossary.md`, `docs/35_protocol/**` | architecture 必须服从 approved contracts 和 protocol drift |
| `build-plan` / WF7 | `docs/Implementation_Roadmap.md`, `docs/20_facts/Codebase_Map.md`, `project_map.json`, `PROJECT_STATE.json` | project map 和 codebase map 不能 stale |
| `code-expert` / WF8 | `src/**`, `scripts/**`, `configs/**`, `project_map.json`, `docs/20_facts/Codebase_Map.md`, `PROJECT_STATE.json` | required reads, py_compile/ruff, project map/codebase map sync |
| `code-debug` | `src/**`, `scripts/**`, `configs/**`, `project_map.json`, `docs/20_facts/Codebase_Map.md` | ordinary implementation code only; hooks/skills/contracts 不在此 scope |
| `validate-run` / WF9 | `docs/Validate_Run_Report.md`, `docs/30_evidence/Validation_Table.md`, `PROJECT_STATE.json` | 没有 semantic review 和 smoke evidence 不能 PASS |
| `iterate` / WF10 | `iteration_log.json`, `docs/40_iterations/**`, legacy `docs/iterations/**`, `docs/50_memory/**`, `MEMORY.md` | decision vocabulary, lesson quality, WF11 handoff |
| `auto-iterate-goal` | `docs/auto_iterate_goal.md`; `.auto_iterate/**` 由 controller 拥有 | goal validation 才能启动 unattended controller |
| `final-exp` / WF11 | `docs/Final_Experiment_Matrix.md`, `PROJECT_STATE.json` | approved contracts 和 claim boundary |
| `release` / WF12 | `submission/**`, `docs/**`, `PROJECT_STATE.json` | release claims 必须在 `Claim_Boundary.md` 内 |
| `code-review` | `.agents/state/review_traces/code-review/**` | review-only; 代码修复转 `$code-debug`, guardrail 修复转 `$harness-maintenance` |
| `harness-maintenance` | `tooling/codex_hooks/**`, `schemas/**`, `.agents/skills/**`, `.agents/references/**`, `.claude/Workflow_Guide.md`, `.claude/skills/**`, `.claude/rules/**`, `.claude/shared/**`, `tooling/model_api/**`, `tooling/.tests/**`, `templates/**`, `docs/**`, `workflow_handbook/**`, root framework docs | hooks、skill contracts、trigger/routing、permission policy、trust/status、guardrail tests/docs |
| `review-packet` | `.evidence/review_packets/<stage>/<build_id>/**`, 相关合同/状态审批记录 | packet 不是 approval; approval 必须来自明确 human decision |

## Skill 权限参考

下面是当前 `schemas/skill_contracts.json` 中每个 skill 的精确
`write_scope.allowed_paths`。目录以 `/` 结尾时表示该目录树。

| Skill | `write_scope.allowed_paths` | 说明 |
| --- | --- | --- |
| `orchestrator` | `PROJECT_STATE.json`, `iteration_log.json`, `project_map.json` | 只移动 workflow 状态和索引, 不写阶段产物正文 |
| `doc-compiler` | `docs/10_contract/`, `docs/20_facts/`, `docs/35_protocol/`, `.evidence/chains/`, `.evidence/index.json` | current docs 与 evidence chain; `.evidence` 内容应由 evidence tooling 生成 |
| `review-packet` | `.evidence/review_packets/`, `docs/10_contract/`, `PROJECT_STATE.json` | 生成审查包和记录审批状态; packet 本身不是 approval |
| `protocol-compiler` | `.evidence/protocol_compiler/`, `docs/35_protocol/` | 生成 protocol draft 和编译痕迹 |
| `protocol-drift-check` | `docs/35_protocol/`, `docs/10_contract/` | 记录 protocol/contract drift 结果, 不批准 contract |
| `survey-idea` | `docs/Feasibility_Report.md`, `docs/30_evidence/`, `docs/35_protocol/`, `PROJECT_STATE.json` | 早期可行性和证据草案 |
| `idea-debate` | `docs/Idea_Debate.md`, `docs/35_protocol/`, `PROJECT_STATE.json` | 记录 debate 和 protocol draft 调整 |
| `refine-idea` | `docs/Refined_Idea.md`, `docs/35_protocol/`, `PROJECT_STATE.json` | 收敛 idea, 不写实现计划 |
| `data-prep` | `docs/Dataset_Stats.md`, `docs/20_facts/`, `docs/30_evidence/Dataset_Table.md`, `PROJECT_STATE.json`, `CLAUDE.md`, `AGENTS.md`, `configs/`, `src/` | 数据事实、Conclusion Evidence 表、配置和必要的数据处理代码 |
| `baseline-repro` | `docs/Baseline_Report.md`, `docs/30_evidence/Baseline_Table.md`, `docs/10_contract/`, `docs/20_facts/Codebase_Map.md`, `PROJECT_STATE.json`, `project_map.json`, `CLAUDE.md`, `baselines/`, `configs/`, `scripts/`, `src/` | 建立第一条可运行 baseline、Conclusion Evidence 表和 contract |
| `refine-arch` | `docs/Technical_Spec.md`, `docs/35_protocol/`, `PROJECT_STATE.json` | 架构设计受 approved contracts 约束 |
| `deep-check` | `docs/Sanity_Check_Log.md`, `docs/35_protocol/`, `docs/10_contract/` | 深度 sanity check, 不直接进入实现 |
| `evaluate` | `iteration_log.json`, `docs/40_iterations/`, legacy `docs/iterations/`, `docs/50_memory/`, `MEMORY.md`, `docs/Stage_Report.md` | 评估和记忆沉淀; observation 不应直接跳到 MEMORY |
| `init-project` | `CLAUDE.md`, `AGENTS.md`, `OPERATOR_CONTEXT.md`, `PROJECT_STATE.json`, `docs/`, `.evidence/` | bootstrap guidance/context; `.evidence` 目录用工具初始化 |
| `env-setup` | `CLAUDE.md`, `requirements.txt`, `requirements-dev.txt`, `environment.yml`, `environment.yaml`, `pyproject.toml`, `scripts/`, `configs/` | 环境声明和启动脚本 |
| `build-plan` | `project_map.json`, `PROJECT_STATE.json`, `docs/20_facts/Codebase_Map.md`, `docs/Implementation_Roadmap.md` | 规划实现, 生成机器 map 和人读 codebase map |
| `code-expert` | `src/`, `scripts/`, `configs/`, `project_map.json`, `docs/20_facts/Codebase_Map.md`, `PROJECT_STATE.json` | 从 roadmap 做首轮实现并同步 stable map |
| `code-debug` | `src/`, `scripts/`, `configs/`, `project_map.json`, `docs/20_facts/Codebase_Map.md` | 普通实现代码修复; 不写 hooks、skills、contracts、permission docs |
| `harness-maintenance` | `schemas/`, `.agents/skills/`, `.agents/references/`, `.claude/Workflow_Guide.md`, `.claude/skills/`, `.claude/rules/`, `.claude/shared/`, `tooling/codex_hooks/`, `tooling/model_api/`, `tooling/.tests/`, `templates/`, `docs/`, `workflow_handbook/`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `AI_AGENT_SETUP.md` | 维护 hooks、skill contract、routing/trigger、permission policy、trust/status、guardrail 测试和文档 |
| `code-review` | `.agents/state/review_traces/code-review/` | review-only; subject files 只读, 代码修复转 `$code-debug`, guardrail 修复转 `$harness-maintenance` |
| `validate-run` | `docs/Validate_Run_Report.md`, `docs/30_evidence/Validation_Table.md`, `PROJECT_STATE.json` | 记录 WF9 验证结果; PASS 需要 smoke/semantic evidence |
| `iterate` | `iteration_log.json`, `docs/40_iterations/`, legacy `docs/iterations/`, `docs/50_memory/`, `MEMORY.md` | WF10 loop 状态和 lessons |
| `auto-iterate-goal` | `docs/auto_iterate_goal.md` | 只写 operator-facing goal; `.auto_iterate/**` 由 controller 拥有 |
| `final-exp` | `docs/Final_Experiment_Matrix.md`, `PROJECT_STATE.json` | 最终实验矩阵必须在 claim boundary 内 |
| `release` | `submission/`, `docs/`, `PROJECT_STATE.json` | 发布材料和状态; claims 不能越过 `Claim_Boundary.md` |

需要特别注意:

- `write_scope` 是允许写入面, 不是审批。human approval 仍要来自当前对话或可审计 artifact。
- `sensitive_paths` 仍用于 Gate ledger/change detection, 可以比 `write_scope` 更宽。例如 `code-review` 的敏感目标包括 subject files, 但允许写入面只有 review trace。
- `.evidence/**` 和 `.auto_iterate/**` 是工具托管区域。即使某个 skill 的 logical output 在 `.evidence/**`, 普通 `Edit`/`Write`/手工 patch 仍不应直接改它。
- `required_actions` 和 `forbidden_actions` 是 contract/gate 义务清单。
  `validate_contract_files()` 会校验这些 action 名称是否已知, 但 hook
  不会把它们当作通用动作语言逐条解释执行。
- `code-debug` 和 `harness-maintenance` 是两个不同的提权面:
  `code-debug` 负责实现代码, `harness-maintenance` 负责 Harness guardrails。
  即使 prompt 中出现 `fix` 或 `debug`, 只要语义是在改 hook、skill、
  trigger/routing 或 permission policy, 检测逻辑应推断为
  `$harness-maintenance`。

## 新增或修改 Stage 权限的步骤

1. 找到或新增对应 skill contract:

```text
schemas/skill_contracts.json
```

2. 确认 trigger 能稳定激活该 Stage:

```json
"triggers": ["$validate-run", "/validate-run", "validate run", "WF9"]
```

3. 确认写入前必须读取的文件在 `required_read_set` 中:

```json
"required_read_set": {
  "harness": ["..."],
  "skill": ["..."],
  "project_when_present": ["AGENTS.md", "PROJECT_STATE.json"],
  "project_optional": ["..."]
}
```

4. 声明最小写入面。当前仓库中这是必填字段:

```json
"write_scope": {
  "allowed_paths": [
    "docs/Validate_Run_Report.md",
    "PROJECT_STATE.json"
  ]
}
```

5. 配置 `sensitive_paths`。它主要用于 Gate ledger/change detection, 不等同于允许写入面:

```json
"sensitive_paths": [
  "docs/Validate_Run_Report.md",
  "PROJECT_STATE.json"
]
```

`write_scope.allowed_paths` 应该比 `sensitive_paths` 更接近“当前 Stage 真正允许写什么”。
`sensitive_paths` 可以更宽, 用来发现需要 Gate ledger 的 subject files 或状态文件变化。

6. 更新 required actions / forbidden actions / Gate ledger 条件。这些字段用于
   描述该 skill 的 gate obligations, 不是通用 runtime action interpreter:

```json
"required_actions": ["semantic_review", "smoke_test_or_NOT_RUN", "gate_ledger"],
"forbidden_actions": ["WF9_PASS_without_semantic_review", "WF9_PASS_without_smoke_evidence"],
"gate_ledger_required_when": ["WF10_readiness", "validate_report_write"]
```

7. 为新行为加测试:

- scope 内写入应允许。
- scope 外写入应 deny。
- missing required reads 仍应优先阻止。
- `code-review` 仍保持 review-only。
- `.evidence/**` 和 `.auto_iterate/**` 手工写入仍应被阻止。

## 检查清单

### Contract 检查

- [ ] `skill` 名称与 `.agents/skills/<skill>/SKILL.md` 一致。
- [ ] `triggers` 不会误触发普通路径名或文件名。
- [ ] `required_read_set.skill` 包含 `.agents/skills/<skill>/SKILL.md`。
- [ ] `required_read_set.project_when_present` 包含 `AGENTS.md`。
- [ ] `write_scope.allowed_paths` 是最小必要写入面, 且每个 contract 都声明了它。
- [ ] 缺失 `write_scope.allowed_paths` 时 path-aware writes 会 fail closed, 不回退到 `sensitive_paths`。
- [ ] `sensitive_paths` 的用途是 Gate ledger/change detection, 与 `write_scope` 的允许写入面职责清楚。
- [ ] `required_actions` 都是 `harness_contracts.py` 已知 action。
- [ ] `forbidden_actions` 都是 `harness_contracts.py` 已知 forbidden action。
- [ ] `gate_ledger_required_when` 覆盖所有高风险写入。

### Hook 行为检查

- [ ] Stage 激活后, scope 内 `apply_patch` 可以通过。
- [ ] Stage 激活后, scope 外 `apply_patch` 会被 deny。
- [ ] `Edit` / `Write` 的 path 字段会被检查。
- [ ] external review wrapper 的 output path 会被检查。
- [ ] missing required reads 仍在写入前阻止。
- [ ] `code-review` 只能写 `.agents/state/review_traces/code-review/**`。
- [ ] direct external model scripts 仍被阻止, 必须走 wrapper。
- [ ] `.evidence/**` / `.auto_iterate/**` 手工 patch、`Edit`、`Write` 仍被阻止。
- [ ] 命中 active contract `sensitive_paths` 的实际变更会触发 pending Gate ledger。
- [ ] Stop hook 会在 pending Gate ledger 缺失时 block。

### Operator 流程检查

- [ ] Stage 提权只在 active skill/session 内有效。
- [ ] Stage 写入权限不等于 human approval。
- [ ] review packet 不等于 approval。
- [ ] contract approval 必须来自当前对话或可审计 artifact 中的明确 human decision。
- [ ] release claim 必须受 `Claim_Boundary.md` 约束。

## 必跑验证命令

修改 hooks、contracts 或 schema 后运行:

```bash
python -m py_compile tooling/codex_hooks/harness_contracts.py tooling/.tests/test_codex_hooks_contracts.py
ruff check --select=E,F,I tooling/codex_hooks/harness_contracts.py tooling/.tests/test_codex_hooks_contracts.py
python tooling/codex_hooks/check_contracts.py --workspace-root .
pytest tooling/.tests/test_codex_hooks_contracts.py
python tooling/codex_hooks/simulate_hook.py UserPromptSubmit --workspace-root . --event-json '{"prompt":"帮我修改 hook的判断和触发"}'
python tooling/codex_hooks/simulate_hook.py UserPromptSubmit --workspace-root . --event-json '{"prompt":"帮我修改 Python 模块中的数据处理逻辑"}'
python tooling/codex_hooks/hook_status.py --workspace-root . --trust-status
```

如果需要检查安装和 trust 状态一起通过:

```bash
python tooling/codex_hooks/check_contracts.py --workspace-root . --hook-status --trust-status
```

## 已知边界

1. Hooks 是 runtime guardrail, 不是 proof。

```text
hooks can show:
  -> observed read/write tool events
  -> blocked boundary violations
  -> pending Gate ledger requirements

hooks cannot prove:
  -> claims are true
  -> contracts are approved
  -> experiments are valid
```

2. Stage scope 是路径级 guardrail, 不是 OS 级 sandbox。

Codex sandbox 仍应保持:

```toml
sandbox_mode = "workspace-write"
approval_policy = "on-request"

[sandbox_workspace_write]
network_access = false
writable_roots = []

[features]
hooks = true
```

3. `danger-full-access` 不应作为默认方案。

只有在外部环境已经隔离, 且 operator 明确接受 hooks 成为唯一剩余边界时, 才考虑使用 `danger-full-access`。

## Gate Ledger 模板

当 Stage 写入敏感 workflow 文件后, 最终回复中应包含:

```text
Gate ledger:
- command: <command that checked or produced evidence>
- result: PASS | FAIL | NOT_RUN
- reason: <why this result is acceptable or blocked>
- artifacts: <paths or outputs>
```

如果某个检查没有运行, 用 `NOT_RUN` 并说明原因, 不要把未运行的 gate 写成通过。
