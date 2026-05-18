# Workflow Operator Handbook

本文是 Harness operator 的低负担入口。它不替代
`.agents/skill-contracts/contracts.json`、skill instructions、workflow guide 或
evidence tooling; 它回答一个操作问题:

```text
我现在在哪一层, 应该看什么, 允许做什么, 下一步要证明什么?
```

## 0. 当前符合性结论

结论: 旧版 handbook 的方向基本符合 current workflow, 但不够完整。主要缺口是:

- 没有把 `init -> evidence -> protocol -> contract -> code -> validate -> iterate -> release`
  这八个 operator primitives 放到入口层。
- 没有把 WF0-WF12、dynamic context、docchain、contract approval、Gate ledger、
  Stage Cards 和 auto-iterate 串成一条可执行路径。
- 对 WF9 -> WF10 bridge、`$auto-iterate-goal`、WF10 dynamic-context preflight、
  `--allow-draft-contract` / `--allow-review-required` 的 human acceptance 边界写得不够清楚。
- 对 state ownership 的强调不足: `PROJECT_STATE.json`、`iteration_log.json`、
  `project_map.json`、`.auto_iterate/**` 不能互相替代。

本文已按 current workflow 细化。仍然要记住: handbook 是读法, 不是 source of truth。

## 1. 八个 Operator Primitives

日常不要先背 WF1-WF12。先用八个 primitives 判断自己在做什么:

| Primitive | Human question | Main entrypoints | Boundary |
| --- | --- | --- | --- |
| `init` | workspace 和稳定上下文在哪里? | `$orchestrator init`, `$init-project`, `init_context.py` | 只建立结构和 explicit operator preferences, 不证明 research facts。 |
| `evidence` | 我们实际知道什么? | fact docs, evidence tables, `compile_doc.py` | facts 必须来自 source artifacts、logs、metrics、configs 或 explicit records。 |
| `protocol` | 当前 procedure 应该怎么走? | `$protocol-compiler`, `compile_protocol.py` | protocol 是 draft, 直到 human approval 或 explicit acceptance。 |
| `contract` | 哪些边界已经批准? | `$review-packet`, `approve_contract.py`, dynamic gates | review packet 不是 approval; approval 必须可审计。 |
| `code` | 需要改什么实现? | `$code-expert`, `$code-debug` | code 必须服从 contracts、roadmap 和 `project_map.json`。 |
| `validate` | 这次 change 或 stage 是否真的通过? | `$validate-run`, tests, context/docchain gates | 只能报告 `PASS`, `FAIL`, `NOT_RUN`; 未运行不能写成通过。 |
| `iterate` | 下一轮实验决策是什么? | `$iterate`, auto-iterate controller | `iteration_log.json` 是 experiment source of truth。 |
| `release` | 哪些 claims 被支持? | `$final-exp`, `$release`, docchain/context gates | claims 必须落在 approved Claim Boundary 内。 |

六个 operator 阶段仍然有用, 但它们只是分组:

```text
Init -> Explore -> Contract -> Build -> Iterate -> Release
```

| Operator 阶段 | 内部 WF | 对应 primitives |
| --- | --- | --- |
| `Init` | WF0 | `init` |
| `Explore` | WF1-WF4 | `evidence`, `protocol` |
| `Contract` | WF5-WF7 | `contract`, `validate`, planning for `code` |
| `Build` | WF8-WF9 | `code`, `validate` |
| `Iterate` | WF10-WF11 | `iterate`, `validate`, final experiment design |
| `Release` | WF12 | `release` |

## 2. 主流程图

下面这张图把 current workflow 的主要路径、artifact ownership、Gate Evidence 和
human decision 串在一起。图里所有路径名、command 和 workflow IDs 保持英文。

```text
START
  |
  v
WF0 Init
  inputs:
    target workspace, framework source, optional baseline/reference repo
    explicit operator preferences
  writes:
    AGENTS.md, CLAUDE.md, optional OPERATOR_CONTEXT.md
    PROJECT_STATE.json
    optional numbered docs and .evidence scaffold through tooling
  decides:
    workflow_mode = dynamic_context | standard | compatibility
  gates:
    context gate / workflow-state gate or NOT_RUN
  never:
    approve contracts, infer OPERATOR_CONTEXT.md, hand-edit .auto_iterate/**
  |
  v
WF1 Survey
  conclusion artifacts:
    docs/Feasibility_Report.md
    docs/30_evidence/** when dynamic context is enabled
  protocol:
    optional compile_protocol.py -> draft packet
  decision:
    PROCEED | PIVOT | ABANDON
  |
  v
WF2 Idea Debate  (mandatory for new dynamic_context/standard projects)
  conclusion artifacts:
    docs/Idea_Debate.md
  protocol:
    refresh draft assumptions when evidence changed
  decision:
    SELECT | PILOT_FIRST | MERGE | PIVOT | ABANDON
  |
  v
WF3 Refine Idea
  conclusion artifacts:
    docs/Refined_Idea.md
  records:
    task framing, success criteria, metric needs, baseline needs, open questions
  boundary:
    no architecture decision here
  |
  v
WF4 Data Prep
  conclusion artifacts:
    docs/Dataset_Stats.md
    docs/20_facts/** when dynamic context is enabled
  sync:
    PROJECT_STATE.json dataset paths
    CLAUDE.md Dataset Paths
  |
  v
WF5 Baseline Repro
  execution artifacts:
    reproduced/partial baselines, metrics, runnable environment
    docs/Baseline_Report.md
  contract artifacts:
    draft or approved Baseline_Contract.md
    draft or approved Evaluation_Contract.md
  gates:
    protocol drift
    dynamic context
    docchain when current contract/fact/protocol docs change
    review packet for human approval
  approval path:
    review packet -> explicit human approval -> approve_contract.py
      -> check_dynamic_context.py --stage wf10 --review-packet
  |
  v
WF6 Architecture Design
  reads:
    WF1-WF5 evidence, dataset facts, baseline results, contracts
  writes:
    docs/Technical_Spec.md
    optional docs/20_facts/Project_Glossary.md
  gate:
    deep-check when architecture, metric, claim boundary, or high-cost
    interface direction changes
  |
  v
WF7 Build Plan
  reads:
    Technical_Spec, Baseline_Report, contracts, glossary
  writes:
    docs/Implementation_Roadmap.md
    project_map.json
  includes:
    slice_plan + commit_plan
    one planned Commit Slice per roadmap slice unless cross-cutting reason exists
  boundary:
    plan implementation order; do not make new architecture decisions
  |
  v
WF8 Code
  writes:
    src/**, scripts/**, configs/**, project_map.json, PROJECT_STATE.json
  gates:
    read project_map before stable code
    py_compile / ruff or NOT_RUN for modified Python files
    update project_map for stable files/interfaces
    read sliced-commit-rule before git commit
    one completed Commit Slice -> one semantic commit
  |
  v
WF9 Validate
  writes:
    docs/Validate_Run_Report.md
  gates:
    semantic review
    smoke test or NOT_RUN
    WF10 readiness
  bridge:
    PASS -> $auto-iterate-goal check/init/refresh
       -> WF10 dynamic-context preflight for auto mode
    FAIL -> $code-debug
    REVIEW -> human decision before continuing
  |
  v
WF10 Iterate
  owner:
    $iterate writes iteration_log.json
    auto-iterate controller owns .auto_iterate/**
  manual loop:
    plan -> code -> run -> eval
  auto loop:
    auto_iterate_ctl.sh start/resume
      -> check_dynamic_context.py --stage wf10 --review-packet
      -> controller phases invoke $iterate-style plan/code/run/eval
  decisions:
    NEXT_ROUND -> WF10 plan
    DEBUG      -> WF10 plan with bugfix/debug hypothesis
    CONTINUE   -> WF11
    PIVOT      -> WF2 idea-debate/refine-idea
    ABORT      -> stop project
  |
  v
WF11 Final Experiment
  prerequisites:
    final WF10 decision = CONTINUE
    approved Project Contract, Evaluation Contract, Claim Boundary
  writes:
    docs/Final_Experiment_Matrix.md
  gates:
    dynamic context
    respect Evaluation Contract
    respect Claim Boundary
  |
  v
WF12 Release
  writes:
    submission/**, release docs, PROJECT_STATE.json
  gates:
    WF12 dynamic context
    release manifest validation
    claim boundary check
    docchain/context gates for release claims
  decision:
    submit only on explicit user request
  |
  v
DONE
```

## 3. Permission 和 Gate 执行链

Harness 的 runtime guardrails 不是研究结论, 它们只帮助执行 workflow 边界。

```text
UserPromptSubmit
  -> detect active skill / Stage
  -> write .harness_hooks/session.json

PreToolUse
  -> block forbidden manual writes such as .evidence/** and .auto_iterate/**
  -> require active Read Contract before writes
  -> enforce write_scope.allowed_paths for path-aware writes

PostToolUse
  -> record reads and writes
  -> mark pending Gate ledger when sensitive paths changed

Stop
  -> require missing reads or Gate ledger before the turn closes
```

Operator-facing shortcut:

```text
filesystem permission = can this directory be written at the OS/sandbox layer?
stage permission      = has this active Stage earned this write_scope now?
Gate Evidence         = what command/check/review/approval actually ran?
```

## 3.1 Git Commit 分片执行链

`Commit Slice` 是能被单独验证、review 和回滚的最小功能单元。日常修改和
WF8/WF10 code 阶段都按同一个节奏提交:

```text
git commit requested
  |
  v
PreToolUse
  -> require current-turn read:
       .agents/references/sliced-commit-rule.md
  |
  v
inspect worktree
  -> git status --short
  -> git diff --name-only
  -> git diff --cached --name-only when staged files exist
  |
  v
identify Commit Slices
  -> roadmap slice_id, active Stage, subsystem, one bug fix,
     one behavior change, one docs update, or one guardrail change
  |
  v
stage only current slice
  -> files or hunks for that completed slice
  |
  v
validate slice
  -> command PASS/FAIL or explicit NOT_RUN reason
  |
  v
git commit -m "<semantic message explaining what and why>"
  |
  v
repeat for the next independent slice
```

禁止把可分离的改动打成一个 "all changes" commit。不能 stage 用户的无关改动,
也不能把 framework guardrail 改动和 research implementation 改动混在同一个
commit 里。确实必须 cross-cutting 提交时, handoff 里写明为什么拆分会造成
破坏性或误导性状态。

## 4. Evidence 语言

不要把 Evidence 当作单一概念。

| Term | 用途 | 常见 source |
| --- | --- | --- |
| `Conclusion Evidence` | 支持 claim、fact、idea、protocol choice 或 research conclusion | papers, repos, dataset stats, metrics, configs, logs, fact docs |
| `Evidence Chain` | 从 source artifacts 到 current doc/claim 的结构化链 | `.evidence/chains/**`, `.evidence/index.json` |
| `Gate Evidence` | 证明某个 gate、test、command、approval check 是否执行和结果 | command output, CI, controller preflight, approval tool output |
| `Execution Evidence` | command/test/script/training run 的 Gate Evidence | pytest, ruff, training/eval logs, generated artifacts |
| `Approval Evidence` | explicit human approval | current conversation, auditable approval artifact, `approve_contract.py` output |
| `Gate Ledger` | final command/result/reason/artifact report | assistant final response, generated review/validation docs |

一句话规则:

```text
结论为什么可信 -> Conclusion Evidence
流程为什么可放行 -> Gate Evidence
合同为什么已批准 -> Approval Evidence
```

## 5. Dynamic Context 和 Contract Approval

Dynamic context 项目的核心路径:

```text
OPERATOR_CONTEXT.md
  -> docs/30_evidence/**
  -> docs/35_protocol/** draft
  -> docs/10_contract/** draft
  -> review packet
  -> explicit human approval
  -> approve_contract.py
  -> dynamic-context gates
  -> approved contract
```

关键边界:

- `OPERATOR_CONTEXT.md` 只记录 operator 明确给出的稳定偏好, 不是 project facts。
- `docs/35_protocol/**` 是 evidence-derived Protocol Draft, 不是 Approved Contract。
- `docs/10_contract/**` 只有在 Markdown 和 `PROJECT_STATE.json` 两边都记录 approval
  metadata 后, 才能当作 Approved Contract。
- `$review-packet` 只是 human decision input, 不是 approval。
- AI 可以生成 `draft` 或 proposed 内容, 不能自行标记 `approved`。

推荐 approval 命令链:

```bash
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage wf10 --review-packet
python tooling/evidence/approve_contract.py \
  --workspace-root . \
  --contract evaluation_contract \
  --approved-by "<human reviewer>" \
  --approval-source ".evidence/review_packets/wf10/<build_id>/review_packet.md"
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage wf10 --review-packet
```

## 6. State Ownership

| Artifact | Owner | Meaning | Do not use it for |
| --- | --- | --- | --- |
| `PROJECT_STATE.json` | `$orchestrator` owns stage transitions; stage skills may record their own artifact metadata | workflow stage source of truth | experiment history |
| `iteration_log.json` | `$iterate` | experiment source of truth | stage transitions |
| `project_map.json` | `$build-plan`, `$code-expert`, `$code-debug`, or any stable-interface changer | stable implementation map | experiment diary or architecture decision |
| `CLAUDE.md` / `AGENTS.md` | `$init-project` and framework templates | compact session guidance | fast-changing run state |
| `OPERATOR_CONTEXT.md` | operator explicit input, recorded by init/orchestrator | stable preferences and constraints | inferred project facts |
| `docs/10_contract/**` | contract tooling plus explicit human approval | approved or draft boundaries | raw protocol drafts |
| `docs/20_facts/**` | evidence/docchain tooling and stage skills | current facts | unverified assumptions |
| `docs/30_evidence/**` | evidence gathering stages | source tables and open questions | approval records |
| `docs/35_protocol/**` | protocol compiler / protocol drift work | draft protocol | approved contract |
| `docs/50_memory/**` and `MEMORY.md` | `$evaluate`, `$iterate`, human review | candidate and accepted lessons | raw auto-run output |
| `.evidence/**` | evidence tooling | docchains, review packets, protocol compiler output | manual editing |
| `.auto_iterate/**` | auto-iterate controller | runtime state, lock, events, phase logs | manual editing or project facts |

Important invariant:

```text
$iterate does not write PROJECT_STATE.json
$orchestrator does not write iteration_log.json
auto-iterate controller reads PROJECT_STATE.json and iteration_log.json
auto-iterate controller writes only controller-owned runtime under .auto_iterate/**
```

## 7. WF10 Manual 和 Auto Iterate

Manual WF10:

```text
$iterate plan
  -> record hypothesis, config_diff, repeated-lesson check
  -> status = planned
  |
  v
$iterate code
  -> route implementation through $code-debug
  -> identify Commit Slices
  -> require one sliced semantic commit per completed training-related slice
  -> status = training
  |
  v
$iterate run
  -> run training/eval or register manual run
  -> record run_manifest, metrics, training_trace
  -> status = running
  |
  v
$iterate eval
  -> route analysis through $evaluate
  -> write per-iteration report
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
  -> starts phase loop
  |
  v
controller phases
  -> plan -> code -> run -> eval
  -> each phase starts fresh codex exec
  -> postconditions update controller state/events
```

Operator controls:

| Command | Meaning |
| --- | --- |
| `auto_iterate_ctl.sh status --json` | machine-readable status for wrappers |
| `auto_iterate_ctl.sh tail --jsonl --lines 50` | machine-readable events |
| `auto_iterate_ctl.sh pause` | pause at next safe phase boundary |
| `auto_iterate_ctl.sh stop` | stop at next safe phase boundary |
| `auto_iterate_ctl.sh resume` | rerun dynamic preflight and continue |
| `auto_iterate_ctl.sh override --goal <path>` | stage next goal for next round boundary |

Risk flags require explicit operator acceptance:

- `--allow-draft-contract`: run with draft Evaluation Contract for this run.
- `--allow-review-required`: run despite a protocol review gap for this run.
- `--skip-dynamic-preflight --skip-dynamic-preflight-reason "<reason>"`: only for legacy or manually gated runs; controller records the reason.

## 8. Stage Cards 和 Source of Truth

Stage Cards 是读法, 不是 contract source of truth。

```text
.agents/skill-contracts/contracts.json
  -> source of truth for required reads, write scope, required actions, forbidden actions
  |
  v
tooling/codex_hooks/generate_stage_cards.py
  |
  v
docs/Workflow_Stage_Cards.md
  -> operator quick read
```

生成 Stage Cards:

```bash
python tooling/codex_hooks/generate_stage_cards.py --workspace-root . --output docs/Workflow_Stage_Cards.md
```

每张 card 应该能回答:

```text
Stage:
Purpose:
Inputs:
Can write:
Must read:
Must prove:
Cannot do:
Exit condition:
```

## 9. Skill Routing 快速判断

| 你要做的事 | 应用 skill |
| --- | --- |
| stage status、advance、rollback、decision logging | `$orchestrator` |
| 初始化或刷新 compact guidance / operator context | `$init-project` |
| 编译 protocol draft | `$protocol-compiler` |
| 检查 protocol drift | `$protocol-drift-check` |
| 构建 human review packet 或记录 contract approval | `$review-packet` |
| first-pass WF8 implementation from roadmap | `$code-expert` |
| 普通 implementation bugfix / iteration code change | `$code-debug` |
| code review only, 不修改 subject files | `$code-review` |
| hook、skill contract、routing、permission、operator handbook、Stage Cards | `$harness-maintenance` |
| WF10 manual loop | `$iterate` |
| WF10 auto goal readiness | `$auto-iterate-goal` |
| experiment result analysis | `$evaluate` |
| WF11 final experiment matrix | `$final-exp` |
| WF12 package / submit / release validation | `$release` |

## 10. Operator 检查清单

开始一个阶段前:

- [ ] 当前 `workflow_mode` 是 `dynamic_context`, `standard`, 还是 `compatibility`。
- [ ] 当前 active skill 和 Stage 是明确的。
- [ ] 已读对应 Stage Card 或 skill contract 的 `Must read`。
- [ ] 知道 `write_scope.allowed_paths` 是否覆盖要写的路径。
- [ ] 知道这一步需要 Conclusion Evidence、Gate Evidence、Approval Evidence 中的哪一种。
- [ ] 知道哪些 decision 需要 explicit human approval。

结束一个阶段前:

- [ ] 新增 claim 有 Conclusion Evidence 或标为 open question。
- [ ] 当前 doc/contract/fact/protocol write 使用了需要的 evidence/docchain tooling, 或明确 `NOT_RUN`。
- [ ] 需要的 tests、context gates、workflow-state gates、controller preflight 已报告 `PASS`、`FAIL` 或 `NOT_RUN`。
- [ ] Gate ledger 没有把 `NOT_RUN` 写成 `PASS`。
- [ ] Review packet 没有被当成人类批准。
- [ ] 下一步 decision 是 explicit, 不是 agent 自己推进。

## 11. 什么时候读深文档

| 情况 | 读什么 |
| --- | --- |
| 想理解完整 workflow | `.agents/references/workflow-guide.md` 或 `.claude/Workflow_Guide.md` |
| 想低负担查看每个 skill 边界 | `docs/Workflow_Stage_Cards.md` |
| 想修改 hooks、permission 或 routing | `tooling/codex_hooks/README.md` |
| 想理解 Stage 权限提升 | `tooling/codex_hooks/Stage_Permission_Elevation_Guide.md` |
| 想统一 workflow 术语 | `.agents/references/ubiquitous-language.md` |
| 想理解 git commit 分片提交规则 | `.agents/references/sliced-commit-rule.md` |
| 想启动或恢复 auto-iterate | `tooling/auto_iterate/docs/cli_control_guide.md` |
| 想设置新 workspace / dual-repo | `AI_AGENT_SETUP.md` |

## 12. 推荐的改进节奏

每一版 workflow 优化只回答一个问题:

```text
这次减少了哪一类认知负担?
```

建议顺序:

1. 统一语言: 先稳定 `Conclusion Evidence`, `Gate Evidence`, `Approval Evidence`, `Contract`, `Stage`, `Skill`。
2. 统一读法: Handbook 是入口, Stage Cards 是每个 skill 的 quick read。
3. 统一机器源: `contracts.json`、schemas、tooling outputs 尽可能生成或校验说明。
4. 统一路由: natural-language prompts 应稳定映射到正确 skill。
5. 统一 gate: Gate ledger 只报告 Gate Evidence, 不冒充 Conclusion Evidence 或 Approval Evidence。
