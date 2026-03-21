# CV 研究工作流完整指南

本文档详细介绍基于 Claude Code Skills 构建的 CV 研究工作流系统。
该系统将一个 CV 研究项目从"想法"推进到"竞赛提交/论文就绪"的完整过程，自动化管理并保证每一步的质量。

---

## 1. 系统架构概览

### 1.1 三层配置体系

系统采用 Claude Code 的三层配置机制，按加载频率和作用范围分层：

| 层级 | 位置 | 加载方式 | 用途 |
|------|------|---------|------|
| **CLAUDE.md** | 项目根目录 | 每次会话自动加载 | 全局上下文：项目名、环境、技术栈、当前阶段 |
| **Rules** | `.claude/rules/` | 编辑匹配 `globs` 的文件时自动加载 | 行为约束：代码修改规范、训练前 git 操作、依赖变更提醒 |
| **Skills** | `.claude/skills/` | 用户通过 `/skill-name` 手动调用 | 阶段执行器：每个工作流阶段的完整逻辑 |

**设计理念**：CLAUDE.md 极简（≤80 行），只放"每次都需要知道的"稳定信息；Rules 按路径条件加载（通过 globs frontmatter），避免无关信息污染上下文；Skills 按需调用，执行具体工作。Stage skills 设置 `disable-model-invocation: true`，必须由用户或 orchestrator 显式触发。

### 1.2 状态归属（State Ownership）

每个状态文件有唯一的写入责任方，避免多源分歧：

| 文件 | 唯一写入者 | 作用 |
|------|-----------|------|
| `PROJECT_STATE.json` | orchestrator + 各 WF skill | 阶段流转（唯一阶段真相源） |
| `iteration_log.json` | iterate skill | 实验历史（唯一实验真相源） |
| `project_map.json` | build-plan 生成，code-debug 维护 | 代码结构（唯一架构真相源，仅 stable 文件） |
| `CLAUDE.md` | init-project 分阶段生成 | Claude Code 每次会话的全局上下文 |

**关键规则**：iterate **不写** PROJECT_STATE.json；orchestrator **不写** iteration_log.json。需要跨文件信息时通过**读取**获得。

### 1.3 工作流全景

```
┌─────────────────────── 前期调研与设计 ───────────────────────┐
│                                                              │
│  ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐       │
│  │ WF1 │ →  │ WF2 │ →  │ WF3 │ →  │ WF4 │ →  │ WF5 │       │
│  │ 调研 │    │ 架构 │    │ 论证 │    │ 数据 │    │ base│       │
│  │      │    │      │ ←──│NO-GO│    │      │    │ line│       │
│  └─────┘    └──↑───┘    └─────┘    └─────┘    └─────┘       │
│                │                                              │
└────────────────│──────────────────────────────────────────────┘
                 │
┌────────────────│──── 实现与验证 ─────────────────────────┐
│                │                                          │
│  ┌─────┐    ┌──┴──┐    ┌──────┐                          │
│  │ WF6 │ →  │ WF7 │ →  │WF7.5 │                          │
│  │ 规划 │    │ 编码 │    │ 验证  │                          │
│  └─────┘    └─────┘    └──┬───┘                          │
│                        FAIL│→ /code-debug → 重试          │
│                            │                              │
└────────────────────────────│──────────────────────────────┘
                          PASS│
┌─────────────────────────────│── 迭代优化 ──────────────────────────────┐
│                             ▼                                          │
│  ┌──────────────────────────────────────────────────────┐              │
│  │                      WF8 迭代                         │              │
│  │                                                       │              │
│  │    /plan ──→ /code ──→ /run ──→ /eval ──→ 决策       │              │
│  │      ↑                                     │          │              │
│  │      │              DEBUG                  │          │              │
│  │      └─────────────────────────────────────┘          │              │
│  │                                                       │              │
│  │    可选: /ablate (组件贡献度分析)                       │              │
│  └───────────────────────┬───────────────────────────────┘              │
│                          │                                              │
│           ┌──────────────┼──────────────┐                              │
│        CONTINUE        PIVOT          ABORT                            │
│           │              │              │                               │
│           ▼              │              ▼                               │
│  ┌─────┐    ┌─────┐     │           终止项目                           │
│  │ WF9 │ →  │WF10 │     │                                              │
│  │ 消融 │    │ 提交 │     └──→ 回退 WF2（重新架构）                      │
│  └─────┘    └─────┘                                                    │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

Utility skills（非编号阶段）：
- `/code-debug` — 代码修复（被 /iterate code 调用或独立使用）
- `/evaluate` — 结果分析（被 /iterate eval 调用或独立使用）
- `/env-setup` — 维护型工具；用于依赖变化后的环境刷新，不是主流程前置步骤

---

## 2. Orchestrator — 中央调度器

**调用方式**: `/orchestrator [init|status|next|rollback|decision]`

Orchestrator 不执行具体研究工作，而是管理整个工作流的状态流转：

- **`init`** — 初始化项目：创建目录结构、生成 PROJECT_STATE.json、调用 `/init-project init` 生成最小版 CLAUDE.md
- **`status`** — 查看当前进度：含阶段一致性校验，WF8 时额外读取 iteration_log.json
- **`next`** — 推进到下一阶段：验证前置条件（artifact 是否齐全、是否有 blocker），通过后调用对应 skill
- **`rollback`** — 回退到指定阶段：保留历史记录，不删除任何 artifact
- **`decision`** — 记录关键决策：内容、理由、考虑过的替代方案

**自动触发**：`next` 命令在阶段完成后会自动调用 `/init-project update` 更新 CLAUDE.md（WF1/WF2/WF4/WF5/WF6 完成时）。

---

## 3. 阶段详解

### WF1–WF4: 调研→架构→论证→数据

| 阶段 | Skill | 输出 | 决策 |
|------|-------|------|------|
| WF1 survey-idea | `/survey-idea` | docs/Feasibility_Report.md | PROCEED/PIVOT/ABANDON |
| WF2 refine-arch | `/refine-arch` | docs/Technical_Spec.md | — |
| WF3 deep-check | `/deep-check` | docs/Sanity_Check_Log.md | GO/CONDITIONAL GO/NO-GO |
| WF4 data-prep | `/data-prep` | docs/Dataset_Stats.md + 数据管道 + CLAUDE.md 数据集路径同步 | — |

### WF5: Baseline 复现（含强制门控）

| | |
|---|---|
| **Skill** | `/baseline-repro [baseline_name or 'all']` |
| **输出** | `docs/Baseline_Report.md` + baseline_metrics + evaluation_protocol |
| **门控** | Baseline_Report.md 必须存在，每个 baseline 的 status 必须为 verified/partial（不可为 untested） |

如果有意跳过某些 baseline，必须标记为 `partial` 并在报告中说明原因。
WF5 同时负责创建首个可运行环境，并把 `CLAUDE.md` 的 `## Environment` 与 baseline 摘要同步到位。

### WF6–WF7: 规划→编码

| 阶段 | Skill | 输出 |
|------|-------|------|
| WF6 build-plan | `/build-plan` | docs/Implementation_Roadmap.md + project_map.json |
| WF7 code-expert | `/code-expert` | 全部项目代码 |

### WF7.5: 代码审查 + 训练链路验证（门控）

| | |
|---|---|
| **Skill** | `/validate-run [config_path]` |
| **审查项** | Codex 代码审查（新代码 vs baseline 等价性：数据管道、模型、loss、评估指标、常见 ML bug） |
| **验证项** | 100-step 训练、checkpoint 保存/加载、eval 流程、wandb 连接、git_snapshot |
| **门控** | PASS → WF8，REVIEW → 用户确认后继续或修复，FAIL → /code-debug 修复 |

确保不会在迭代中遇到代码正确性问题和基础设施问题。

### WF8: 结构化实验迭代（核心）

| | |
|---|---|
| **Skill** | `/iterate [plan|code|run|eval|ablate|status|log]` |
| **输出** | iteration_log.json（持续更新），最佳 checkpoint |
| **决策** | CONTINUE → WF9 / DEBUG → 新迭代 / PIVOT → WF2 / ABORT |

**七个子命令**：

| 子命令 | 用途 | 调用的 utility |
|--------|------|---------------|
| `plan [hypothesis]` | 记录假设，重复教训检查，设计变更，选择性 Codex 审查 | — |
| `code [description]` | 实现代码变更，强制 git commit | `/code-debug` |
| `run [config_path]` | 执行训练 + 运行 eval + 收集指标（自动化） | — |
| `eval [log_path]` | 评估结果，对比 baseline + best，做出决策 | `/evaluate` |
| `ablate [iter_id] --components "..."` | 迭代内消融实验，确定各组件贡献度 | — |
| `status` | 查看当前迭代 + 最近 5 次 + best | — |
| `log` | 完整迭代历史表格 | — |

**典型迭代循环**：
```
/iterate plan "将 backbone 从 ResNet-50 升级到 ResNet-101 以增强特征表达"
  → 重复教训检查（警告已知失败模式）
  → 记录 hypothesis, 设计 config_diff
  → (选择性) Codex 审查方案

/iterate code "升级 backbone 到 ResNet-101"
  → 写入持久化 context (.claude/iterations/iter{N}/context.json)
  → 调用 /code-debug 修改代码 + 强制 git commit
  → 移除 symlink（保留持久化 context）
  → status 变为 "training"

/iterate run {config_path}
  → 自动执行训练（background task）
  → 训练完成后自动运行 {EVAL_SCRIPT}
  → 解析 stdout 提取 metrics，更新 iteration_log.json
  → status 变为 "running"，输出指标摘要

/iterate eval experiments/{exp_prefix}_iter27/
  → 调用 /evaluate 解析 metrics → per-iteration 报告 (docs/iterations/iter27.md)
  → 对比 baseline + best, 做出决策
  → 输出推荐下一步命令

# 可选：消融实验（确定各组件贡献度）
/iterate ablate iter27 --components "aux_loss:loss.lambda_aux=0.0,lr_warmup:train.warmup_steps=0"
  → 对每个组件运行 w/o 训练
  → 输出对比表（component / primary_metric / Delta / Contribution）
```

**`run` 自动执行流程**：

`run` 子命令自动完成训练全链路，取代之前的手动训练流程：

```
构建训练命令 → Bash(run_in_background) → 解析 stdout 指标 → 运行 {EVAL_SCRIPT} → 更新 iteration_log.json
```

- 从 config_diff 自动构建 `python {TRAIN_SCRIPT} --config ... --no_snapshot` 命令
- 使用 `run_in_background: true` 支持 10-60 分钟长训练
- 训练完成后解析 stdout 中的训练轨迹字段（如 best step、final step、中间验证摘要）
- 自动运行 `{EVAL_SCRIPT}`，按 WF5 固化的 evaluation protocol 抽取最终指标
- 错误处理：OOM/NaN/crash 时保持 status="training" 并报错，不会静默失败
- `--manual` 回退：集群训练等场景退化为元数据登记模式

**`ablate` 消融实验**：

快速确定各组件贡献度，生成对比表：

```
/iterate ablate {base_iter} --components "name1:override1,name2:override2"
```

组件通过 `--components` 参数传入 `name:override` 对。
对每个组件生成 `{base_iter}_no_{component}` 子迭代，训练后自动 eval 并按 delta 分类：

| Delta 范围 | 分类 |
|-----------|------|
| < -1.0 dB | `significant` — 核心组件 |
| < -0.3 dB | `moderate` — 有贡献 |
| >= -0.3 dB | `minimal` — 可简化 |
| > 0 dB | `negative` — 移除反而更好 |

支持断点续跑：已完成的 sub-iteration 自动跳过。

**其他关键特性**：
- **持久化 context**: 存储到 `.claude/iterations/iter{N}/context.json`，symlink 作为兼容层
- **强制 git commit**: code 子命令完成后若无 commit hash，保持 coding 状态不推进
- **重复教训检查**: plan 阶段扫描已知 lessons，警告重复失败模式
- **Screening protocol**: 非架构/loss 变更建议先做 5K-10K proxy run

### WF9: 正式消融实验

| | |
|---|---|
| **Skill** | `/final-exp [stage_report_path]` |
| **输出** | docs/Final_Experiment_Matrix.md |
| **前置** | WF8 最终 iteration 决策为 CONTINUE |

设计符合顶会标准的完整实验矩阵：
- **消融实验**：每个创新组件 ON/OFF，隔离各组件贡献（可复用 WF8 `/iterate ablate` 的初步结果）
- **超参搜索**：关键超参数的搜索空间和策略
- **鲁棒性测试**：不同分辨率、极端场景、OOD 数据
- **跨数据集评估**：验证泛化性
- **计算预算**：估算总 GPU 小时数，规划执行顺序

### WF10: 提交与发布

| | |
|---|---|
| **Skill** | `/release [submit|package|validate]` |
| **输出** | 提交包（多场景渲染 + 打包 + 文件名校验） |
| **前置** | WF9 消融实验完成 |

三个子命令：
- **`validate`** — 检查提交包完整性（文件名格式、分辨率、场景覆盖）
- **`package`** — 生成符合竞赛/会议要求的提交包
- **`submit`** — 多场景训练 + 渲染 + 打包 + dry-run 检查

---

## 4. Utility Skills

### 4.1 env-setup — 维护型环境刷新

**调用方式**: `/env-setup [create|refresh]`

- 不属于主流程前置步骤
- 首次可运行环境由 WF5 `/baseline-repro` 创建
- 仅在依赖变化、机器切换或 `CLAUDE.md` 环境节过期时使用

当 `requirements*.txt`、`environment*.yml`、`pyproject.toml` 变更时，`deps-update` rule 会自动提醒运行 refresh。

### 4.2 code-debug — 代码修复

**调用方式**: `/code-debug [error_log_path or issue description]`

**Operation modes**（由 `.claude/current_iteration.json` context 决定）：
- `planned_change`: 由 /iterate code 调用，按 hypothesis 实现变更，完成后语义化 commit
- `bugfix`: 独立调用，诊断修复 crash/error
- `perf_tuning`: 独立调用，性能优化

修改代码后自动执行 `py_compile` + `ruff check`，接口变更时同步更新 `project_map.json`。

### 4.3 evaluate — 结果分析

**调用方式**: `/evaluate [log_path]`

核心功能：
- 解析训练日志，提取 baseline/evaluation protocol 定义的目标指标
- 诊断训练问题（过拟合、梯度消失、loss 发散等）
- 对比 Baseline 性能 + 历史最佳
- 给出 CONTINUE/DEBUG/PIVOT/ABORT 决策

**Per-iteration 报告**: 从 /iterate eval 调用时写入 `docs/iterations/iter{N}.md`。
`docs/Stage_Report.md` 作为最新摘要索引。

---

## 5. 关键功能详解

### 5.1 Stable vs Volatile 文件分层

project_map.json 只追踪 **stable 架构文件**：
- src/ 核心模块
- baselines/ 子目录
- 核心 configs 和 scripts（在 CLAUDE.md Entry Scripts 中列出的）

**Volatile 实验资产**不需追踪：
- per-iteration scripts (run_*.sh, run_ablation_*.py)
- 临时实验配置
- experiments/ 下所有内容

### 5.2 训练前 Git + wandb 集成

三层保障确保每次训练都有完整版本记录：

1. **Claude 的语义化 Commit**（rule 约束）
2. **git_snapshot.py 安全网**（代码中）
3. **wandb + checkpoint 记录**（代码中）

### 5.3 Codex Cross-Validation

| 触发点 | 触发条件 | 审查对象 | 审查重点 |
|--------|---------|---------|---------|
| WF3 deep-check | **始终触发**（关键门禁） | Technical_Spec 技术方案 | 找遗漏风险和失败模式 |
| WF7.5 validate-run | **始终触发**（代码入口门禁） | src/ 新代码 vs baselines/ 参考实现 | Baseline 等价性：数据管道、模型计算、loss、评估指标 |
| WF8 /iterate plan | **选择性触发**：新 loss 族、架构变更、PIVOT 后、连续 3 次 DEBUG | 单次迭代 hypothesis | 假设验证，避免重复失败 |

记录值：`"used"` / `"skipped_low_value"` / `"unavailable"`（不再使用 null）

### 5.4 CLAUDE.md 分阶段生成

CLAUDE.md 保持为**稳定操作指南**（≤80 行），不放快变实验内容。
快变内容（当前最佳、当前风险、下次实验）存在 iteration_log.json 和 MEMORY.md 中。

| 时机 | 填入内容 |
|------|---------|
| `init` | Environment 占位 + Workflow 概览 |
| WF1 完成后 | Idea 描述 |
| WF2 完成后 | Tech Stack 细节 |
| WF4 完成后 | Dataset 路径和统计 |
| WF5 完成后 | Baseline 指标参考 |
| WF6 完成后 | Project Structure + Core Artifacts |
| WF7 首次实验后 | Entry Scripts（锁定入口脚本） |

### 5.5 自动化训练执行

`/iterate run` 实现了从代码到指标的全链路自动化：

```
                     /iterate run [config_path]
                               │
                               ▼
                ┌────────────────────────────┐
                │ ① 读取 iteration_log.json   │
                │    找 status="training" 迭代 │
                │    提取 config_diff          │
                └──────────────┬─────────────┘
                               │
                               ▼
                ┌────────────────────────────┐
                │ ② 构建训练命令               │
                │    python {TRAIN_SCRIPT}    │
                │      --config {config_path} │
                │      --no_snapshot          │
                │      {dotlist overrides}    │
                │    确定 exp_dir              │
                └──────────────┬─────────────┘
                               │
                               ▼
                ┌────────────────────────────┐
                │ ③ Bash(run_in_background)   │
                │    执行训练，⏱ 10-60 min     │
                │    记录 started_at 时间戳    │
                └──────────────┬─────────────┘
                               │
                       ┌───────┴───────┐
                       │               │
                   exit = 0        exit ≠ 0
                       │               │
                       │               ▼
                       │    ┌────────────────────────┐
                       │    │ 错误诊断                 │
                       │    │ ┌──────────────────────┐│
                       │    │ │ "CUDA out of memory" ││
                       │    │ │ → OOM, 建议降分辨率   ││
                       │    │ ├──────────────────────┤│
                       │    │ │ "nan" in loss 行     ││
                       │    │ │ → NaN, 建议降 LR     ││
                       │    │ ├──────────────────────┤│
                       │    │ │ 其他非零 exit code    ││
                       │    │ │ → crash, 输出 stderr ││
                       │    │ └──────────────────────┘│
                       │    │ status 保持 "training"   │
                       │    │ 报错给用户，终止流程      │
                       │    └────────────────────────┘
                       │
                       ▼
                ┌────────────────────────────┐
                │ ④ 解析训练 stdout            │
                │    提取 training_trace       │
                │    如 best_step/final_step   │
                │    和训练脚本暴露的中间指标    │
                └──────────────┬─────────────┘
                               │
                               ▼
                ┌────────────────────────────┐
                │ ⑤ 定位最佳 checkpoint        │
                │    扫描 exp_dir/checkpoints/ │
                │    按 step 排序取最新        │
                └──────────────┬─────────────┘
                               │
                               ▼
                ┌────────────────────────────┐
                │ ⑥ 运行 {EVAL_SCRIPT}        │
                │    --checkpoint {best_ckpt} │
                │    --output_dir {exp}/eval  │
                │    按 WF5 固定下来的         │
                │    evaluation protocol 取数 │
                └──────────────┬─────────────┘
                               │
                       ┌───────┴───────┐
                       │               │
                   eval 成功        eval 失败
                       │               │
                       ▼               ▼
              ┌──────────────┐  ┌──────────────────┐
              │ 记录全部指标   │  │ 仅记录训练指标     │
              │ (train+eval) │  │ 提示用户手动 eval  │
              └──────┬───────┘  └────────┬─────────┘
                     │                   │
                     └─────────┬─────────┘
                               │
                               ▼
                ┌────────────────────────────┐
                │ ⑦ 更新 iteration_log.json   │
                │    run_manifest:            │
                │      command, config_path,  │
                │      exp_dir, duration,     │
                │      exit_code, ckpt_path   │
                │    metrics:                 │
                │      仅写 protocol 定义的    │
                │      tracked metrics        │
                │    training_trace:          │
                │      best_step/final_step等 │
                │    status → "running"       │
                └──────────────┬─────────────┘
                               │
                               ▼
                    输出指标摘要 + 推荐
                    `/iterate eval`
```

**`--manual` 回退**：如果训练需要在集群上运行或用户传 `--manual`，退化为元数据登记模式
（只记录 command, config_path, exp_dir, expected_steps），status→"running"，用户训练完成后调用 `/iterate eval`。

### 5.6 Per-iteration 报告

评估报告按迭代存储：
- `docs/iterations/iter1.md`, `docs/iterations/iter2.md`, ...
- `docs/Stage_Report.md` 作为最新摘要索引
- code-debug 读取最新 iteration 报告而非过时的单例

---

## 6. Rules 详解

### 6.1 project-map.md

**触发条件**：编辑 `src/`, `baselines/`, `configs/`, `scripts/`, `tests/` 下的文件时。
**覆盖格式**：`*.py`, `*.yaml`, `*.yml`, `*.json`, `*.sh`
**区分 stable/volatile**：仅 stable 文件需要更新 project_map.json。

### 6.2 pre-training.md

**触发条件**：编辑 `scripts/train*.py`, `src/**/*.py`, `baselines/**/train*.py` 时。

### 6.3 deps-update.md

**触发条件**：编辑 `requirements*.txt`, `environment*.yml`, `pyproject.toml`, `setup.py` 时。

---

## 7. 状态流转总览

### 7.1 工作流阶段流转（PROJECT_STATE.json 管理）

```
┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌─────┐  ┌────┐  ┌────┐  ┌────┐
│WF1 │→ │WF2 │→ │WF3 │→ │WF4 │→ │WF5 │→ │WF6 │→ │WF7 │→ │WF7.5│→ │WF8 │→ │WF9 │→ │WF10│
│调研│  │架构│  │论证│  │数据│  │base│  │规划│  │编码│  │验证 │  │迭代│  │消融│  │提交│
└────┘  └─┬──┘  └─┬──┘  └────┘  └────┘  └────┘  └────┘  └──┬──┘  └─┬──┘  └────┘  └────┘
          ↑       │                                          │       │
          │    NO-GO → 回退 WF2                              │       │
          │                                            FAIL → fix    │
          ↑                                                          │
          │  PIVOT                                                   │
          └──────────────────────────────────────────────────────────┘
```

每个阶段完成后 orchestrator 自动触发 `/init-project update` 更新 CLAUDE.md。

### 7.2 WF8 迭代内部状态机（iteration_log.json 管理）

```
                        /iterate plan "hypothesis"
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │           planned              │  重复教训检查
                    │  hypothesis + config_diff 已记录│  (选择性) Codex 审查
                    └───────────────┬───────────────┘
                                    │
                                    │  /iterate code "description"
                                    ▼
                    ┌───────────────────────────────┐
                    │           coding               │  写入持久化 context
                    │  调用 /code-debug 修改代码      │  → .claude/iterations/iter{N}/
                    │  执行 py_compile + ruff check  │
                    │  语义化 git commit              │
                    └───────────────┬───────────────┘
                                    │
                            commit 成功?
                           ┌────────┴────────┐
                           │                 │
                          失败              成功
                           │                 │
                           ▼                 ▼
                 保持 "coding"    ┌──────────────────────────┐
                 报错给用户       │        training           │
                 等待手动修复     │  代码就绪，等待训练登记     │
                                 └────────────┬─────────────┘
                                              │
                                              │  /iterate run [config_path]
                                              ▼
                         ┌─────────────────────────────────────────────┐
                         │              训练执行阶段                     │
                         │                                              │
                         │  ┌──────────────────────────────────────┐   │
                         │  │ 构建命令 → Bash(background) → 等待完成 │   │
                         │  │ {TRAIN_SCRIPT} --config ... ⏱10-60min│   │
                         │  └──────────────────┬───────────────────┘   │
                         │                     │                        │
                         │             ┌───────┴───────┐                │
                         │             │               │                │
                         │          exit=0          exit≠0              │
                         │             │               │                │
                         │             │               ▼                │
                         │             │     ┌───────────────────┐      │
                         │             │     │ OOM → 建议降分辨率 │      │
                         │             │     │ NaN → 建议降 LR   │      │
                         │             │     │ crash → stderr    │      │
                         │             │     │ 保持 "training"   │      │
                         │             │     │ 报错，终止流程 ✗   │      │
                         │             │     └───────────────────┘      │
                         │             ▼                                │
                         │  ┌────────────────────────────────────┐     │
                         │  │ 解析 stdout → peak/final metrics   │     │
                         │  │ 定位最佳 checkpoint                 │     │
                │  │ 运行 {EVAL_SCRIPT} → protocol-defined │     │
                │  │ final metrics                         │     │
                         │  └──────────────────┬─────────────────┘     │
                         │                     │                        │
                         │                     ▼                        │
                         │  ┌────────────────────────────────────┐     │
                         │  │ 更新 iteration_log.json             │     │
                         │  │   run_manifest + metrics            │     │
                         │  │   status → "running"                │     │
                         │  └────────────────────────────────────┘     │
                         └─────────────────────────────────────────────┘
                                              │
                                              │  /iterate eval [exp_dir]
                                              ▼
                    ┌───────────────────────────────┐
                    │           running              │  调用 /evaluate 解析
                    │  对比 baseline + 历史最佳       │  生成 per-iteration 报告
                    │  提取 lessons learned           │  docs/iterations/iter{N}.md
                    │  做出决策                       │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │         completed              │
                    │  status="completed", 决策已记录 │
                    └───────────────┬───────────────┘
                                    │
                  ┌─────────┬───────┴───────┬─────────┐
                  │         │               │         │
               CONTINUE   DEBUG           PIVOT     ABORT
                  │         │               │         │
                  ▼         ▼               ▼         ▼
               → WF9     回到 plan       → WF2      终止
              (消融实验)  (新 hypothesis)  (重新架构)  项目
                            │
                            └──→ /iterate plan "基于 lessons 的新假设"
                                        │
                                        ▼
                                   (循环回到 planned)

            ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
            可选支线: /iterate ablate (在 completed 后)
            ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄

              /iterate ablate {base_iter} --components "..."
                                │
                        ┌───────┴────────┐
                        │ 对每个组件:     │
                        │  训练 w/o comp  │
                        │  运行 eval       │
                        │  记录 sub-iter  │
                        └───────┬────────┘
                                │
                                ▼
                ┌───────────────────────────────────┐
                │ 输出对比表                          │
                │ Component | Metric | Delta | 分类  │
                │ ─────────────────────────────────  │
                │ < -1.0 dB → significant (核心)     │
                │ < -0.3 dB → moderate (有贡献)      │
                │ >= -0.3  → minimal (可简化)        │
                │ > 0 dB   → negative (移除更好)     │
                └───────────────────────────────────┘
```

### 7.3 状态文件归属

```
┌─────────────────────────┐     ┌─────────────────────────┐
│   PROJECT_STATE.json    │     │   iteration_log.json    │
│   唯一阶段真相源         │     │   唯一实验真相源         │
│                         │     │                         │
│   写入者:               │     │   写入者:               │
│     orchestrator        │     │     /iterate skill      │
│     各 WF skill         │     │                         │
│                         │     │   内容:                 │
│   内容:                 │     │     iterations[]        │
│     current_stage       │     │     best_iteration      │
│     history[]           │     │     baseline_metrics    │
│     artifacts           │     │                         │
├─────────────────────────┤     ├─────────────────────────┤
│   project_map.json      │     │   CLAUDE.md             │
│   唯一架构真相源         │     │   全局上下文             │
│                         │     │                         │
│   写入者:               │     │   写入者:               │
│     build-plan 生成      │     │     /init-project       │
│     code-debug 维护      │     │     分阶段增量填充       │
│                         │     │                         │
│   仅追踪 stable 文件     │     │   ≤80 行，稳定操作指南   │
└─────────────────────────┘     └─────────────────────────┘

关键规则: /iterate 不写 PROJECT_STATE.json
         orchestrator 不写 iteration_log.json
         需要跨文件信息时通过「读取」获得
```

### 7.4 一致性防漂移规则

- 始终使用单一定义：`WF5=baseline`、`WF6=build-plan`、`WF7=code-expert`、`WF7.5=validate-run`、`WF8=iterate`。
- WF4 完成后，`PROJECT_STATE.json.dataset_paths` 与 `CLAUDE.md` 的 `### Dataset Paths` 必须立即同步。
- WF5 完成后，`CLAUDE.md` 的 `## Environment` 不能再保留占位内容。
- WF8 的 `run/eval` 必须以 WF5 产出的 baseline/evaluation protocol 决定要记录哪些指标；训练轨迹和最终评估指标分开存。
- WF8 任一子命令完成后，`PROJECT_STATE.json.current_stage.latest_iteration`、`iteration_count` 和 `CLAUDE.md Current stage` 必须与 `iteration_log.json` 最新迭代一致。
- 缺少语义化 commit、`run_manifest` 或 `lessons` 的 iteration 不得标记为 completed。

---

## 8. 快速参考

**常用命令**：
```
/orchestrator init          # 初始化项目
/orchestrator status        # 查看当前状态
/orchestrator next          # 推进到下一阶段
/orchestrator rollback 2    # 回退到 WF2
/orchestrator decision      # 记录关键决策

/baseline-repro all         # 复现所有 baseline
/validate-run               # WF7.5 训练链路验证

/iterate plan "hypothesis"  # 规划新迭代（含重复教训检查）
/iterate code "description" # 实现变更（强制 git commit）
/iterate run config.yaml    # 执行训练 + 自动收集指标
/iterate eval path/to/exp   # 评估结果 + 做出决策
/iterate ablate {base_iter} --components "name:override,..."  # 消融实验
/iterate status             # 查看迭代进度
/iterate log                # 完整迭代历史

/code-debug [error info]    # 修复代码问题（可独立使用）
/evaluate [log_path]        # 分析结果（可独立使用）
/env-setup refresh          # 依赖变化后刷新环境快照

/release validate           # 检查提交包完整性
/release package            # 生成提交包
/release submit             # 多场景训练 + 打包
```

**Git 分支策略**：单人项目可直接在 master/main 开发。团队协作时可按阶段建分支（可选）。

**Commit 规范**（按场景选择格式）：
- 训练相关代码变更: `train(research): {描述}` 或 `train(baseline/{name}): {描述}`
- 工作流文档/配置: `[WF{n}] {type}: {message}`，type = feat / fix / docs / refactor / exp
