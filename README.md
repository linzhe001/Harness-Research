# Harness Research

Harness Research 是一套面向严肃 AI/ML 科研的 workflow framework。它的目标不是替研究者“想 idea”，而是帮助研究者把来自实践观察的 idea 更快、更可信地验证出来，并在实现、实验和反思中持续迭代自己的想法。

这套框架把 AI assistant 当作研究工程伙伴使用：用清晰的 human-facing
entrypoints、Skill Contracts、Hooks、可溯源文档、代码切片计划和 Ralph-style
iteration loop，把科研从“让模型自由发挥”变成“让模型在当前证据、边界和反馈回路内工作”。

## What This Is

这个仓库只包含 Harness framework 本身：

- Codex / Claude Code skills
- workflow rules and references
- Codex hook contracts and hook runtime
- dynamic-context and Evidence Chain tooling
- bootstrap templates and schemas
- WF10 auto-iterate controller
- framework regression tests

它不包含某个具体科研项目的研究代码。推荐使用 dual-repo layout：Harness 作为 `.harness` framework repo，目标研究项目作为普通 `.git` repo，两者共享同一个 worktree。

## Research Philosophy

Harness 的核心立场：

```text
good research idea
  -> comes from researcher observation, taste, failure analysis, and domain insight
  -> not from the workflow itself
```

Harness 不承诺提供 idea 的来源，也不把 AI 的 survey 输出当成创造力替代品。它做的是另一件事：

```text
researcher idea
  -> clarify intent and constraints
  -> gather Conclusion Evidence
  -> derive Protocol Draft
  -> get human-approved boundaries
  -> implement in reviewable Commit Slices
  -> validate with Gate Evidence
  -> iterate through Ralph-style loop
  -> keep claims inside approved Claim Boundary
```

研究者仍然负责判断：这个问题是否值得做、哪些观察重要、哪些 tradeoff 可以接受、最终 claim 能说到什么程度。Harness 负责降低中间过程的摩擦和认知负担。

## Core Workflow

Operator 视角先记住 2 个顶层入口：

```text
grill -> clarify rough research intent
execution supervisor -> prepare | build | iterate | release | change
```

| Top-level mode | Use when | First status surface |
| --- | --- | --- |
| `harness grill` | idea 还不清楚，需要追问和收敛 Research Intent | Research Intent Draft / Grill Round Log |
| `harness <action>` / `$workflow-supervisor` | intent 已经能进入执行、验证、迭代、release，或成熟代码库出现新需求 | `workflow_ctl status --json`、worker result JSON、Gate ledger |

Execution Supervisor 下面再选择具体 action：

| Action | Use when | First status surface |
| --- | --- | --- |
| `prepare` | intent 已有，需要 readiness、Review Packet、approval plumbing | pending request JSON / Review Packet |
| `build` | 在边界内推进 build / validate | worker result JSON / Gate ledger |
| `iterate` | 进入多轮实验 loop | `auto_iterate_ctl.sh status --json` / `iteration_log.json` |
| `release` | 检查 release claim 或 package/submit action | WF12 Review Packet / Claim Boundary |
| `change` | 成熟代码库收到新需求、新 idea 或 config/code delta | Change Request JSON / route confidence |

内部 WF0-WF12 参考仍然存在，但它主要服务 artifact ownership、Skill
Contract、Gate 条件和失败排查，不是普通用户的第一层入口。日常操作先读
[workflow_handbook/Workflow_Operator_Handbook.md](workflow_handbook/Workflow_Operator_Handbook.md)
和
[workflow_handbook/pages/operator_task_index.md](workflow_handbook/pages/operator_task_index.md)；
需要细查内部节点时再打开 detailed reference。

## How Harness Helps

### 1. 控制每阶段给模型的上下文

Harness 使用 Skill Contract 和 Codex hooks，把每个阶段的上下文和受控路径显式化：

```text
UserPromptSubmit
  -> infer route hint
  -> expose compact workspace context

PreToolUse
  -> warn for missing recommended reads or mixed owner writes
  -> block manual edits to controlled tool-owned paths

PostToolUse
  -> record read/write/pending metadata

Stop
  -> clear compatible pending metadata when a Gate ledger is present
  -> do not block final responses by default
```

这不是为了制造仪式感，而是为了减少模型在错误上下文里做大范围修改的概率。一个 WF7 plan 不应该偷偷做架构决策；一个 code review 不应该顺手改 subject files；一个 Protocol Draft 不应该被模型标成 Approved Contract。

### 2. 用可溯源文档降低认知过载

Harness 区分几类证据：

| Term | Meaning |
| --- | --- |
| `Conclusion Evidence` | 支持 claim、fact、idea、protocol choice 或 research conclusion 的 Source Artifact。 |
| `Evidence Chain` | 从 Source Artifact 到 current doc/claim 的结构化链。 |
| `Gate Evidence` | 证明命令、测试、review、approval check 或 workflow gate 是否执行以及结果。 |
| `Approval Evidence` | explicit human approval，来自当前对话或可审计 artifact。 |

目标是让 researcher 不必重新读完整上下文，而是优先读可信的 current docs、Review Packets、Gate Ledger 和 Evidence Chain，再决定下一步该让 AI 做什么。

动态上下文链路：

```text
OPERATOR_CONTEXT.md
  -> docs/30_evidence/** Conclusion Evidence tables
  -> docs/35_protocol/** Protocol Draft
  -> docs/10_contract/** draft/approved contracts
  -> .evidence/chains/**
  -> Review Packet
  -> explicit Human Approval
```

### 3. 用多轮代码库搜索和审查生成更可信代码

Harness 不鼓励让 AI 在不了解代码库的情况下直接生成大补丁。稳定实现前，相关 Skill 会读取 `project_map.json`、已存在的 `docs/20_facts/Codebase_Map.md`、roadmap、glossary、contracts 和当前代码路径；实现后再通过 `$code-review`、`$validate-run`、测试命令和 Gate Ledger 把风险显式化。

```text
read project_map and glossary
  -> inspect existing modules, configs, tests, and entry scripts
  -> implement one bounded slice
  -> run py_compile / ruff / focused tests or report NOT_RUN
  -> review changed lines and module boundaries
  -> record Gate Evidence
```

在高风险场景下，`$code-review heavy` 可以通过受控 wrapper 调用外部模型 reviewer。外部 reviewer 的输出仍然不是事实，必须由本地文件、diff、line references 和人类判断复核。

### 4. 用分片代码规划生成更可信代码

Harness 的 coding discipline 收敛在 [workflow_handbook/Workflow_Operator_Handbook.md](workflow_handbook/Workflow_Operator_Handbook.md)。关键原则是：AI 可以加速代码生成，但必须被软件工程约束住。

核心方法：

- `Project_Glossary.md`: 统一系统语言，减少命名漂移。
- vertical slice: 每次只打通一条可运行、可验证的端到端路径。
- TDD / smoke feedback: 先定义最小反馈，再实现。
- deep modules and module boundaries: 控制 public API 和依赖方向。
- complexity budget: 防止 AI 大面积铺代码、扩大边界、制造系统熵增。

切片追踪链：

```text
WF6 Technical_Spec.md
  -> why this path exists and which hypothesis it serves

WF7 Implementation_Roadmap.md
  -> slice_id, planned files, public interfaces, tests, acceptance command

project_map.json
  -> stable file ownership and maintenance entry points

WF8 code / code-debug
  -> implement one Commit Slice at a time

WF9 Validate_Run_Report.md
  -> semantic review, smoke commands, raw logs, verdict

WF10 iteration_log.json / docs/40_iterations/** (legacy mirror: docs/iterations/**)
  -> run, metrics, observation, lesson, decision
```

这使得代码生成不再是“生成一堆文件后让人猜是否正确”，而是每个切片都有来源、边界、验收命令和后续实验记录。

### 5. 用 Ralph-style loop 承担繁重迭代

WF10 是 Harness 的核心实验循环：

```text
$iterate plan
  -> hypothesis and config_diff
  |
  v
$iterate code
  -> implementation through $code-debug
  -> semantic Commit Slice
  |
  v
$iterate run
  -> train/eval or register manual run
  -> metrics and run_manifest
  |
  v
$iterate eval
  -> NEXT_ROUND | DEBUG | CONTINUE | PIVOT | ABORT
```

对于调参、微调模型结构、反复实验这种繁重操作，可以使用 Codex auto-iterate controller 运行 Ralph-style multi-round loop。控制器可以减少手动摩擦，但不会替代 Human Approval：合同、Claim Boundary、release readiness 和高风险转向仍然需要人确认。

## Main Artifacts

| Path | Purpose |
| --- | --- |
| `AGENTS.md` | Codex/native agent guidance for this framework workspace. |
| `CLAUDE.md` | Claude Code-compatible guidance for this framework workspace. |
| `.agents/skills/**` | Codex-facing Skill definitions. |
| `schemas/skill_contracts.json` | Machine-readable high-risk Skill Contracts. |
| `.agents/references/**` | Shared workflow rules and terminology. |
| `.claude/skills/**` | Claude Code-facing skills. |
| `tooling/codex_hooks/**` | Codex hook runtime, install/status, and simulation tools. |
| `tooling/evidence/**` | Protocol, docchain, Review Packet, approval, and gate tooling. |
| `tooling/auto_iterate/**` | WF10 auto-iterate controller and runtime adapter. |
| `tooling/workflow_supervisor/**` | V0 execution supervisor runtime CLI, node registry, and worker-result validation. |
| `tooling/model_api/**` | External model reviewer helpers. |
| `templates/**` | Files copied into target research workspaces. |
| `schemas/**` | JSON schemas for evidence and framework artifacts. |
| `tooling/.tests/**` | Framework regression tests. |
| `workflow_handbook/Workflow_Operator_Handbook.md` | Human-facing workflow entrypoint and operating model. |
| `workflow_handbook/pages/operator_task_index.md` | Task-first index for choosing a top-level mode, supervisor action, status surface, and stop condition. |
| `workflow_handbook/Workflow_Stage_Cards.md` | Detailed internal artifact and gate reference generated from Skill Contracts. |

## Dynamic Context Tools

Common commands:

```bash
python tooling/evidence/init_context.py --workspace-root . --set-state
python tooling/evidence/compile_protocol.py --workspace-root .
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage wf10 --review-packet
python tooling/evidence/check_protocol_drift.py --workspace-root . --stage wf10
python tooling/evidence/build_review_packet.py --workspace-root . --stage wf10
python tooling/evidence/approve_contract.py --workspace-root . --contract evaluation_contract --approved-by "<human reviewer>" --approval-source ".evidence/review_packets/wf10/<build_id>/review_packet.md"
python tooling/evidence/compile_doc.py --workspace-root . --doc docs/10_contract/Project_Contract.md --source PROJECT_STATE.json docs/30_evidence/Evidence_Index.md
python tooling/evidence/validate_docchain.py .evidence/chains/<doc_id>/<build_id>
python tooling/evidence/check_docchain_gates.py --workspace-root .
python tooling/evidence/check_workflow_state.py --workspace-root .
```

Important boundaries:

- `compile_protocol.py` produces Protocol Drafts, not Approved Contracts.
- `build_review_packet.py` produces Review Packets, not Approval Evidence.
- `approve_contract.py` should run only after explicit Human Approval.
- `docs/30_evidence/**` stores operator-readable Conclusion Evidence tables.
- `.evidence/**` is tool-owned; do not hand-edit Evidence Chains.

## Grill And Workflow Supervisor

V0 adds two optional top-level modes without changing the default manual
Skill workflow:

```text
grill -> draft early research intent
execution supervisor -> prepare | build | iterate | release | change
```

`$grill` writes draft intent/readiness artifacts only; it does not complete
WF1-WF3 or approve contracts. The workflow supervisor owns
`.workflow_supervisor/**` and currently supports runtime status, dry-run start,
typed pending requests, node-registry validation, worker-result validation, and
postcondition validation.
Non-dry-run `prepare` is a v0 HITL PoC: it generates a WF5 Review Packet
through evidence tooling after first verifying candidate readiness inputs and
compiling a draft protocol packet. `workflow_ctl approve` runs the exact
contract approval action through `approve_contract.py` only after explicit
human approval; `workflow_ctl resume` reruns the gate and records
`prepare_hitl_poc`, not `prepare_complete`.
`prepare --complete` runs deterministic data acquisition or verification,
baseline clone/acquisition, protocol compilation, and WF5 Review Packet
generation. External dataset downloads and baseline clones require
`--allow-external-downloads` or an explicit Grill readiness value such as
`external_download_policy: allow`. On start, full prepare also writes
`.workflow_supervisor/runs/<run_id>/runtime/grill_bridge.json` by reading
`.workflow_supervisor/readiness.json`, `docs/Execution_Readiness_Packet.md`,
`docs/Research_Intent_Draft.md`, and `docs/Grill_Round_Log.md`, so a
conversation-triggered `$workflow-supervisor` can use Grill's structured
dataset/baseline answers without the operator hand-building CLI arguments.
Redacted or ambiguous Grill values still become typed input requests. Full
prepare pauses for Human Approval and only resumes to `prepare_complete` after
approval.
`build` runs the build registry through structured workers. Use `--auto` to
delegate non-deterministic nodes to Codex, or `--worker-command` to provide a
command template that writes a validated worker-result JSON. Build stops as
`build_ready_for_iterate` only after validate-run postconditions pass. Build
worker prompts include postconditions and allowed write patterns; workers must
run concrete checks, debug failures inside the node budget, and write Gate
ledger entries instead of prose-only success claims. Codex workers write their
result JSON to `.agents/state/workflow_supervisor_worker_results/**`; the
supervisor validates and adopts it into `.workflow_supervisor/**`.
Harness hooks do not block ordinary build writes under declared implementation
surfaces such as `src/`, `scripts/`, `configs/`, `project_map.json`, or owned
docs. They block manual writes to tool-owned runtime/generated paths; use the
owning supervisor, evidence, or docs-site command for those paths.
`start --segment iterate` delegates WF10 to `auto_iterate_ctl.py`; the
supervisor records status and maps `manual_action_required` to a typed pending
request without writing `.auto_iterate/**` directly.
`start --segment change` runs deterministic Change Intake, writes a
schema-validated Change Request under supervisor runtime, and either records a
route such as `code-debug`, `iterate`, `review_packet`, or `delta_grill`, or
pauses with `STEER` when the route is uncertain. It does not invoke the routed
Skill by itself.
`start --segment release` is a conservative WF12 approval gate: it requires an
explicit `validate`, `package`, or `submit` action, runs the WF12
dynamic-context Review Packet gate, and pauses with an exact scoped
`APPROVE_ACTION` only after dynamic context plus approved Project Contract,
Evaluation Contract, and Claim Boundary are confirmed. Resume records approval
and reruns the gate; it does not package or submit.

```bash
tooling/workflow_supervisor/scripts/harness.sh prepare --goal "<goal>" --dry-run
tooling/workflow_supervisor/scripts/harness.sh change --goal "<new request>" --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh status --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment prepare --goal "<goal>" --dry-run
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment prepare --goal "<goal>"
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment prepare --goal "<goal>" --complete --dataset-source <path-or-url> --dataset-target <path> --baseline-repo <path-or-url> --allow-external-downloads
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment build --goal "<goal>" --auto
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment build --goal "<goal>" --worker-command '<command template>'
tooling/workflow_supervisor/scripts/workflow_ctl.sh approve --request-id <id> --decision approve --approved-by "<human>" --approval-source ".evidence/review_packets/<stage>/<build_id>/review_packet.md"
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment iterate --goal "<goal>" --auto-goal docs/auto_iterate_goal.md
tooling/workflow_supervisor/scripts/workflow_ctl.sh monitor-iterate --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment change --goal "<new request>" --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment release --goal "package release artifacts" --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh validate-nodes
tooling/workflow_supervisor/scripts/workflow_ctl.sh validate-postconditions --node-id build_validate_run --run-id <run_id> --worker-result <result.json> --json
```

Do not hand-edit `.workflow_supervisor/**`; use the supervisor tooling.

## Hooks And Contracts

Workspace-local Codex hooks are optional but recommended:

```bash
python tooling/codex_hooks/install_hooks.py --workspace-root .
python tooling/codex_hooks/hook_status.py --workspace-root .
python tooling/codex_hooks/hook_status.py --workspace-root . --trust-status
python tooling/codex_hooks/check_contracts.py --workspace-root .
```

The hook model:

```text
Codex sandbox
  -> coarse filesystem/network boundary

Harness hooks
  -> route hints and workspace capsule
  -> one-time advisory notices
  -> tool-owned path blocks
  -> external review guard
```

Hooks are runtime guardrails, not proof that a research gate passed. Readiness still depends on tooling outputs, tests, Review Packets, Gate Ledger, and explicit Human Approval.

Generate the detailed Stage reference:

```bash
python tooling/codex_hooks/generate_stage_cards.py --workspace-root . --output workflow_handbook/Workflow_Stage_Cards.md
```

## Auto-Iterate

Prepare the goal:

```bash
$auto-iterate-goal check
```

Start a controller-assisted WF10 loop from the target research workspace:

```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh start \
  --tool codex \
  --goal docs/auto_iterate_goal.md \
  --config tooling/auto_iterate/config/controller.local.yaml
```

Useful controller commands:

```bash
tooling/auto_iterate/scripts/auto_iterate_ctl.sh status --json
tooling/auto_iterate/scripts/auto_iterate_ctl.sh tail --jsonl --lines 50
tooling/auto_iterate/scripts/auto_iterate_ctl.sh pause
tooling/auto_iterate/scripts/auto_iterate_ctl.sh resume
tooling/auto_iterate/scripts/auto_iterate_ctl.sh stop
```

Risk flags such as `--allow-draft-contract`, `--allow-review-required`, and `--skip-dynamic-preflight` require explicit operator acceptance for that run. They are not permanent approval.

## Bootstrap

For full setup, read [AI_AGENT_SETUP.md](AI_AGENT_SETUP.md). The short version:

```text
target workspace
  -> normal research .git

Harness framework
  -> .harness

shared worktree
  -> CLAUDE.md, AGENTS.md, PROJECT_STATE.json, iteration_log.json,
     project_map.json, docs/**, src/**, configs/**, scripts/**
```

Recommended WF0 order:

1. Choose the real target workspace root.
2. Move framework git history to `.harness`.
3. Initialize or reuse the normal research `.git`.
4. Create `CLAUDE.md`, `AGENTS.md`, `MEMORY.md`, and `docs/auto_iterate_goal.md`.
5. Optionally initialize dynamic context docs and `.evidence/` with tooling.
6. Configure local auto-iterate YAML.
7. Verify hooks, contracts, and controller plumbing.

## Claude Code And Codex

Both agents share the same workflow state, iteration schema, and decision vocabulary.

| | Claude Code (`.claude/`) | Codex (`.agents/`) |
| --- | --- | --- |
| Execution mode | Interactive | Batch/controller-friendly |
| Best for | exploratory work, debugging, human-steered sessions | unattended multi-round WF10 optimization |
| Auto-iterate | manual loop only | full controller support |
| Safety net | human reviews each step | controller postconditions + hooks + contracts |

In practice: use Claude Code for interactive research sessions and Codex for controller-driven WF10 loops.

## AI Read To Setup And Update

AI agent 在 setup、同步、维护、更新 Harness 时，应该按任务读取内部资料。不要要求 researcher 逐一阅读这些文件；AI 应该把结论压缩成可判断的 Review Packet、Gate Ledger 或明确的下一步选择。

| Task | AI should read |
| --- | --- |
| Repository orientation | `AGENTS.md`, `CLAUDE.md`, `README.md` |
| Bootstrap or refresh workspace setup | [AI_AGENT_SETUP.md](AI_AGENT_SETUP.md), `templates/**`, [tooling/auto_iterate/docs/cli_control_guide.md](tooling/auto_iterate/docs/cli_control_guide.md), [tooling/auto_iterate/docs/auto_iterate_goal_template.md](tooling/auto_iterate/docs/auto_iterate_goal_template.md) |
| Workflow docs or operator guidance update | [workflow_handbook/Workflow_Operator_Handbook.md](workflow_handbook/Workflow_Operator_Handbook.md), [workflow_handbook/Workflow_Stage_Cards.md](workflow_handbook/Workflow_Stage_Cards.md), `.agents/references/ubiquitous-language.md` |
| Skill, routing, or contract update | relevant `.agents/skills/*/SKILL.md`, relevant `.claude/skills/*/SKILL.md`, `schemas/skill_contracts.json` |
| Hook or permission boundary update | [tooling/codex_hooks/README.md](tooling/codex_hooks/README.md), `schemas/skill_contracts.json`, `tooling/.tests/test_codex_hooks_contracts.py` |
| Dynamic context, protocol, or review packet update | `tooling/evidence/**`, `schemas/**`, `.agents/skills/protocol-compiler/SKILL.md`, `.agents/skills/protocol-drift-check/SKILL.md`, `.agents/skills/review-packet/SKILL.md` |
| WF10 auto-iterate update | `.agents/skills/iterate/SKILL.md`, `.agents/skills/auto-iterate-goal/SKILL.md`, `tooling/auto_iterate/**`, `tooling/.tests/test_auto_iterate*.py` |
| Grill or supervisor update | `docs/grill_execution_supervisor.md`, `docs/grill_execution_supervisor_implementation_plan.md`, `.agents/skills/grill/SKILL.md`, `.agents/skills/workflow-supervisor/SKILL.md`, `tooling/workflow_supervisor/**`, `tooling/.tests/test_workflow_supervisor*.py` |

## Human Read

The human-facing entry point is [workflow_handbook/Workflow_Operator_Handbook.md](workflow_handbook/Workflow_Operator_Handbook.md).

## Acknowledgment

Some controller ideas are based on [ralph](https://github.com/snarktank/ralph).
