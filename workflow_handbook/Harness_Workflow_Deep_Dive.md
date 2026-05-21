# Harness 工作流深度解析

本文是对 Harness Research 工作流、hooks、审查、动态证据链和 auto-iterate 控制器的代码库级梳理。

最近复核日期: 2026-05-20
适用范围: Harness Research 框架仓库
目标读者: 需要理解整套 Harness 工作流、运行边界、审查机制和 gate 证据要求的 operator/agent

## 0. 证据边界

本文来自对当前仓库源码和文档的静态检查，以及一组只读/测试命令。它不是 `.evidence/**` 下的 evidence-chain 编译产物，也不是人类审批记录。

已读取的关键来源包括:

- `AGENTS.md`
- `README.md`
- `.agents/references/workflow-guide.md`
- `schemas/skill_contracts.json`
- `schemas/skill_contracts.schema.json`
- `tooling/codex_hooks/README.md`
- `tooling/codex_hooks/hooks.json`
- `tooling/codex_hooks/harness_contracts.py`
- `tooling/codex_hooks/user_prompt_submit.py`
- `tooling/codex_hooks/pre_tool_use_policy.py`
- `tooling/codex_hooks/post_tool_use_markers.py`
- `tooling/codex_hooks/require_gate_ledger.py`
- `tooling/evidence/check_dynamic_context.py`
- `tooling/evidence/check_workflow_state.py`
- `tooling/evidence/check_context_gates.py`
- `tooling/evidence/check_protocol_drift.py`
- `tooling/evidence/check_docchain_gates.py`
- `tooling/evidence/compile_doc.py`
- `tooling/evidence/compile_protocol.py`
- `tooling/evidence/approve_contract.py`
- `tooling/auto_iterate/README.md`
- `tooling/auto_iterate/docs/cli_control_guide.md`
- `tooling/auto_iterate/docs/auto_iterate_goal_template.md`
- `tooling/auto_iterate/scripts/auto_iterate/controller.py`
- `tooling/auto_iterate/scripts/auto_iterate/postcondition.py`
- `tooling/auto_iterate/scripts/auto_iterate/recovery.py`
- `tooling/model_api/README.md`
- `tooling/model_api/harness_external_review.py`
- `tooling/.tests/test_codex_hooks_contracts.py`
- `tooling/.tests/test_dynamic_context_suite.py`
- `tooling/.tests/test_auto_iterate_controller_fsm.py`
- `tooling/.tests/test_auto_iterate_runtime_adapter.py`
- `tooling/.tests/test_workflow_state_check.py`

解释约定:

- 已验证: 直接来自源码、模板、测试或命令输出。
- 推断: 由多个源码位置合并出的结构性解释。
- 待确认: 当前检查仍未完全确认的事项。

## 1. 仓库使命与边界

已验证:

Harness Research 是一个以证据为基础的研究工作流框架。它提供 skills、hooks、templates、schemas、workflow rules、evidence tooling 和 auto-iterate controller。默认情况下，这份 checkout 是框架仓库，不是某个具体研究项目仓库。

核心目标:

- 降低研究探索启动成本。
- 增强研究过程的可复现性。
- 强制区分事实、假设、推断和审批。
- 让 human operator 保留关键决策权。
- 防止 agent 用未经验证的叙述冒充 evidence。

仓库角色:

```text
Harness-Research/
|
+-- .agents/                    面向 Codex 的 skills、contracts、references
+-- .claude/                    面向 Claude Code 的 skills 和 shared rules
+-- tooling/codex_hooks/        workspace-local Codex hook 实现
+-- tooling/evidence/           dynamic context、docchain、gates、review packets
+-- tooling/auto_iterate/       WF10 controller、runtime adapter、recovery
+-- tooling/model_api/          external model review wrappers 和 helpers
+-- templates/                  target workspaces 的 bootstrap docs/templates
+-- schemas/                    framework artifacts 的 JSON schemas
+-- tooling/.tests/                      contracts、gates、controller 的 regression tests
+-- docs/                       framework documentation
```

重要边界:

```text
框架仓库
  |
  +-- 拥有: skills, hooks, tooling, schemas, tests, templates
  |
  +-- 通常不拥有:
      PROJECT_STATE.json
      iteration_log.json
      project_map.json
      MEMORY.md
      OPERATOR_CONTEXT.md
      .evidence/**
      .auto_iterate/**

目标研究工作区
  |
  +-- 拥有具体研究项目的状态、当前文档、实验日志、证据链
```

除非 operator 明确要求把这份 checkout 当作自我改进项目运行，否则不要在本仓库手工创建或编辑 target workspace state。

## 2. 总体工作流

标准工作流应当从 `WF0 bootstrap/init` 开始理解。`WF0` 不是研究阶段，而是把一个 target workspace 变成可运行 Harness 的工作区。

```text
WF0  bootstrap / init
  |
  v
WF1  survey-idea
  |
  v
WF2  idea-debate
  |
  v
WF3  refine-idea
  |
  v
WF4  data-prep
  |
  v
WF5  baseline-repro
  |
  v
WF6  refine-arch
  |
  v
WF7  build-plan
  |
  v
WF8  code-expert
  |
  v
WF9  validate-run
  |
  v
WF10 iterate / auto-iterate
  |
  v
WF11 final-exp
  |
  v
WF12 release
```

`WF0` 的职责:

```text
选择 target workspace
  |
  v
区分 framework source / research repo / baseline reference repo
  |
  v
创建或刷新 CLAUDE.md / AGENTS.md / MEMORY.md
  |
  +-- 可选: 仅在人类明确给出稳定偏好时创建 OPERATOR_CONTEXT.md
  |
  +-- 可选: 初始化 docs/10_contract, docs/20_facts, docs/30_evidence,
  |        docs/35_protocol, docs/40_iterations, docs/50_memory, .evidence/
  |
  +-- 可选: 安装并检查 Codex hooks
  |
  v
进入 WF1-WF12 研究流程
```

`WF0` 可以通过 bootstrap 手册执行，也可以通过 `$init-project init/update` 执行。其中 `tooling/evidence/init_context.py` 只负责动态上下文目录、模板和 schema，不负责创建 operator preference。

推断出的高层控制环:

```text
人类目标
  |
  v
工作流 skill contract
  |
  v
必读文件 + 当前项目状态
  |
  v
agent 工作
  |
  v
工具输出 / 测试输出 / 证据 artifact
  |
  v
gate 检查
  |
  +--> FAIL/REVIEW --> 人类决策或回退到更早工作流阶段
  |
  v
状态更新 + Gate ledger
  |
  v
只有明确人类批准后才进入下一工作流阶段
```

阶段目标摘要:

| 阶段 | Skill | 主要输出 | 主要 gate 压力 |
| --- | --- | --- | --- |
| WF0 | `init-project` / bootstrap tools | workspace scaffold、guidance、可选 dynamic context layout | 不编造 evidence；`OPERATOR_CONTEXT.md` 只能来自明确 operator 偏好 |
| WF1 | `survey-idea` | 可行性和证据种子 | 不得把协议草稿当作已批准合同 |
| WF2 | `idea-debate` | 备选想法和批判 | 审查者独立性、协议漂移意识 |
| WF3 | `refine-idea` | 精炼想法和假设 | 避免过早做架构决策 |
| WF4 | `data-prep` | 数据集统计、数据假设和 `Dataset_Table.md` | 数据集事实必须可记录、可复现 |
| WF5 | `baseline-repro` | 基线报告、合同、`Baseline_Table.md` 和可选 codebase map 更新 | 已批准的 baseline/evaluation contract readiness |
| WF6 | `refine-arch` | 技术规格 | 架构必须遵守证据和合同 |
| WF7 | `build-plan` | 实施路线图、`project_map.json` 和 `Codebase_Map.md` | plan 不能发明架构；map 必须保持最新 |
| WF8 | `code-expert` | 首轮实现和稳定 codebase map 同步 | stable code 需要先读取 project map/codebase map 并验证 |
| WF9 | `validate-run` | 语义审查、smoke evidence 和 `Validation_Table.md` | 没有 review 和 smoke evidence 不能 PASS |
| WF10 | `iterate` / controller | 反复 plan/code/run/eval 循环 | 决策词汇、lessons、iteration log 完整性 |
| WF11 | `final-exp` | final experiment matrix/results | 需要 approved contracts 和 claim boundary |
| WF12 | `release` | release manifest/submission package | claims 必须留在 approved boundary 内 |

## 3. 动态上下文工作流

动态上下文是证据层，用来防止研究 claims 偏离已经记录的事实。

`operator 上下文` 的创建规则:

```text
bootstrap 手动路径
  |
  +-- 从 OPERATOR_CONTEXT.md.template 复制
  +-- 只有 operator 准备填写稳定偏好时才创建
  |
  v
OPERATOR_CONTEXT.md

$init-project init 路径
  |
  +-- 读取 init-project skill 和 context-layering policy
  +-- 只有 operator 明确提供稳定偏好或本地约束时才创建/更新
  |
  v
OPERATOR_CONTEXT.md

tooling/evidence/init_context.py
  |
  +-- 初始化 docs/ 和 .evidence/ layout
  +-- 不创建 OPERATOR_CONTEXT.md
```

`OPERATOR_CONTEXT.md` 只表达偏好、约束、工作方式和本地习惯。它可以影响默认选择，但不能证明 project facts，也不能替代 evidence tables、contracts 或 human approval。

核心流程:

```text
operator 上下文
  |
  v
docs/30_evidence/*.md 表格
  (operator 可读的 Conclusion Evidence，例如 Dataset/Baseline/Validation tables)
  |
  v
compile_protocol.py
  |
  v
docs/35_protocol/Research_Protocol.md
docs/35_protocol/Protocol_Assumptions.md
docs/35_protocol/Protocol_Changelog.md
docs/35_protocol/Protocol_Review.md
  |
  v
docs/10_contract/ 下的 contract 文档
  |
  v
compile_doc.py 证据链
  |
  v
.evidence/chains/<doc_id>/<build_id>/
  (tool-owned audit artifacts，不手工编辑)
  |
  v
check_dynamic_context.py
  |
  +-- context gate
  +-- protocol drift gate
  +-- docchain gate
  +-- workflow state gate
  |
  v
人类 review packet / approval decision
```

重要区别:

```text
skill instructions      = agent 行为契约
protocol draft          = 结构化研究计划
docchain                = 文档的 provenance/audit metadata
gate result             = 工具检查过的 readiness signal
human approval artifact = 实际 approval boundary
```

只有最后两类能支撑高风险 transition；只要 workflow 要求人类批准，就仍然需要 human approval。

## 4. 状态所有权

框架按 owner 分离项目状态。这是最重要的安全属性之一。

```text
PROJECT_STATE.json
  owner: orchestrator
  purpose: 标准 workflow stage、contracts、approval metadata、transitions
  rule: stage transitions 需要明确 human approval

iteration_log.json
  owner: iterate skill / WF10 loop
  purpose: experiment entries、metrics、decisions、lessons
  rule: orchestrator/controller 读取它；iterate 写入实验事实

project_map.json
  owner: build-plan 和 stable code-change steps
  purpose: 映射 stable files、interfaces、commands、contracts
  rule: 文件存在时，code-expert/code-debug 在 stable code edits 前必须读取它

docs/20_facts/Codebase_Map.md
  owner: build-plan 和 stable code-change steps
  purpose: operator-facing 当前代码库说明，覆盖 stable files、module responsibilities、public interfaces、entry points、maintenance owners
  rule: 文件存在时，stable 文件、接口、入口、依赖方向或职责变化必须和 project_map.json 同步更新

.evidence/**
  owner: evidence tooling
  purpose: docchains、protocol compiler builds、review packets、indexes
  rule: 不要手工编辑

.auto_iterate/**
  owner: auto-iterate controller
  purpose: lock、state、events、runtime logs、recovery metadata
  rule: 不要手工编辑

CLAUDE.md
  owner: init-project / workspace bootstrap flow
  purpose: 精简的本地 guidance
  rule: 保留生成文件里的 Custom sections

OPERATOR_CONTEXT.md
  owner: human/operator context flow
  purpose: preferences 和 constraints
  rule: 它本身不是 project facts 的 evidence
```

状态交互图:

```text
orchestrator
  |
  +-- 写入 PROJECT_STATE.json
  +-- 读取 iteration_log.json
  +-- 读取 project_map.json
  |
  v
工作流阶段决策

iterate / auto-iterate
  |
  +-- 写入 iteration_log.json
  +-- 写入 docs/40_iterations/*；仅兼容旧路径时镜像 docs/iterations/*
  +-- 读取 PROJECT_STATE.json
  +-- 不得执行 stage transition
  |
  v
NEXT_ROUND / DEBUG / CONTINUE / PIVOT / ABORT

证据工具链
  |
  +-- 写入 .evidence/**
  +-- 更新 doc evidence headers
  +-- 对 docs 和 contracts 执行 gate
  |
  v
review packet / gate result
```

## 5. 合同批准语义

Contract approval 有意采用冗余确认。不是某个文档写了 approved，这个 contract 就真的 approved。

Approval 需要同时具备文档级 evidence 和 canonical state 级 evidence:

```text
docs/10_contract/<Contract>.md
  |
  +-- Status: approved
  +-- Human approved: yes
  |
  v
PROJECT_STATE.json.contracts.<contract>
  |
  +-- status: approved
  +-- approved_at
  +-- approved_by
  +-- approval_source
```

Approval 流程:

```text
agent 起草 contract
  |
  v
dynamic context gates
  |
  v
review packet
  |
  v
人类在当前对话中明确批准，或给出可审计 artifact
  |
  v
approve_contract.py
  |
  +-- 更新 contract markdown 字段
  +-- 更新 PROJECT_STATE.json 中的 contract metadata
  |
  v
重新运行 dynamic context gate
```

禁止的捷径:

- 把 `Protocol_Review.md` 当作 contract approval
- 把 review packet 当作 approval
- 没有明确 human approval 就批准
- 没有 approved contracts 就进入 WF11
- 在 `Claim_Boundary.md` 之外提出 release claims

## 6. 证据工具链

### 6.1 Context 初始化

`tooling/evidence/init_context.py` 初始化 target workspace 的 docs 和 schema scaffold。它面向项目工作区，不适合普通框架文档修改。

典型输出形态:

```text
docs/
  10_contract/
  20_facts/
    Codebase_Map.md
  30_evidence/
    Dataset_Table.md
    Baseline_Table.md
    Validation_Table.md
  35_protocol/
  40_iterations/
  50_memory/
.evidence/
  schemas/
```

### 6.2 Protocol Compiler

`compile_protocol.py` 读取 evidence tables，并生成 protocol drafts。

流程:

```text
docs/30_evidence/
  |
  +-- Paper_Table.md
  +-- Dataset_Table.md
  +-- Metric_Table.md
  +-- Baseline_Table.md
  +-- Validation_Table.md
  +-- Repo_Table.md
  +-- Open_Questions.md
  |
  v
compile_protocol.py
  |
  v
.evidence/protocol_compiler/<build_id>/
  |
  +-- 生成的 protocol docs
  +-- manifest / build metadata
  |
  v
optional --apply
  |
  v
docs/35_protocol/*.md
```

重要: protocol compilation 可以生成更强的 draft，但 protocol draft 不是 approved contract。

### 6.3 Docchain Compiler

`compile_doc.py` 把当前文档连接到明确的 evidence sources。

流程:

```text
当前 markdown doc
  |
  +-- --source file/path/or/artifact
  |
  v
compile_doc.py
  |
  +-- 对 sources 做 hash
  +-- 写入 evidence_chain.json
  +-- 写入 source_manifest.json
  +-- 写入 doc_audit.json
  +-- 更新 doc evidence headers
  +-- 更新 .evidence/index.json
  |
  v
.evidence/chains/<doc_id>/<build_id>/
```

Docchain 证明 provenance 和 auditability。它本身不证明某个 claim 在科学上为真。

### 6.4 Dynamic Context Gate 套件

`check_dynamic_context.py` 是稳定的聚合 gate 入口。

```text
check_dynamic_context.py
  |
  +-- check_context_gates.py
  |     检查 contract readiness 和 status consistency
  |
  +-- check_protocol_drift.py
  |     检查 protocol review、open questions、assumptions、negative results
  |
  +-- check_docchain_gates.py
  |     检查 evidence chains、manifests、audits、staleness、contract evidence strength
  |
  +-- check_workflow_state.py
        检查 PROJECT_STATE、iteration_log、project_map、.auto_iterate consistency
```

阶段映射:

| CLI stage | Context 含义 | Protocol drift 含义 |
| --- | --- | --- |
| `status` | status 检查 | status 检查 |
| `wf5` | evaluation contract readiness | WF5 drift 检查 |
| `wf10` | WF10 auto readiness | WF10 drift 检查 |
| `wf11` | final experiment readiness | WF11 drift 检查 |
| `wf12` | release readiness | WF12 drift 检查 |

常用命令:

```bash
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage wf10 --review-packet
```

只有当 operator 明确接受当前 run 的风险时，`--allow-*` flags 才能把特定 blocking conditions 降级。

## 7. Codex Hooks 总览

Workspace-local hook 模板:

```text
tooling/codex_hooks/hooks.json
```

安装后的 workspace files:

```text
.codex/config.toml
.codex/hooks.json
.codex/rules/harness_external_review.rules
```

Hook 生命周期:

```text
UserPromptSubmit
  |
  v
检测 active skill / intent
写入 .harness_hooks/session.json
重置或保留 read ledger
发出 required read set 和 contract context
  |
  v
PreToolUse
  |
  +-- 在 mutating tools 前阻止 missing required reads
  +-- 阻止直接手工写入 .evidence/** 或 .auto_iterate/**
  +-- 阻止 git-add 已知本地/reference artifacts
  +-- 阻止直接运行 external model review scripts
  +-- 在 code-review 期间阻止 subject-file edits
  |
  v
工具运行
  |
  v
PostToolUse
  |
  +-- 记录 tracked reads
  +-- 记录 mutating tool activity
  +-- 检测 sensitive changed paths
  +-- 必要时标记 pending Gate ledger
  |
  v
Stop
  |
  +-- 如果 required read set 缺失，则阻止最终回答
  +-- 如果 Gate ledger 缺失，则阻止最终回答
```

运行时文件:

```text
.harness_hooks/
  |
  +-- session.json
  +-- sessions/<session_key>.json
  +-- read_ledger.json
  +-- read_ledgers/<session_key>.json
  +-- pending_actions.json
```

这些文件是 runtime state，不应提交。

## 8. Hook Detection 策略

`UserPromptSubmit` 使用 `harness_contracts.detect_skill_match()`。

Detection 层级:

```text
原始 prompt
  |
  v
detection_text()
  |
  +-- 保留 `$code-review` 这类 explicit triggers
  +-- 从通用匹配中剥离 path-like text 和 filenames
  |
  v
explicit trigger / WF trigger / implicit trigger
  |
  v
active skill contract，或只有 daily workspace context
```

Skill 激活示例:

```text
"run $validate-run"
  -> explicit trigger -> validate-run contract

"WF10 auto"
  -> workflow trigger -> 根据匹配结果进入 auto-iterate-goal 或 iterate contract

"fix the hook policy"
  -> inferred code_write -> code-debug contract

"review current diff deeply"
  -> inferred code_review_heavy -> code-review contract

"where is compile_doc implemented?"
  -> code_search -> 不触发 workflow Stop blocking
```

Continuation 行为:

```text
prompt = "继续" / "continue" / "resume"
  |
  v
是否为同一个非空 Codex session_id?
  |
  +-- 是 --> 保留上一个 active skill
  +-- 否 --> 不复用 stale session
```

Daily workspace context（日常工作区上下文）:

如果当前是 Harness workspace 且没有 active workflow skill，hooks 仍会要求 agent 在仓库特定工作前读取 `AGENTS.md` 和 `CLAUDE.md` 等 repository guidance。这只是 context，不是完整 workflow contract。

## 9. Read Ledger 机制

Read ledger 是一层 guardrail，用来防止 agent 在 hook 没有观察到读取行为时声称工作已经基于 required files。

可追踪的读取来源:

```text
直接 read tools:
  Read
  View
  Open

内容读取 shell commands:
  cat
  sed
  nl
  rg
  grep
  head
  tail
  less
  more
  git diff
  git show
```

重要限制:

```text
可观察到的精确 operand
  |
  v
记录为 read

隐藏在 pipe/control operator 内的 path
  |
  v
不计为 audited read proof
```

这意味着 `cat AGENTS.md` 可以计数，但复杂 shell pipeline 即使在终端输出里显示了文本，也可能不会被计为 required read。

Read contract 执行:

```text
active contract
  |
  v
required_existing_files()
  |
  +-- read_set.harness
  +-- read_set.skill
  +-- read_set.project_when_present 如果文件存在
  |
  v
missing_reads()
  |
  +-- PreToolUse 阻止 mutating tools
  +-- Stop 在 enforcement conditions 满足时阻止最终回答
```

Stop hook 在以下情况强制 missing reads 检查:

- skill 被明确调用，或
- mutating tool 已运行，或
- pending Gate ledger 存在。

`code-review` 更严格: review prompts 在 finalization 前必须满足 review read-set compliance。

## 10. PreToolUse 边界

`PreToolUse` 是主要 runtime boundary hook。

边界图:

```text
mutating event
  |
  +-- apply_patch/Edit/Write
  |
  +-- 使用 rm/mv/cp/touch/mkdir/chmod/chown/git add/git commit/git rm 的 Bash
  |
  +-- 带 shell redirection 的 Bash
  |
  +-- 带 output paths 的 external review wrapper
```

被阻止的动作:

```text
直接写入 .evidence/**
  -> 除非通过 tooling/evidence/*，否则阻止

直接写入 .auto_iterate/**
  -> 除非通过 tooling/auto_iterate/*，否则阻止

git add 本地/reference artifacts
  -> 对已知 local/reference patterns 阻止

直接运行 external model scripts
  -> 阻止；必须使用 harness_external_review.py

在 `$code-review heavy` 之外运行 harness_external_review.py
  -> 阻止

code-review 期间修改 subject files
  -> 除 review trace artifacts 外均阻止

required reads 前执行 mutating tool
  -> 阻止
```

允许的 code-review 写入区域:

```text
.agents/state/review_traces/code-review/
```

Review 中发现的 source fixes 必须通过 `$code-debug` 路由，不能在 `$code-review` 中直接修改。

## 11. PostToolUse 与 Gate Ledger

`PostToolUse` 记录工具运行之后发生了什么。

```text
PostToolUse
  |
  +-- record_direct_tool_read()
  |
  +-- record_command_reads()
  |
  +-- mark_tool_activity()
  |
  +-- mark_pending_for_changes()
  |
  v
.harness_hooks/read_ledger.json
.harness_hooks/pending_actions.json
```

当 sensitive workflow paths 被修改时，会设置 pending Gate ledger。

没有 active contract 时的默认 sensitive paths:

```text
PROJECT_STATE.json
iteration_log.json
project_map.json
docs/
src/
scripts/
configs/
```

每个 active contract 可以定义自己的 `sensitive_paths`。例如，`code-expert` 包含 stable code 和 project map 路径；`release` 包含 `submission/`、`docs/` 和 `PROJECT_STATE.json`。

Gate ledger 要求:

```text
sensitive path 被修改
  |
  v
pending_actions.requires_gate_ledger = true
  |
  v
Stop hook 检查 final assistant message
  |
  +-- 必须包含 "Gate ledger"
  +-- 必须包含 command/result/reason/artifact 字段
  |
  +-- 缺失 -> 阻止 final response
```

Gate ledger 不只是记账。它是 final response 里的审计摘要，用来把 sensitive edit 和实际运行过的 checks 连接起来。

## 12. Skill Contracts

Contract 来源:

```text
schemas/skill_contracts.json
schemas/skill_contracts.schema.json
```

每个 contract 定义:

```text
skill
triggers
required_read_set
  harness
  skill
  project_when_present
  project_optional
required_actions
forbidden_actions
gate_ledger_required_when
sensitive_paths
```

本仓库的 contract 覆盖:

```text
orchestrator
doc-compiler
review-packet
protocol-compiler
protocol-drift-check
survey-idea
idea-debate
refine-idea
data-prep
baseline-repro
refine-arch
deep-check
evaluate
init-project
env-setup
build-plan
code-expert
code-debug
code-review
validate-run
iterate
auto-iterate-goal
final-exp
release
```

Contract 分类:

| 分类 | Skills | 主要保护 |
| --- | --- | --- |
| 工作流编排 | `orchestrator`, WF1-WF12 stage skills | human approval、state transitions、stage gates |
| 动态文档 | `doc-compiler`, `protocol-compiler`, `protocol-drift-check`, `review-packet` | evidence chain、protocol drift、contract readiness |
| 代码工作 | `build-plan`, `code-expert`, `code-debug`, `validate-run` | project map、stable code validation、smoke evidence |
| 审查工作 | `code-review`, `deep-check` | reviewer independence、trace artifacts、禁止 subject mutation |
| 迭代工作 | `iterate`, `evaluate`, `auto-iterate-goal` | iteration log integrity、decision vocabulary、lessons |
| 环境和 bootstrap | `init-project`, `env-setup` | context layering、dependency/documentation sync |

Contract 验证:

```bash
python tooling/codex_hooks/check_contracts.py --workspace-root .
```

该命令验证 contract files 存在、required read sets 包含对应 skill file、project guidance 包含 `AGENTS.md`，并且 required/forbidden actions 都是已知项。

## 13. Code Review 工作流

`$code-review` 只做 review，不修复 subject files。

模式:

```text
light
  |
  +-- 较小范围/read-only review 或解释

medium
  |
  +-- changed line map
  +-- git metadata snapshot
  +-- 带 line references 的 findings
  +-- 按请求或需要生成 review report

heavy
  |
  +-- medium requirements
  +-- independent reviewer attempts
  +-- 可用时执行 external model review
  +-- reconciliation table
  +-- trace artifacts
```

Heavy review 流程:

```text
收集 review scope
  |
  v
git metadata snapshot
  |
  v
changed line map
  |
  v
local Codex review attempt
  |
  v
external model review attempt
  |
  +-- 必须通过 tooling/model_api/harness_external_review.py 运行
  +-- 直接运行 agentic_review.py/external_chat.py 会被阻止
  |
  v
reconcile findings
  |
  v
在 .agents/state/review_traces/code-review/ 下写入 review trace
  |
  v
Gate ledger
```

Review 输出纪律:

- Findings 放在最前面，并按严重程度排序。
- 使用 file 和 line references。
- 避免把未经验证的 model findings 当作 facts。
- 对不可用的 review tools 报告 `NOT_RUN`，不要假装已经运行。
- 修复通过 `$code-debug` 路由。

## 14. WF9 Validate Run

`validate-run` 是从 implementation 进入 iterative experiments 的桥。

预期检查:

```text
semantic review
  |
  +-- data path correctness
  +-- model/loss/metric consistency
  +-- training/eval split sanity
  +-- 常见 ML bugs
  |
  v
smoke run
  |
  +-- 短训练 run，通常约 100 steps
  +-- checkpoint save/load
  +-- eval path
  +-- 适用时检查 wandb 等 logging path
  +-- git snapshot / reproducibility metadata
  |
  v
docs/Validate_Run_Report.md
docs/30_evidence/Validation_Table.md
  |
  v
PASS / REVIEW / FAIL
```

禁止:

```text
没有 semantic review 就 WF9 PASS
没有 smoke evidence 就 WF9 PASS
```

如果 WF9 通过且项目已准备好进入 automated iteration，下一个 handoff 是 `$auto-iterate-goal`。

## 15. Auto-Iterate Goal

Goal 文档:

```text
docs/auto_iterate_goal.md
```

Goal 文件面向 operator。它需要包含足够结构，让 controller 知道优化目标和约束。

重要字段:

```text
primary metric name
primary metric direction
target threshold
constraints
patience
budget
screening policy
hypotheses
forbidden directions
```

Goal 流程:

```text
人类目标
  |
  v
$auto-iterate-goal
  |
  +-- 读取 workflow/context rules
  +-- 创建或验证 docs/auto_iterate_goal.md
  +-- 检查 dynamic context readiness
  |
  v
controller start/resume
```

Controller 不应从未验证或缺失的 goal 启动 WF10 auto-iteration。

## 16. Auto-Iterate Controller

Controller 的作用是重复执行 WF10 loops，同时不移除 human responsibility。

顶层流程:

```text
start / resume
  |
  v
解析 goal
  |
  v
验证 budget、metric、constraints
  |
  v
获取 .auto_iterate/lock.json
  |
  v
动态预检
  |
  +-- check_dynamic_context.py --stage wf10
  +-- 可选 review packet
  |
  v
轮次循环
  |
  +-- plan
  +-- code
  +-- run_screening
  +-- run_full
  +-- eval
  |
  v
决策处理
```

Controller 拥有的状态:

```text
.auto_iterate/
  |
  +-- lock.json
  +-- events.jsonl
  +-- state.json 或 controller state files
  +-- runtime/
      |
      +-- round<N>_<phase>.stdout.log
      +-- round<N>_<phase>.stderr.log
```

Controller 读取 `iteration_log.json`，但不替代人类对 experiment truth 的责任。

动态预检:

```text
check_dynamic_context.py --stage wf10 --review-packet
  |
  +-- FAIL -> controller 必须停止
  |
  +-- PASS -> controller 可以继续
  |
  +-- allow flags 需要明确接受风险
```

高风险 flags:

```text
--allow-draft-contract
--allow-review-required
--skip-dynamic-preflight
```

最后一个 flag 需要 reason，并且应被视为可审计异常，而不是常规操作。

## 17. Auto-Iterate Phase Postconditions

Controller 必须根据 repository state 判断 phase success，而不是根据 chat prose 判断。

`postcondition.py` 明确说明 phase success 只能通过检查 `iteration_log.json` 和 `PROJECT_STATE.json` 等 repository state 来确定。

Phase contract（阶段契约）:

```text
plan
  |
  +-- 恰好一个 new iteration ID
  +-- status = planned
  +-- hypothesis
  +-- date
  +-- changes_summary
  +-- config_diff object
  +-- screening.recommended boolean
  +-- codex_review

code
  |
  +-- current_iteration_id 已绑定
  +-- status = training
  +-- git_commit
  +-- git_message

run_screening
  |
  +-- screening.status = passed | failed | skipped
  +-- 除 skipped 外都需要 run_manifest
  +-- passed/failed 需要 metrics
  +-- metric names 必须遵守 tracked metric protocol

run_full
  |
  +-- full_run.status = completed | recoverable_failed | failed
  +-- completed 需要 metrics 和 run_manifest
  +-- failed statuses 需要 error information
  +-- 配置 primary metric 时，该 metric 必须存在且为 numeric

eval
  |
  +-- status = completed
  +-- decision in NEXT_ROUND | DEBUG | CONTINUE | PIVOT | ABORT
  +-- 至少一个 lesson
  +-- final metrics
  +-- git_commit
  +-- run_manifest
  +-- docs/40_iterations/ 下的 per-iteration report；旧项目可镜像 docs/iterations/
```

Decision 语义:

```text
NEXT_ROUND
  -> 使用下一个 experiment 继续 WF10

DEBUG
  -> 留在 WF10 并修复 recoverable issue

CONTINUE
  -> 停止 auto loop 并 hand off 到 WF11 方向

PIVOT
  -> 停止 auto loop 并返回 idea/protocol stages

ABORT
  -> 停止 auto loop，因为 objective 不应继续
```

## 18. Auto-Iterate Recovery

Recovery engine 应检查 state 和 logs，而不是编造 success。

Recovery 逻辑概念图:

```text
interrupted 或 failed phase
  |
  v
检查 controller state
  |
  v
检查 iteration_log.json
  |
  v
检查 phase logs
  |
  +-- state 已满足 postcondition -> adopt
  +-- recoverable missing work -> rerun phase
  +-- repeated failure / unclear state -> manual_action_required
```

Lock 语义:

```text
controller start
  |
  v
获取 lock
  |
  +-- active lock -> 有意 stop 或 resume
  +-- stale lock -> 可按 policy 清理
  |
  v
heartbeat updates
```

这可以防止并行 controller runs 破坏 `.auto_iterate/**` 和 `iteration_log.json`。

## 19. 人类在环政策

人类批准不是走形式。

Agent 应暴露:

- 当前 hypothesis
- 使用过的 evidence
- 触碰过的 code paths
- 运行过的 commands
- gate 结果
- 未解决假设
- operator 需要做出的下一步决策

不得自动推进:

```text
工作流阶段
合同批准
无人值守的 WF10 acceptance
高风险 transition
release-ready claim（发布就绪声明）
```

所需 approval 形态:

```text
当前对话中的明确 human confirmation
  或
可审计 approval artifact
```

## 20. Review 与 Approval 不同

系统有意把 review 与 approval 分开。

```text
review packet
  |
  +-- 总结 evidence 和 gate status
  +-- 帮助人类决策
  +-- 可能识别 missing evidence
  |
  v
不是 approval

human approval（人类批准）
  |
  +-- explicit decision（明确决策）
  +-- contract state 变化时，通过 approved tooling 写入
  |
  v
approval boundary（批准边界）
```

同理:

```text
code review finding（代码审查发现）
  |
  +-- 可以识别 risk
  +-- 可能是错的
  +-- 必须被 reconciled
  |
  v
除非已验证，否则不是 project fact
```

## 21. 验证矩阵

常用检查:

```bash
python tooling/codex_hooks/check_contracts.py --workspace-root .
python tooling/codex_hooks/hook_status.py --workspace-root .
python tooling/codex_hooks/hook_status.py --workspace-root . --trust-status
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage status
python tooling/evidence/check_workflow_state.py --workspace-root .
pytest tooling/.tests/test_codex_hooks_contracts.py
pytest tooling/.tests/test_dynamic_context_suite.py
pytest tooling/.tests/test_protocol_compiler.py tooling/.tests/test_protocol_drift_check.py
pytest tooling/.tests/test_review_packet.py
pytest tooling/.tests/test_evidence_docchain.py tooling/.tests/test_evidence_docchain_gates.py
pytest tooling/.tests/test_auto_iterate_controller_fsm.py
pytest tooling/.tests/test_auto_iterate_runtime_adapter.py
```

修改 Python files 时:

```bash
python -m py_compile <modified files>
ruff check --select=E,F,I <modified files>
```

修改 hook detection 或 policy 时:

```bash
python tooling/codex_hooks/simulate_hook.py UserPromptSubmit \
  --workspace-root . \
  --event-json '{"prompt":"run $validate-run"}'
```

修改 contracts 时:

```bash
python tooling/codex_hooks/check_contracts.py --workspace-root .
pytest tooling/.tests/test_codex_hooks_contracts.py
```

修改 dynamic context 时:

```bash
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage status
pytest tooling/.tests/test_dynamic_context_suite.py
pytest tooling/.tests/test_dynamic_context_contracts.py
pytest tooling/.tests/test_evidence_docchain.py tooling/.tests/test_evidence_docchain_gates.py
```

修改 auto-iterate 时:

```bash
pytest tooling/.tests/test_auto_iterate_goal_parser.py
pytest tooling/.tests/test_auto_iterate_controller_fsm.py
pytest tooling/.tests/test_auto_iterate_runtime_adapter.py
pytest tooling/.tests/test_auto_iterate_recovery.py
```

## 22. 当前仓库观察

本次检查已验证:

```text
docs/
  |
  +-- framework docs 区域存在
  +-- 本文件是 framework-level doc，不是 target research state doc

target-workspace runtime state（目标工作区运行时状态）
  |
  +-- status gate 期间 root 下没有 PROJECT_STATE.json
  +-- status gate 期间 root 下没有 iteration_log.json
  +-- status gate 期间 root 下没有 project_map.json
  +-- status gate 期间 .auto_iterate/ 不存在或未激活
```

本次 session 观察到的当前验证结果:

```text
python tooling/codex_hooks/check_contracts.py --workspace-root .
  -> PASS

python tooling/codex_hooks/hook_status.py --workspace-root .
  -> workspace hooks 已激活；feature 已启用；workspace hook commands 存在

python tooling/evidence/check_dynamic_context.py --workspace-root . --stage status
  -> PASS

python tooling/evidence/check_workflow_state.py --workspace-root .
  -> PASS

pytest
  -> 475 passed
```

待确认项:

```text
python tooling/codex_hooks/hook_status.py --workspace-root . --trust-status
  -> NOT_RUN / 本次 session 中结论不确定，因为 local Codex app-server
     在等待 initialize response 时超时。
```

## 23. 心智模型

最短准确模型:

```text
skills 告诉 agent 当前扮演什么角色
contracts 告诉 hooks 必须读什么、不能做什么
hooks 在 Codex lifecycle 中执行本地 guardrails
evidence tooling 证明 document provenance 和 gate status
workflow state 记录 canonical stage 和 approval facts
iteration log 记录 experiment truth
controller 重复执行 WF10，但不能批准 claims
human operator 批准 boundaries 和 high-risk transitions
```

更适合 operator 的 8 个原语:

```text
init
  -> 让 workspace 可运行；创建 guidance、可选 operator context、可选动态上下文目录

evidence
  -> 收集论文、repo、数据集、metrics、open questions；不直接等于结论

protocol
  -> 从 evidence 编译出当前研究计划草稿；可审查，但不是批准

contract
  -> 人类批准后的执行边界；决定 evaluation、baseline、claim boundary

code
  -> 按 roadmap/project_map/Codebase_Map 实现或修复；代码事实要靠测试和运行证明

validate
  -> WF9 的 semantic review + smoke evidence；决定能否进入 WF10

iterate
  -> WF10 反复 plan/code/run/eval；产生实验事实，但不能批准 claim

release
  -> WF11/WF12 在 approved contracts 和 claim boundary 内做最终实验和发布
```

端到端安全栈:

```text
人类指令
  |
  v
skill 路由
  |
  v
必读文件集合
  |
  v
工具执行边界
  |
  v
证据 artifacts
  |
  v
动态 gates
  |
  v
review packet / 代码审查
  |
  v
Gate ledger
  |
  v
人类决策
```

失败处理原则:

```text
缺失 evidence
  -> 说 NOT_RUN 或 FAIL

状态不清楚
  -> 停止，并从 state/logs 恢复

未批准 boundary
  -> 询问人类，不推进

model/reviewer disagreement
  -> reconcile，不盲目接受

工具拥有的 state path
  -> 使用 tool，不手工编辑
```

## 24. 执行条件与边界速查

这张表是给 operator 的简化入口。它不是替代 skill contracts，而是告诉人什么时候该进入哪条链路。

| 你现在要做什么 | 进入条件 | 怎么执行 | 边界 |
| --- | --- | --- | --- |
| 初始化项目 | 新 target workspace，或需要刷新 guidance | bootstrap 手册，或 `$init-project init/update` | 不编造 evidence；`OPERATOR_CONTEXT.md` 只写明确偏好 |
| 初始化动态上下文 | 项目要使用 numbered docs 和 evidence chain | `python tooling/evidence/init_context.py --workspace-root . --set-state` | 只建目录/模板/schema；不批准 contract |
| 收集研究证据 | 有研究问题、论文、repo、数据或 metric 需要记录 | 填 `docs/30_evidence/**` | Conclusion Evidence 是材料，不是 approved contract；`.evidence/**` 是工具维护的 audit artifact |
| 编译研究协议 | evidence tables 有足够内容，需要形成当前研究计划 | `python tooling/evidence/compile_protocol.py --workspace-root .` | protocol draft 可审查，但不能直接当 approval |
| 批准执行边界 | 准备 baseline、WF10、WF11 或 release | review packet + human approval + `approve_contract.py` | agent 不能自批；packet 不是 approval |
| 写代码 | 已有 refined idea、technical spec、roadmap 或明确 bug | `$code-expert` / `$code-debug` | stable code 前读取 `project_map.json` 和已存在的 `Codebase_Map.md`；不要跳过验证 |
| 做代码审查 | 有 diff、高风险文档、release 相关变更或需要交叉审查 | `$code-review` light/medium/heavy | review-only；不能修改 subject files |
| 验证能否实验 | 实现完成，准备进入 WF10 | `$validate-run` | 没有 semantic review 和 smoke evidence 不能 PASS |
| 自动迭代 | WF9 PASS，goal 明确，dynamic gates 可接受 | `$auto-iterate-goal` + controller | controller 不批准 claim；不手改 `.auto_iterate/**` |
| 最终实验/发布 | WF10 决策进入 final/release，contracts 已批准 | `$final-exp` / `$release` | claims 必须在 approved claim boundary 内 |

## 25. 简化方向

系统复杂度主要来自同时处理 research evidence、human approval、runtime hooks、docchain 和 auto-iterate。优化方向不是去掉所有工程，而是把工程解释成少数稳定入口。

建议优先级:

1. 明确把 `WF0 bootstrap/init` 写进所有主流程图。
2. 对 operator 只暴露少数稳定命令:

```text
$init-project init/update
python tooling/evidence/check_dynamic_context.py --stage status|wf5|wf10|wf11|wf12
python tooling/codex_hooks/check_contracts.py --workspace-root .
python tooling/codex_hooks/hook_status.py --workspace-root .
$validate-run
$auto-iterate-goal
```

3. 把工具分成三层解释:

```text
always-on
  -> AGENTS.md, skill contracts, hooks

on-demand
  -> compile_protocol.py, compile_doc.py, review_packet, dynamic gates

controller-owned
  -> .auto_iterate/**, WF10 runtime logs, controller state
```

4. 每个 workflow 文档段落都按同一模板写:

```text
什么时候执行
怎么执行
写什么状态
不能做什么
通过什么 gate
需要人类决定什么
```

5. 对 hooks 的解释降级为 guardrail，不把 hooks 讲成 proof:

```text
hooks 能证明:
  -> 运行时看到过哪些读/写
  -> 哪些边界被阻止
  -> 是否需要 Gate ledger

hooks 不能证明:
  -> claim 是真的
  -> contract 已批准
  -> 实验结果有效
```

## 26. Codex 权限规划

如果把 Codex 的权限开大，推荐只开到 `workspace-write`，不要默认用
`danger-full-access`。原因很简单：workflow 边界是语义边界，不是单纯的目录可写边界。

```text
Codex sandbox
  -> 控制哪些目录可写
  -> 控制网络是否可用
  -> 只能表达粗粒度 filesystem boundary

Harness hooks
  -> 控制当前 skill / stage
  -> 控制 required reads
  -> 控制 tool-owned paths
  -> 控制 Gate ledger
  -> 控制 review / approval / claim boundary
```

建议写入的 Codex 配置含义:

```toml
sandbox_mode = "workspace-write"
approval_policy = "on-request"

[sandbox_workspace_write]
network_access = false
writable_roots = []

[features]
hooks = true
```

如果确实需要 repo 外目录, 只把那个绝对路径加入 `writable_roots` 或用
`--add-dir`。不要为了某个阶段把整个环境开成 danger 模式。

### Stage 权限提升模型

更细的模型不是"某个 docs 层永久可写", 而是"进入某个 Stage 后临时获得一组写入面"。

```text
base session
  |
  v
UserPromptSubmit 识别 Stage / skill
  |
  v
active contract 赋予当前 Stage 的窄写入面
  |
  v
PreToolUse 检查 required reads 和 forbidden writes
  |
  v
PostToolUse 把 sensitive writes 标记为 pending Gate ledger
  |
  v
Stop 检查最终 read set 和 Gate ledger
```

docs 层不是权限入口; Stage 才是权限入口。`docs/10_contract/**`,
`docs/20_facts/**`, `docs/30_evidence/**`, `docs/35_protocol/**`,
`docs/40_iterations/**`, `docs/50_memory/**` 都应该作为某个 Stage 的写入面来理解。

| Stage / skill | 临时提升的写入面 | 仍然必须 gate 的边界 |
| --- | --- | --- |
| `init-project` / WF0 | `CLAUDE.md`, `AGENTS.md`, `OPERATOR_CONTEXT.md`, `PROJECT_STATE.json`, `docs/**`, `.evidence/**` scaffold | 不能推断 operator preferences; guidance/state 写入需要 Gate ledger |
| `survey-idea` / WF1 | `docs/30_evidence/**`, `docs/Feasibility_Report.md`, `docs/35_protocol/**` | Conclusion Evidence 不是 approved contract; protocol draft 需要 review |
| `idea-debate` / WF2 | `docs/Idea_Debate.md`, `docs/35_protocol/**` | reviewer independence, protocol drift |
| `refine-idea` / WF3 | `docs/Refined_Idea.md`, `docs/35_protocol/**` | 不提前写 architecture decision |
| `data-prep` / WF4 | `docs/Dataset_Stats.md`, `docs/20_facts/**`, `docs/30_evidence/Dataset_Table.md`, `configs/**`, `src/**`, `CLAUDE.md`, `AGENTS.md` | dataset facts 必须来自 artifacts/commands |
| `baseline-repro` / WF5 | `docs/Baseline_Report.md`, `docs/30_evidence/Baseline_Table.md`, `docs/10_contract/**`, `docs/20_facts/Codebase_Map.md`, `baselines/**`, `configs/**`, `scripts/**`, `src/**` | semantic commit, dynamic gates, codebase map sync when baseline layout changes, contract human approval |
| `refine-arch` / WF6 | `docs/Technical_Spec.md`, `docs/20_facts/Project_Glossary.md`, `docs/35_protocol/**` | architecture 必须服从 approved contracts 和 protocol drift |
| `build-plan` / WF7 | `docs/Implementation_Roadmap.md`, `docs/20_facts/Project_Glossary.md`, `docs/20_facts/Codebase_Map.md`, `project_map.json`, `PROJECT_STATE.json` | project map 和 codebase map 不能 stale |
| `code-expert` / WF8 | `src/**`, `scripts/**`, `configs/**`, `project_map.json`, `docs/20_facts/Codebase_Map.md`, `PROJECT_STATE.json` | required reads, py_compile/ruff, project map/codebase map sync |
| `validate-run` / WF9 | `docs/Validate_Run_Report.md`, `docs/30_evidence/Validation_Table.md`, `PROJECT_STATE.json` | 没有 semantic review 和 smoke evidence 不能 PASS |
| `iterate` / WF10 | `iteration_log.json`, `docs/40_iterations/**`, legacy `docs/iterations/**`, `docs/50_memory/**`, `MEMORY.md` | decision vocabulary, lesson quality, WF11 handoff |
| `auto-iterate-goal` | `docs/auto_iterate_goal.md`; `.auto_iterate/**` 由 controller 拥有 | goal validation 才能启动 unattended controller |
| `final-exp` / WF11 | `docs/Final_Experiment_Matrix.md`, `PROJECT_STATE.json` | approved contracts 和 claim boundary |
| `release` / WF12 | `submission/**`, `docs/**`, `PROJECT_STATE.json` | release claims 必须在 `Claim_Boundary.md` 内 |
| `code-review` | `.agents/state/review_traces/code-review/**` | review-only; 修复必须转 `$code-debug` |
| `review-packet` | `.evidence/review_packets/<stage>/<build_id>/**`, 相关合同/状态审批记录 | packet 不是 approval; approval 必须来自明确 human decision |

### 最简结论

`workspace-write + hooks` 是默认答案。
`danger-full-access` 只适合你明确接受“只靠 hooks 管边界”的隔离环境。
对于你的 workflow, 最稳妥的组合是:

```text
Codex sandbox = 目录级边界
Hooks = 阶段级边界
Evidence tools = 结构化写入入口
Human approval = 合同和 release 权限
```
