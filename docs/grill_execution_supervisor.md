# Grill + Execution Supervisor 机制参考架构

## Context Summary

本文档阐述 Harness Research 中一套拟议的 `grill + execution supervisor`
机制。它的用途是帮助人类理解这套机制的目的、边界、完整流程、HITL
细节、状态恢复模型，以及外部可参考的实现。它不是用于指导 agent
直接修改 workflow 的操作手册。

用户第一层不应该先选择内部 WF node，而应该先选择 human-facing entrypoint：

```text
rough idea or request
  -> grill | execution supervisor
  -> supervisor action, when applicable
  -> status / output / pending request
  -> Human Approval or next safe action
```

内部 WF0-WF12 map 保留为 artifact、Skill Contract、Gate 和恢复排查索引。
只有需要解释兼容关系、postcondition 或 completion 条件时，本文才展开细节。

核心拆分如下：

```text
Grill mode
  -> WF1-WF3
  -> 高互动、多轮追问、挑战研究目标
  -> 产出 Research Intent Draft
  -> 由人类明确决定是否进入执行段

Execution supervisor mode
  -> WF4-WF12
  -> 确定性状态机依次调用现有 Skill
  -> 通过 postcondition / Gate Evidence 判断是否继续
  -> 在缺信息、需要 Human Approval、需要转向判断时持久化暂停

Change intake / delta grill
  -> codebase 已建立后的新需求、新 idea、config/code delta
  -> 先分类影响范围，再路由到 code-debug / iterate / build_delta / contract review
  -> 不默认重跑完整 WF1-WF12
```

这套机制不替代 `Skill`。`Skill` 仍然描述某个 Stage 或任务应该怎么做；
supervisor 负责什么时候调用哪个 Skill、如何验证、何时中断、如何恢复。

## Reader Path

- 只想操作：读 `workflow_handbook/Workflow_Operator_Handbook.md` 和
  `workflow_handbook/pages/operator_task_index.md`。
- 想理解机制：读本文的设计目的、总体架构、HITL 和 segment model。
- 想实现或维护：读 `docs/grill_execution_supervisor_implementation_plan.md`。
- 想排查内部 artifact：读 `workflow_handbook/Workflow_Stage_Cards.md` 和生成的
  Stage / Skill detail pages。

## Currentness Rule

本文的外部链接和设计综述是背景资料；实现判断必须以当前仓库 source artifacts、
schemas、tests 和 tooling output 为准。修改本文后，应同步 handbook source 和
`docs/_site/workflow_handbook/**`，并在最终 handoff 报告运行过的 validator / tests。

## Document Boundary

本文档只负责解释 `grill + execution supervisor` 的机制设计：

- 为什么要把 early research discussion 和 later execution automation 分开。
- Grill、execution supervisor、change intake 各自解决什么问题。
- HITL、postconditions、Gate Evidence、Approval Evidence 的设计语义。
- 可复用的外部架构模式和工程经验。

具体如何把这套机制落地到 Harness Research 仓库，包括文件路径、schema 名称、
CLI 命令、hook 改动、测试列表和 rollout slice，放在
`docs/grill_execution_supervisor_implementation_plan.md`。本文只在必要处提到
Harness 名称和 artifact 类型，以便解释机制边界。

## Evidence Sources

| Source | Why It Was Read | Key Facts Used |
| --- | --- | --- |
| `README.md` | 当前 Harness 目标和 workflow 形状 | Harness 目标是用 Stage、Skill、Hook、可溯源文档、代码切片计划和 Ralph-style loop 降低研究执行摩擦，而不是替研究者产生 idea。 |
| `AGENTS.md` | 本仓库的 workflow、HITL、docs 和 auto-iterate 规则 | Human Approval 对 contracts、claim boundaries、高风险 transitions 和 release decisions 仍然强制；`.auto_iterate/` 是 controller-owned。 |
| `CLAUDE.md` | 本仓库的语言策略和当前 auto-iterate 边界 | 自然语言 artifact 应匹配用户语言；auto-iterate 不替代 contracts、claims、stage transitions 的 Human Approval。 |
| `.agents/references/workflow-guide.md` | Canonical Stage model 和 state ownership | WF0-WF12、八个 operator-facing primitives、Gate Evidence model、`PROJECT_STATE.json` / `iteration_log.json` / `.auto_iterate/` 的 ownership。 |
| `.agents/references/ubiquitous-language.md` | Harness 术语 | Stage、Skill、Skill Contract、Gate Evidence、Approval Evidence、Review Packet、Protocol Draft、Approved Contract、Claim Boundary 的定义。 |
| `.agents/references/documentation-evidence-rule.md` | 文档证据要求 | 文档应区分 verified facts、inferences、open questions。 |
| `.agents/references/documentation-style.md` | 文档格式要求 | workflow 和状态转换优先用简洁 ASCII 图；当前文档应面向人类快速理解。 |
| `.agents/skills/iterate/SKILL.md` | 当前 WF10 loop ownership | `$iterate` 拥有 `iteration_log.json`；auto-iterate controller 只通过 runtime adapter 调用 `$iterate` phases，不写 experiment source of truth。 |
| `.agents/skills/code-expert/SKILL.md` | Hook 推荐读取项 | WF8 code generation 要基于 roadmap、project map、contracts、Gate Evidence；这强化了 supervisor 不应绕过现有 Skill Contract。 |
| `.agents/skills/code-debug/SKILL.md` | post-WF8 修改路由 | `$code-debug` 适用于 post-WF8 bug fixes、planned iteration changes、narrow performance tuning；不应用于 hooks、skill contracts、routing 或 permission policy。 |
| `tooling/auto_iterate/docs/cli_control_guide.md` | 现有 durable loop 行为 | 当前 controller 已有 `start/status/pause/stop/resume`、JSON status、event logs、exit codes、`manual_action_required`。 |
| Autoresearch-style docs, 2026-06-05 local review | 文档结构参考 | 好的 autonomous research docs 通常先给 quick start、status/monitoring、resume/recovery、workdir/state surface，再给深层机制说明。 |
| `schemas/skill_contracts.json` | 机器可读 Skill Contract surface | 当前 contracts 已包含 triggers、required reads、required actions、forbidden actions、gates、sensitive paths、write scopes、artifact outputs。 |
| `docs/grill_execution_supervisor.md` | 当前被扩展的机制文档 | 原文已定义 Grill mode、Execution supervisor mode、typed HITL interrupts、postconditions、segments、implementation outline。 |
| 当前用户需求 | 本次扩展的设计输入 | 需要覆盖 codebase 建成后的新需求/新 idea 交互，以及提前回答 execution supervisor 断点问题的识别和预采集。 |
| [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) | 当前 HITL interrupt 模式 | `interrupt()` 可暂停执行、保存 graph state、返回 JSON-serializable payload，并用 `Command(resume=...)` 从同一 cursor 恢复。 |
| [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | durable execution 模型 | Checkpointer 会在每个 step 保存 graph state，支持 HITL、time travel debugging 和 fault-tolerant execution。 |
| [LangGraph workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) | workflow vs agent 模式 | Workflows 是预定义 code paths；agents 是动态决定过程和 tool usage；orchestrator-worker 和 routing 是常见模式。 |
| [OpenAI Agents SDK HITL](https://openai.github.io/openai-agents-python/human_in_the_loop/) | approval 和 RunState 模式 | Tools 可声明 `needs_approval`；run 返回 interruptions；`RunState` 可序列化，并在 approve/reject 后 resume。 |
| [OpenAI Agents SDK running agents](https://openai.github.io/openai-agents-python/running_agents/) | 长运行 durable integrations | OpenAI 文档把长运行 HITL agents 指向 Dapr、Temporal、Restate、DBOS 等 durable orchestration。 |
| [OpenAI Agents SDK handoffs](https://openai.github.io/openai-agents-python/handoffs/) | multi-agent delegation 模式 | Handoffs 可把执行转交给 specialist agent；delegated workflow 需要 tool-level guardrails。 |
| [OpenAI Agents SDK guardrails](https://openai.github.io/openai-agents-python/guardrails/) | guardrail 放置位置 | manager、handoff、delegated specialist 工作流中，不能只依赖 agent-level input/output guardrails；function tool 需要 tool guardrails。 |
| [OpenAI practical guide to building agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) | 当前 agent architecture guidance | 建议先最大化 single-agent 能力，只有任务/工具复杂度需要时才拆 multi-agent；高风险函数应按风险等级触发 guardrail 或 human escalation。 |
| [Anthropic, Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) | workflow vs agent distinction | 对已知路径，workflow 提供 predictability；对需要动态决策的场景，agent 更合适。 |
| [HumanLayer 12-factor-agents](https://github.com/humanlayer/12-factor-agents) | production-oriented LLM app principles | 相关原则包括 own context/control flow、launch/pause/resume APIs、contact humans with tool calls、small focused agents、stateless reducer。 |
| [awaithumans](https://github.com/awaithumans/awaithumans) | 可复用 HITL infrastructure | 提供 `await_human()` / `awaitHuman()`、typed Pydantic/Zod responses、Slack/email/dashboard、idempotency、AI verifier、Temporal/LangGraph adapters。 |
| [IRAS](https://github.com/krishnashakula/IRAS) | production-style state machine example | 使用 LangGraph state machine、typed Pydantic outputs、PostgreSQL checkpoints、Slack/API approval、rollback-aware remediation。 |
| [Thoughtworks Technology Radar, April 2026](https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2026/04/tr_technology_radar_vol_34_en.pdf) | 2026 durable execution guidance | 建议先用 agent framework 原生 durable execution，复杂或关键后再上 Temporal/Restate/Golem 等独立平台。 |
| [NIST AI Agent Standards Initiative, February 2026](https://www.nist.gov/news-events/news/2026/02/announcing-ai-agent-standards-initiative-interoperable-and-secure) | governance context | NIST 将 reliability、interoperability、security、identity、authorization 视为 agent adoption 的核心问题。 |
| [CSA Agentic Universe, April 2026](https://labs.cloudsecurityalliance.org/wp-content/uploads/2026/04/agentic-universe-april-2026-v1.pdf) | HITL threat model | HITL agents 的主要风险包括 approval fatigue、context manipulation、approval bypass；approval request 需要详细、可审计。 |
| [Guardrails Beat Guidance, arXiv 2604.11088](https://arxiv.org/abs/2604.11088) | coding-agent rule reliability | 该研究报告负向约束类规则比正向行为指导更可靠，支持把关键安全性放进 guardrails/postconditions，而不是长 prompt。 |
| [TSAssistant, arXiv 2604.23938](https://arxiv.org/abs/2604.23938) | domain HITL report-writing pattern | 使用 specialized subagents、section-level evidence synthesis、interactive refinement，并保留专家最终决策权。 |

## Verified Facts

- Harness 当前已有 canonical WF0-WF12 workflow 和 WF10 auto-iterate
  controller。
- 当前 WF10 controller 已支持 `start`、`status`、`pause`、`stop`、`resume`、
  event logs、JSON status、exit codes、lock/heartbeat 和
  `manual_action_required`。
- `schemas/skill_contracts.json` 已有机器可读 Skill Contract 字段，可作为
  supervisor node registry 的初始来源。
- 当前 Harness policy 要求人类显式批准 contracts、claim boundaries、高风险
  transitions 和 release decisions。
- 当前 `$code-debug` 是 post-WF8 implementation change 的主要入口，适用于 bugfix、
  planned iteration change 和窄范围 performance edit。
- 2026 年仍在维护的 agent 工程实践强调 durable pause/resume、typed approval
  payload、tool guardrails、postconditions、deterministic orchestration，而不是
  单纯增加自由协作 agent 数量。

## Inferences

- Harness 可以从“人工依次调用 Skill”演进为“分段 supervised workflow”，同时保留
  Skill 层。
- WF1-WF3 应保持高互动，因为 research idea 的质量依赖 operator observation、
  taste、domain insight、failure analysis 和 claim discipline。
- WF4-WF12 可在 postconditions 和 Gate Evidence 足够强时逐步自动化。
- codebase 已经建立之后的新需求不应默认重跑完整 WF1-WF12；应先做 change
  intake，按影响范围路由。
- Grill mode 可以提前收集 execution supervisor 可能需要的信息，但 supervisor
  启动前仍需验证这些预回答是否存在、可用、未过期、不冲突。
- 最稳的落地方式是先做 Harness-native lightweight supervisor，复用
  `tooling/auto_iterate` 的状态、事件、暂停和恢复模式；当 run 变成多用户、多机器
  或多日等待时，再考虑 Temporal/Restate/DBOS/Dapr。

## Open Questions

- 第一版 runtime 应放在 `.workflow_supervisor/`，还是扩展 `.auto_iterate/`？
  本文建议单独使用 `.workflow_supervisor/`，避免 WF10 runtime ownership 混淆。
- `grill` mode 应写哪些 artifacts：root `docs/*.md`、dynamic-context numbered
  docs，还是两者都写？
- `grill` 应实现为新 Skill、supervisor subgraph，还是普通 CLI 命令？
- `schemas/skill_contracts.json` 应直接扩展 `automation_policy`，还是新增
  `workflow_supervisor_nodes.json` 引用 Skill Contracts？
- `Execution Readiness Packet` 应写成 root `docs/*.md`、JSON state，还是同时写
  human-readable Markdown 和 machine-readable JSON？
- codebase 建成后的 `change intake` 是否应是显式 supervisor action，还是由
  `build` / `iterate` actions 内部自动路由？

V0 implementation should not leave these choices ambiguous. The implementation
plan freezes the first runtime namespace, artifact layout, node registry shape,
human interface, and change-intake action; later versions may revisit those
choices after tests and fixture runs prove the baseline.

## 设计目的

这套机制的目标是：减少 workflow 手工调用摩擦，同时不削弱人类对研究判断、
contracts、claims 和 release 的责任。

当前手动调用 Skill 的优点是灵活、人类参与充分、问题容易局部定位；缺点是操作
成本高，operator 必须记住下一步 Skill、必跑 gates、哪些 artifact 是 Review
Packet 而不是 Approval Evidence，以及中断后如何恢复。

`grill + execution supervisor` 的设计把这两个问题拆开：

```text
research judgment problem
  -> Grill mode
  -> 多轮追问、挑战、澄清 human intent

workflow friction problem
  -> Execution supervisor
  -> 状态机、postconditions、Gate Evidence、typed HITL interrupts
```

这套机制应该让 operator 的理解更清楚，而不是把 operator 变成 approve button。

## Non-Goals

- 不做 autonomous idea generator。
- 不让模型自行批准 contracts、Claim Boundaries、release claims 或 Stage
  transitions。
- 不把 model-written summary 当成 Gate Evidence。
- 不把模型自称“完成了”当成 completion definition。
- 不把所有 Skills 合并成一个 mega-agent。
- 不采用“多个 agent 自由聊天决定下一步”的通用 swarm。
- 不在没有 postconditions 的情况下假装自动化已经可靠。

## 总体架构

```text
                        +----------------------+
                        |      Operator        |
                        +----------+-----------+
                                   |
             answers / approvals / steering / rejection
                                   |
                                   v
+------------------+      +--------+---------+      +------------------+
|  Grill Runtime   | ---> | Segment Boundary | ---> | Exec Supervisor  |
|  WF1-WF3         |      | Human Decision   |      | WF4-WF12         |
+------------------+      +------------------+      +--------+---------+
                                                                  |
                                                                  v
                                                        +---------+---------+
                                                        | Skill Workers     |
                                                        | existing Skills   |
                                                        +---------+---------+
                                                                  |
                                                                  v
                                                        +---------+---------+
                                                        | Postconditions    |
                                                        | gates / artifacts |
                                                        +-------------------+
```

| Mode | Main Work | Automation Level | Human Role | Exit Condition |
| --- | --- | --- | --- | --- |
| `grill` | WF1-WF3 idea clarification、debate、claim discipline | 低自动化，高对话 | Co-designer / decision maker | 人类接受 Research Intent Draft，或 pivot / abandon |
| `execution_supervisor` | WF4-WF12 data、baseline、build、validate、iterate、release | postconditions 强的地方自动继续 | Approver / information provider / steering authority | segment 完成、HITL interrupt、gate failure 或 fatal error |
| `change_intake` action | post-WF8/WF9 mature codebase 上的新需求、新 idea、config/code delta | Execution Supervisor 内部先分类，低风险自动路由，高风险进入 delta grill | Intent clarifier / steering authority | change route 明确，或进入 STEER / approval gate |

## Segment Model

这套机制只暴露两个第一层 human-facing entrypoint：`grill` 和
`execution supervisor`。Execution Supervisor 再暴露 scoped actions：

```text
harness grill
  -> WF1-WF3
  -> produces Research Intent Draft
  -> requires explicit exit decision

harness <action>
  -> execution supervisor
  -> action is one of prepare / build / iterate / release / change

prepare
  -> WF4-WF5
  -> data, baseline, protocol, review packet
  -> pauses for dataset input and Evaluation Contract approval

build
  -> WF6-WF9
  -> architecture, plan, implementation, validation
  -> pauses for architecture tradeoffs and high-risk scope changes

iterate
  -> WF10
  -> existing auto-iterate controller
  -> pauses for manual_action_required, PIVOT, ABORT, budget, or goal changes

release
  -> WF11-WF12
  -> final experiment, claim boundary, release package
  -> pauses for Claim Boundary and release/submission approval

change
  -> after WF8/WF9 or after a mature codebase exists
  -> classify a new request as bugfix / experiment_delta / stable_code_delta /
     architecture_delta / evaluation_delta / claim_boundary_delta /
     new_research_direction
  -> route to code-debug / iterate / build_delta / review-packet / delta grill
```

这些 actions 不是新的顶层入口。它们代表 Execution Supervisor 内部不同的人类参与语义：

- `grill`: human input 本身就是主要工作。
- `prepare`: human input 解决缺失事实和 contract risk。
- `build`: human input 处理 architecture / scope / tradeoff。
- `iterate`: human input 处理 loop exits、pivot、failure、budget。
- `release`: human input 批准 supported claims 和 submission actions。
- `change`: human input 说明新需求意图；supervisor 判断它是局部 delta 还是新研究
  branch。

Compatibility rule: `harness grill` may cover the interactive intent work that
historically spans WF1-WF3, but its draft artifacts do not by themselves
complete WF1, WF2, or WF3. Stage completion still requires canonical Stage
artifacts and Gate ledger, produced by existing Skills or by an explicit bridge
path that validates those Skill contracts.

## Grill Mode

### Purpose

`grill` mode 的目的不是自动产出 idea，而是帮助研究者把隐含的观察、动机、
约束和 claim 边界说清楚。它应该像一个严格但有建设性的研究合作者：持续追问、
挑战、收敛，而不是马上执行。

它的输出是 `Research Intent Draft`，不是 Approved Contract。

### Core Flow

```text
seed idea
  -> intake summary
  -> hard question round
  -> human answers
  -> skeptic critique
  -> methodologist critique
  -> implementation realism check
  -> draft update
  -> gap check
  -> another round OR exit decision
```

### Internal Review Lenses

用户面前最好只有一个 facilitator，但内部可以使用多个 lens：

| Lens | Purpose | Typical Challenge |
| --- | --- | --- |
| `facilitator` | 控制对话节奏，把回答转成结构化 state | “这一轮我们到底要决定什么？” |
| `skeptic` | 挑战 novelty、evidence、motivation | “什么结果会说明这个 idea 不值得继续？” |
| `methodologist` | 挑战 evaluation design 和 causal claim | “这个 metric 能区分 hypothesis 和 confounder 吗？” |
| `implementation realist` | 挑战 data、compute、code、timeline 可行性 | “最小可运行 slice 是什么？” |
| `claim boundary reviewer` | 防止过度 claim | “如果实验成功，最多能 claim 到什么程度？” |

第一版不需要真的启动多个 agent。一个 model call 按这些 lens 输出 structured
sections 更容易 debug。只有当单模型 lens 质量不足时，再引入 specialist workers。

### Round Contract

每轮 grill 应该有固定结构，避免变成闲聊：

```json
{
  "round_id": "grill_001",
  "input_state": {
    "idea_summary": "...",
    "known_constraints": [],
    "open_questions": []
  },
  "questions": [
    {
      "id": "q1",
      "why_this_matters": "...",
      "question": "...",
      "answer_type": "free_text|choice|path|number|approval"
    }
  ],
  "human_answers": {},
  "critiques": {
    "skeptic": [],
    "methodologist": [],
    "implementation_realist": []
  },
  "draft_updates": {},
  "exit_recommendation": "continue_grill|accept_intent|pivot|abandon"
}
```

### Question Policy

每轮默认 3-5 个高价值问题。问题要少，但要硬。

应该问：

- 你真正想验证的 target claim 是什么？
- 为什么这个问题值得做？
- 什么结果会 falsify 这个 hypothesis？
- 哪个 baseline 如果不做会被 reviewer 质疑？
- 哪些 constraints 是 hard boundaries，而不是 preferences？
- 哪个 data / metric / compute fact 现在缺失？
- 如果实验有效，claim 最多能说到哪里？
- 如果实验失败，pivot / abort 条件是什么？

不应该问：

- 仓库里能自己查到的事实。
- 宽泛而无决策价值的 survey 问题。
- 没有具体 action 的 approval。
- 一次性抛出十几个问题造成 fatigue。

### Grill Output: Research Intent Draft

建议产物：

```markdown
# Research Intent Draft

## Problem

## Operator Observation

## Candidate Claim

## Minimal Hypothesis

## Why This Is Worth Testing

## Target Metric / Evaluation Signal

## Baselines and Negative Controls

## Dataset and Compute Assumptions

## Forbidden Directions

## Pivot / Abort Conditions

## Open Questions

## Human Exit Decision
```

`Human Exit Decision` 是 segment boundary，可取：

- `accept_intent_continue_to_prepare`
- `continue_grill`
- `pivot`
- `abandon`

agent 可以推荐，但不能代替 operator 做 exit decision。

### Grill and WF1-WF3 Artifacts

`Research Intent Draft` is an intake artifact. It can seed WF1-WF3, but it is
not a drop-in replacement for existing Harness outputs:

| Existing Stage | Canonical Artifact | Grill Relationship |
| --- | --- | --- |
| WF1 survey-idea | `docs/Feasibility_Report.md` and evidence tables | Grill clarifies the question and evidence needs; WF1 still records Conclusion Evidence and feasibility. |
| WF2 idea-debate | `docs/Idea_Debate.md` | Grill asks debate-style questions; WF2 still records selected direction, alternatives, and risks. |
| WF3 refine-idea | `docs/Refined_Idea.md` | An accepted Research Intent Draft can be promoted only through the `$refine-idea` contract or an explicit bridge validator. |

第一版可以提供两个模式：

```text
harness grill
  -> draft only
  -> no Stage completion claim

harness grill --bridge-stages
  -> run/validate WF1-WF3 Skill contracts
  -> mark nodes complete only when canonical artifacts and Gate ledger exist
```

这样 Grill 保留高互动优势，同时不破坏 `workflow_handbook` 中已有的
Stage / Skill / Gate source-of-truth。

### Execution Readiness Questions

Grill mode 可以提前询问 execution supervisor 运行时常见的断点问题，但要把这些
问题和 research-intent 问题区分开：

```text
Research Intent Questions
  -> 为什么做、claim 是什么、metric 是什么、baseline 是什么

Execution Readiness Questions
  -> 数据放哪、baseline 下载到哪、训练命令是什么、预算多少
```

Grill 不应该一次性把执行问题变成长问卷。更合适的做法是在每轮末尾或退出前收集
少量高价值 readiness 信息：

- `dataset_root`: 数据集根目录或候选下载目录。
- `baseline_download_dir`: baseline checkpoints / external artifacts 的缓存目录。
- `train_command`: 预期训练入口或 smoke command。
- `eval_command`: 预期评估入口。
- `output_dir`: experiment outputs / reports 的默认位置。
- `compute_budget`: GPU、CPU、wall-clock、API 或 LLM budget。
- `external_download_policy`: 是否允许下载外部模型、数据、baseline artifacts。
- `approved_datasets` / `approved_baselines`: 允许 prepare 自动获取的精确来源。
- dataset item 可记录 `source`、`target`、`license`、`max_size_gb`；baseline item
  可记录 `repo`、`ref`、`target`。
- `target_paths`: 数据集和 baseline 的本地目标路径。
- `unknowns`: 仍会阻塞自动化的开放问题。
- `operator_approved_at`: operator 明确批准这些来源的时间戳；缺失时不能当作 unattended approval。
- `credential_boundary`: 哪些账号、API key、远程服务不能由 agent 自动操作。
- `runtime_limit`: 单次 run 的最大时长。
- `forbidden_code_or_config_changes`: 不允许改动的路径、config key、public interface。

这些答案只能作为 candidate inputs。Execution supervisor 启动前仍需验证它们存在、
可访问、未过期，并且不与 Approved Contract 或当前 facts 冲突。

### Execution Readiness Packet

Grill mode 的第二个建议产物是 `Execution Readiness Packet`。它是给 execution
supervisor 消费的预回答输入，不是 Approval Evidence，也不是 project facts 的最终
证明。

建议同时保留 human-readable summary 和 machine-readable state。设计要求是：

- 记录 answer provenance：谁回答、什么时候回答、来自哪一轮 Grill。
- 区分 input value 和 verification status。
- 对 local/private values 支持 redaction，不把敏感路径或 credentials 写进公开 docs。
- 把所有字段标成 candidate / unchecked，直到 readiness preflight 验证。
- 明确声明这些答案不是 Approved Contract、不是 Approval Evidence、不是 verified
  project fact。

具体 Markdown 路径、runtime JSON 路径和 schema 字段由实施计划维护。

Execution supervisor 只有在相关字段通过 preflight 后，才能把这些答案当作已解决
断点；否则应发出 `ASK_INPUT` 或 `STEER` interrupt。

### Grill vs Auto-Survey

`grill` 不是普通 survey，也不是自动文献综述。Survey 可作为 WF1 的一部分提供
Conclusion Evidence，但 Grill 首先解决的是 human intent、claim shape、failure
criteria 和 workflow readiness。

## Execution Supervisor Mode

### Purpose

Execution supervisor mode 用来减少 WF4-WF12 的手工 Skill 调用。它要回答：

- 下一步应该运行哪个 node / Skill？
- 运行前需要哪些 files、inputs、contracts？
- 什么 postcondition 证明 node 完成？
- 哪些 gates 必须运行？
- 哪些情况必须暂停给人？
- 中断后如何 adopt / rerun / fail closed？

### High-Level Loop

```text
load state
  -> select current node
  -> render bounded worker prompt
  -> run Skill worker
  -> classify runtime result
  -> validate postconditions
  -> run gates
  -> update state
  -> continue OR interrupt OR fail
```

supervisor 只拥有 runtime state 和 orchestration。Stage artifacts 仍由现有
Skills 和工具拥有。

### Preanswered Inputs and Readiness Preflight

Execution supervisor 启动前应先运行 readiness preflight。它的目标是识别用户已经
提前回答的问题，减少运行中不必要的 `ASK_INPUT` interrupt。

输入解析优先级建议如下：

```text
Approved Contracts
  -> PROJECT_STATE.json / CLAUDE.md / AGENTS.md
  -> Execution Readiness Packet
  -> Grill Round Log / Research Intent Draft
  -> verified filesystem / command checks
  -> ASK_INPUT interrupt
```

这个顺序很重要：

- Approved Contracts 优先于 operator preference 和 Grill output。
- `PROJECT_STATE.json`、`CLAUDE.md`、`AGENTS.md` 中的 current facts 优先于未验证
  的 conversation answer。
- `Execution Readiness Packet` 是 candidate input，需要验证后才能用于自动继续。
- Grill output 可解释 intent 和 constraints，但不直接证明环境事实。
- 文件系统路径、命令、权限、依赖需要通过 command 或 gate 检查。

Readiness preflight 的输出应包含四类信息：

- resolved inputs：已验证可用的预回答。
- missing inputs：还需要人类提供的字段。
- conflicts：预回答与 Approved Contract、current facts 或本地检查冲突的地方。
- interrupt suggestion：如果不能继续，应生成哪类 typed interrupt。

如果用户提前提供了 `baseline_download_dir`，supervisor 不应该再暂停询问同一问题。
但它应先验证：

```bash
test -d /data/baselines
test -w /data/baselines
```

验证通过则继续；验证失败或与当前 contracts 冲突，则发出 typed interrupt。

### Runtime State and Node Registry Principles

Execution supervisor 需要 durable runtime state，但设计层只规定语义，不规定具体
文件布局。实现层必须能记录：

- current segment / node / attempt / run status；
- lock、heartbeat 或等价并发控制；
- resolved candidate inputs 和它们的 verification status；
- completed nodes、artifact refs、Gate Evidence refs；
- pending human request 和 resume cursor；
- budget、timeout、last failure、recovery strategy；
- append-only events，便于 crash recovery 和 audit。

Node registry 也应是机器可读的，但它不是 Skill 的替代品。Skill Contract 说明一个
Skill 如何安全执行；node registry 说明这个 Skill 在 supervised workflow 里的自动化
资格、前置条件、后置条件、强制暂停点和恢复策略。

具体 runtime namespace、JSON schema、registry 文件名和字段，见
`docs/grill_execution_supervisor_implementation_plan.md`。

实现层还必须让 `state.json` 成为可恢复 cursor，而不是只依赖 event replay 或模型
summary。`state.json`、node record、worker result 和 pending request 之间的关系应
能通过 schema tests 和 recovery fixture 验证。

### Suggested Nodes

| Segment | Nodes | Auto-Continue Default | Mandatory Stop Points |
| --- | --- | --- | --- |
| `prepare` | `data-prep`, `baseline-repro`, `protocol-compiler`, `review-packet` | facts/gates 通过时继续 | dataset source missing、baseline ambiguity、Evaluation Contract approval |
| `build` | `refine-arch`, optional `deep-check`, `build-plan`, `code-expert` / `code-debug`, `validate-run` | accepted roadmap 内继续 | architecture tradeoff、scope expansion、high-risk interface change、validation failure |
| `iterate` | existing `auto_iterate` controller | 复用 WF10 logic | `manual_action_required`、`PIVOT`、`ABORT`、budget exhausted、goal override |
| `release` | `final-exp`, `release`, `review-packet`, docchain/context gates | 保守，通常会频繁暂停 | Claim Boundary approval、release claim approval、submission request |

Prepare 的第一版 HITL proof-of-concept 不应叫 `prepare_complete`。它可以先证明
readiness preflight、Review Packet 和 approval resume，但只有 data-prep 与
baseline-repro 的 postconditions 都满足后，才允许 build、iterate 或 release 依赖
prepare。

当前实现保留 PoC 路径，同时提供 `prepare --complete`。启动 full prepare 时，
supervisor 会先写
`.workflow_supervisor/runs/<run_id>/runtime/grill_bridge.json`：它读取
`.workflow_supervisor/readiness.json`、`docs/Execution_Readiness_Packet.md`、
`docs/Research_Intent_Draft.md` 和 `docs/Grill_Round_Log.md`，只采用结构化
readiness rows、显式 `key: value` 行或带 dataset/baseline 标签的 URL。
readiness 通过后，supervisor 会在实际下载或 clone 前写
`.workflow_supervisor/runs/<run_id>/runtime/acquisition_plan.json`，记录
dataset/baseline source、target、policy、blocked remote sources 和 next nodes。
Redacted 或 ambiguous 值不会被猜测，会转成 typed pending request。远端操作仍需
`--allow-external-downloads` 或 Grill readiness 中明确的
`external_download_policy: allow` / `allow_external_downloads: true`。`build`
通过结构化 worker result 顺序执行 registry 节点，worker prompt 带 postconditions
和 allowed write patterns；Codex worker 先把 result JSON 写到
`.agents/state/workflow_supervisor_worker_results/**` handoff path，再由
supervisor 验证并采纳进 `.workflow_supervisor/**`。只有 `validate-run`
postconditions 通过才到 `build_ready_for_iterate`。

### Worker Prompt Contract

每个 worker prompt 必须窄：

```text
You are executing node wf7_build_plan inside execution_supervisor.

Use Skill: $build-plan.
Segment: build.
auto_mode: true.

Do:
- perform only this node's work
- write only artifacts owned by the Skill
- report Gate Evidence
- emit a structured completion summary

Do not:
- ask the user directly
- approve contracts
- advance Stage
- write supervisor state
- edit .workflow_supervisor or .auto_iterate
```

worker 如果发现缺信息，应返回 typed interrupt request，而不是在 stdout 里直接问人。

### Worker Result Contract

Worker prompt 还不够；supervisor 需要机器可解析的 worker result。最小结果应包含：

```json
{
  "schema_version": 1,
  "run_id": "sup_...",
  "node_id": "wf7_build_plan",
  "skill": "build-plan",
  "status": "success|failed|interrupt_requested|not_run",
  "artifact_refs": [],
  "gate_ledger": [],
  "postcondition_claims": [],
  "interrupt_request": null,
  "worker_warnings": []
}
```

如果 worker 只输出 prose、直接问用户、修改 supervisor runtime、或在触发 gate 时没有
Gate ledger，supervisor 应 fail closed，而不是从自然语言里猜 completion。

实现层应把 stdout/stderr、exit code、observed writes、contract violations 和
postcondition result 都纳入 worker result 或 node record；否则 supervisor 无法可靠
地区分真实完成、partial side effect、missing gate 和 contract violation。

## Human-in-the-Loop Semantics

HITL 应该是 typed control primitive，而不是聊天习惯。

### Interrupt Types

| Type | Meaning | Example | Resume Behavior |
| --- | --- | --- | --- |
| `ASK_INPUT` | 必要事实缺失 | dataset path、training command、account credential status | 保存答案并 rerun/adopt node |
| `APPROVE_ACTION` | 敏感动作需要批准 | approve Evaluation Contract、run release packaging、submit package | 只执行 exact approved action |
| `STEER` | 需要人类 judgment | choose baseline subset、accept architecture tradeoff、pivot vs continue | 更新 node plan 或 route |
| `REVIEW_EDIT` | 人类需要审阅/编辑 artifact | edit Research Intent Draft、revise Review Packet notes | 重新验证修改后的 artifact |
| `ESCALATE` | supervisor 不能安全继续 | repeated gate failure、conflicting contracts | 停止直到 operator 决定 |

### Interrupt Payload Principles

Interrupt payload 必须是 typed、scoped、auditable。它至少要表达：

- request identity：request id、run id、segment、node。
- interrupt type：`ASK_INPUT`、`APPROVE_ACTION`、`STEER`、`REVIEW_EDIT` 或
  `ESCALATE`。
- reason and question：为什么现在必须停，以及人类要回答什么。
- allowed responses：可接受的回答集合或 answer schema。
- exact action：当请求是 approval 时，被批准的动作、命令、contract 或 claim text。
- evidence refs：Review Packet、Gate Evidence、raw artifact、diff 或 log 路径。
- risks：已知风险和不可逆副作用。
- resume cursor：回答后从哪里继续，以及采用 adopt / rerun / fail-closed 哪种策略。

具体 `pending_request.json` schema、answer command 和 approval command 放在实施计划
中维护，避免设计文档和实现文档各自维护一份字段定义。

### Approval Request Requirements

为了降低 approval fatigue 和 context manipulation，approval request 不能只展示
model summary。必须展示：

- exact action
- target files / commands / contracts
- raw artifact links
- diff 或 changed lines（如适用）
- Gate Evidence status
- known risks
- rollback / recovery plan（如适用）
- allowed responses
- timeout / escalation policy
- response 后的 approver identity 和 timestamp

避免：

- 一个 `approve all` 覆盖整个 workflow。
- 只显示模型总结，不显示原始 artifact。
- scope 不清。
- 隐藏 command parameters。
- 把 Review Packet 当成 approval。

### Approval Scope

Approval 只作用于 payload 里的 exact action。

```text
Approved:
  approve evaluation_contract using review_packet build_id=abc123

Not approved:
  future claim boundary changes
  release submission
  unrelated contract updates
  skipping future gates
```

### Human Answers Are Not Automatically Facts

operator 提供的信息需要分类：

| Input Kind | Meaning | Next Step |
| --- | --- | --- |
| operator preference | 显式偏好 | 通过 proper owner 更新 Operator Context |
| environment fact | 本地环境声明 | 用命令验证，或标记 unverified |
| dataset path | candidate path | 先检查路径存在和权限 |
| baseline/cache path | candidate execution input | 先检查目录存在、可写、空间和 ownership |
| training/eval command | candidate command | 先检查入口文件、config、依赖和 dry-run/smoke feasibility |
| compute/budget answer | execution constraint | 写入 readiness packet；supervisor 用于 timeout/budget preflight |
| approval | scoped Approval Evidence | 需要时用 approval tooling 记录 |
| research claim | candidate claim | 需要 Conclusion Evidence 才能写成 durable claim |

提前回答的问题如果未验证，状态应是 `candidate` 或 `unchecked`，不能被写成
`verified`。这条规则避免 supervisor 因为聊天中出现过路径或命令就跳过必要检查。

## Postconditions and Gates

supervisor 应遵循现有 WF10 controller 的原则：成功来自 repository artifacts、
commands 和 gates，而不是模型 prose。

### Postcondition Classes

| Class | Example |
| --- | --- |
| artifact existence | `docs/Baseline_Report.md` exists |
| schema validity | `PROJECT_STATE.json` validates |
| ownership compliance | worker did not edit `.auto_iterate/` |
| gate result | `check_dynamic_context.py` returned PASS |
| semantic completion | `iteration_log.json` entry has required fields |
| commit evidence | semantic commit exists for stable code changes |
| review evidence | Review Packet path recorded |

### Gate Result Principles

Gate result 不能是 prose summary。它必须至少记录：

- gate name；
- exact command、controller postcondition、CI job 或 approval tool；
- `PASS` / `FAIL` / `NOT_RUN`；
- 为什么这个 gate 对当前 node 或 segment 必要；
- 产生或读取的 artifact refs；
- checked timestamp。

如果 gate 没有实际运行，只能记录 `NOT_RUN` 和原因，不能把 Skill instruction、hook
提醒或模型自述当成 machine verification。

### Resume Strategy

| Strategy | Meaning | Example |
| --- | --- | --- |
| `adopt_if_postconditions_pass_else_rerun` | artifacts 满足 postconditions 就继续 | doc generation 完成后 crash |
| `rerun_idempotent` | rerun 安全，因为输出通过工具生成或确定性覆盖 | gate checks |
| `manual_recover` | side effects 可能 partial，需人类决定 | external run、package upload |
| `fail_closed` | 状态不清时停止 | contract approval、release submission |

## 与现有 Harness 组件的关系

### Skills

```text
Skill
  -> how to perform the local task

Supervisor
  -> when to run the Skill
  -> what context to pass
  -> how to validate result
  -> when to pause
```

### Skill Contracts

`schemas/skill_contracts.json` 继续作为以下内容的 source of truth：

- triggers
- required reads
- required actions
- forbidden actions
- gate ledger requirements
- sensitive paths
- write scopes
- artifact outputs

supervisor registry 额外声明：

- segment membership
- node order
- automation eligibility
- postconditions
- interrupt rules
- resume strategy
- timeout policy

### Existing Auto-Iterate

WF10 auto-iterate 应继续作为 specialized controller。Execution supervisor 调用它，
而不是重写 WF10。

```text
execution_supervisor segment=iterate
  -> validate auto_iterate_goal
  -> start tooling/auto_iterate/scripts/auto_iterate_ctl.sh
  -> monitor status --json
  -> stop on manual_action_required / PIVOT / ABORT / budget
```

### Orchestrator

当前 `$orchestrator` 仍是 Stage reasoning 和 transition owner。supervisor 可以准备
transition packet，但不能 silent stage advance。Stage transition 仍需 explicit Human
Approval。

## Post-Codebase Change Flow

codebase 已经通过 WF8/WF9 建立后，用户经常会提出新的需求：基于现有 codebase 的
新 idea、局部 code/config 修改、性能调优、bugfix、evaluation 变化、claim 变化。
这些请求不应默认回到完整 WF1-WF12，也不应直接让 agent 改代码。

建议新增 `change intake`：

```text
user new request
  -> change intake
  -> classify change type
  -> inspect current codebase / project_map / contracts as needed
  -> route to code-debug / iterate / build_delta / review-packet / delta grill
  -> validate and record Gate Evidence
```

### Change Classification

| Change Type | Example | Default Route | Human Stop Point |
| --- | --- | --- | --- |
| `bugfix` | 某脚本报错、config key 不生效 | `$code-debug` -> focused test / `$validate-run` | root cause 跨越 slice 或需要改 public interface |
| `experiment_delta` | 基于当前 hypothesis 改一个 config、loss weight、schedule | `$iterate plan/code/run/eval` | metric、baseline、contract 变化 |
| `stable_code_delta` | 在现有架构内增加一个 data transform 或 helper | `build_delta` -> `$code-debug` -> `$validate-run` | 改 stable interface、project_map、Codebase_Map |
| `architecture_delta` | 改核心模型结构、数据流、public API | `delta grill` -> `$refine-arch` / `$build-plan` | architecture tradeoff 或 claim boundary impact |
| `evaluation_delta` | 改 primary metric、baseline set、validation protocol | `$review-packet` / contract gate | Evaluation Contract approval |
| `claim_boundary_delta` | 新 claim 或 stronger claim | Claim Boundary review | Claim Boundary approval |
| `new_research_direction` | 在同一 codebase 上提出新 idea | `delta grill` or new branch intent | 是否作为新 research branch |
| `harness_guardrail_delta` | hooks、Skill Contracts、routing、permission policy | `$harness-maintenance` | guardrail tests / human review |

`$code-expert` 仍应主要用于 WF8 first-pass implementation。codebase 成熟后，普通
实现修改的默认入口是 `$code-debug`；实验变化默认入口是 `$iterate`；涉及 claim、
evaluation 或 architecture 的变化先做 delta intake。

### Delta Grill

`delta grill` 是 codebase 建成后的轻量 Grill。它不重新讨论所有研究背景，只围绕
新变化提问：

- 这个 change 想验证哪个 hypothesis？
- 它是 bugfix、experiment delta、stable code delta，还是 new research direction？
- 它是否改变 Evaluation Contract、Baseline Contract 或 Claim Boundary？
- 它是否改变 public interface、data flow、training command 或 config schema？
- 旧路径是否需要保留为 baseline 或 fallback？
- 成功/失败的判断命令是什么？
- 这个 change 的最小 Commit Slice 是什么？
- 如果改动失败，是 rollback、debug，还是 pivot？

### Change Request Artifact

建议为每次 post-codebase change 生成小型 artifact：

```markdown
# Change Request

## Request Summary

## Change Type

## Base State

- base_commit:
- current_stage:
- related_iteration:

## Intended Hypothesis or Fix

## Affected Contracts

## Affected Files / Configs

## Validation Command

## Human Decisions Needed

## Route

## Gate Evidence Plan
```

对应 machine-readable record 应保存 request id、change type、base state、route、
affected contracts、affected paths、validation plan 和 human stop points。具体
schema 和文件路径由实施计划维护。

### Routing Rule

默认从低风险路线开始：

```text
can be handled as bugfix?
  -> code-debug
else can be handled as experiment_delta?
  -> iterate
else does it change stable code but not architecture/claims?
  -> build_delta + code-debug
else does it change architecture/evaluation/claims?
  -> delta grill + review packet / contract gate
else is it a new research direction?
  -> new Research Intent Draft branch
```

当路由不确定时，supervisor 应 `fail_closed` 到 `STEER` interrupt，而不是猜测后直接
改代码。

Change intake classifier 必须输出 machine-readable record，包括 change type、route、
confidence、uncertainty reasons、affected contracts、affected paths、validation plan
和 Gate Evidence plan。`confidence=low` 或 contract/claim/evaluation impact 不清时，
只能生成 `STEER` interrupt。

## 可复用的外部模式和代码

### LangGraph Interrupt + Checkpointer

核心模式：

```text
node calls interrupt(payload)
  -> runtime persists graph state
  -> caller receives payload
  -> human responds
  -> graph resumes with Command(resume=response)
```

对 Harness 的启发：

- `run_id` 类似 LangGraph `thread_id`，是 durable cursor。
- `.workflow_supervisor/state.json` 可作为轻量 checkpoint。
- 如果 run 跨多用户、多机器或长时间等待，可换成 SQLite/PostgreSQL。

参考：

- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)

### OpenAI Agents SDK HITL

核心模式：

```text
tool declares needs_approval
  -> run returns interruptions
  -> app serializes RunState
  -> human approves/rejects
  -> app resumes original run
```

对 Harness 的启发：

- contract approval、release submission、shell actions、patch actions 可建模为
  approval-requiring tools。
- nested Skill worker 发现 approval need 后，approval 应冒泡到 outer supervisor
  run。
- approval 应按 per-action scope，而不是批准整个 workflow。

参考：

- [OpenAI Agents SDK HITL](https://openai.github.io/openai-agents-python/human_in_the_loop/)
- [OpenAI Agents SDK handoffs](https://openai.github.io/openai-agents-python/handoffs/)
- [OpenAI Agents SDK guardrails](https://openai.github.io/openai-agents-python/guardrails/)
- [openai/openai-agents-python](https://github.com/openai/openai-agents-python)

### HumanLayer 12-Factor Agents

相关原则：

- own your context window
- tools are just structured outputs
- unify execution state and business state
- launch/pause/resume with simple APIs
- contact humans with tool calls
- own your control flow
- small, focused agents
- stateless reducer

对 Harness 的启发：

- human contact 应是 `pending_request.json`，不是临时聊天。
- control flow 应在 supervisor code，而不是模型自由 loop。
- Skill workers 应小而明确。
- runtime state 应可序列化、可审计、可恢复。

参考：

- [humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents)

### awaithumans

核心模式：

```text
await_human(task, typed_payload, typed_response_schema)
  -> notify via Slack/email/dashboard
  -> wait durably
  -> resume with typed answer
```

可复用点：

- typed request/response shape。
- Slack/email/dashboard 多渠道 reviewer workflow。
- deterministic idempotency key。
- AI verifier 可用于检查 careless approval，但 verifier 不能替代 Human Approval。
- Temporal/LangGraph adapters 提供 durable wait 思路。

参考：

- [awaithumans](https://github.com/awaithumans/awaithumans)
- [awaithumans LangGraph example](https://github.com/awaithumans/awaithumans/tree/main/examples/langgraph-py)

### IRAS

IRAS 的 incident-response state machine：

```text
Alert -> Triage -> Context -> RCA -> Plan -> Human Approval -> Apply -> Post-mortem
```

可复用点：

- typed Pydantic outputs。
- LangGraph state machine。
- PostgreSQL checkpoints。
- Slack/API approval。
- confidence gates。
- rollback commands。
- adversarial tests。

参考：

- [IRAS](https://github.com/krishnashakula/IRAS)

### Temporal / Restate / DBOS / Dapr

这些是更重的 durable execution 平台，适合：

- 多小时或多天的人类等待。
- distributed workers。
- cross-machine crash recovery。
- audit-grade workflow history。
- task queues 和 signals。

Harness 本地研究 workspace 的第一版不一定需要这些平台，但 supervisor 的模型应保持
兼容：

```text
workflow id
  -> activities
  -> signals
  -> durable state
  -> replay-safe decisions
```

参考：

- [OpenAI Agents SDK durable integrations](https://openai.github.io/openai-agents-python/running_agents/)
- [Thoughtworks Technology Radar, April 2026](https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2026/04/tr_technology_radar_vol_34_en.pdf)

## Detailed Segment Flow

### Segment A: Grill

```text
start grill
  -> load current idea notes if present
  -> ask hard questions
  -> update Research Intent Draft
  -> critique draft
  -> repeat until human exits
  -> produce segment boundary packet
```

Minimum outputs:

- Research Intent Draft
- Execution Readiness Packet when the operator has preanswered execution inputs
- Grill Round Log
- unresolved open questions
- operator exit decision

Stop reasons:

- operator wants another round
- operator pivots
- operator abandons
- operator accepts intent and continues

### Segment B: Prepare

```text
Research Intent Draft accepted
  -> readiness preflight
  -> data-prep
  -> baseline-repro
  -> protocol-compiler
  -> review-packet
  -> contract approval gate
  -> prepare complete
```

可自动继续的条件：

- dataset facts 已知且可验证。
- preanswered dataset/cache/command/budget inputs 已通过 readiness preflight。
- baselines 已指定或 ambiguity 已解决。
- required docs 已产生。
- gates PASS，或明确 `NOT_RUN` 且有 reason。

必须暂停：

- dataset path missing。
- preanswered path/command 验证失败或与 current facts 冲突。
- baseline set ambiguous。
- dynamic-context gate fails。
- Evaluation Contract approval required。
- protocol drift needs review。

### Segment C: Build

```text
prepare complete
  -> refine-arch
  -> optional deep-check
  -> build-plan
  -> code-expert / code-debug
  -> validate-run
  -> WF10 readiness packet
```

可自动继续的条件：

- architecture 在 accepted intent 和 contracts 内。
- implementation 遵守 roadmap 和 Commit Slice boundaries。
- tests / validation commands 执行，或明确 `NOT_RUN`。
- 没有 high-risk interface 或 Claim Boundary 变化。

必须暂停：

- architecture choice 改变 claim boundary。
- plan 暴露新的 research assumption。
- implementation scope 扩大。
- validation fails。
- required test environment missing。

### Segment D: Iterate

```text
WF10 readiness accepted
  -> auto-iterate-goal check/init/refresh
  -> auto_iterate start
  -> monitor status --json
  -> stop on controller halt reason
```

复用现有 controller：

- `tooling/auto_iterate/scripts/auto_iterate_ctl.sh start`
- `status --json`
- `tail --jsonl`
- `pause`
- `resume`
- `override`

必须暂停：

- controller emits `manual_action_required`。
- decision is `PIVOT` or `ABORT`。
- goal update changes metric name/direction。
- budget exhausted。
- preflight fails。

### Segment E: Release

```text
iteration decision CONTINUE
  -> final-exp
  -> context/docchain gates
  -> Claim Boundary check
  -> release packet
  -> explicit human release/submission approval
```

这一段应保守，因为最终 claim 和 release package 风险最高。

必须暂停：

- Project Contract、Evaluation Contract 或 Claim Boundary missing。
- final experiment design 超出 approved boundary。
- release claims unsupported。
- submission/package overwrite requested。
- operator 没有 explicit release/submission request。

### Segment F: Change Intake

```text
mature codebase or post-WF8 project
  -> user submits new request
  -> classify change type
  -> optional delta grill
  -> route to code-debug / iterate / build_delta / review-packet
  -> validate and record Gate Evidence
```

可自动继续的条件：

- change type 明确且低风险。
- 不改变 Approved Contracts、Claim Boundary、primary metric 或 public interface。
- affected files 在当前 project_map / Codebase_Map 边界内。
- validation command 明确，或 `NOT_RUN` reason 可接受。

必须暂停：

- request 可能是 new research direction。
- request 会改变 Evaluation Contract、Baseline Contract 或 Claim Boundary。
- request 需要 architecture tradeoff。
- request 会改变 dataset assumptions、metric、baseline set 或 release claim。
- route 不确定，或 postcondition 无法定义。

## Approval UX Requirements

每个 approval request 应展示：

```text
Action:
  exact command/tool/action to approve

Scope:
  files, contracts, paths, systems, or claim text affected

Why now:
  what gate or node requires this decision

Evidence:
  direct artifact paths and gate results

Risks:
  known failure modes and irreversible effects

Alternatives:
  approve / revise / reject / pause / abort

After approval:
  exact next node and resume behavior
```

不应出现：

- final-only approve button。
- 没有 raw evidence 的 polished summary。
- scope 模糊的批准。
- action parameters 被隐藏。
- approval 后 agent 可改变 action 内容。

## Implementation Handoff

设计上，最小可行路径是：

```text
Grill mode
  -> readiness preflight
  -> prepare supervisor over low-risk nodes
  -> typed HITL interrupt / resume
  -> change intake
  -> build / iterate / release expansion
```

这个顺序是设计约束，不是文件级实施清单：先证明人类问题收集、候选输入验证、
Gate Evidence、Review Packet 和可恢复暂停，再扩大到代码生成和 release 自动化。

具体 Harness Research 改造，包括新增 schema、runtime namespace、CLI shape、hook
规则、测试文件和 rollout slice，见
`docs/grill_execution_supervisor_implementation_plan.md`。

## Failure Modes and Controls

| Failure Mode | Risk | Control |
| --- | --- | --- |
| approval fatigue | operator 机械批准 | 减少 approval 次数；payload 展示 raw evidence；设置 timeout/escalation；追踪异常 approval rate |
| context manipulation | model summary 隐藏风险 | 展示 raw artifacts、diffs、commands、gate outputs |
| approval bypass | worker 在暂停前执行敏感动作 | deterministic pre-action policy 和 tool-level guardrails |
| stale context | facts changed 后继续执行 | pre-node freshness checks 和 protocol drift checks |
| stale preanswered input | Grill 阶段给出的路径/命令已失效 | readiness preflight 验证 path、permission、command、contract consistency |
| partial side effects | external command 后 crash | idempotency keys、rollback metadata、manual recovery state |
| model self-certification | model 自称成功 | postconditions 基于 files、commands、gates |
| multi-agent confusion | specialists 共享过多 context | small worker prompts 和 filtered inputs |
| state corruption | 并发 runs 写同一 runtime state | lock、heartbeat、run IDs、atomic writes |
| over-automation | 早期研究判断被跳过 | WF1-WF3 保持 Grill mode，并要求 exit decision |
| wrong delta route | post-codebase 新需求被误当成普通 bugfix | change intake classification、delta grill、contract impact check |

## Validation Principles

这套机制是否成立，不看模型是否把流程说圆，而看四类行为是否被证明：

- discussion quality：Grill 是否提出少量高价值问题，并让 operator 更清楚地表达
  hypothesis、claim boundary、failure criteria 和 readiness inputs。
- durable execution：supervisor 是否能在 node、gate、human interrupt、crash 和 resume
  之间保持一致状态。
- evidence discipline：current docs、contracts、review packets、Gate Evidence 和
  Approval Evidence 是否仍由正确 owner 和 tooling 产生。
- bounded automation：低风险 node 是否减少手工调用，高风险 action 是否仍 scoped
  pause，并展示 raw evidence、exact action 和后续 resume behavior。

具体测试文件、fixture、validation commands 和 rollout acceptance criteria 由
`docs/grill_execution_supervisor_implementation_plan.md` 维护。

## Reference Links

### Official and Primary Documentation

- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
- [OpenAI Agents SDK HITL](https://openai.github.io/openai-agents-python/human_in_the_loop/)
- [OpenAI Agents SDK running agents](https://openai.github.io/openai-agents-python/running_agents/)
- [OpenAI Agents SDK handoffs](https://openai.github.io/openai-agents-python/handoffs/)
- [OpenAI Agents SDK guardrails](https://openai.github.io/openai-agents-python/guardrails/)
- [OpenAI practical guide to building agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)
- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [NIST AI Agent Standards Initiative](https://www.nist.gov/news-events/news/2026/02/announcing-ai-agent-standards-initiative-interoperable-and-secure)

### Reusable Code and Implementation References

- [openai/openai-agents-python](https://github.com/openai/openai-agents-python)
- [humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents)
- [awaithumans](https://github.com/awaithumans/awaithumans)
- [awaithumans LangGraph example](https://github.com/awaithumans/awaithumans/tree/main/examples/langgraph-py)
- [IRAS incident-response agent](https://github.com/krishnashakula/IRAS)

### 2026 Reports and Research

- [Thoughtworks Technology Radar, April 2026](https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2026/04/tr_technology_radar_vol_34_en.pdf)
- [CSA Agentic Universe, April 2026](https://labs.cloudsecurityalliance.org/wp-content/uploads/2026/04/agentic-universe-april-2026-v1.pdf)
- [Guardrails Beat Guidance, arXiv 2604.11088](https://arxiv.org/abs/2604.11088)
- [TSAssistant, arXiv 2604.23938](https://arxiv.org/abs/2604.23938)

## Final Position

`grill + execution supervisor` 适合 Harness，因为它把两个不同问题拆开：

```text
research judgment problem
  -> Grill mode
  -> repeated human challenge and clarification

workflow friction problem
  -> Execution Supervisor
  -> durable state, postconditions, gates, typed HITL interrupts
```

这套设计应从小 slice 开始，复用现有 WF10 controller 的可靠部分，并把关键安全性
放在 deterministic guardrails、postconditions、Gate Evidence 和 scoped Human
Approval 上，而不是依赖更长的 instruction files 或更多自由协作 agent。
