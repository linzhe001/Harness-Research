# AI Coding 软件工程方法与 Harness Workflow 融合指南

## 目的

这份文档把 `coding_jpg/` 中那组 AI Coding 方法截图整理成可执行的软件工程指南，并补充稳定的软件工程资料，说明怎样把这些方法融入 Harness Research 的 WF0-WF12 工作流。

核心判断：

- AI 可以显著提高代码生成速度，但它也会放大系统复杂度、命名漂移、模块边界不清和反馈不足。
- AI Coding 的专业化重点不是“写更多 prompt”，而是用软件工程基本功约束 AI 的输出。
- 开发者的价值会更集中在：统一语言、定义边界、拆分垂直切片、设计测试、缩短反馈回路、控制系统熵增。

外部参考用于细化实践，不替代当前仓库的 Harness 规则。Harness 术语以 `.agents/references/ubiquitous-language.md` 为准。

## 通用语言和统一系统语言是不是同一个东西

结论：它们高度相关，但不是完全同一个层级。

`通用语言`通常对应 DDD 里的 `Ubiquitous Language`：业务专家、开发者、文档、测试和代码共同使用的一套语言。它不是普通词汇表，而是领域模型的一部分。DDD Reference 强调团队要在对话、图、文档和代码中持续使用同一套模型语言。

`统一系统语言`更像一个操作目标：让一个项目在需求、代码、数据库、API、测试、prompt、文档里尽量使用一致的概念和命名。它可以看作在 AI Coding 场景里对 `Ubiquitous Language` 的工程化落地。

需要注意边界：

- 如果只是一个产品或一个 bounded context，二者可以合并为同一个 `Project_Glossary.md`。
- 如果系统里有多个 bounded context，不应该强行让全公司或全系统只用一套词。不同上下文可以有不同语言，但上下文之间的翻译关系必须显式记录。
- 在 Harness 里还要区分两层语言：Workflow Skill Language 是 Harness 工作流术语，例如 `Stage`、`Skill`、`Gate Evidence`；Application Codebase Language 是目标项目自己的领域词和代码词。前者放在共享 reference，后者必须落在具体 stage 的项目 artifact 中。

推荐说法：

- 对 DDD 或业务建模：使用 `通用语言 / Ubiquitous Language`。
- 对 AI Coding 操作规范：使用 `统一系统语言`，并说明它是通用语言在代码、测试、prompt、文档中的落地。

### 当前代码库怎么实现

当前 Harness 代码库把两层语言分开实现：

| 实现点 | 作用 |
| --- | --- |
| `.agents/references/ubiquitous-language.md` | Codex 侧只定义 Workflow Skill Language 和 Evidence 命名规则。 |
| `.claude/shared/ubiquitous-language.md` | Claude 侧的对应 workflow 术语规则，用来保持 `.agents/` 和 `.claude/` 语义对齐。 |
| `.agents/skills/refine-arch/SKILL.md` / `.claude/skills/refine-arch/SKILL.md` | WF6 生成或刷新 `docs/20_facts/Project_Glossary.md` 的初始 codebase 词汇种子。 |
| `.agents/skills/build-plan/SKILL.md` / `.claude/skills/build-plan/SKILL.md` | WF7 根据稳定 file tree、接口、配置、metric、测试和错误名完善 `Project_Glossary.md` 和 `docs/20_facts/Codebase_Map.md`。 |
| `README.md` / `CLAUDE.md` | 明确 workflow 术语跟随 ubiquitous-language 规则；目标研究工作区的项目词汇由 WF6/WF7 维护。 |
| `.agents/skills/init-project/references/claude-md-template.md` | 在生成的项目指导里加入 `Global Rule: Ubiquitous Language`，只要求使用 Harness workflow 术语，并指向 WF6/WF7 的 glossary 职责。 |
| `tooling/.tests/test_codex_hooks_contracts.py` | 检查 `harness-maintenance` Contract 覆盖 `.agents/references/ubiquitous-language.md`，保证修改 workflow 术语时必须读这份规则。 |

也就是说，当前代码库有两层语言模型，但不把它们写在同一份共享 reference 里：

```text
Workflow Skill Language
  -> Harness 自己的 Stage / Skill / Contract / Gate / Evidence / Claim 等词

Application Codebase Language
  -> 目标研究项目自己的 Domain Term / Code Term / Dataset / Metric / Run 等词
```

仍然没有的部分：

- 没有自动生成 `Project_Glossary.md` 的专用工具。
- 没有强制检查代码 identifier 是否全部来自 glossary 的 lint。
- 对目标项目 glossary 的执行主要依赖 WF6/WF7 的 stage instruction、skill 读集、文档模板和人工/agent review。

因此本文件建议的“统一系统语言”应理解为：把 `Project_Glossary.md` 作为目标项目的稳定 Source Artifact，由 WF6 生成初稿、WF7 完善为实现语言，并在 WF8/WF9/WF10 中读取和审查。稳定代码库结构则由 `project_map.json` 提供机器可读索引，并由 `docs/20_facts/Codebase_Map.md` 提供 operator 可读说明；WF7 生成或刷新，WF8/WF9 之后只要稳定文件、接口、入口或依赖方向变化就同步。

## 一条专业化 AI Coding 回路

```text
Explore Grill checkpoints
  -> 通用语言 / 统一系统语言
  -> 垂直切片
  -> TDD
  -> 深模块和模块边界
  -> 快速反馈
  -> 复杂度和熵增控制
  -> Harness Gate Evidence / iteration_log
```

这里的 `Grill Me` 不是每个 Stage 都要重复执行的仪式，而是集中放在 Explore 相关的少数关键点，用来把用户意图和研究问题问透。后续 Contract、Build、Iterate 阶段主要消费这些回答，只在边界不清或发现重大冲突时做轻量补问。

这个顺序背后的原因：

1. 先在 Explore 前后让 AI 盘问用户目的、idea 内容、关键假设和取舍，暴露隐含意图。
2. 再统一概念和命名，减少人和 AI 的误解。
3. 用垂直切片缩小改动范围。
4. 用 TDD 给 AI 加限速器和方向盘。
5. 用深模块和模块边界封装复杂度。
6. 用反馈回路快速发现偏差。
7. 用 Harness 的 Gate Evidence 和 workflow state 记录“做了什么、验证了什么、还有什么没验证”。

## 方法 1：Grill Me

### 它是什么

`Grill Me` 是一种反向盘问方法：不要让 AI 只根据用户第一段 idea 直接下结论，而是让 AI 围绕用户目的、idea 内容、边界、取舍、风险、成功标准和未决问题连续追问。它解决的是“我以为我说清楚了，AI 以为它听懂了，但双方其实不是同一个理解”的问题。

在 Harness 里，`Grill Me` 最适合放在 `Explore` 相关阶段，而不是到处出现。它的主要目标不是替代后续 survey、debate、contract 或 build，而是把人类真实意图问清楚，为后面的 Contract 和 Build 提供依据。

### 建议集中出现的阶段

建议只设置三个 Grill 点，其中前两个是主要点，第三个是保护性补问：

| Grill 点 | 所属 operator 阶段 | 内部 WF | 目的 | 产出 |
| --- | --- | --- | --- | --- |
| Explore Intake Grill | `Explore` 开始 | WF1 survey-idea 开始 | 在联网 survey 前问清用户目的、idea 原始动机、目标场景、限制、偏好和不想做的方向。 | `Feasibility_Report.md` 的 idea overview、search keywords、open questions、risk seeds。 |
| Explore Synthesis Grill | `Explore` 后半段或结束前 | WF1 证据收集后，必要时延续到 WF2/WF3/WF4 | 根据 Explore 得到的论文、竞品、数据和失败案例，反问用户关键取舍，确认哪些问题会影响 contract、baseline、metric、claim boundary 和 build scope。 | `Idea_Debate.md`、`Refined_Idea.md`、`Open_Questions.md`、draft protocol assumptions。 |
| Contract Handoff Grill | `Contract` 开始前的窄门 | WF5/WF6/WF7 前，只在关键意图仍不清时使用 | 只追问会影响 Evaluation Contract、Baseline Contract、Claim Boundary、架构边界或垂直切片优先级的问题。 | contract review inputs、WF6 architecture inputs、WF7 roadmap constraints。 |

不建议在 WF8 code、WF9 validate、WF10 每轮 iterate 都做完整 Grill。Build 和 Iterate 阶段应该主要执行已确认的切片、测试和 Gate；如果出现重大漂移，再回到 Explore Synthesis 或 Contract Handoff 做一次集中补问。

### 专业化做法

让 AI 按阶段和类别提问，而不是随机追问。

Explore Intake Grill 的问题应尽量细，重点问用户自己的意图：

| 类别 | 要问清楚什么 |
| --- | --- |
| 用户目的 | 为什么想做这个 idea；最终希望得到 paper、demo、产品能力、benchmark 结果还是学习验证。 |
| 原始动机 | 这个 idea 来自哪篇论文、哪次失败、哪个产品痛点、哪个直觉或哪个已有项目缺口。 |
| 目标对象 | 面向哪类任务、数据、用户、模型、系统或评测场景。 |
| 成功形态 | 什么结果会让用户觉得值得继续；什么结果说明该 pivot 或 abort。 |
| 非目标 | 明确这次不做什么，避免 survey 和 build 被 AI 扩大范围。 |
| 资源约束 | 时间、算力、数据、代码基础、可接受工程量。 |
| 个人偏好 | 用户偏向保守复现、快速原型、论文创新、工程稳定性，还是探索性试错。 |
| 已知担忧 | 用户最担心的失败点、竞争方法、实现难点、数据风险。 |

Explore Synthesis Grill 要基于已经收集的 Conclusion Evidence 再问第二轮：

| 类别 | 要问清楚什么 |
| --- | --- |
| 证据冲突 | survey 发现的竞品、失败案例或数据限制是否改变用户意图。 |
| 取舍排序 | novelty、feasibility、impact、compute、time-to-demo 哪个优先。 |
| Baseline 选择 | 哪些 baseline 必须复现，哪些可记录为 deferred。 |
| Metric 选择 | 哪些 metric 真正代表成功，哪些只是辅助观察。 |
| Contract 边界 | 哪些 claim 可以承诺，哪些只能作为 exploratory observation。 |
| Build 边界 | 第一条垂直切片应该验证哪个最小假设。 |
| Pivot 条件 | 哪些负结果会触发 `PIVOT`、`ABORT` 或重新 survey。 |

一个可复用 prompt：

```text
我们在 Explore 阶段，请先 Grill Me。
不要急着给结论，也不要设计架构。
请围绕我的目的、idea 原始动机、目标任务、成功形态、非目标、资源约束、已知担忧和想避开的方向逐项追问。
一次最多问 10 个问题。问完第一轮后，先总结你理解的意图，再列出仍会影响 survey / contract / build 的 open questions。
```

Explore Synthesis Grill 的 prompt：

```text
基于刚才 Explore 得到的论文、竞品、数据、baseline、metric 和失败案例，请再次 Grill Me。
这次只问会影响 Contract 或 Build 的关键问题：
Evaluation Contract、Baseline Contract、Claim Boundary、第一条垂直切片、pivot/abort 条件、资源上限。
每个问题都说明它会影响哪个后续 artifact。
```

### 完成标准

- 能写出一句清楚的目标句。
- 能列出非目标。
- 能说明用户为什么想做这个 idea，而不只是复述 idea 表面内容。
- 能把用户意图映射到 survey keywords、competitor search、baseline 候选和 metric 候选。
- 能列出会影响 Contract 或 Build 的关键 open questions。
- 能定义第一条最小可验证垂直切片的目标。
- 仍然不清楚的问题被记录为 open questions，而不是假装已经解决。

### 和 Harness workflow 的融合

| Workflow 点位 | 融合方式 |
| --- | --- |
| WF1 survey-idea | 主要 Grill 点。先问用户目的和 idea 细节，再做 web research；survey 后基于证据做第二轮关键追问。 |
| WF2 idea-debate | 不做完整 Grill；使用 WF1 的 Grill 结果来构造 candidate variants、failure modes 和 strongest objections。 |
| WF3 refine-idea | 把 Grill 结果固化成 problem statement、success criteria、kill criteria、pivot triggers 和 open questions。 |
| WF4 data-prep | 只补问数据路径、可用性、split、label、metric 这类阻塞问题。 |
| WF5-WF7 Contract/Arch/Plan | 只在 contract 或 build 边界仍不清时做 Contract Handoff Grill；不要重新展开成大范围 idea 讨论。 |
| WF8-WF10 | 默认不做完整 Grill；如果实现或实验暴露根本性意图漂移，回到 Explore/Contract 的对应询问点。 |

注意：Grill Me 可以产出问题和计划，但它不是 Gate Evidence。真正的 Gate Evidence 来自命令、测试、审查、指标、日志或明确的人类批准记录。

## 方法 2：通用语言 / 统一系统语言

### 它是什么

通用语言是项目共同使用的领域语言。它要求业务、研究、产品、代码、测试、数据库、API 和 prompt 使用同一套核心概念。

AI Coding 里它更重要，因为 AI 会从上下文里学习命名。如果同一个东西在需求里叫“订单”，在客服文档里叫“单子”，在代码里叫 `Order`，在数据库里叫 `trade_record`，在 prompt 里又叫“交易”，AI 会倾向继续扩散混乱。

### 它解决什么问题

- 同一概念多套命名。
- 同名不同义。
- prompt、代码、测试、文档互相翻译。
- AI 新增文件时不知道沿用哪个词。
- 后续维护者读代码时要重新建立脑内词典。

### 专业化做法

在目标项目中维护一个稳定词汇文件，推荐路径：

```text
docs/20_facts/Project_Glossary.md
```

建议结构：

```markdown
# Project Glossary

## Canonical Terms

| Domain Term | Code Term | Definition | Do Not Use | Source Artifact |
| --- | --- | --- | --- | --- |
| Order | `Order` | 用户确认购买后形成的业务对象。 | deal, trade, ticket | docs/... |

## Naming Rules

- 业务实体使用名词。
- 命令和脚本使用动词。
- 指标名包含方向或单位，例如 `latency_ms`。

## Bounded Contexts

| Context | Owns | Terms | Translation Boundary |
| --- | --- | --- | --- |
| Checkout | 创建和支付订单 | Order, Payment | 与 Fulfillment 通过 `FulfillmentRequest` 交互 |
```

### AI 使用规则

每次让 AI 做稳定实现前，要求它先读 glossary，并遵守：

- 新 identifier 必须来自 glossary 或明确提出新增词。
- 不允许随意引入同义词。
- 如果业务语言和代码语言冲突，先提出冲突，不直接实现。
- 测试名、错误消息、API 字段、配置项也要跟 glossary 对齐。

### 和 Harness workflow 的融合

| Workflow 点位 | 融合方式 |
| --- | --- |
| WF0 init | 初始化项目指导时声明 glossary 路径和语言政策。 |
| WF1 survey | 从 Source Artifact 中抽取候选领域词。 |
| WF2 idea-debate | 发现不同方案对同一概念的不同叫法。 |
| WF3 refine-idea | 固化首版核心词汇和非目标词。 |
| WF4 data | 记录 Dataset、Split、Sample、Label、Metric 的定义。 |
| WF5 baseline | 统一 Baseline、Metric、Run、Checkpoint 等实验词。 |
| WF6 arch | 用词汇边界辅助模块边界和 bounded context。 |
| WF7 plan | roadmap 中每个任务引用一致的 Domain Term 和 Code Term。 |
| WF8 code | 代码生成前读取 glossary；新增词必须说明理由。 |
| WF9 validate | 检查测试、报告、错误输出是否使用统一语言。 |
| WF10 iterate | 从 Observation 中提炼 Lesson 时使用稳定词。 |
| WF12 release | release Claim 必须使用已经定义的词，避免扩大含义。 |

## 方法 3：垂直切片

### 它是什么

垂直切片是从一个具体用户场景切入，打通端到端链路。它不是先铺满前端、后端、数据库、接口骨架，再慢慢填；而是先完成一条可运行、可验证、可演示的小链路。

例子：

```text
用户创建一个任务，并能在任务列表看到它。

切片范围：
UI button -> API request -> validation -> persistence -> list query -> UI render
```

### 它解决什么问题

AI 很容易横向铺架构：一次生成几十个文件，看起来完整，但没有任何路径真正跑通。垂直切片把每次改动限制在一个业务结果里，降低理解和验证成本。

### 专业化做法

一个好的切片需要满足：

- 有明确用户场景。
- 有可观察结果。
- 覆盖真实的数据流或控制流。
- 代码量小到人能 review。
- 出问题时改动范围有限。
- 可以被测试或手动 demo 验证。

切片计划模板：

```markdown
## Slice: <name>

User outcome:
- ...

Path:
- UI / CLI entry:
- Application service:
- Domain behavior:
- Persistence / artifact:
- Output / metric:

Acceptance:
- ...

Tests:
- ...

Out of scope:
- ...
```

### 反模式

- “先生成完整架构，后面再补细节。”
- “先把所有数据库表建好。”
- “先把所有 API skeleton 写出来。”
- “这个功能太简单，不需要切片。”
- “一次改完，测试最后再补。”

### 和 Harness workflow 的融合

| Workflow 点位 | 融合方式 |
| --- | --- |
| WF6 arch | 架构文档不只描述层，还要描述第一条端到端路径。 |
| WF7 plan | `Implementation_Roadmap.md` 按垂直切片排序。 |
| WF8 code | 每次实现只领取一个切片，不让 AI 同时铺开多个方向。 |
| WF9 validate | 验证切片是否真的跑通，而不是只检查文件存在。 |
| WF10 iterate | 每轮选择一个最小实验切片或 debug 切片。 |

### 每条实现路径如何落成可溯源文档

垂直切片不能只停留在口头计划里。每条实现路径应当从 WF6 到 WF10 留下可追踪记录：

```text
WF6 Technical_Spec.md
  -> 说明为什么需要这条路径、它服务哪个假设、依赖哪些 Source Artifact

WF7 Implementation_Roadmap.md
  -> 把路径拆成 slice_id、文件、接口、测试、验收命令和依赖顺序

project_map.json
  -> 记录稳定文件、责任、接口和后续维护入口

docs/20_facts/Codebase_Map.md
  -> 用 operator 可读语言说明当前代码结构、入口、public interfaces 和维护 owner

WF8 code / code-debug
  -> 实现对应 slice，Gate ledger 记录命令、结果、原因、artifacts

WF9 Validate_Run_Report.md
  -> 记录 evidence sources、review trace、smoke commands、smoke results 和 verdict

WF10 iteration_log.json / docs/40_iterations/** (legacy mirror: docs/iterations/**)
  -> 如果该 slice 进入实验循环，记录 run、Observation、Lesson 和 Decision
```

推荐在 `docs/Implementation_Roadmap.md` 给每条切片加一个 trace block：

```markdown
### Slice Trace: {slice_id}

- User / research outcome:
- Source Artifact:
- Conclusion Evidence:
- Design anchor: `docs/Technical_Spec.md#...`
- Planned files:
- Public interfaces:
- Test / smoke command:
- Gate Evidence target:
- Downstream validation doc:
```

当前代码库已经有可追溯文档机制，但覆盖面要分清：

- `docs/Technical_Spec.md` 和 `docs/Implementation_Roadmap.md` 模板都有 `evidence_sources`，能记录设计和计划的来源。
- `project_map.json` 是机器可读的稳定代码库索引；`docs/20_facts/Codebase_Map.md` 是实施计划落地后给 operator 看的当前代码库说明，两者需要在同一个稳定代码改动切片里保持一致。
- `docs/Validate_Run_Report.md` 模板记录 semantic review、review trace、smoke commands、smoke results 和 verdict。
- `tooling/evidence/compile_doc.py` 可以为当前 contract/fact/protocol 文档生成 `.evidence/chains/**` 下的 Evidence Chain。
- `tooling/evidence/check_docchain_gates.py` 默认检查 `docs/10_contract/**`、`docs/20_facts/**`、`docs/35_protocol/**`。它不是对所有 flat docs 自动生效。

因此，普通实现切片的主追踪链是 `Technical_Spec.md -> Implementation_Roadmap.md -> project_map.json / Codebase_Map.md -> Validate_Run_Report.md -> iteration_log.json/docs/40_iterations/**`，只有兼容旧报告路径时才镜像 `docs/iterations/**`。如果切片改变了 Current Facts、Protocol Draft、Approved Contract 或 Claim Boundary，再用 docchain 工具为对应 current docs 生成 Evidence Chain；不要手动编辑 `.evidence/**`。

## 方法 4：TDD 测试驱动开发

### 它是什么

TDD 的经典节奏是：

```text
Red -> Green -> Refactor
```

先写一个失败测试描述期望行为，再写最小实现让测试通过，最后在测试保护下重构。

AI Coding 中，TDD 的角色更像限速器和方向盘。AI 不缺速度，缺的是约束。测试把“我要什么”变成可执行边界，让 AI 小步前进。

### 它解决什么问题

- AI 一口气写太多代码。
- 错误扩散到很多文件后才发现。
- prompt 描述不精确。
- 回归行为没人守住。
- 人类 review 只能读代码，缺少行为锚点。

### 专业化做法

按层次选择测试：

| 测试类型 | 适用场景 | AI Coding 用法 |
| --- | --- | --- |
| 单元测试 | 纯函数、规则、解析、转换、边界条件 | 先固定小行为，减少误解。 |
| 集成测试 | API、数据库、文件、外部服务边界 | 验证切片真实链路。 |
| Golden test | 结构化输出、报告、序列化结果 | 防止输出格式漂移。 |
| Smoke test | 训练、推理、CLI、web app 启动 | 验证基本可运行。 |
| Contract test | 模块或服务之间的接口 | 固定模块边界。 |

AI 协作 prompt：

```text
先不要实现。
根据这个垂直切片写最小测试清单。
然后先写一个失败测试。
实现只允许覆盖这个测试需要的最小行为。
通过后再建议是否需要重构或补第二个测试。
```

### 完成标准

- 至少有一个测试在实现前能表达期望行为。
- 测试失败原因和目标行为匹配。
- 实现通过测试。
- 重构后测试仍通过。
- 如果无法自动化验证，必须记录手动验证步骤和 `NOT_RUN` 原因。

### 和 Harness workflow 的融合

| Workflow 点位 | 融合方式 |
| --- | --- |
| WF5 baseline | 为基线复现建立 smoke test 和 metric check。 |
| WF7 plan | 每个切片写清测试入口和验收命令。 |
| WF8 code | 用 Red-Green-Refactor 约束 AI 实现。 |
| WF9 validate | 把测试结果作为 Gate Evidence。 |
| WF10 iterate | 每轮实验的改动必须有对应测试、smoke 或 run command。 |
| WF11 final-exp | 最终实验前锁定评估脚本和指标测试。 |

## 方法 5：深模块和浅模块

### 它是什么

深模块的核心是：对外接口简单，内部封装足够多的复杂度。浅模块则相反：看起来拆了很多函数，但调用方仍然需要知道大量内部步骤。

例子：

```text
深模块：
sendEmail(to, subject, body)

内部隐藏：
- 建立连接
- 认证
- 组装 headers
- retry
- timeout
- 关闭资源
- 错误分类
```

浅模块反例：

```text
connectMailServer()
authenticateMailServer()
buildHeaders()
buildBody()
sendRawPayload()
retrySend()
closeConnection()
```

如果调用方必须按顺序调用一堆细节函数，模块没有真正降低复杂度。

### 它解决什么问题

- AI 把内部步骤全部暴露成 public function。
- 看起来符合 DRY，实际上把复杂度转移给调用方。
- 每个模块接口都不同，调用关系越来越绕。
- 人类必须把整张调用图装进脑子里才能改代码。

### 专业化做法

设计模块时先回答：

- 这个模块对外承诺什么行为？
- 调用方最少需要知道哪些概念？
- 哪些细节应该隐藏在模块内部？
- 这个模块失败时暴露什么错误？
- 这个模块是否能被独立测试？
- 未来替换内部实现时，调用方是否不需要变？

模块接口评审清单：

```text
接口数量是否少？
参数是否表达领域概念，而不是内部步骤？
返回值是否稳定？
错误是否可理解？
内部 helper 是否没有泄露给外部？
测试是否覆盖对外行为，而不是绑定内部实现？
```

### 和 Harness workflow 的融合

| Workflow 点位 | 融合方式 |
| --- | --- |
| WF6 arch | 技术设计必须标出候选深模块和它们的 public API。 |
| WF7 plan | roadmap 不只列文件，还列模块责任和调用方向。 |
| WF8 code | 让 AI 实现内部细节，但 public API 由人审定。 |
| WF9 validate | 用 contract test 或 integration test 验证模块边界。 |
| WF10 iterate | debug 时优先判断问题是内部实现错，还是边界设计错。 |

## 方法 6：模块边界

### 它是什么

模块边界是系统中“谁负责什么、谁可以依赖谁、哪些细节不能泄露”的设计边界。深模块是一个模块内部的设计质量，模块边界是多个模块之间的组织质量。

AI 可以很快写实现，但它不会天然知道系统应该怎么长。开发者必须在更高层决定边界。

### 它解决什么问题

- 改一个功能牵一发动全身。
- 业务规则散落在 UI、API、数据库脚本和测试里。
- 模块之间循环依赖。
- 新功能不知道应该放在哪里。
- AI 为了通过当前任务绕过已有抽象。

### 专业化做法

模块边界文档至少记录：

```markdown
## Module Boundary: <module>

Owns:
- ...

Does not own:
- ...

Public API:
- ...

Depends on:
- ...

Must not depend on:
- ...

Tests:
- ...

Known risks:
- ...
```

依赖方向建议：

```text
UI / CLI
  -> Application service
  -> Domain model
  -> Infrastructure adapters
```

这不是要求所有项目都用同一种架构，而是要求依赖方向可解释、可检查。

### 和 Harness workflow 的融合

| Workflow 点位 | 融合方式 |
| --- | --- |
| WF6 arch | 明确模块边界、依赖方向、替换点和禁止依赖。 |
| WF7 plan | `project_map.json` 和 roadmap 对齐模块责任。 |
| WF8 code | AI 改代码前先说明会触碰哪些模块和边界。 |
| WF9 validate | 运行边界相关测试或 import/lint 检查。 |
| WF10 iterate | 如果 debug 反复跨模块，回到边界设计而不是继续补丁。 |

## 方法 7：控制系统熵增

### 它是什么

系统熵增指代码库随时间自然变乱：命名漂移、重复逻辑、依赖交叉、抽象泄漏、测试失效、文档过期、隐含约定增多。AI 让代码生成更快，也让熵增更快。

关键判断：

```text
AI 是复杂度放大器，不是复杂度清洁工。
```

在清晰系统里，AI 会把产出放大；在混乱系统里，AI 会把混乱放大。

### 熵增信号

- 同一概念有多种命名。
- 一个小改动跨很多文件。
- 测试需要大量 mock 内部细节。
- AI 每次都找错位置。
- 新增功能总是绕过已有模块。
- 文档描述和代码实际不一致。
- 失败后只能靠人工通读大段代码定位。

### 专业化做法

用固定节奏控制熵增：

| 节奏 | 动作 |
| --- | --- |
| 每个切片前 | 检查 glossary、模块边界、测试入口。 |
| 每个切片后 | 删除无用代码，统一命名，更新受影响文档；稳定代码结构变化时同步 `project_map.json` 和 `docs/20_facts/Codebase_Map.md`。 |
| 每轮 WF10 eval | 记录 Observation 和 Lesson，判断是否需要重构切片。 |
| 每次架构变更 | 更新边界、`project_map.json`、`docs/20_facts/Codebase_Map.md` 和测试策略。 |
| 每次 release 前 | 检查 Claim Boundary、文档、指标、语言是否一致。 |

复杂度预算：

```text
新增 public API 必须有理由。
新增术语必须进入 glossary。
新增依赖必须解释方向。
新增测试必须验证行为，不绑定无意义内部细节。
删除死代码和重复路径是正常交付的一部分。
```

### 和 Harness workflow 的融合

| Workflow 点位 | 融合方式 |
| --- | --- |
| WF6 arch | 把复杂度控制作为架构目标，而不只是功能拆分。 |
| WF7 plan | 每个任务包含“不会增加哪些复杂度”的说明。 |
| WF8 code | 小步实现，禁止让 AI 大面积铺代码。 |
| WF9 validate | 验证不只看测试，也看改动范围和边界是否合理。 |
| WF10 eval | 把熵增观察写入 Lesson 候选，而不是只记录指标。 |
| WF12 release | release 前处理高风险命名漂移和边界漂移。 |

## 方法 8：反馈回路

### 它是什么

反馈回路是从“做出改变”到“知道改变是否正确”的路径。反馈速度决定开发速度上限。AI 生成速度超过反馈速度时，系统会很快积累错误。

常见反馈回路：

- 单元测试。
- 类型检查。
- lint。
- 集成测试。
- smoke run。
- 用户 demo。
- code review。
- 指标对比。
- Harness Gate ledger。
- WF10 iteration eval。

### 专业化做法

设计反馈回路时问：

- 这个改动最快用什么验证？
- 失败时能不能定位到一个小范围？
- 是否有自动化命令？
- 如果不能自动化，手动验证步骤是什么？
- 反馈结果是否被记录为 Gate Evidence 或 iteration record？

一个切片的反馈栈示例：

```text
unit test
  -> integration test
  -> smoke command
  -> manual demo
  -> Gate ledger
  -> iteration_log decision
```

### 和 Harness workflow 的融合

| Workflow 点位 | 融合方式 |
| --- | --- |
| WF5 baseline | 指标和复现命令构成第一批反馈。 |
| WF8 code | 每个代码任务都有最小验证命令。 |
| WF9 validate | 汇总测试、smoke、review 和未运行项。 |
| WF10 run/eval | 反馈进入 `iteration_log.json`，形成下一轮决策。 |
| WF11 final-exp | 固化最终实验矩阵和指标反馈。 |
| WF12 release | 用 Claim Boundary 防止反馈不足的结论进入发布。 |

## 方法 9：管理复杂度

### 它是什么

管理复杂度是以上所有方法的共同目标。会写代码只是入口，能让系统长期可理解、可验证、可修改才是专业能力。

AI 时代的开发者角色更接近系统设计者：

- 判断什么应该做，什么不应该做。
- 把需求拆成可验证的垂直切片。
- 设计语言和边界。
- 选择测试和反馈方式。
- 审查 AI 产出是否增加了长期复杂度。
- 在必要时让 AI 停下，回到问题定义。

### 专业化做法

每次工作前建立四个约束：

```text
Language: 这次使用哪些稳定概念？
Slice: 这次只打通哪条端到端路径？
Boundary: 这次允许触碰哪些模块，不允许触碰哪些模块？
Feedback: 用什么命令、测试或审查证明结果？
```

每次工作后回答四个问题：

```text
代码是否更容易理解？
边界是否更清晰？
反馈是否更快？
下次 AI 是否更容易做对？
```

## 与 Harness WF0-WF12 的整体融合图

| Stage | 主要方法 | 应产出或检查 |
| --- | --- | --- |
| WF0 init | 通用语言、反馈回路 | 初始化项目指导，声明 glossary、测试命令、Gate ledger 规则。 |
| WF1 survey | Explore Intake Grill、Explore Synthesis Grill、通用语言 | 先问清用户目的和 idea 细节；survey 后基于 Conclusion Evidence 再追问会影响 contract/build 的关键意图。 |
| WF2 idea-debate | 复杂度管理、失败模式 | 消费 Grill 结果，比较方案假设、失败模式、语言冲突；不重新做大范围 Grill。 |
| WF3 refine-idea | Explore Synthesis 输出、验收标准 | 把 Grill 结果和 debate 结果固化成目标、非目标、success criteria、kill criteria、pivot triggers。 |
| WF4 data-prep | 通用语言、反馈回路 | 固化 Dataset、Split、Sample、Metric 等词和数据验证命令；只补问阻塞性数据问题。 |
| WF5 baseline-repro | TDD、反馈回路 | baseline smoke、metric check、`Baseline_Table.md` 和 Evaluation Contract 准备。 |
| WF6 arch | 深模块、模块边界、可溯源切片 | 模块责任、public API、依赖方向、复杂度风险；把关键路径锚定到 `Technical_Spec.md`。 |
| WF7 build-plan | 垂直切片、TDD、trace block | roadmap 按切片组织，每片有 `slice_id`、测试、验收命令和 downstream validation doc，并生成或刷新 `project_map.json` / `Codebase_Map.md`。 |
| WF8 code | TDD、深模块、边界 | 小步实现，不让 AI 大面积铺开；更新 `project_map.json` 时同步 `Codebase_Map.md`。 |
| WF9 validate | 反馈回路、Gate Evidence | 测试、smoke、review、`NOT_RUN` 项清楚记录。 |
| WF10 iterate | 反馈回路、复杂度控制 | 默认不做完整 Grill；按 Slice -> Test -> Code -> Run -> Eval 执行，只有意图漂移时回到 Explore/Contract 补问。 |
| WF11 final-exp | 反馈回路、复杂度控制 | 固化最终实验矩阵，避免临时漂移。 |
| WF12 release | 统一语言、Claim Boundary | 发布表述只使用已定义概念和有 Conclusion Evidence 支持的 Claim。 |

## 推荐工作模板

### 开工前

```markdown
## Pre-Work Alignment

Goal:
- ...

Non-goals:
- ...

Glossary terms:
- ...

Vertical slice:
- ...

Module boundaries:
- Allowed:
- Not allowed:

Tests / feedback:
- ...

Open questions:
- ...
```

### 让 AI 实现前

```text
请先读取项目 glossary、相关模块和测试。
只实现下面这个垂直切片。
先给出测试清单，再写第一个失败测试。
实现只能覆盖测试需要的最小行为。
不要新增 glossary 之外的概念；如果必须新增，先说明理由。
不要扩大模块 public API，除非先解释边界变化。
```

### 完成后

```markdown
## Completion Check

Changed paths:
- ...

Tests / commands:
- command:
  result:
  reason:
  artifacts:

Boundary review:
- ...

Language review:
- ...

Complexity review:
- ...

Remaining risks:
- ...
```

## 实践优先级

如果只能先做三件事：

1. 把 `Grill Me` 集中放在 WF1 Explore Intake 和 Explore Synthesis，问清用户目的、idea 内容和会影响 Contract/Build 的关键取舍。
2. 建立 `Project_Glossary.md`，让 AI 每次稳定实现前读取。
3. 所有任务改成垂直切片，每片必须可演示或可测试，并在 roadmap 中留下 trace block。

如果已经进入中大型系统，再补两件事：

4. 用 TDD 或 smoke command 给 AI 加反馈约束。
5. 明确深模块和模块边界，并在 WF10 eval 或每次 review 时记录复杂度和熵增观察。

## 资料来源

本文件综合了以下 Source Artifact 和参考资料：

- 本仓库 `coding_jpg/` 中 16 张 AI Coding 方法截图。
- Harness 工作流和术语：`AGENTS.md`、`CLAUDE.md`、`.agents/references/ubiquitous-language.md`、`.agents/references/workflow-guide.md`。
- Domain-Driven Design Reference：<https://www.domainlanguage.com/ddd/reference/>
- Matt Pocock 的 `grill-me` skill：<https://github.com/mattpocock/skills/blob/main/skills/grill-me/SKILL.md>
- Martin Fowler on Test-Driven Development：<https://martinfowler.com/bliki/TestDrivenDevelopment.html>
- Jimmy Bogard on Vertical Slice Architecture：<https://www.jimmybogard.com/vertical-slice-architecture/>
- John Ousterhout, A Philosophy of Software Design：<https://web.stanford.edu/~ouster/cgi-bin/book.php>
- DORA / Google Cloud DevOps capabilities：<https://dora.dev/devops-capabilities/>
