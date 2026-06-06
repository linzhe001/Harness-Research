# Grill + Execution Supervisor Implementation Plan

## Context Summary

本文档是把当前 Harness workflow 改造成 `grill + execution supervisor`
架构的实施计划。它不是重新解释机制的概念，而是说明现有仓库应该如何改：

- 哪些 framework files、schemas、Skills、hooks、tooling 要新增或调整。
- `.evidence/**` 如何参与，但仍保持 tool-owned。
- 哪些 docs 在什么时候生成，哪些 docs 需要 Evidence Chain。
- 每个 Stage、每次 supervisor run、每个 node run 应记录什么。
- 用户输入导致中断后，用户应如何提供信息，supervisor 如何继续。
- 如何逐步 rollout，避免一次性重写整个 workflow。

本文以当前仓库状态为前提：Harness framework 已有 WF0-WF12、Skill Contracts、
dynamic-context evidence tooling、Review Packet tooling、Codex hooks、以及 WF10
auto-iterate controller。计划的核心不是删除现有 workflow，而是增加一个可恢复的
supervisor layer，让现有 Skills 成为可编排节点。

用户文档必须 top-level entrypoint first：先说明只有 `grill` 和
`execution supervisor` 两个第一层入口；`prepare/build/iterate/release/change`
只是 Execution Supervisor actions，用来说明怎么运行、看什么状态、何时暂停。
WF0-WF12 只作为 detailed reference、compatibility 和 postcondition 语言出现。

## Document Boundary

本文档只负责回答“如何把设计落到 Harness Research 仓库”：

- 新增或修改哪些 framework files、schemas、Skills、hooks 和 tests。
- `.workflow_supervisor/**`、`.auto_iterate/**`、`.evidence/**` 的 ownership 如何划分。
- 每个 segment 的 first implementation slice、acceptance criteria 和 validation
  commands。
- HITL interrupt 后用户如何通过 CLI / approval artifact 回答，以及 supervisor
  如何 resume。

机制层面的论证、外部实践、HITL 设计原则、workflow-vs-agent 取舍、approval UX
原则，放在 `docs/grill_execution_supervisor.md`。本文可以引用这些原则，但避免再
维护一份外部实践综述或概念解释。

## Reader Path

- Operator：先读 `workflow_handbook/Workflow_Operator_Handbook.md` 和
  `workflow_handbook/pages/operator_task_index.md`。
- Maintainer：先读本文的 frozen decisions、slice plan、schemas、tests。
- Reviewer：先读 acceptance criteria、validation commands、known non-goals。
- Deep debugging：再读 generated detailed reference。

## Currentness Rule

本文是 implementation plan，不是运行状态报告。每次继续实现前必须重新读取当前
source files、schemas、tests 和 CLI output；不能因为本文列过某个状态就推断当前
仓库已经满足。修改 durable Markdown 后，重建 handbook reference index 和
`docs/_site/workflow_handbook/**`。

## Evidence Sources

| Source | Why It Was Read | Key Facts Used |
| --- | --- | --- |
| `docs/grill_execution_supervisor.md` | 机制参考架构 | 已定义 Grill mode、Execution supervisor mode、Change intake、Execution Readiness Packet、typed HITL interrupts、postconditions、segments。 |
| `README.md` | 当前 Harness 总体目标和 artifacts | Harness 目标是减少科研执行摩擦，不替研究者产生 idea；已有 WF0-WF12、dynamic context tooling、WF10 auto-iterate controller。 |
| `AGENTS.md` | 本仓库工作边界 | `.evidence/**` 和 `.auto_iterate/**` 不能手写；Human Approval 对 contracts、claim boundaries、高风险 transitions、release decisions 强制。 |
| `CLAUDE.md` | 当前 framework 结构和语言策略 | 当前 repo 是 framework repo；target research state 属于目标 workspace；自然语言 artifacts 应匹配用户语言。 |
| `.agents/references/workflow-guide.md` | Canonical workflow 和 state ownership | `PROJECT_STATE.json`、`iteration_log.json`、`project_map.json`、`.auto_iterate/**` 的 ownership；Gate Evidence model；dynamic context layer。 |
| `.agents/references/evidence-chain-rule.md` | `.evidence` 和 docchain 规则 | `.evidence/chains/**`、`.evidence/index.json` 由 tooling 生成；current contract/fact/protocol/release docs 需要 `compile_doc.py` 和 docchain gates。 |
| `.agents/references/contract-gating-rule.md` | Contract approval 语义 | Review Packet 不是 approval；`approve_contract.py` 只能在 explicit Human Approval 后运行；approved contract 要同时更新 Markdown 和 `PROJECT_STATE.json`。 |
| `.agents/references/context-layering-policy.md` | Context 分层 | Operator Context、local/private inputs、Conclusion Evidence、Protocol Draft、Approved Contracts、Project facts、Runtime state 必须分层。 |
| `.agents/skills/protocol-compiler/SKILL.md` | Protocol Draft 生成流程 | `compile_protocol.py` 生成 `.evidence/protocol_compiler/**`，apply 前需要 review；Protocol Draft 不能变成 Approved Contract。 |
| `.agents/skills/doc-compiler/SKILL.md` | Current docs 可信链 | contract/fact/protocol/release docs 要用 `compile_doc.py` 生成 Evidence Chain、source manifest、doc audit。 |
| `.agents/skills/review-packet/SKILL.md` | Human decision packet | `check_dynamic_context.py --review-packet` 和 `build_review_packet.py` 生成 `.evidence/review_packets/**`；approval 另走 `approve_contract.py`。 |
| `.agents/skills/docs-site/SKILL.md` | HTML docs render boundary | `docs/_site/**` 和 `docs/_views/**` 是 generated view；在 durable Markdown finalized 后才渲染。 |
| `.agents/skills/iterate/SKILL.md` | WF10 ownership | `$iterate` 仍拥有 `iteration_log.json`；controller 只调 phase 和检查 postconditions。 |
| `.agents/skills/code-expert/SKILL.md` | WF8 first-pass implementation boundary | `$code-expert` 用于 roadmap first-pass code generation，不应成为 post-codebase delta 的默认入口。 |
| `.agents/skills/code-debug/SKILL.md` | Post-WF8 change route | `$code-debug` 是 bugfix、planned iteration change、narrow performance tuning 的默认入口。 |
| `tooling/auto_iterate/docs/cli_control_guide.md` | 可复用 controller contract | 已有 start/status/pause/stop/resume、JSON status、JSONL events、exit codes、`manual_action_required`。 |
| Autoresearch-style docs, 2026-06-05 local review | 文档结构参考 | 用户文档应先给 quick start、status/monitoring、resume/recovery、workdir/state surface，再给深层机制。 |
| `tooling/auto_iterate/scripts/auto_iterate/controller.py` | 可复用 controller design | 现有 controller 使用 `.auto_iterate` state、lock、heartbeat、events、dynamic preflight、fresh Codex phases、postconditions。 |
| `schemas/skill_contracts.json` | 当前 Skill Contract machine-readable surface | 已有 triggers、required reads、required actions、forbidden actions、gates、sensitive paths、write scopes、artifact outputs。 |

## Verified Facts

- 当前 framework 已有手动 Skill workflow 和 WF10 auto-iterate controller。
- 当前 `.evidence/**` 是 tool-owned，不能由 agent 或 supervisor 手写。
- Review Packet 是 human decision input，不是 Approval Evidence。
- `approve_contract.py` 只能在当前对话或可审计 artifact 中有 explicit Human Approval 后运行。
- `docs/_site/**` 和 `docs/_views/**` 是 generated views，不是 Markdown source of truth。
- 这个 framework repo 默认忽略 `/docs/*`，需要 `.gitignore` 例外才能跟踪新增 framework docs。

## Inferences

- 实施应分层，不应一次性重写 WF0-WF12。
- 应先复用 `tooling/auto_iterate` 的状态机模式，做 lightweight supervisor，而不是立刻引入 Temporal/Restate。
- Grill 输出中的本地路径、预算、命令等 readiness 信息应先作为 candidate inputs，不能直接成为 verified project facts。
- Execution supervisor 应通过 node postconditions、Gate Evidence 和 Review Packets 判断是否继续，而不是信任 worker prose。
- 新架构需要新增 runtime namespace：`.workflow_supervisor/**`，避免污染 `.auto_iterate/**`。

## Open Questions

这些问题仍可在后续版本重新评估，但 v0 implementation 必须先冻结选择，避免每个
slice 重新分叉。冻结决策见下一节。

- `docs/05_intake/**` 是否应成为长期动态上下文目录。
- `workflow_supervisor_nodes.json` 稳定后是否合并为 `schemas/skill_contracts.json`
  的 `automation_policy`。
- 是否需要 human-facing dashboard 或 Slack/email approval channel。
- 当 supervisor 变成默认 route 后，是否需要跨机器 durable backend。

## V0 Frozen Decisions

| Decision Area | V0 Decision | Reason |
| --- | --- | --- |
| Runtime namespace | Use `.workflow_supervisor/**`; do not extend `.auto_iterate/**`. | Keeps WF10 controller ownership separate from general supervisor state. |
| Grill artifacts | Write `docs/Research_Intent_Draft.md`, `docs/Grill_Round_Log.md`, and `docs/Execution_Readiness_Packet.md`. | Preserves current operator-readable Markdown convention while keeping Grill output draft-only. |
| Exact local readiness values | Store exact paths, commands, budgets, and local/private values in `.workflow_supervisor/readiness.json`; Markdown packet may redact sensitive values. | Prevents local execution details from being promoted into public/current docs before verification. |
| Grill implementation shape | Add a `grill` Skill plus lightweight `tooling/grill/**` helpers; optional CLI wrapper may call the Skill, but v0 does not implement Grill as a supervisor subgraph. | Keeps early human discussion separate from execution automation. |
| Node registry | Add `schemas/workflow_supervisor_nodes.schema.json` and `tooling/workflow_supervisor/config/default_nodes.json`; do not modify `schemas/skill_contracts.json` in the first runtime slice. | Avoids destabilizing hook/contract behavior before the registry contract is tested. |
| Human interface | Use CLI + Markdown/Review Packet payloads; no dashboard in v0. | Matches local research workspace usage and keeps implementation auditable. |
| Change intake action | Add explicit `harness change` / `workflow_ctl start --segment change` as an Execution Supervisor action; later `build` or `iterate` may internally route to it only after classifier tests pass. | Prevents post-codebase requests from silently becoming code edits while keeping only two top-level entrypoints. |
| Default enablement | Manual Skill workflow remains default until the final default-enablement gate passes. | Preserves existing Harness behavior during rollout. |

## Operator Documentation Contract

所有 human-facing supervisor 文档都应遵循同一顺序：

```text
what you want
  -> top-level entrypoint
  -> supervisor action, when applicable
  -> command
  -> required input
  -> status surface
  -> output artifact
  -> pause / approval condition
  -> detailed reference
```

Required index surfaces:

- `workflow_handbook/Workflow_Operator_Handbook.md`: short mental model and
  quick task index.
- `workflow_handbook/pages/operator_task_index.md`: complete task-to-mode/action
  index.
- `workflow_handbook/pages/workflow_supervisor_model.md`: two top-level modes,
  supervisor actions, status surfaces, HITL boundary.
- `workflow_handbook/Workflow_Stage_Cards.md`: detailed internal reference
  generated from Skill Contracts.
- `README.md`: repository-level overview that links to the operator index
  before listing WF0-WF12.

## Completeness Check

两份文档合在一起已经覆盖 v0 架构设计所需的关键面：

| Area | Covered In | Current Status |
| --- | --- | --- |
| mechanism purpose and non-goals | `docs/grill_execution_supervisor.md` | covered |
| Grill / execution supervisor / change intake boundary | `docs/grill_execution_supervisor.md` | covered |
| HITL interrupt semantics and approval UX | `docs/grill_execution_supervisor.md` | covered |
| Harness runtime namespace and state records | this plan | covered as implementation target |
| `.evidence/**` ownership and evidence tool integration | this plan | covered as implementation target |
| docs generation and doc trust path | this plan | covered as implementation target |
| segment rollout and tests | this plan | covered as implementation target |
| exact schema details and CLI behavior | this plan | v0 contract specified; code/schema files still need implementation |

The remaining work is implementation, not mechanism design: schema drafts,
tooling code, hooks, tests, templates, and fixture runs still need to be built
and validated before supervisor mode can become a default route.

## Implementation Reference Synthesis

Reference Links 支持一个保守实现方向：先做 Harness-native lightweight
supervisor，而不是把 Harness 迁移到某个外部 agent framework。

可直接吸收的模式：

- LangGraph 的 `interrupt` / checkpointer 模式对应 Harness 的
  `pending_request.json`、`run_id`、`resume_strategy` 和 durable state。
  关键约束是：resume 要使用同一个持久 cursor；interrupt payload 必须
  JSON-serializable；interrupt 前的副作用必须可重跑或有 idempotency。
- OpenAI Agents SDK 的 HITL `RunState` 模式对应 Harness 的
  `worker_result.json` + `pending_request.json` + `workflow_ctl approve/resume`。
  关键约束是：approval/rejection 作用于具体 interruption；nested worker
  interruption 必须冒泡到 outer supervisor，而不是由 worker 私自处理。
- HumanLayer 12-factor-agents 对 Harness 最有价值的是
  own control flow、tools as structured outputs、launch/pause/resume API、
  contact humans with tool calls、small focused agents。也就是说第一版不应
  引入自由多 agent swarm，而应把 Skill worker 结果变成 structured output。
- awaithumans 的可借鉴点是 typed request/response、idempotency key、
  audit trail 和多 channel reviewer UX。Harness v0 可先用 CLI/Markdown，
  但 schema 应保留 `request_id`、`idempotency_key`、`answered_by`、
  `answered_at`、`approval_source`。
- IRAS 的可借鉴点是 deterministic graph nodes、typed state、approval API、
  timeout escalation、rollback-aware remediation。Harness 对应的是 node
  registry、postcondition validators、timeout/escalation policy 和
  `manual_recover`。

不建议第一版采用的模式：

- 不引入 Temporal / Dapr / Restate / DBOS 作为本地默认依赖。只保留状态模型和
  event contract 兼容这些 durable platforms，等出现多用户、多机器、长时间等待
  需求后再替换 backend。
- 不把 Grill 拆成多个自由协作 specialist agents。先用一个 facilitator model
  call 输出多个 review lenses，便于调试和 gate。
- 不把 supervisor registry 合并进 `schemas/skill_contracts.json` 作为第一步。
  先用独立 node registry，稳定后再考虑 `automation_policy`。

## Review Finding Resolutions

本节把当前 implementation review 中的六个问题变成 v0 必须满足的约束。

### 1. Grill Must Bridge, Not Replace, WF1-WF3 Artifacts

`Research Intent Draft` 不是 `docs/Feasibility_Report.md`、
`docs/Idea_Debate.md` 或 `docs/Refined_Idea.md` 的替代品。

v0 行为：

```text
harness grill
  -> writes Grill draft artifacts
  -> records operator exit decision
  -> does not mark WF1/WF2/WF3 complete

harness grill --bridge-stages
  -> uses accepted Research Intent Draft as input context
  -> runs or prompts the existing WF1/WF2/WF3 Skills in order
  -> only marks a Stage complete when its canonical artifact and Gate ledger exist
```

Required postconditions:

- WF1 complete requires `docs/Feasibility_Report.md` or explicit legacy
  compatibility decision plus Gate ledger.
- WF2 complete requires `docs/Idea_Debate.md` or explicit operator decision to
  defer debate, with the deferral recorded as a risk.
- WF3 complete requires `docs/Refined_Idea.md` or an accepted
  `Research Intent Draft` promoted through the existing `$refine-idea` contract.
- `Research Intent Draft` may be an input source to protocol/compiler work, but
  it is not an Approved Contract and not verified Current Facts.

### 2. Prepare PoC Is Not `prepare_complete`

The first prepare slice can prove HITL and Review Packet plumbing without
claiming WF4/WF5 completion.

Use explicit run states:

```text
prepare_hitl_poc
  -> readiness preflight
  -> protocol-compiler / review-packet if enough evidence exists
  -> pending approval/revision interrupt
  -> status = paused | poc_complete

prepare_complete
  -> data-prep postconditions
  -> baseline-repro postconditions
  -> WF5 dynamic-context gate
  -> required approval/revision handled
```

`poc_complete` must not unlock build, iterate, or release. Build starts only
from `prepare_complete` or from an explicit legacy/manual compatibility
decision recorded by `$orchestrator`.

### 3. Worker Result Contract Is Required

Skill workers must not communicate machine state through prose only. Add:

- `schemas/workflow_supervisor_worker_result.schema.json`
- `tooling/workflow_supervisor/scripts/run_worker.py` or equivalent adapter
- tests for success, failure, interrupt request, malformed result, and
  forbidden direct user question

Minimum worker result:

```json
{
  "schema_version": 1,
  "run_id": "sup_...",
  "node_id": "wf7_build_plan",
  "skill": "build-plan",
  "status": "success|failed|interrupt_requested|not_run",
  "summary": "short human-readable result",
  "artifact_refs": [],
  "gate_ledger": [
    {
      "command": "exact command or not run",
      "result": "PASS|FAIL|NOT_RUN",
      "reason": "why required or why not run",
      "artifacts": []
    }
  ],
  "postcondition_claims": [],
  "interrupt_request": null,
  "worker_warnings": []
}
```

Supervisor accepts a node only when this result validates and postcondition
validators pass. If the worker asks the user directly, omits Gate ledger for a
touched gate, or writes supervisor runtime state, classify as
`failed_contract_violation`.

### 4. `.workflow_supervisor/**` Is Controller-Owned Runtime

Implementation must update all current guardrail surfaces:

- root `.gitignore`: ignore `/.workflow_supervisor/`;
- `tooling/codex_hooks/harness_contracts.py`:
  - add `.workflow_supervisor/` to `DIRECT_TOOL_OWNED_PATHS`;
  - add `tooling/workflow_supervisor/` to `TOOL_OWNED_WRITE_TOOL_PREFIXES`;
- `tooling/codex_hooks/README.md`, `AGENTS.md`, `CLAUDE.md`,
  `.agents/references/workflow-guide.md`, `.claude/Workflow_Guide.md`:
  document the runtime boundary;
- tests:
  - manual Edit/Write/apply_patch to `.workflow_supervisor/**` is blocked;
  - supervisor tooling commands are allowed;
  - `.workflow_supervisor/**` is not included in Skill artifact outputs unless
    the owner is supervisor tooling.

### 5. Approval Resume Must Preserve `approval_source`

`workflow_ctl approve` must not be a local boolean toggle. It must bridge to
`approve_contract.py` with an auditable approval source.

Required CLI behavior:

```bash
tooling/workflow_supervisor/scripts/workflow_ctl.sh approve \
  --request-id req_... \
  --decision approve \
  --approved-by "<human reviewer>" \
  --approval-source ".evidence/review_packets/<stage>/<build_id>/review_packet.md"
```

If `--approval-source` is omitted, the CLI may derive it only when exactly one
review packet path exists in `pending_request.evidence_refs`. Otherwise it must
fail closed and ask for an explicit source.

Required checks:

- decision is in `allowed_responses`;
- approved action matches `pending_request.exact_action`;
- approval source is recorded in the answer record;
- `approve_contract.py` runs only after explicit approval;
- dynamic-context gate reruns after approval;
- reject/revise never marks contract approved.

### 6. Handbook Integration Must Respect Source-Of-Truth Rules

Do not add a new top-level narrative file under `workflow_handbook/`. Current
tests require the top-level human entrypoints to remain
`Workflow_Operator_Handbook.md` and `Workflow_Stage_Cards.md`.

Required handbook changes:

- add `workflow_handbook/pages/workflow_supervisor_model.md`;
- update `workflow_handbook/config/navigation.json`;
- update `Workflow_Operator_Handbook.md` so the run model becomes:

```text
Intent
  -> Entrypoint
  -> Stage
  -> Skill
  -> Gate
```

- keep `Workflow_Stage_Cards.md` generated from `schemas/skill_contracts.json`;
- add Skill Contracts for `grill`, `workflow-supervisor`, and `change-intake`
  before their rollout slices are accepted, then regenerate Stage/Skill handbook
  pages with `generate_stage_cards.py`;
- update `tooling/.tests/test_workflow_handbook_site.py` and
  `test_codex_hooks_contracts.py` so the new page is validated without adding
  a third top-level handbook entrypoint.

## Target Architecture

### Control Layers

```text
Human operator
  -> Grill / Delta Grill
  -> Execution Supervisor
  -> Skill Worker
  -> Evidence tooling / local commands
  -> Gate Evidence / Review Packet / Approval Evidence
```

职责边界：

| Layer | Owns | Must Not Own |
| --- | --- | --- |
| Grill | Research intent clarification, hard questions, candidate readiness inputs | Approved Contracts, verified environment facts |
| Execution Supervisor | runtime state, node order, interrupts, postcondition checks | Stage artifacts, `.evidence/**`, `iteration_log.json`, `PROJECT_STATE.json` transitions |
| Skill Worker | stage/task-specific artifact generation | supervisor state, Human Approval |
| Evidence Tooling | `.evidence/**`, Review Packets, approval records | semantic truth, human judgment |
| Orchestrator | Stage transitions and `PROJECT_STATE.json` transition decisions | `iteration_log.json`, supervisor runtime state |
| Auto-Iterate Controller | WF10 loop runtime under `.auto_iterate/**` | arbitrary Stage flow or contracts |

### Design-to-Implementation Map

This map removes ambiguity between the mechanism document's Segment A-F, this
plan's implementation segments, and rollout slices.

| Design Segment | Implementation Segment | Rollout Slice | First Code Deliverable | Exit Status |
| --- | --- | --- | --- | --- |
| Shared runtime foundation | Segment 0: Bootstrap and Compatibility | Slice 1 and Slice 3 | schemas, `default_nodes.json`, `workflow_ctl.py status/start`, state/lock/events tests | `idle` or dry-run `completed` |
| Segment A: Grill | Segment 1: Grill | Slice 2 | `grill` Skill, `tooling/grill/**`, draft/readiness templates | `grill_draft_ready` or `grill_bridge_complete` |
| Segment B: Prepare | Segment 2: Prepare Supervisor and Segment 3: Data and Baseline | Slice 4 and part of Slice 5 | readiness preflight, protocol/review-packet nodes, later data/baseline nodes | `prepare_hitl_poc` or `prepare_complete` |
| Segment C: Build | Segment 4: Build | part of Slice 5 | build-plan/code-debug/validate-run nodes and postcondition validators | `build_ready_for_iterate` |
| Segment D: Iterate | Segment 5: Iterate Delegation | Slice 6 | auto-iterate wrapper node and halt reason mapping | `iterate_delegated` |
| Segment F: Change Intake | Segment 6: Change Intake | Slice 7 | Change Request schema, classifier, delta grill route | `change_routed` |
| Segment E: Release | Segment 7: Release | Slice 8 | final-exp/release nodes and release approval interrupt | `release_ready_for_approval` |

### Runtime Namespaces

```text
.workflow_supervisor/                 # new controller-owned runtime
  state.json
  lock.json
  events.jsonl
  pending_request.json
  readiness.json
  readiness_preflight.json
  runs/<run_id>/
    run_manifest.json
    node_runs/<node_id>.json
    gate_results/<gate_id>.json
    runtime/*.stdout.log
    runtime/*.stderr.log
    runtime/*.brief.json
    runtime/*.result.json

.auto_iterate/                        # unchanged WF10 runtime
  state.json
  events.jsonl
  runtime/**

.evidence/                            # unchanged tool-owned evidence/audit
  chains/**
  protocol_compiler/**
  review_packets/**
  index.json
```

`.workflow_supervisor/**` should be ignored in target research workspaces, like
`.auto_iterate/**`, but can be inspected for recovery and audit.

### Runtime File Ownership

| Path | Owner | Written By | Committed? | Notes |
| --- | --- | --- | --- | --- |
| `.workflow_supervisor/state.json` | Execution Supervisor | `workflow_ctl.py` only | No | Active run cursor; never hand-edit. |
| `.workflow_supervisor/lock.json` | Execution Supervisor | `workflow_ctl.py` only | No | Concurrency control and stale-lock recovery. |
| `.workflow_supervisor/events.jsonl` | Execution Supervisor | `workflow_ctl.py` only | No | Append-only audit trail, not the resume cursor. |
| `.workflow_supervisor/pending_request.json` | Execution Supervisor | `workflow_ctl.py` only | No | Typed HITL request. |
| `.workflow_supervisor/readiness.json` | Grill / Supervisor tooling | `tooling/grill/**` or `workflow_ctl.py` | No | Exact local candidate inputs; may contain private paths. |
| `.workflow_supervisor/runs/<run_id>/**` | Execution Supervisor | `workflow_ctl.py` and run adapters | No | Run-local logs, node records, summaries, worker results. |
| `.auto_iterate/**` | Auto-Iterate Controller | `auto_iterate_ctl.sh` and controller code | No | Supervisor may read status, not write. |
| `.evidence/**` | Evidence Tooling | `tooling/evidence/**` only | Depends on target workspace policy | Supervisor stores refs only and must not write directly. |
| `docs/Research_Intent_Draft.md` | Grill Skill | `tooling/grill/**` / Skill worker | Yes in target workspace | Draft intent, not Approved Contract. |
| `docs/Execution_Readiness_Packet.md` | Grill Skill | `tooling/grill/**` / Skill worker | Yes in target workspace | Redacted/local-safe summary; exact values stay in runtime JSON. |
| `docs/_views/**`, `docs/_site/**` | Docs renderer | `tooling/evidence/build_docs_site.py` | Generated view policy | Never source of truth. |

## Documentation and Evidence Model

### Document Classes

| Class | Example | Source of Truth | Evidence Chain Required? |
| --- | --- | --- | --- |
| Framework design docs | `docs/grill_execution_supervisor.md`, this plan | Markdown in framework repo | No, but must include Evidence Sources / Verified Facts / Inferences / Open Questions |
| Grill draft docs | `docs/Research_Intent_Draft.md`, `docs/Grill_Round_Log.md` | Markdown + supervisor/grill state | No by default; use Evidence Sources and mark draft/open questions |
| Execution readiness docs | `docs/Execution_Readiness_Packet.md` | Markdown summary + `.workflow_supervisor/readiness.json` | No by default; exact local/private values should be verified before promotion |
| Current fact docs | `docs/20_facts/**` | Markdown + `.evidence/chains/**` | Yes via `compile_doc.py` |
| Protocol drafts | `docs/35_protocol/**` | Markdown + `.evidence/protocol_compiler/**` + docchain when current | Yes when used for decisions |
| Contract docs | `docs/10_contract/**` | Markdown + `.evidence/chains/**` + `PROJECT_STATE.json` approval markers | Yes; stronger support required |
| Review Packets | `.evidence/review_packets/**` | Evidence tooling output | Generated by `check_dynamic_context.py` / `build_review_packet.py` |
| Iteration docs | `docs/40_iterations/**`, `iteration_log.json` | `$iterate` and `$evaluate` | Gate ledger required; docchain only when promoted into current facts/claims |
| Generated HTML | `docs/_site/**`, `docs/_views/**` | Renderer output | No; it is a view over Markdown and `.evidence/index.json` |

### When Docs Are Generated

```text
Grill round
  -> update Research Intent Draft
  -> append Grill Round Log
  -> optionally update Execution Readiness Packet
  -> no approval, no docchain by default

Prepare segment
  -> data-prep / baseline-repro write stage docs
  -> evidence tables in docs/30_evidence/**
  -> protocol-compiler may generate Protocol Draft
  -> doc-compiler compiles current fact/protocol/contract docs
  -> review-packet builds human decision packet

Build segment
  -> Technical_Spec / Implementation_Roadmap / Codebase_Map
  -> project_map.json sync
  -> compile_doc for Codebase_Map when current fact doc changed
  -> validate-run writes Validate_Run_Report

Iterate segment
  -> iteration_log.json + docs/40_iterations/**
  -> no direct MEMORY promotion unless lesson-quality rule passes
  -> final claim material must later pass docchain/context gates

Release segment
  -> final experiment matrix
  -> release/claim docs
  -> compile_doc + check_dynamic_context --stage wf12 --review-packet
```

### How Docs Become Trustworthy

The trustworthy-doc path is:

```text
Source Artifact
  -> Markdown with fact/open-question markers
  -> compile_doc.py / compile_protocol.py
  -> .evidence/chains or .evidence/protocol_compiler
  -> check_docchain_gates.py / check_dynamic_context.py
  -> Review Packet
  -> explicit Human Approval when required
```

Rules:

- A Grill draft is useful input, not a verified fact doc.
- A Review Packet is decision input, not approval.
- A contract is approved only after `approve_contract.py` records both Markdown
  and `PROJECT_STATE.json` approval state.
- A fact/protocol/contract/release doc is not machine-verified unless the
  relevant evidence command ran and the Gate ledger reports PASS.
- `docs/_site/**` is never a source of truth; render only after durable Markdown
  is finalized.

## `.evidence` Integration

### Ownership Rule

Supervisor must never write `.evidence/**` directly. It may:

- call evidence tools,
- read evidence outputs,
- store references to evidence paths in `.workflow_supervisor/**`,
- include evidence paths in interrupt payloads.

### Evidence Tool Calls By Supervisor Point

| Supervisor Point | Tooling | Purpose |
| --- | --- | --- |
| dynamic context init | `python tooling/evidence/init_context.py --workspace-root . --set-state` | create numbered docs dirs and dynamic markers |
| evidence table changed | `python tooling/evidence/compile_protocol.py --workspace-root .` | generate `.evidence/protocol_compiler/<build_id>/` |
| protocol accepted for current use | `compile_protocol.py --apply --overwrite` then `compile_doc.py` if current decision material | apply draft and create docchain |
| fact/contract/protocol/release doc changed | `python tooling/evidence/compile_doc.py --workspace-root . --doc <doc> --source <sources...>` | create `.evidence/chains/**` |
| current doc readiness | `python tooling/evidence/check_docchain_gates.py --workspace-root .` | gate docchain readiness |
| WF5/WF10/WF11/WF12 readiness | `python tooling/evidence/check_dynamic_context.py --workspace-root . --stage <stage> --review-packet` | create gate result + Review Packet |
| protocol drift | `python tooling/evidence/check_protocol_drift.py --workspace-root . --stage <stage>` | detect stale protocol/contracts |
| contract approval | `python tooling/evidence/approve_contract.py ...` | record Approval Evidence after explicit Human Approval |
| state consistency | `python tooling/evidence/check_workflow_state.py --workspace-root .` | check state files near transitions |

### Supervisor Evidence References

Each node run should store evidence references, not evidence copies:

```json
{
  "node_id": "wf5_review_packet",
  "evidence_refs": [
    {
      "kind": "review_packet",
      "path": ".evidence/review_packets/wf10/<build_id>/review_packet.md"
    },
    {
      "kind": "docchain",
      "path": ".evidence/chains/docs__10_contract__Evaluation_Contract/<build_id>/evidence_chain.json"
    }
  ]
}
```

## Supervisor State and Records

All supervisor runtime files must be written atomically: write to a temporary
file in the same directory, `fsync` when feasible, then rename. The controller
must hold `.workflow_supervisor/lock.json` before mutating `state.json`,
`pending_request.json`, or a run-local node record. Event appends should be
append-only and never used as the only source of current state.

### Top-Level State Schema

`.workflow_supervisor/state.json` is the durable cursor for the active or most
recent supervisor run. It must be small enough to inspect manually, but complete
enough to resume without reading model prose:

```json
{
  "schema_version": 1,
  "active_run_id": "sup_20260604_000001",
  "status": "idle|running|paused|failed|completed|stopped|recovering",
  "segment": "prepare|build|iterate|release|change",
  "current_node_id": "wf5_review_packet",
  "current_attempt": 1,
  "pending_request_id": "req_20260604_000001",
  "last_event_seq": 42,
  "completed_nodes": ["prepare_readiness_preflight"],
  "failed_nodes": [],
  "resolved_inputs_ref": ".workflow_supervisor/readiness.json",
  "last_failure": null,
  "recovery_strategy": "adopt_if_postconditions_pass_else_rerun",
  "updated_at": "2026-06-04T00:00:00Z"
}
```

Required invariants:

- `status=paused` requires `pending_request_id` and
  `.workflow_supervisor/pending_request.json`.
- `status=running` requires an unexpired lock and a current node.
- `status=completed` requires no pending request and all required segment
  postconditions recorded.
- `last_event_seq` must match the latest parsed event sequence after recovery.
- `resolved_inputs_ref` may point to candidate inputs, but each input must carry
  its own verification status.

### Run Manifest

Every execution supervisor run should write:

```json
{
  "schema_version": 1,
  "run_id": "sup_20260604_000001",
  "segment": "prepare|build|iterate|release|change",
  "started_at": "...",
  "started_by": "operator|cli|wrapper",
  "workspace_root": "...",
  "base_git_commit": "...",
  "base_git_dirty": true,
  "goal": "...",
  "top_level_mode": "execution_supervisor",
  "supervisor_action": "prepare",
  "command": "harness prepare",
  "policy": {
    "max_llm_calls": 50,
    "max_node_attempts": 2,
    "pause_on_gate_fail": true,
    "allow_external_downloads": false
  }
}
```

### Node Run Record

Each node should write a record under `.workflow_supervisor/runs/<run_id>/node_runs/`:

```json
{
  "schema_version": 1,
  "run_id": "sup_...",
  "node_id": "wf5_baseline_repro",
  "skill": "baseline-repro",
  "stage": "WF5",
  "status": "success|failed|paused|adopted|rerun_required",
  "attempt": 1,
  "started_at": "...",
  "finished_at": "...",
  "input_refs": [
    "PROJECT_STATE.json",
    "docs/Execution_Readiness_Packet.md"
  ],
  "output_refs": [
    "docs/Baseline_Report.md",
    "docs/30_evidence/Baseline_Table.md"
  ],
  "evidence_refs": [],
  "gate_refs": [],
  "worker_result_ref": ".workflow_supervisor/runs/sup_.../runtime/wf5_baseline_repro.result.json",
  "observed_writes": [
    "docs/Baseline_Report.md"
  ],
  "postcondition_result": {
    "ok": true,
    "classification": "baseline_report_ready",
    "failed_checks": []
  },
  "contract_violations": [],
  "next_node": "wf5_review_packet"
}
```

Node records must be derived from structured worker results and postcondition
validators. They must not be reconstructed from a natural-language summary.

### Event Log

`events.jsonl` should use a stable machine-readable event contract:

```json
{
  "v": 1,
  "ts": "2026-06-04T00:00:00Z",
  "event": "NODE_COMPLETED",
  "run_id": "sup_...",
  "segment": "prepare",
  "node_id": "wf5_baseline_repro",
  "status": "success",
  "payload": {
    "postcondition": "PASS"
  }
}
```

Required event types:

- `RUN_STARTED`
- `RUN_RESUMED`
- `RUN_STOPPED`
- `RUN_FAILED`
- `NODE_STARTED`
- `NODE_COMPLETED`
- `NODE_FAILED`
- `GATE_STARTED`
- `GATE_COMPLETED`
- `INTERRUPT_CREATED`
- `INTERRUPT_RESOLVED`
- `DOC_GENERATED`
- `DOCCHAIN_COMPILED`
- `REVIEW_PACKET_BUILT`
- `APPROVAL_RECORDED`
- `AUTO_ITERATE_DELEGATED`
- `CHANGE_CLASSIFIED`

Each event should include a monotonically increasing `seq` in the concrete
schema. Recovery should replay events only as an audit aid; `state.json` remains
the resume cursor.

### Stage Run Summary

Stage-level summaries should be generated at durable boundaries:

```text
.workflow_supervisor/runs/<run_id>/stage_summary.md
```

This runtime summary is the v0 source for supervisor recovery and audit. If an
operator-facing Markdown copy is needed, generate it from the runtime summary as
`docs/Workflow_Supervisor_Run_Summary.md` or a segment-specific current doc
only after deciding whether it needs docchain support. The runtime summary must
include:

- segment and node list,
- artifacts created,
- gates run,
- Gate ledger,
- unresolved assumptions,
- pending human decisions,
- next safe action.

For current contract/fact/protocol/release docs, summary is not enough; use
`compile_doc.py` and `.evidence/**`.

### Worker Result Implementation Contract

`run_worker.py` must require every worker to emit one JSON result file under the
run-local runtime directory. The supervisor may show the worker summary to the
operator, but it must only make state decisions from this JSON object:

```json
{
  "schema_version": 1,
  "run_id": "sup_...",
  "node_id": "wf7_build_plan",
  "skill": "build-plan",
  "attempt": 1,
  "status": "success|failed|interrupt_requested|not_run",
  "exit_code": 0,
  "started_at": "2026-06-04T00:00:00Z",
  "finished_at": "2026-06-04T00:01:00Z",
  "summary": "short human-readable result",
  "artifact_refs": [],
  "gate_ledger": [],
  "postcondition_claims": [],
  "interrupt_request": null,
  "observed_writes": [],
  "stdout_ref": ".workflow_supervisor/runs/sup_.../runtime/wf7_build_plan.stdout.log",
  "stderr_ref": ".workflow_supervisor/runs/sup_.../runtime/wf7_build_plan.stderr.log",
  "contract_violations": [],
  "worker_warnings": []
}
```

Fail-closed classifications:

| Condition | Classification |
| --- | --- |
| no JSON result file | `missing_worker_result` |
| JSON schema invalid | `malformed_worker_result` |
| worker asks user directly | `worker_direct_user_question` |
| worker writes `.workflow_supervisor/**` or `.auto_iterate/**` | `worker_runtime_ownership_violation` |
| touched gate without Gate ledger | `missing_gate_ledger` |
| declared success but required artifact missing | `postcondition_failed` |
| approval-like action performed without pending request | `approval_bypass` |

`observed_writes` should come from hook metadata or run adapter inspection when
available. If write observation is unavailable, high-risk nodes must pause or
rerun postcondition validators instead of trusting the worker.

## HITL Interrupt and Resume Protocol

### Interrupt Lifecycle

```text
worker or supervisor detects missing input / approval / steering need
  -> write .workflow_supervisor/pending_request.json
  -> emit INTERRUPT_CREATED
  -> set state.status=paused
  -> return exit code 105 manual_action_required
  -> human answers with CLI or review packet approval
  -> supervisor validates answer
  -> emit INTERRUPT_RESOLVED
  -> resume node with adopt/rerun/fail-closed strategy
```

### Pending Request Schema

```json
{
  "schema_version": 1,
  "request_id": "req_20260604_000001",
  "run_id": "sup_20260604_000001",
  "node_id": "wf5_review_packet",
  "type": "ASK_INPUT|APPROVE_ACTION|STEER|REVIEW_EDIT|ESCALATE",
  "reason": "evaluation_contract_approval_required",
  "question": "Approve the Evaluation Contract for unattended WF10?",
  "allowed_responses": ["approve", "revise", "reject"],
  "exact_action": {
    "command": "python tooling/evidence/approve_contract.py ...",
    "contract": "evaluation_contract",
    "approval_source": ".evidence/review_packets/wf10/<build_id>/review_packet.md",
    "action_hash": "sha256:<hash-of-canonical-exact-action>"
  },
  "evidence_refs": [
    ".evidence/review_packets/wf10/<build_id>/review_packet.md"
  ],
  "diff_refs": [],
  "gate_status_refs": [],
  "risk_summary": [],
  "rollback_plan": null,
  "escalation_policy": {
    "expires_at": null,
    "on_expire": "fail_closed"
  },
  "request_snapshot_hash": "sha256:<hash-of-request-payload-without-answer>",
  "resume_strategy": "adopt_if_postconditions_pass_else_rerun",
  "created_at": "...",
  "expires_at": null
}
```

### How the User Provides Information

Supported answer paths:

```bash
# Provide structured input.
tooling/workflow_supervisor/scripts/workflow_ctl.sh answer \
  --request-id req_... \
  --json answers.json

# Approve or reject exact action.
tooling/workflow_supervisor/scripts/workflow_ctl.sh approve \
  --request-id req_... \
  --decision approve \
  --approved-by "<human reviewer>" \
  --approval-source ".evidence/review_packets/wf10/<build_id>/review_packet.md"

# Resume after editing the requested artifact manually.
tooling/workflow_supervisor/scripts/workflow_ctl.sh resume \
  --request-id req_...
```

### CLI Command Matrix

All commands should support `--workspace-root` and `--json` where meaningful.
Commands that mutate supervisor state must acquire `.workflow_supervisor/lock.json`.

| Command | Required Input | Output | Exit Code | Mutates |
| --- | --- | --- | --- | --- |
| `workflow_ctl.py start --segment <segment> --goal <text>` | segment, goal or goal file | run id and status JSON | `0` started, `2` invalid input, `105` manual action required | `state.json`, `lock.json`, `events.jsonl`, `runs/<run_id>/**` |
| `workflow_ctl.py status --json` | workspace root | current state, pending request ref, last event seq | `0` status available, `3` no supervisor state | none |
| `workflow_ctl.py pause --reason <reason>` | active run | paused state JSON | `0` paused, `4` no active run | `state.json`, `events.jsonl` |
| `workflow_ctl.py stop --reason <reason>` | active run | stopped state JSON | `0` stopped, `4` no active run | `state.json`, `events.jsonl` |
| `workflow_ctl.py resume --request-id <id>` | matching pending request or recoverable paused run | resumed/adopted/rerun status JSON | `0` resumed, `2` stale request, `105` still blocked | `state.json`, `events.jsonl`, node records |
| `workflow_ctl.py answer --request-id <id> --json <file>` | typed answer file | accepted answer record or validation error | `0` accepted, `2` invalid/stale answer | `pending_request.json`, `state.json`, `events.jsonl` |
| `workflow_ctl.py approve --request-id <id> --decision <approve|revise|reject>` | approval source or derivable single review packet | approval/rejection record | `0` recorded, `2` invalid/stale approval, `105` needs explicit source | `pending_request.json`, `state.json`, `events.jsonl`; approval tooling mutates contract state |
| `workflow_ctl.py recover --run-id <id>` | existing runtime state | recovery plan or recovered status JSON | `0` recovered, `105` manual recovery required | `state.json`, `events.jsonl` |
| `workflow_ctl.py tail --jsonl` | active or named run | event stream | `0` stream/read success, `3` no events | none |

Exit code `105` is reserved for `manual_action_required`, matching the existing
auto-iterate controller convention. Other nonzero codes should be stable and
documented in `workflow_ctl.py --help`.

The answer file should be typed:

```json
{
  "request_id": "req_...",
  "request_snapshot_hash": "sha256:<hash-from-pending-request>",
  "idempotency_key": "req_...:operator:approve",
  "answered_by": "operator",
  "answered_at": "2026-06-04T00:00:00Z",
  "answers": {
    "dataset_root": "/data/project_x",
    "baseline_download_dir": "/data/baselines"
  }
}
```

Validation rules:

- `ASK_INPUT` answers are candidate inputs until verified.
- `APPROVE_ACTION` answers must match one of `allowed_responses`.
- Approval decision must not change `exact_action`.
- `request_snapshot_hash` in the answer must match the pending request. If it
  differs, reject the answer and require a fresh request.
- `action_hash` must be recomputed before executing the approved action. If the
  command, contract, claim text, target path, or approval source changed, fail
  closed.
- `APPROVE_ACTION` must pass `approval_source` to `approve_contract.py`; the CLI
  may derive it only when the pending request contains exactly one review packet
  reference.
- If the user edits a doc, supervisor reruns the relevant docchain/gate before continuing.
- If a request expired or the current node changed, supervisor rejects the answer and asks for a fresh decision.
- `idempotency_key` prevents duplicate approval execution after retry. Reusing a
  key with a different answer body is a contract violation.

### Resume Strategies

| Strategy | Use When | Behavior |
| --- | --- | --- |
| `adopt_if_postconditions_pass_else_rerun` | node may have completed before pause/crash | inspect artifacts; adopt if valid; otherwise rerun |
| `rerun_idempotent` | gate or compiler can safely rerun | rerun command and update Gate ledger |
| `resume_with_answer` | missing input resolved | merge answer into state, preflight, rerun node |
| `manual_recover` | external side effects may be partial | require operator to inspect logs/artifacts |
| `fail_closed` | approval/release/contract ambiguity | stop until explicit new decision |

### Segment Status and Transition Guards

Supervisor segment status must be explicit. A run cannot infer readiness from
the fact that a previous command completed.

| Segment Status | Meaning | May Unlock |
| --- | --- | --- |
| `grill_draft_ready` | Research Intent Draft exists, but WF1-WF3 bridge has not run. | Nothing; operator may run more Grill or bridge WF1-WF3. |
| `grill_bridge_complete` | WF1-WF3 canonical artifacts and Gate ledger exist. | `prepare_hitl_poc` or manual WF4 route. |
| `prepare_hitl_poc` | readiness/review-packet/approval plumbing proved, but data/baseline postconditions are not complete. | Nothing beyond another prepare run. |
| `prepare_complete` | data-prep, baseline-repro, dynamic context, and required approval/revision checks pass. | `build` after explicit operator or orchestrator decision. |
| `build_ready_for_iterate` | build-plan/code changes/validate-run postconditions pass. | WF10 goal validation; not auto-iterate start by itself. |
| `iterate_delegated` | supervisor has started/monitored WF10 auto-iterate. | No stage transition; defer to WF10 controller result. |
| `release_ready_for_approval` | release docs and gates pass, but human release approval is pending. | Only exact release/submission action after approval. |
| `change_routed` | change request has a deterministic route and postconditions. | The selected route only; no broad workflow advance. |

Guard rules:

- `prepare_hitl_poc` must never satisfy a precondition for `build`, `iterate`,
  or `release`.
- `build_ready_for_iterate` may run `$auto-iterate-goal`, but cannot silently
  start WF10 if required approvals or goal acceptance are missing.
- `release_ready_for_approval` must fail closed if exact claim text or
  `approval_source` changes after request creation.
- Any legacy/manual compatibility decision must be recorded by `$orchestrator`
  and referenced in supervisor state before it can unlock a later segment.

## Segment Implementation Plan

Each implementation segment must state its entry condition, primary deliverable,
machine outputs, exit status, and what it may unlock. That keeps rollout slices
from accidentally turning advisory or proof-of-concept work into workflow
completion.

| Impl Segment | Entry Condition | Primary Deliverable | Machine Outputs | Exit Status | May Unlock |
| --- | --- | --- | --- | --- | --- |
| Segment 0: Bootstrap | framework repo only; no target behavior change | schemas, CLI skeleton, registry skeleton | schema fixtures, dry-run state/events | `idle` or dry-run `completed` | Segment 1/2 implementation work only |
| Segment 1: Grill | operator starts `harness grill` or Skill route | intent/readiness draft flow | Grill draft docs, readiness JSON | `grill_draft_ready` or `grill_bridge_complete` | Prepare only after bridge or explicit operator decision |
| Segment 2: Prepare PoC | accepted intent or compatibility decision | HITL/review-packet plumbing | readiness preflight, review packet refs, pending request | `prepare_hitl_poc`, `paused`, or `failed_contract_violation` | No later segment |
| Segment 3: Data/Baseline | reliable readiness preflight | data/baseline postconditions | verified input refs, baseline/data artifacts, dynamic-context gate refs | `prepare_complete` | Build after operator/orchestrator decision |
| Segment 4: Build | `prepare_complete` | build/validate orchestration | roadmap/code/debug/validate node records, Gate ledger | `build_ready_for_iterate` | WF10 goal validation, not unattended WF10 start |
| Segment 5: Iterate | WF10 goal accepted and gates ready | delegate to auto-iterate | delegation event, status refs, pending request on halt | `iterate_delegated`, `paused`, or `manual_recover` | Follow WF10 controller result only |
| Segment 6: Change Intake | mature codebase or post-WF8 request | deterministic change route | Change Request JSON, classifier output, route postconditions | `change_routed` or `paused` | Selected route only |
| Segment 7: Release | supported final experiment material | release/claim approval flow | release node records, docchain/context refs, approval request | `release_ready_for_approval` | Exact approved release/submission action only |

### Segment 0: Bootstrap and Compatibility

Add framework support without changing existing default behavior:

- Add schemas:
  - `schemas/workflow_supervisor_state.schema.json`
  - `schemas/workflow_supervisor_nodes.schema.json`
  - `schemas/workflow_supervisor_worker_result.schema.json`
  - `schemas/human_interrupt.schema.json`
  - `schemas/execution_readiness.schema.json`
  - `schemas/change_request.schema.json`
- Add `tooling/workflow_supervisor/config/default_nodes.json`.
- Add CLI skeleton:
  - `tooling/workflow_supervisor/scripts/workflow_ctl.py`
  - `tooling/workflow_supervisor/scripts/workflow_ctl.sh`
  - command names from the CLI Command Matrix with validation stubs and stable
    exit codes, even when the command body is not implemented yet.
- Add tests for schemas, loading, `status --json`, state invariants, event
  sequence recovery, worker-result validation, approval hash validation, and
  `.workflow_supervisor/**` guardrails.

This bootstrap phase should not auto-run Skills. Later slices add explicit
worker-backed automation after state, interrupts, and postconditions are in
place.

### Segment 1: Grill

Add a new `grill` Skill and lightweight tooling:

```text
.agents/skills/grill/SKILL.md
tooling/grill/
  state.py
  questions.py
  draft.py
  readiness.py
```

Artifacts:

- `docs/Research_Intent_Draft.md`
- `docs/Grill_Round_Log.md`
- `docs/Execution_Readiness_Packet.md` with redacted/local-safe details
- `.workflow_supervisor/readiness.json` with exact local candidate inputs

Trust model:

- Grill docs include Evidence Sources / Verified Facts / Inferences / Open Questions.
- No Grill output is an Approved Contract.
- Local paths are candidate inputs until readiness preflight verifies them.
- Grill output alone does not mark WF1-WF3 complete; the bridge path must
  produce the existing canonical Stage artifacts and Gate ledger.

### Segment 2: Prepare Supervisor

The low-risk orchestration path remains available as `prepare_hitl_poc`:

```text
readiness preflight
  -> protocol-compiler
  -> review-packet
  -> human interrupt for contract approval/revision
```

This path proves typed HITL, Review Packet handling, and resume. It must not
report `prepare_complete` and must not unlock later segments.

Required postconditions:

- readiness preflight written,
- protocol compiler packet path recorded when run,
- review packet path recorded,
- pending approval request generated when approval is required,
- no direct `.evidence/**` writes by supervisor,
- worker result validates against `workflow_supervisor_worker_result.schema.json`,
- `prepare_hitl_poc` state cannot satisfy any later-segment precondition.

### Segment 3: Data and Baseline

Add `data-prep` and `baseline-repro` only after readiness preflight is reliable.

Rules:

- If dataset path was preanswered, verify path/readability before continuing.
- If baseline cache dir was preanswered, verify directory/writability before continuing.
- If downloads or baseline clones are needed, require explicit
  `--allow-external-downloads` or an explicit Grill readiness policy such as
  `external_download_policy: allow`. Concrete source/target inputs may come
  from CLI, `.workflow_supervisor/readiness.json`, or the Grill bridge parser
  reading `docs/Execution_Readiness_Packet.md`, `docs/Research_Intent_Draft.md`,
  and `docs/Grill_Round_Log.md`.
- Redacted or ambiguous Grill values must not be guessed; produce a typed
  pending request instead.
- Baseline/evaluation evidence should update `docs/30_evidence/**`.
- Evaluation Contract readiness triggers `check_dynamic_context.py --stage wf5 --review-packet`.

Current implementation:

```text
workflow_ctl start --segment prepare --complete
  -> Grill/readiness bridge writes runtime/grill_bridge.json
  -> readiness preflight
  -> deterministic dataset acquisition / verification
  -> deterministic baseline clone / acquisition
  -> protocol-compiler
  -> WF5 Review Packet
  -> APPROVE_ACTION
  -> resume to prepare_complete only after explicit approval
```

### Segment 4: Build

Add build orchestration:

```text
refine-arch
  -> optional deep-check
  -> build-plan
  -> code-expert only for first-pass WF8
  -> code-debug for post-WF8 deltas
  -> validate-run
```

Rules:

- `code-expert` is first-pass only.
- `code-debug` is default for post-WF8 implementation changes.
- Build nodes run through structured workers: `--auto` delegates to Codex and
  `--worker-command` supplies a testable command template.
- Worker prompts include node postconditions and allowed write patterns. A
  worker must run concrete checks, debug failures inside the node budget, and
  record PASS/FAIL/NOT_RUN Gate ledger entries before claiming success.
- Codex worker result JSON uses
  `.agents/state/workflow_supervisor_worker_results/**` as a temporary handoff;
  supervisor runtime state is written only by the supervisor after validation.
- Stable interface/file changes require `project_map.json` and `docs/20_facts/Codebase_Map.md` sync.
- If `Codebase_Map.md` changes, run `compile_doc.py` and docchain gates.
- WF9 PASS triggers `$auto-iterate-goal` readiness checks but does not silently start WF10 without required approvals.
- The segment stops as `build_ready_for_iterate` only after `validate-run`
  postconditions pass.
- Harness hooks should not block ordinary build writes under declared
  implementation surfaces such as `src/`, `scripts/`, `configs/`,
  `project_map.json`, and owned docs. They should continue blocking manual
  writes to tool-owned paths such as `.evidence/**`, `.auto_iterate/**`,
  `.workflow_supervisor/**`, `docs/_views/**`, and `docs/_site/**`.

### Segment 5: Iterate Delegation

Do not rewrite auto-iterate. Wrap it:

```text
workflow_ctl start --segment iterate
  -> auto-iterate-goal check/init/refresh
  -> check_dynamic_context.py --stage wf10 --review-packet
  -> tooling/auto_iterate/scripts/auto_iterate_ctl.sh start --tool codex --goal docs/auto_iterate_goal.md
  -> monitor status --json
```

Rules:

- `.auto_iterate/**` remains owned by auto-iterate.
- `.workflow_supervisor/**` records delegation event and current status refs.
- If auto-iterate exits `manual_action_required`, supervisor surfaces that as its own pending request without editing `.auto_iterate/**`.
- `PIVOT` / `ABORT` require operator steering before Stage rollback or termination.
- Nested manual-action or approval conditions from auto-iterate must surface as
  typed outer supervisor requests and resume through the original supervisor run.

### Segment 6: Change Intake

Add mature-codebase change routing:

```text
user request
  -> classify change
  -> generate Change Request
  -> route
```

Routes:

- `bugfix` -> `$code-debug`
- `experiment_delta` -> `$iterate`
- `stable_code_delta` -> build_delta + `$code-debug`
- `architecture_delta` -> delta grill + `$refine-arch` / `$build-plan`
- `evaluation_delta` -> Review Packet / contract gate
- `claim_boundary_delta` -> Claim Boundary review/approval
- `new_research_direction` -> new Research Intent Draft branch

The classifier must fail closed when uncertain.

Classifier input contract:

- current user request text;
- current Stage and last known segment status;
- `project_map.json` when present;
- `docs/20_facts/Codebase_Map.md` when present;
- current Project / Evaluation / Baseline / Claim Boundary contracts when present;
- latest relevant `iteration_log.json` entry when present;
- affected path hints from the request and from changed files;
- proposed validation command or reason it is unknown.

Classifier output contract:

```json
{
  "schema_version": 1,
  "request_id": "chg_20260604_000001",
  "change_type": "bugfix|experiment_delta|stable_code_delta|architecture_delta|evaluation_delta|claim_boundary_delta|new_research_direction|harness_guardrail_delta|unknown",
  "route": "code-debug|iterate|build_delta|delta_grill|review_packet|claim_boundary_review|harness-maintenance|steer",
  "confidence": "high|medium|low",
  "uncertainty_reasons": [],
  "affected_contracts": [],
  "affected_paths": [],
  "validation_plan": [],
  "human_stop_points": [],
  "gate_evidence_plan": []
}
```

Fail-closed rules:

- `confidence=low` routes to `STEER`, not to code edits.
- Any possible Evaluation Contract, Baseline Contract, or Claim Boundary impact
  routes to Review Packet / approval gate.
- Public interface, config schema, data flow, or primary metric changes cannot
  be classified as plain `bugfix`.
- `harness_guardrail_delta` routes to `$harness-maintenance`, never
  `$code-debug`.
- `unknown` must include `uncertainty_reasons` and a concrete question for the
  operator.

### Segment 7: Release

Implement release last.

Rules:

- WF11/WF12 require approved Project Contract, Evaluation Contract, and Claim Boundary.
- Final experiment docs and release docs must pass docchain/context gates.
- Release/submission commands require `APPROVE_ACTION`.
- Supervisor must show exact claim text, evidence refs, risks, and allowed responses.

## Skill and Contract Changes

### New Skills

V0 Skill requirements:

| Skill | Required In V0? | Purpose | First Slice |
| --- | --- | --- | --- |
| `.agents/skills/grill/SKILL.md` | Yes | Human-facing intent clarification and draft/readiness artifact contract. | Slice 2 |
| `.agents/skills/workflow-supervisor/SKILL.md` | Yes | Operator-facing wrapper and guardrails for invoking supervisor tooling; does not replace `workflow_ctl.py`. | Slice 3 |
| `.agents/skills/change-intake/SKILL.md` | Yes before Slice 7 acceptance | Human-facing change classification contract for mature codebases. | Slice 7 |

Keep them aligned with `.claude/skills/**` if Claude support remains required.

### Skill Contract Extensions

V0 uses a separate node registry. Do not add `automation_policy` to
`schemas/skill_contracts.json` until the registry schema, validators, and hook
tests are stable.

Example:

```json
{
  "node_id": "prepare_review_packet",
  "skill": "review-packet",
  "segment": "prepare",
  "stage": "WF5",
  "order": 40,
  "auto_allowed": true,
  "manual_only": false,
  "max_attempts": 2,
  "timeout_seconds": 600,
  "preconditions": [
    {
      "type": "artifact_exists",
      "path": "docs/Execution_Readiness_Packet.md"
    }
  ],
  "postconditions": [
    {
      "type": "review_packet_exists",
      "kind": "dynamic_context",
      "stage": "wf5"
    }
  ],
  "interrupts": [
    {
      "when": "approval_required",
      "type": "APPROVE_ACTION",
      "reason": "evaluation_contract_approval_required"
    }
  ],
  "evidence_tools": [
    {
      "command": "python tooling/evidence/check_dynamic_context.py --workspace-root . --stage wf5 --review-packet",
      "outputs": [".evidence/review_packets/"]
    }
  ],
  "resume_strategy": "adopt_if_postconditions_pass_else_rerun",
  "failure_strategy": "pause_on_gate_fail",
  "allowed_worker_write_patterns": [
    "docs/"
  ],
  "tool_owned_output_refs": [
    ".evidence/review_packets/"
  ]
}
```

Allowed precondition/postcondition types for v0:

| Type | Required Fields | Meaning |
| --- | --- | --- |
| `artifact_exists` | `path` | File or directory must exist after the node. |
| `artifact_matches_schema` | `path`, `schema` | JSON/YAML artifact must validate. |
| `command_passes` | `command` | Command must return zero and be recorded in Gate ledger. |
| `docchain_gate_passes` | `doc_path` | `compile_doc.py` / `check_docchain_gates.py` output must be current. |
| `dynamic_context_gate_passes` | `stage` | `check_dynamic_context.py` must PASS or produce a Review Packet. |
| `review_packet_exists` | `stage` or `kind` | Review Packet path must be present in evidence refs. |
| `approval_recorded` | `contract` or `claim_scope` | Approval tooling must record approval source and state update. |
| `auto_iterate_status` | `allowed_statuses` | Delegated auto-iterate status must map to allowed supervisor states. |
| `no_forbidden_writes` | `patterns` | Observed writes must not touch controlled runtime paths. |

Registry validators must reject unknown condition types, empty
postconditions for `auto_allowed=true` nodes, and any node that can auto-continue
without a `resume_strategy`.

Write-boundary rule:

- `allowed_worker_write_patterns` must never include `.evidence/**`,
  `.auto_iterate/**`, `.workflow_supervisor/**`, `docs/_views/**`, or
  `docs/_site/**`.
- Tool-owned outputs from evidence, auto-iterate, or docs-site tooling belong in
  `tool_owned_output_refs` or `evidence_refs`, not in worker write allowlists.
- If a node needs `.evidence/**`, it must invoke the owning evidence command and
  record the resulting path as a ref.

## Hook and Guardrail Changes

Codex hooks should recognize supervisor prompts and runtime paths.

Add hook behavior:

- route hints for `harness grill` and Execution Supervisor action commands
  such as `harness prepare`, `harness build`, `harness change`, and
  `harness release`;
- warn when worker attempts to ask user directly in `auto_mode`;
- block manual writes to `.workflow_supervisor/**` except through supervisor tooling;
- continue blocking manual writes to `.evidence/**` and `.auto_iterate/**`;
- record read/write metadata for supervisor worker prompts;
- warn if a worker attempts to approve contracts or release claims;
- test `.workflow_supervisor/**` direct-write blocks and supervisor-tool
  allowlist behavior.

Tests:

```bash
python tooling/codex_hooks/check_contracts.py --workspace-root .
pytest tooling/.tests/test_codex_hooks_contracts.py
python tooling/codex_hooks/simulate_hook.py UserPromptSubmit \
  --workspace-root . \
  --event-json '{"prompt":"run harness prepare"}'
```

## Tests and Validation

### Unit Tests

Add:

- `tooling/.tests/test_workflow_supervisor_state.py`
- `tooling/.tests/test_workflow_supervisor_nodes.py`
- `tooling/.tests/test_workflow_supervisor_interrupts.py`
- `tooling/.tests/test_workflow_supervisor_readiness.py`
- `tooling/.tests/test_workflow_supervisor_change_intake.py`
- `tooling/.tests/test_workflow_supervisor_postconditions.py`
- `tooling/.tests/test_workflow_supervisor_worker_result.py`

### Integration Tests

Use fixture target workspaces:

- standard project without dynamic context,
- dynamic-context project with draft contracts,
- dynamic-context project with approved Evaluation Contract,
- mature-codebase fixture with `project_map.json` and `Codebase_Map.md`,
- interrupted run fixture with pending request,
- stale lock fixture.

Test scenarios:

- Grill writes draft and readiness packet.
- Readiness preflight uses preanswered path and skips duplicate `ASK_INPUT`.
- Readiness preflight rejects stale/unwritable path.
- Prepare supervisor builds Review Packet and pauses for approval.
- Explicit approval carries `approval_source`, runs `approve_contract.py`, and
  rechecks dynamic context.
- Malformed worker result fails closed before postcondition adoption.
- Auto-iterate delegation records status refs but does not write `.auto_iterate/**`.
- Change intake routes bugfix to `$code-debug`.
- Change intake routes evaluation delta to Review Packet / contract gate.
- Change intake with low confidence fails closed into `STEER`.
- Approval answer with mismatched `request_snapshot_hash` is rejected.
- Reused `idempotency_key` with a different answer body is rejected.
- Release segment fails closed without Claim Boundary approval.

### Validation Commands

For framework changes:

```bash
python -m py_compile tooling/workflow_supervisor/scripts/workflow_ctl.py
ruff check --select=E,F,I tooling/workflow_supervisor
python tooling/codex_hooks/check_contracts.py --workspace-root .
pytest tooling/.tests/test_codex_hooks_contracts.py
pytest tooling/.tests/test_workflow_supervisor_state.py
pytest tooling/.tests/test_workflow_supervisor_nodes.py
pytest tooling/.tests/test_workflow_supervisor_interrupts.py
pytest tooling/.tests/test_workflow_supervisor_readiness.py
pytest tooling/.tests/test_workflow_supervisor_change_intake.py
pytest tooling/.tests/test_workflow_supervisor_postconditions.py
pytest tooling/.tests/test_workflow_supervisor_worker_result.py
```

For docs and evidence tooling changes:

```bash
pytest tooling/.tests/test_dynamic_context_contracts.py
pytest tooling/.tests/test_protocol_compiler.py tooling/.tests/test_protocol_drift_check.py
pytest tooling/.tests/test_review_packet.py
pytest tooling/.tests/test_evidence_docchain.py tooling/.tests/test_evidence_docchain_gates.py
```

## Rollout Plan

### Slice 1: Planning and Schemas

Deliver:

- this implementation plan,
- schema drafts,
- node registry draft,
- no runtime automation.

Acceptance:

- schemas validate fixtures,
- runtime file ownership table maps to schema/path validators,
- docs are readable,
- no behavior change.

### Slice 2: Grill and Readiness

Deliver:

- Grill Skill,
- Research Intent Draft template,
- Execution Readiness Packet template,
- readiness JSON schema,
- WF1-WF3 bridge contract,
- basic tests.

Acceptance:

- one grill round can run without touching `.evidence/**`;
- readiness preflight can validate synthetic paths;
- Grill output alone does not satisfy WF1-WF3 Stage completion.
- `.agents/skills/grill/SKILL.md` and matching contract are present.

### Slice 3: Supervisor Runtime Skeleton

Deliver:

- `workflow_ctl.py` start/status/pause/stop/resume/recover/tail,
- state/lock/events,
- dry-run node execution,
- status JSON contract.

Acceptance:

- dry-run segment produces state and events,
- stale lock and resume tests pass,
- worker result schema validates success, failure, and interrupt paths.
- state invariants reject paused/running/completed contradictions.
- approval hash and idempotency validation reject stale answers.
- `workflow-supervisor` Skill wrapper exists and points to supervisor tooling.

### Slice 4: Prepare Segment HITL

Deliver:

- protocol compiler node,
- review packet node,
- pending approval interrupt,
- `answer` and `approve` command implementation,
- resume after approval/reject/revise.

Acceptance:

- Review Packet generated through tooling,
- `approve_contract.py` only runs after explicit approval,
- dynamic-context gate reruns after approval,
- `prepare_hitl_poc` cannot unlock build/iterate/release.
- stale approval payloads fail closed.

### Slice 5: Data/Baseline and Build Segments

Deliver:

- data-prep and baseline nodes,
- build-plan/code-debug/validate-run nodes,
- postcondition validators,
- project map / Codebase Map sync checks.

Acceptance:

- no direct `.evidence/**` writes,
- registry uses `tool_owned_output_refs` for `.evidence/**`, not
  `allowed_worker_write_patterns`,
- Codebase Map docchain compiles when changed,
- validation gates record PASS/FAIL/NOT_RUN.

### Slice 6: Auto-Iterate Delegation

Deliver:

- wrapper node for existing auto-iterate,
- status bridge,
- halt reason mapping.

Acceptance:

- supervisor can start/monitor auto-iterate,
- `manual_action_required` maps to typed pending request,
- no supervisor writes under `.auto_iterate/**`.

### Slice 7: Change Intake

Deliver:

- Change Request schema,
- classifier,
- delta grill,
- route-specific postconditions.

Acceptance:

- bugfix route uses `$code-debug`,
- experiment delta route uses `$iterate`,
- evaluation/claim deltas fail closed into approval gates.
- `change-intake` Skill contract exists before accepting this slice.

### Slice 8: Release Segment

Deliver:

- final-exp/release nodes,
- Claim Boundary checks,
- release approval interrupts.

Acceptance:

- release claims require docchain/context gates,
- submission/package commands require exact scoped approval.

## Migration Strategy

Existing workflow remains valid during rollout.

```text
manual Skill invocation
  -> still supported

workflow supervisor dry-run
  -> advisory only

prepare supervisor
  -> optional

build / iterate / release supervisor
  -> enabled after tests and human acceptance
```

No existing target workspace should be forced into supervisor mode. The
supervisor should detect missing dynamic-context layout and either:

- run in standard/legacy compatibility mode with warnings, or
- stop and ask whether to initialize dynamic context.

## Required Updates to Templates and Docs

Update:

- `.gitignore` and hook policy docs for `.workflow_supervisor/**` runtime ownership.
- `AI_AGENT_SETUP.md` for bootstrap instructions and `.workflow_supervisor/` ignore rules.
- `templates/**` to include optional Grill / supervisor docs.
- `README.md` to describe two top-level modes: `grill` and Execution Supervisor
  actions (`prepare/build/iterate/release/change`).
- `AGENTS.md` and `CLAUDE.md` to add concise routing rules.
- `workflow_handbook/Workflow_Operator_Handbook.md` for operator-facing flows.
- `workflow_handbook/pages/workflow_supervisor_model.md` and navigation.
- `workflow_handbook/Workflow_Stage_Cards.md` after Skill Contract updates.
- `.agents/skills/**` and `.claude/skills/**` for semantic alignment.
- `schemas/skill_contracts.json` only after node registry behavior stabilizes.

## Final Gate Before Enabling by Default

Before making supervisor the default route, require:

- passing hook contract tests,
- passing supervisor unit/integration tests,
- successful dry-run on at least one fixture target workspace,
- successful interrupted/resumed run,
- evidence tooling still passes dynamic context and docchain tests,
- human review of approval payload UX,
- explicit operator acceptance that supervisor can run the selected segment.

## Summary

The correct implementation path is incremental:

```text
1. Keep existing Skills and gates.
2. Add Grill to improve early human intent capture.
3. Add readiness preflight to reduce avoidable interrupts.
4. Add supervisor runtime that records state/events/postconditions.
5. Use evidence tooling for all `.evidence/**` outputs.
6. Stop at typed HITL interrupts for input, steering, and approval.
7. Delegate WF10 to existing auto-iterate instead of rewriting it.
8. Add change intake for mature-codebase deltas.
9. Only then expand toward build and release automation.
```

This plan preserves Harness's core principle: automation may reduce friction,
but current facts, Gate Evidence, and Human Approval remain the authority for
research claims and workflow transitions.
