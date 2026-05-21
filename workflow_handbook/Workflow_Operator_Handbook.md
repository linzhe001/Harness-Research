# Workflow Operator Handbook

本文是 Harness operator 的低负担入口。它不替代
`schemas/skill_contracts.json`、skill instructions、
`.agents/references/workflow-guide.md`、`tooling/evidence/**` 或
`tooling/auto_iterate/**`; 它把这些 source of truth 分层解释成可操作手册。

核心问题:

```text
我现在在哪个 Stage / Skill?
应该读什么?
允许写什么?
Hook 会拦什么?
必须用什么 Gate Evidence 或 Approval Evidence 证明可以继续?
```

## 0. 分层读法

```text
Layer 1: 8 个 primitive
  -> init / evidence / protocol / contract / code / validate / iterate / release

Layer 2: WF0-WF12 Stage
  -> 当前 workflow phase 和下一步 stage

Layer 3: Skill Contract
  -> required reads, write_scope, required actions, forbidden actions

Layer 4: Hook Runtime
  -> 缺失 reads、越界写入、工具托管目录手改、缺失 Gate ledger 的拦截

Layer 5: Human Decision
  -> stage transition、contract approval、claim boundary、release submit 需要人确认
```

推荐的单 turn 形状:

```text
operator intent
  -> active Skill
  -> read source artifacts
  -> write only active write_scope
  -> run gates or report NOT_RUN
  -> Gate ledger
  -> explicit human decision when needed
```

## 1. Source Of Truth

```text
schemas/skill_contracts.json
  -> triggers
  -> required_read_set
  -> required_actions
  -> forbidden_actions
  -> gate_ledger_required_when
  -> sensitive_paths
  -> write_scope.allowed_paths
      |
      v
tooling/codex_hooks/*.py
  -> UserPromptSubmit / PreToolUse / PostToolUse / Stop guardrails
      |
      v
docs/Workflow_Stage_Cards.md
workflow_handbook/Workflow_Stage_Cards.md
workflow_handbook/Workflow_Operator_Handbook.md
  -> operator reading aids, not source of truth
```

状态源:

```text
PROJECT_STATE.json             -> workflow stage source of truth
iteration_log.json             -> experiment source of truth
project_map.json               -> stable implementation map
docs/10_contract/**            -> draft or approved contracts
docs/20_facts/**               -> current facts
docs/20_facts/Codebase_Map.md  -> operator-facing stable codebase map
docs/30_evidence/**            -> source tables and open questions
docs/35_protocol/**            -> Protocol Drafts
.evidence/chains/**            -> Evidence Chain audit artifacts
.auto_iterate/**               -> auto-iterate controller runtime
```

## 2. 八个 Operator Primitives

| Primitive | Human question | Main entrypoints | Boundary |
| --- | --- | --- | --- |
| `init` | workspace 和稳定上下文在哪里? | `$orchestrator init`, `$init-project`, `init_context.py` | 只建结构和 explicit operator preferences; 不证明 research facts。 |
| `evidence` | 我们实际知道什么? | `$survey-idea`, evidence tables, `compile_doc.py` | Conclusion Evidence 来自 source artifacts、logs、metrics、configs 或 explicit records。 |
| `protocol` | 当前 procedure 应该怎么走? | `$protocol-compiler`, `$protocol-drift-check` | Protocol Draft 不是 Approved Contract。 |
| `contract` | 哪些边界已经批准? | `$review-packet`, `approve_contract.py`, dynamic gates | Review Packet 不是 Approval Evidence。 |
| `code` | 需要改什么实现? | `$code-expert`, `$code-debug` | 代码必须服从 contracts、roadmap、project_map 和 Commit Slice。 |
| `validate` | 这次 change 或 stage 是否通过? | `$validate-run`, tests, gates | 只能报告 `PASS`, `FAIL`, `NOT_RUN`。 |
| `iterate` | 下一轮实验决策是什么? | `$iterate`, auto-iterate controller | `iteration_log.json` 是 experiment source of truth。 |
| `release` | 哪些 claims 被支持? | `$final-exp`, `$release` | Release claims 必须在 Claim Boundary 内。 |

```text
Init      -> WF0
Explore   -> WF1 survey -> WF2 idea-debate -> WF3 refine-idea -> WF4 data-prep
Contract  -> WF5 baseline-repro -> WF6 refine-arch -> WF7 build-plan
Build     -> WF8 code-expert -> WF9 validate-run
Iterate   -> WF10 iterate -> WF11 final-exp
Release   -> WF12 release
```

## 3. 主流程图

```text
START
  |
  v
WF0 init
  inputs: target workspace, framework source, explicit operator preferences
  writes: AGENTS.md, CLAUDE.md, OPERATOR_CONTEXT.md only if explicit,
          PROJECT_STATE.json, optional docs/.evidence scaffold through tooling
  gates: context gate or NOT_RUN, workflow-state gate or NOT_RUN
  |
  v
WF1 survey-idea
  writes: docs/Feasibility_Report.md, docs/30_evidence/**,
          optional docs/35_protocol/** draft
  decision: PROCEED | PIVOT | ABANDON
  |
  v
WF2 idea-debate
  writes: docs/Idea_Debate.md, optional protocol draft refresh
  decision: SELECT | PILOT_FIRST | MERGE | PIVOT | ABANDON
  |
  v
WF3 refine-idea
  writes: docs/Refined_Idea.md, protocol assumptions, open questions
  boundary: no architecture decision
  |
  v
WF4 data-prep
  writes: docs/Dataset_Stats.md, docs/20_facts/**,
          docs/30_evidence/Dataset_Table.md,
          configs/**, src/**, CLAUDE.md dataset sync
  |
  v
WF5 baseline-repro
  writes: docs/Baseline_Report.md, docs/30_evidence/Baseline_Table.md,
          docs/10_contract/**, optional docs/20_facts/Codebase_Map.md,
          baseline code/config/scripts, PROJECT_STATE.json, project_map.json
  gates: protocol drift, dynamic context, docchain, review packet,
         codebase map sync when baseline layout changes,
         explicit human approval before approved contracts
  |
  v
WF6 refine-arch
  writes: docs/Technical_Spec.md, docs/20_facts/Project_Glossary.md,
          optional protocol draft updates
  gate: $deep-check when architecture affects claim boundary, metric,
        high-cost interface, or evaluation assumptions
  |
  v
WF7 build-plan
  writes: docs/Implementation_Roadmap.md, project_map.json,
          docs/20_facts/Project_Glossary.md,
          docs/20_facts/Codebase_Map.md
  boundary: no new architecture choice
  |
  v
WF8 code-expert
  writes: src/**, scripts/**, configs/**, project_map.json,
          docs/20_facts/Codebase_Map.md, PROJECT_STATE.json
  gates: py_compile/ruff or NOT_RUN, project_map/codebase map sync,
         semantic commit or NOT_RUN
  |
  v
WF9 validate-run
  writes: docs/Validate_Run_Report.md,
          docs/30_evidence/Validation_Table.md, PROJECT_STATE.json
  verdict: PASS | REVIEW | FAIL
  bridge: PASS -> $auto-iterate-goal check/init/refresh -> WF10 readiness
  |
  v
WF10 iterate
  manual: $iterate plan -> $iterate code -> $iterate run -> $iterate eval
  auto: auto_iterate_ctl.sh start/resume -> controller plan/code/run/eval
  writes: iteration_log.json, docs/40_iterations/**, legacy docs/iterations/**,
          docs/50_memory/**, MEMORY.md
  decisions: NEXT_ROUND | DEBUG | CONTINUE | PIVOT | ABORT
  |
  v
WF11 final-exp
  writes: docs/Final_Experiment_Matrix.md, PROJECT_STATE.json
  gates: Evaluation Contract, Claim Boundary, dynamic context
  |
  v
WF12 release
  writes: submission/**, docs/**, PROJECT_STATE.json
  gates: WF12 dynamic context, release manifest, claim boundary,
         explicit submit request
  |
  v
DONE
```

## 4. State Ownership

```text
$orchestrator owns stage transitions in PROJECT_STATE.json
$iterate owns experiments in iteration_log.json
$build-plan / $code-expert / $code-debug own stable map updates in project_map.json
and docs/20_facts/Codebase_Map.md when present
auto-iterate controller owns .auto_iterate/**
evidence tooling owns .evidence/**
```

| Artifact | Owner | Meaning | Do not use it for |
| --- | --- | --- | --- |
| `PROJECT_STATE.json` | `$orchestrator`; stage skills may record own artifact metadata | workflow stage and approved state metadata | experiment diary |
| `iteration_log.json` | `$iterate` | experiment history, metrics, decisions, lessons | stage transitions |
| `project_map.json` | `$build-plan`, `$code-expert`, `$code-debug` | stable files, interfaces, entry points | architecture decision record |
| `docs/20_facts/Codebase_Map.md` | `$build-plan`, `$code-expert`, `$code-debug`; `$baseline-repro` when baseline layout changes | human-readable stable codebase map | machine-readable schema source |
| `OPERATOR_CONTEXT.md` | explicit operator input | stable preferences | inferred project facts |
| `docs/10_contract/**` | contract tooling + explicit human approval | boundaries | raw protocol drafts |
| `docs/30_evidence/**` | stage skills | human-readable Conclusion Evidence tables and open questions | tool-owned Evidence Chains |
| `docs/35_protocol/**` | protocol compiler/drift checks | Protocol Draft | Approved Contract |
| `.evidence/**` | evidence tooling | Evidence Chains, review packets, compiler output | manual editing |
| `.auto_iterate/**` | controller | runtime state, lock, events, phase logs | manual editing |

Invariant:

```text
$iterate does not write PROJECT_STATE.json
$orchestrator does not write iteration_log.json
controller reads PROJECT_STATE.json and iteration_log.json
controller writes only .auto_iterate/**
ordinary edits do not touch .evidence/** or .auto_iterate/**
```

## 5. Evidence 语言

| Term | 用途 | 常见 source |
| --- | --- | --- |
| `Conclusion Evidence` | 支持 claim、fact、idea、protocol choice 或 research conclusion | papers, repos, dataset stats, metrics, configs, logs |
| `Evidence Chain` | 从 source artifacts 到 current doc/claim 的结构化链 | `.evidence/chains/**`, `.evidence/index.json` |
| `Gate Evidence` | 证明 gate、test、command、approval check 是否执行以及结果 | command output, CI, controller preflight, approval tool output |
| `Execution Evidence` | command/test/script/training run 的 Gate Evidence | pytest, ruff, train/eval logs |
| `Approval Evidence` | explicit human approval | current conversation, auditable approval artifact |
| `Gate Ledger` | command/result/reason/artifact report | final response, review/validation docs |

```text
结论为什么可信 -> Conclusion Evidence
流程为什么可放行 -> Gate Evidence
合同为什么已批准 -> Approval Evidence
```

`docs/30_evidence/**` 和 `.evidence/**` 不同:

```text
docs/30_evidence/**
  -> human-readable Conclusion Evidence tables
  -> examples: Dataset_Table.md, Baseline_Table.md, Validation_Table.md

.evidence/**
  -> tool-owned audit artifacts
  -> examples: Evidence Chains, review packets, protocol compiler traces
```

普通 Stage 可以维护自己负责的 `docs/30_evidence/**` 表, 但不能手工编辑
`.evidence/**`。如果 current contract/fact/protocol doc 需要可审计链路,
用 `tooling/evidence/**` 生成 Evidence Chain。

Gate ledger:

```text
Gate ledger
- command: <exact command or NOT_RUN>
- result: PASS | FAIL | NOT_RUN
- reason: <why required, or why not run>
- artifacts: <state/doc/evidence paths created or updated>
```

## 6. Dynamic Context 和 Approval

```text
OPERATOR_CONTEXT.md
  -> docs/30_evidence/**
  -> docs/35_protocol/** Protocol Draft
  -> docs/10_contract/** draft
  -> review packet
  -> explicit human approval
  -> approve_contract.py
  -> dynamic-context gates
  -> Approved Contract
```

Rules:

- `OPERATOR_CONTEXT.md` 只记录 operator 明确给出的稳定偏好。
- `docs/35_protocol/**` 是 Protocol Draft。
- `docs/10_contract/**` 只有 Markdown 和 `PROJECT_STATE.json` 两边都有 approval metadata 后才是 Approved Contract。
- `$review-packet` 是 human decision input, 不是 Approval Evidence。
- AI 可以生成 draft/proposal, 不能自行批准 contract。
- `--allow-draft-contract` 和 `--allow-review-required` 是 run-specific acceptance, 不是永久 approval。

Approval 命令链:

```bash
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage wf10 --review-packet
python tooling/evidence/approve_contract.py \
  --workspace-root . \
  --contract evaluation_contract \
  --approved-by "<human reviewer>" \
  --approval-source ".evidence/review_packets/wf10/<build_id>/review_packet.md"
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage wf10 --review-packet
```

## 7. Hook Runtime

```text
UserPromptSubmit
  -> detect active skill
  -> write .harness_hooks/session.json
  -> emit required read set / required actions / forbidden actions

PreToolUse
  -> block git commit until sliced-commit rule was read
  -> block direct external reviewer scripts
  -> allow external review wrapper only in $code-review heavy
  -> block untrusted manual .evidence/** and .auto_iterate/** writes
  -> require active skill read set before writes
  -> enforce code-review review-only boundary
  -> enforce write_scope.allowed_paths for path-aware writes

PostToolUse
  -> record observable reads
  -> mark mutating tool activity
  -> inspect changed paths
  -> mark pending Gate ledger when sensitive paths changed

Stop
  -> block missing reads when enforcement applies
  -> block missing Gate ledger when sensitive paths changed
```

### 7.1 Hooks Allow

| Situation | Allowed when |
| --- | --- |
| Reads | Always allowed; tracked when observable and in current read candidates. |
| Writes inside active `write_scope.allowed_paths` | Required read set is complete for the active skill. |
| `docs/**` writes | Active skill includes that doc path or directory in `write_scope`. |
| `src/**`, `scripts/**`, `configs/**` writes | `$code-expert`, `$code-debug`, or a stage contract includes those paths. |
| `.evidence/**` outputs | Produced by owning evidence tooling such as `tooling/evidence/*.py`. |
| `.auto_iterate/**` outputs | Produced by auto-iterate controller. |
| `$code-review` report writes | Under `.agents/state/review_traces/code-review/**`. |
| External model review | Through `tooling/model_api/harness_external_review.py` during active `$code-review heavy`. |
| `git commit` | `.agents/references/sliced-commit-rule.md` was read in the current turn and Commit Slice discipline is followed. |

### 7.2 Hooks Block

| Blocked action | Reason |
| --- | --- |
| Write before required reads | Active Skill Contract requires source artifacts first. |
| Path-aware write outside `write_scope.allowed_paths` | Stage permission is temporary and narrow. |
| Manual `.evidence/**` write | Evidence Chains and packets are tool-owned. |
| Manual `.auto_iterate/**` write | Controller runtime is controller-owned. |
| `$code-review` modifying subject files | Review is read-only; fixes route to `$code-debug` or `$harness-maintenance`. |
| Direct `agentic_review.py` or `external_chat.py` | Provider review must use Harness wrapper. |
| External wrapper outside `$code-review heavy` | Network-backed review is scoped to high-rigor review sessions. |
| `git commit` before sliced-commit guidance read | Prevents all-changes commits and accidental user-change commits. |
| Adding known local/reference artifacts | Keeps local-only files out of git. |

### 7.3 Hook Limits

```text
Hook blocked nothing
  does not mean
Gate passed
```

- `required_actions` and `forbidden_actions` are contract obligations; hooks enforce only selected runtime boundaries.
- Complex Bash may not expose reliable paths. It is not proof of strict path scoping.
- Read tracking only covers observable tool events in the current prompt turn.
- Hook trust must be checked after hook config changes.
- Hooks are not Approval Evidence.

Useful commands:

```bash
python tooling/codex_hooks/install_hooks.py --workspace-root .
python tooling/codex_hooks/hook_status.py --workspace-root .
python tooling/codex_hooks/hook_status.py --workspace-root . --trust-status
python tooling/codex_hooks/check_contracts.py --workspace-root .
python tooling/codex_hooks/simulate_hook.py UserPromptSubmit \
  --workspace-root . \
  --event-json '{"prompt":"run $validate-run"}'
```

## 8. Commit Slice

```text
git commit requested
  |
  v
read .agents/references/sliced-commit-rule.md
  |
  v
inspect worktree:
  git status --short
  git diff --name-only
  git diff --cached --name-only
  |
  v
identify independent Commit Slices
  |
  v
stage only current completed slice
  |
  v
validate slice or report NOT_RUN
  |
  v
git commit -m "<semantic message>"
```

不要把可分离改动打成一个 `all changes` commit。不要 stage 用户的无关改动。

## 9. Skill Routing

| Task | Skill |
| --- | --- |
| stage status / advance / rollback / decision | `$orchestrator` |
| bootstrap guidance / operator context | `$init-project` |
| current docs + Evidence Chain | `$doc-compiler` |
| Protocol Draft compilation | `$protocol-compiler` |
| protocol drift | `$protocol-drift-check` |
| human review packet / approval record | `$review-packet` |
| WF1 survey | `$survey-idea` |
| WF2 debate | `$idea-debate` |
| WF3 idea framing | `$refine-idea` |
| WF4 dataset prep | `$data-prep` |
| WF5 baseline and contract readiness | `$baseline-repro` |
| WF6 architecture | `$refine-arch` |
| high-risk design review | `$deep-check` |
| WF7 roadmap and project_map | `$build-plan` |
| WF8 first implementation | `$code-expert` |
| implementation fix or iteration change | `$code-debug` |
| review only | `$code-review` |
| hooks, contracts, routing, permissions, operator docs | `$harness-maintenance` |
| WF9 validation | `$validate-run` |
| WF10 manual loop | `$iterate` |
| WF10 auto goal readiness | `$auto-iterate-goal` |
| result analysis | `$evaluate` |
| WF11 final matrix | `$final-exp` |
| WF12 release | `$release` |
| environment refresh | `$env-setup` |

## 10. Skill I/O 和 Hook 边界矩阵

表中 `Can write` 是 active skill 的 `write_scope.allowed_paths` 简写。
`.evidence/**` 和 `.auto_iterate/**` 即使出现在 logical output 中, 也应由 owning tooling/controller 生成。

| Skill | Inputs | Outputs / Can write | Must prove | Hook blocks / Cannot do |
| --- | --- | --- | --- | --- |
| `$orchestrator` | `PROJECT_STATE.json`, optional `iteration_log.json`, `project_map.json`, contracts | `PROJECT_STATE.json`, `iteration_log.json`, `project_map.json` | user approval for transitions; workflow-state gate or `NOT_RUN`; Gate ledger for transition/state/WF10-WF12 readiness | no transition without approval; no direct `.evidence/**` or `.auto_iterate/**` edits |
| `$init-project` | project name, templates, `PROJECT_STATE.json`, existing guidance, explicit operator preferences | `CLAUDE.md`, `AGENTS.md`, `OPERATOR_CONTEXT.md`, `PROJECT_STATE.json`, `docs/`, `.evidence/` scaffold | context gate or `NOT_RUN`; workflow-state gate or `NOT_RUN`; Gate ledger | no inferred preferences; no manual `.evidence/**`; no `.auto_iterate/**` |
| `$doc-compiler` | target doc, explicit sources, docchain schemas/tools, current contract/fact/protocol docs | `docs/10_contract/`, `docs/20_facts/`, `docs/35_protocol/`, `.evidence/chains/`, `.evidence/index.json` | `compile_doc_or_NOT_RUN`; `check_docchain_gates_or_NOT_RUN`; Gate ledger | no manual Evidence Chain; no current doc without required docchain; no approval from doc compilation |
| `$protocol-compiler` | `docs/30_evidence/**`, open questions, existing protocol | `.evidence/protocol_compiler/`, `docs/35_protocol/` | `compile_protocol_or_NOT_RUN`; `protocol_review_or_NOT_RUN`; docchain gate when current docs change; Gate ledger | Protocol Draft is not Approved Contract; no manual Evidence Chain |
| `$protocol-drift-check` | stage target, open questions, protocol docs, contracts | `docs/35_protocol/`, `docs/10_contract/` | `check_protocol_drift_or_NOT_RUN`; docchain gate when docs change; Gate ledger | do not ignore unresolved drift; do not approve protocol |
| `$review-packet` | stage target, contracts, dynamic gates, protocol/docchain status | `.evidence/review_packets/`, `docs/10_contract/`, `PROJECT_STATE.json` | `check_dynamic_context_or_NOT_RUN`; `build_review_packet_or_NOT_RUN`; approval tool only after human approval; Gate ledger | packet is not approval; no approval without explicit human approval |
| `$survey-idea` | idea, keywords, venue, time window, source artifacts, project state | `docs/Feasibility_Report.md`, `docs/30_evidence/`, `docs/35_protocol/`, `PROJECT_STATE.json` | protocol compile or `NOT_RUN`; workflow-state gate or `NOT_RUN`; Gate ledger | no approved contract; no direct `.evidence/**` |
| `$idea-debate` | WF1 report, evidence tables, candidate variants, reviewer traces | `docs/Idea_Debate.md`, `docs/35_protocol/`, `PROJECT_STATE.json` | protocol compile/drift or `NOT_RUN`; workflow-state gate or `NOT_RUN`; Gate ledger | no approved protocol; no direct `.evidence/**`; not architecture design |
| `$refine-idea` | WF1/WF2 artifacts, explicit constraints, evidence tables, protocol | `docs/Refined_Idea.md`, `docs/35_protocol/`, `PROJECT_STATE.json` | protocol compile/drift or `NOT_RUN`; workflow-state gate or `NOT_RUN`; Gate ledger | no architecture, file tree, registry, roadmap |
| `$data-prep` | dataset path/name, `PROJECT_STATE.json`, `CLAUDE.md`, `AGENTS.md`, refined idea | `docs/Dataset_Stats.md`, `docs/20_facts/`, `docs/30_evidence/Dataset_Table.md`, `PROJECT_STATE.json`, `CLAUDE.md`, `AGENTS.md`, `configs/`, `src/` | compile doc or `NOT_RUN`; workflow-state gate or `NOT_RUN`; Gate ledger | no direct `.evidence/**`; no `.auto_iterate/**`; no stale dataset duplication |
| `$baseline-repro` | refined idea, dataset stats, baseline table, contracts/protocol, optional map | `docs/Baseline_Report.md`, `docs/30_evidence/Baseline_Table.md`, `docs/10_contract/`, `docs/20_facts/Codebase_Map.md`, `PROJECT_STATE.json`, `project_map.json`, `CLAUDE.md`, `baselines/`, `configs/`, `scripts/`, `src/` | protocol drift, dynamic context, workflow-state, codebase map sync when baseline layout changes, semantic commit or `NOT_RUN`; Gate ledger | no training without semantic commit; no approval without human; protocol not contract |
| `$refine-arch` | WF1-WF5 artifacts, dataset/baseline facts, Evaluation/Baseline/Claim contracts, protocol, glossary | `docs/Technical_Spec.md`, `docs/20_facts/Project_Glossary.md`, `docs/35_protocol/`, `PROJECT_STATE.json` | protocol drift or `NOT_RUN`; workflow-state gate or `NOT_RUN`; Gate ledger | no roadmap/project_map; no approved protocol; no stale map |
| `$deep-check` | technical spec, contracts, protocol, negative evidence, dataset/baseline facts | `docs/Sanity_Check_Log.md`, `docs/35_protocol/`, `docs/10_contract/` | Codex/external review or `NOT_RUN`; protocol drift or `NOT_RUN`; Gate ledger | no contract approval; no protocol-as-contract; no approval without human |
| `$build-plan` | technical spec, refined idea, dataset/baseline facts, contracts, glossary, map schema | `project_map.json`, `PROJECT_STATE.json`, `docs/20_facts/Project_Glossary.md`, `docs/20_facts/Codebase_Map.md`, `docs/Implementation_Roadmap.md` | roadmap write; project_map/codebase map update; workflow-state gate or `NOT_RUN`; Gate ledger | no new architecture choice; no stale map |
| `$code-expert` | roadmap, `project_map.json`, state, contracts, glossary, codebase map, code rules | `src/`, `scripts/`, `configs/`, `project_map.json`, `docs/20_facts/Codebase_Map.md`, `PROJECT_STATE.json` | read map before stable code; py_compile/ruff/semantic commit/workflow-state or `NOT_RUN`; Gate ledger | no stable code without map read; no stale map; no training without commit |
| `$code-debug` | issue/log, `project_map.json`, `CLAUDE.md`, glossary, codebase map, validation/iteration context | `src/`, `scripts/`, `configs/`, `project_map.json`, `docs/20_facts/Codebase_Map.md` | read map; py_compile/ruff/semantic commit or `NOT_RUN`; Gate ledger | no hooks/contracts/skills/permission docs; no stale map |
| `$harness-maintenance` | AGENTS/CLAUDE, hook README/runtime, contracts, hook tests, code-style/language/terms refs | `schemas/`, `.agents/skills/`, `.agents/references/`, `.claude/Workflow_Guide.md`, `.claude/skills/`, `.claude/shared/`, `tooling/codex_hooks/`, `tooling/model_api/`, `tooling/.tests/`, `templates/`, `docs/`, `workflow_handbook/`, root guidance/templates | py_compile or `NOT_RUN`; ruff or `NOT_RUN`; Gate ledger for guardrail behavior changes | no manual `.evidence/**`; no `.auto_iterate/**`; ordinary implementation routes elsewhere |
| `$code-review` | review scope, git metadata, changed line ranges, subject files, map, reviewer refs | `.agents/state/review_traces/code-review/` | scope, git metadata, line map, Codex/external review or `NOT_RUN`, reconciliation, report or `NOT_RUN`, Gate ledger | no subject-file edits; no unverified model finding as fact; no heavy review without trace |
| `$validate-run` | implementation, baselines, spec, roadmap, map, codebase map, contracts, glossary | `docs/Validate_Run_Report.md`, `docs/30_evidence/Validation_Table.md`, `PROJECT_STATE.json` | semantic review; smoke test or `NOT_RUN`; report write; workflow-state gate or `NOT_RUN`; Gate ledger | no WF9 PASS without semantic review and smoke evidence |
| `$iterate` | `iteration_log.json`, state, guidance, contracts, glossary, lessons, iteration schema | `iteration_log.json`, `docs/40_iterations/`, legacy `docs/iterations/`, `docs/50_memory/`, `MEMORY.md` | iteration log update; decision vocabulary; lesson quality or `NOT_RUN`; Gate ledger | no `.auto_iterate/**`; no stage transition; no raw auto observation directly to MEMORY |
| `$auto-iterate-goal` | WF5 metrics/protocol, WF9 report, state, contracts, existing goal | `docs/auto_iterate_goal.md` | goal validate/init; context gate or `NOT_RUN`; Gate ledger | does not start controller; does not write `.auto_iterate/**`; no decision-making |
| `$evaluate` | logs, metrics, checkpoints, active iteration context, `iteration_log.json`, contracts, lessons | `iteration_log.json`, `docs/40_iterations/`, legacy `docs/iterations/`, `docs/50_memory/`, `MEMORY.md`, `docs/Stage_Report.md` | decision vocabulary; lesson quality/workflow-state or `NOT_RUN`; Gate ledger | no stage transition; no raw auto observation to MEMORY; protocol not contract |
| `$env-setup` | dependency files, machine env, `CLAUDE.md`, env refresh ref | `CLAUDE.md`, `requirements.txt`, `requirements-dev.txt`, `environment.yml`, `environment.yaml`, `pyproject.toml`, `scripts/`, `configs/` | py_compile/ruff or `NOT_RUN`; Gate ledger for dependency/setup/env-section changes | no training without semantic commit; no `.auto_iterate/**` |
| `$final-exp` | best iteration, reports, approved contracts, Claim Boundary, state | `docs/Final_Experiment_Matrix.md`, `PROJECT_STATE.json` | respect Evaluation Contract and Claim Boundary; dynamic context or `NOT_RUN`; Gate ledger | no final experiment outside Claim Boundary; no WF11 readiness without approved contracts in dynamic projects |
| `$release` | state, iteration log, guidance, final outputs, release checklist/manifest, contracts, Claim Boundary | `submission/`, `docs/`, `PROJECT_STATE.json` | WF12 dynamic context or `NOT_RUN`; manifest validation; claim boundary check; Gate ledger | no claim outside Claim Boundary; no submit without explicit user request; no overwrite without confirmation |

## 11. WF10 Manual 和 Auto

Manual WF10:

```text
$iterate plan
  -> allocate iteration
  -> check prior lessons
  -> status = planned
  |
  v
$iterate code
  -> create .agents/state/iterations/<iter-id>/context.json
  -> mirror .agents/state/current_iteration.json
  -> route implementation through $code-debug
  -> require semantic commit
  -> status = training
  |
  v
$iterate run
  -> build command from CLAUDE.md entry scripts and config
  -> resolve tracked metrics from WF5 protocol/contract
  -> update run_manifest
  -> status = running or stays training on failure
  |
  v
$iterate eval
  -> invoke $evaluate
  -> compare baseline, previous, best
  -> write report
  -> decision = NEXT_ROUND | DEBUG | CONTINUE | PIVOT | ABORT
```

Auto WF10:

```text
$auto-iterate-goal check/init/refresh
  -> validates docs/auto_iterate_goal.md
  -> does not start controller
  |
  v
tooling/auto_iterate/scripts/auto_iterate_ctl.sh start
  -> copies goal into .auto_iterate/goal.md
  -> runs WF10 dynamic-context preflight
  -> creates .auto_iterate/state.json, lock, events, runtime logs
  |
  v
controller phases
  -> plan -> code -> run -> eval
  -> each phase starts fresh codex exec
  -> postconditions inspect iteration_log.json and git state
```

Controller commands:

| Command | Meaning |
| --- | --- |
| `auto_iterate_ctl.sh start --tool codex --goal docs/auto_iterate_goal.md --config tooling/auto_iterate/config/controller.local.yaml` | start loop |
| `auto_iterate_ctl.sh status --json` | machine-readable status |
| `auto_iterate_ctl.sh tail --jsonl --lines 50` | machine-readable events |
| `auto_iterate_ctl.sh pause` | pause at next safe boundary |
| `auto_iterate_ctl.sh stop` | stop at next safe boundary |
| `auto_iterate_ctl.sh resume` | rerun preflight and continue |
| `auto_iterate_ctl.sh override --goal <path>` | stage next goal for next round boundary |

Risk flags requiring explicit operator acceptance:

- `--allow-draft-contract`
- `--allow-review-required`
- `--skip-dynamic-preflight --skip-dynamic-preflight-reason "<reason>"`

## 12. 使用例子

### 12.1 WF0 初始化

```text
$orchestrator init
Project: MyProject
workflow_mode: dynamic_context
Dataset: /data/foo
Preference: keep docs concise, use Chinese natural-language reports
```

Expected:

```text
$orchestrator init
  -> may call $init-project init
  -> may run init_context.py --set-state
  -> writes PROJECT_STATE.json, CLAUDE.md, AGENTS.md
  -> writes OPERATOR_CONTEXT.md only from explicit preference
  -> Gate ledger reports context/workflow-state gates
```

### 12.2 Contract approval

```text
$review-packet wf10
  -> check_dynamic_context.py --stage wf10 --review-packet
  -> writes .evidence/review_packets/wf10/<build_id>/review_packet.md
  -> summarizes blockers and exact decision needed

Human:
  "I approve the Evaluation Contract from packet <path> for WF10."

$review-packet approve
  -> approve_contract.py --contract evaluation_contract ...
  -> rerun check_dynamic_context.py --stage wf10 --review-packet
```

Bad shortcut:

```text
review packet exists -> mark contract approved
```

Reason: packet is decision input, not Approval Evidence。

### 12.3 WF9 PASS 到 auto WF10

```text
$validate-run configs/smoke.yaml
  -> semantic review
  -> smoke test or NOT_RUN
  -> docs/Validate_Run_Report.md
  -> verdict PASS
  |
  v
$auto-iterate-goal check
  -> validates docs/auto_iterate_goal.md
  -> context gate for wf10-auto or NOT_RUN
  |
  v
tooling/auto_iterate/scripts/auto_iterate_ctl.sh start \
  --tool codex \
  --goal docs/auto_iterate_goal.md \
  --config tooling/auto_iterate/config/controller.local.yaml
```

If Evaluation Contract is draft:

```text
start without explicit acceptance -> blocked / not ready
explicit run-specific acceptance -> start --allow-draft-contract
```

This is not permanent contract approval。

### 12.4 Manual WF10

```text
$iterate plan "try lower learning rate with stronger regularization"
  -> iteration_log.json status planned

$iterate code "implement config option for stronger regularization"
  -> writes .agents/state/current_iteration.json
  -> invokes $code-debug
  -> code-debug edits configs/src only
  -> semantic commit before training

$iterate run configs/iter12.yaml
  -> update run_manifest
  -> status running

$iterate eval experiments/iter12/
  -> invokes $evaluate
  -> writes docs/40_iterations/iter12.md
  -> may mirror legacy docs/iterations/iter12.md only for compatibility
  -> decision DEBUG
```

`DEBUG` means stay in WF10 and plan a debug-oriented next round。

### 12.5 Hook block: wrong write scope

If active skill is `$code-debug` and a tool tries to edit
`tooling/codex_hooks/harness_contracts.py`, PreToolUse should deny:

```text
Blocked by Harness policy:
write is outside active `code-debug` stage write scope.

Allowed paths:
- src/
- scripts/
- configs/
- project_map.json
```

Correct route:

```text
$harness-maintenance
  -> read hook/contracts/tests
  -> edit tooling/codex_hooks/**
  -> run focused checks
  -> Gate ledger
```

### 12.6 Hook block: direct Evidence Chain edit

Bad:

```text
apply_patch .evidence/chains/docs__10_contract__Project_Contract/<build>/evidence_chain.json
```

Expected:

```text
Blocked by Harness policy:
do not manually patch .evidence/** or .auto_iterate/**.
```

Correct:

```bash
python tooling/evidence/compile_doc.py \
  --workspace-root . \
  --doc docs/10_contract/Project_Contract.md \
  --source PROJECT_STATE.json docs/30_evidence/Evidence_Index.md
python tooling/evidence/validate_docchain.py .evidence/chains/<doc_id>/<build_id>
python tooling/evidence/check_docchain_gates.py --workspace-root .
```

### 12.7 Release packaging

```text
$release validate
  -> check package contents, filenames, resolution, manifest

$release package
  -> write submission/manifest.json
  -> package outputs
  -> verify package

$release submit
  -> only if operator explicitly asks for submit
  -> run/check WF12 dynamic context
  -> verify Claim Boundary
```

Bad claim unless Claim Boundary and Conclusion Evidence support it:

```text
"This method is state of the art on all scenes."
```

## 13. Operator Checklist

Before a stage:

- [ ] 当前 `workflow_mode` 是 `dynamic_context`, `standard`, 还是 `compatibility`。
- [ ] 当前 active Skill 和 Stage 明确。
- [ ] 已读 active Skill 的 source artifacts 或 Stage Card。
- [ ] `write_scope.allowed_paths` 覆盖要写的路径。
- [ ] 知道需要 Conclusion Evidence、Gate Evidence、Approval Evidence 中哪一种。
- [ ] 知道哪些 decision 需要 explicit human approval。
- [ ] `.evidence/**` 和 `.auto_iterate/**` 会通过 owning tooling/controller 写入。

Before closing a stage:

- [ ] 新 claim 有 Conclusion Evidence 或标为 open question。
- [ ] current contract/fact/protocol doc 已用 docchain tooling, 或明确 `NOT_RUN`。
- [ ] tests、context gates、workflow-state gates、controller preflight 已报告 `PASS`, `FAIL`, 或 `NOT_RUN`。
- [ ] Gate ledger 没有把 `NOT_RUN` 写成 `PASS`。
- [ ] Review Packet 没有被当成 approval。
- [ ] 下一步 decision 是 explicit, 不是 agent 自己推进。
- [ ] stable code/interface 改动已同步 `project_map.json` 和现有 `docs/20_facts/Codebase_Map.md`, 或报告 `NOT_RUN`。
- [ ] commit 已按 Commit Slice staged and validated。

## 14. 什么时候读深文档

| 情况 | 读什么 |
| --- | --- |
| 完整 workflow | `.agents/references/workflow-guide.md` 或 `.claude/Workflow_Guide.md` |
| 机器合同 | `schemas/skill_contracts.json` |
| 快速 skill 边界 | `workflow_handbook/Workflow_Stage_Cards.md`；`docs/Workflow_Stage_Cards.md` 是同一生成内容的 versioned contract snapshot |
| hooks、permission、routing | `tooling/codex_hooks/README.md` |
| Stage 权限提升 | `tooling/codex_hooks/Stage_Permission_Elevation_Guide.md` |
| workflow 术语 | `.agents/references/ubiquitous-language.md` |
| Commit Slice | `.agents/references/sliced-commit-rule.md` |
| auto-iterate | `tooling/auto_iterate/docs/cli_control_guide.md` |
| dual-repo bootstrap | `AI_AGENT_SETUP.md` |

## 15. 维护手册

```text
read source artifacts
  -> schemas/skill_contracts.json
  -> affected Skill.md files
  -> hook README/runtime when permission behavior is described
  -> ubiquitous language
  -> existing handbook
  |
  v
edit handbook
  -> keep it a reading aid
  -> do not make it source of truth
  -> keep examples operational
  |
  v
validate
  -> check_contracts when contract/hook descriptions changed
  -> focused tests when behavior changed
  -> Gate ledger
```

Handbook quality test:

```text
A human can answer:
  1. Which Skill should be active?
  2. What are the inputs?
  3. What can be written?
  4. What is blocked?
  5. What Gate Evidence or Approval Evidence is needed?
  6. What is the next human decision?
```
