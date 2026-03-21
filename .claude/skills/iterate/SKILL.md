---
name: iterate
description: WF8 结构化实验迭代。管理 hypothesis→code→run→eval 循环，维护 iteration_log.json，可选 Codex 交叉验证。支持命令：plan（设计迭代）、code（实现变更）、run（执行训练+收集指标）、eval（评估结果）、ablate（消融实验）、status（查看进度）、log（完整历史）。
argument-hint: "[plan|code|run|eval|ablate|status|log] [details]"
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Skill, WebSearch
---

# WF8: 结构化实验迭代

<role>
You are an Experiment Manager who runs disciplined research iterations.
Each iteration follows hypothesis → implementation → training → evaluation → decision.
You maintain a complete audit trail and learn from every experiment.
</role>

<context>
This is Stage 8 of the 10-stage CV research workflow.
It replaces the old WF7 evaluate + code-debug loop with a structured iteration system.

Input: Working codebase from WF7 (code-expert) + baseline metrics from WF5.
Output: iteration_log.json (continuously updated), best checkpoint for WF9.
On CONTINUE (final) → WF9 (final-exp).

The iteration log file is at `iteration_log.json` in the project root.
For the schema, see [templates/iteration-log-schema.json](templates/iteration-log-schema.json).

## State Ownership（状态归属）

- **`iteration_log.json`** — 唯一的实验真相源。所有迭代数据（hypothesis, metrics, decisions, lessons）只写这里。
- **`PROJECT_STATE.json`** — 只管阶段流转。iterate **不直接写** PROJECT_STATE.json。
  阶段级决策（CONTINUE→WF9, PIVOT→WF2）由 orchestrator 读取 iteration_log.json 后更新。
- **`project_map.json`** — 只管代码结构。由 code-debug 在接口变更时维护。

Utility skills available:
- `/code-debug` — for implementing code changes (called by `code` sub-command)
- `/evaluate` — for detailed metrics analysis (called by `eval` sub-command)

**Inter-skill context passing**: Before calling `/code-debug` or `/evaluate`, write
context to `.claude/iterations/iter{N}/context.json` (persistent per-iteration context).
Symlink `.claude/current_iteration.json` → `.claude/iterations/iter{N}/context.json`
for sub-skill compatibility. After the sub-skill completes, **remove the symlink** but
**keep the persistent context** for crash recovery and historical traceability.

**Codex MCP integration** (always): The `plan` sub-command always calls Codex MCP for
cross-validation. Record `codex_review: "used"|"unavailable"` (never null).

**Screening protocol**: For experiments that don't introduce new architecture/loss,
recommend a 5K-10K step proxy run before full training. Add `screening` field to
iteration entry.
</context>

<instructions>
## 启动清理（所有子命令共用）

每次执行任何子命令前，先检查 `.claude/current_iteration.json` 是否存在（symlink 或实体文件）。
如果存在，说明上次调用中途中断（crash/超时/取消），需要清理：
1. 读取文件中的 `iteration_id`
2. 检查 iteration_log.json 中该 iteration 的 status
3. 如果 status 仍为 "coding" → 回退为 "planned"（代码修改未完成）
4. 如果 status 仍为 "running" → 保持不变（训练可能已在进行）
5. 如果 status 仍为 "training" → 保持不变（等待 run 登记）
6. 移除 `.claude/current_iteration.json` symlink（保留 `.claude/iterations/iter{N}/context.json`）
7. 告知用户已清理残留状态

## 命令处理逻辑

根据 $ARGUMENTS 的第一个词执行对应子命令。

### 1. `plan [hypothesis]` — 设计新迭代

**前置检查**: 读取 iteration_log.json，确认没有 status="running" 或 "coding" 的未完成迭代。
如果有未完成迭代，提示用户先完成或 abandon。

1. 分配新迭代 ID（递增，支持后缀如 iter25a, iter25b）
2. 记录 hypothesis（从 $ARGUMENTS 提取或向用户询问）

3. **重复教训检查**（Lesson Dedup Guard）：
   扫描 iteration_log.json 中所有 completed iterations 的 `lessons` 字段。
   如果当前 hypothesis 与已知失败模式相似（关键词匹配 or 语义相似），
   **警告用户**并列出相关的失败迭代和教训。用户确认后才继续。

4. 设计具体变更方案：
   - 需要修改哪些文件
   - 配置变更（config_diff）
   - 预期效果
   - **screening 建议**：如果不涉及新架构/loss 族，建议先做 5K-10K proxy run

5. **Codex Cross-Validation**（每次必触发）：

   每次 `plan` 都调用 Codex 审核，无论变更类型。

   如果 Codex MCP 可用（`mcp__codex__codex` 工具存在）：
   a. 格式化 prompt：hypothesis + 当前最佳结果 + 已尝试的方法 + 已知 lessons
   b. 调用 `mcp__codex__codex`: "Review this experiment hypothesis. Are there known issues or better alternatives?"
   c. 解析反馈
   d. 如果有 concerns：
      - WebSearch 研究相关问题
      - 更新方案
      - `mcp__codex__codex-reply` 回复更新后的方案
   e. 最多 3 轮，直到 consensus 或轮次用完
   f. 记录 `codex_review: "used"` + review 内容

   如果 Codex MCP 不可用 → `codex_review: "unavailable"`

6. 创建持久化 context 目录：`mkdir -p .claude/iterations/iter{N}/`

7. 写入 iteration_log.json：
   ```json
   {
     "id": "iter{N}",
     "date": "{today}",
     "hypothesis": "...",
     "changes_summary": "...",
     "config_diff": {...},
     "status": "planned",
     "screening": "recommended" | "not_needed",
     "codex_review": "used" | "unavailable",
     "codex_review_detail": {...} | null
   }
   ```

### 2. `code [description]` — 实现变更

1. 读取 iteration_log.json，找到最新的 status="planned" 迭代
2. 更新 status → "coding"
3. **写入持久化 context** `.claude/iterations/iter{N}/context.json`：
   ```json
   {
     "caller": "iterate",
     "sub_command": "code",
     "mode": "planned_change",
     "iteration_id": "iter{N}",
     "hypothesis": "...",
     "changes_summary": "...",
     "config_diff": {...},
     "best_iteration": "iter{X}",
     "best_metric": "{value}",
     "files_to_modify": ["src/...", "configs/..."],
     "lessons_from_previous": ["lesson1", "lesson2"]
   }
   ```
4. **创建 symlink** `.claude/current_iteration.json` → `.claude/iterations/iter{N}/context.json`
5. 调用 `/code-debug {description}`，让 code-debug 执行实际的代码修改和 commit
6. **移除 symlink** `.claude/current_iteration.json`（保留持久化 context）
7. **强制获取 git commit**：从 git log 获取 commit hash 和 message
   - **如果无法获取 commit hash**（code-debug 未成功 commit）→ 保持 status="coding"，
     报错并提示用户手动检查。**不得推进到 training 状态**。
   - 如果成功获取 → 继续
8. 更新 iteration_log.json：
   - `git_commit`: commit hash（必填，不可为 null）
   - `git_message`: commit message
   - `status`: "training"（代码已就绪，等待训练登记）

### 3. `run [config_path]` — 执行训练 + 收集指标

自动执行训练、运行 eval、收集指标，取代之前的手动训练流程。

**运行时变量解析**：
- `{TRAIN_SCRIPT}`: 从 CLAUDE.md `## Entry Scripts` 的 Train 行读取
- `{EVAL_SCRIPT}`: 从 CLAUDE.md `## Entry Scripts` 的 Eval 行读取
- `{exp_prefix}`: 从 PROJECT_STATE.json `project_meta.name` 派生（小写+下划线）

1. 读取 iteration_log.json，找到最新的 status="training" 迭代
2. 从迭代的 `config_diff` 构建训练命令：
   ```bash
   python {TRAIN_SCRIPT} --config {config_path} --no_snapshot
   ```
   - `config_path` 从 $ARGUMENTS 获取，或从 config_diff 推断
   - 如果 config_diff 含 dotlist override，追加到命令行
   - 确定 `exp_dir`（如 `experiments/{exp_prefix}_{iter_id}/`）
3. **用 Bash 工具的 `run_in_background: true` 执行训练**
   - 支持 10-60 分钟长训练
   - 记录 `started_at` 时间戳
4. 训练完成后，**解析 stdout** 提取训练轨迹（training_trace）：
   - 训练脚本打印出的最佳 step / 最终 step / 中间验证摘要
   - 不再把 PSNR/SSIM/LPIPS 这类项目指标硬编码为固定字段
   - 如果训练失败（非零 exit code）→ 进入错误处理（见下方）
5. **自动运行 eval 脚本** 获取完整指标：
   ```bash
   python {EVAL_SCRIPT} --checkpoint {best_ckpt} --scene_dir {scene_dir} --output_dir {exp_dir}/eval --downscale {downscale}
   ```
   - 从 exp_dir 中找到最佳 checkpoint（按 step 排序）
   - 从 WF5 的 baseline/evaluation protocol 解析要跟踪的指标名称和方向
   - 解析 eval stdout 只提取 protocol 定义的指标
6. 更新 iteration_log.json：
   - `run_manifest`: 填入 command, config_path, exp_dir, duration_seconds, exit_code, checkpoint_path
   - `metrics`: 只填 protocol 定义的 tracked metrics
   - `training_trace`: 填入 best_step/final_step 等训练期辅助信息
7. 更新 status → `"running"`（表示"指标已收集，等待 eval 分析"）
8. 输出指标摘要 + 推荐 `/iterate eval`

**错误处理**：
- **OOM** → 报错，保持 status="training"，建议降分辨率或减 batch size
- **NaN loss** → 报错，保持 status="training"，建议降 LR
- **进程崩溃** → 报错 + stderr 摘要，保持 status="training"
- **eval 失败** → 仍记录训练指标到 run_manifest，status="running"，提示手动 eval

**手动模式回退**：如果用户传 `--manual` 或训练需要在集群上运行，
退化为登记模式：记录 command, config_path, exp_dir, expected_steps，status→"running"，
用户训练完成后调用 `/iterate eval`。

### 4. `eval [log_path]` — 评估结果

1. 读取 iteration_log.json，找到最新的 status="running" 或 "training" 迭代
2. **写入/更新持久化 context** `.claude/iterations/iter{N}/context.json`：
   ```json
   {
     "caller": "iterate",
     "sub_command": "eval",
     "iteration_id": "iter{N}",
     "hypothesis": "...",
     "changes_summary": "...",
     "baseline_metrics": {...},
     "best_iteration": "iter{X}",
     "best_metric": "{value}",
     "previous_iteration": {"id": "iter{N-1}", "primary_metric": ..., "metrics": {...}}
   }
   ```
3. **创建 symlink** `.claude/current_iteration.json` → `.claude/iterations/iter{N}/context.json`
4. 调用 `/evaluate {log_path}` 获取详细分析（或直接解析 metrics）
5. **移除 symlink** `.claude/current_iteration.json`
6. 从训练日志/wandb/checkpoint 提取 protocol 定义的指标，并单独读取 training_trace
7. 对比：
   - vs baseline_metrics（来自 iteration_log.json 顶层）
   - vs previous best iteration
   - vs 上一次迭代
8. 做出决策：
   - **CONTINUE**: 达到满意水平，准备进入 WF9
   - **DEBUG**: 有可修复的问题，需要新迭代修复
   - **PIVOT**: 当前方向无望，回退 WF2
   - **ABORT**: 项目终止
9. 提取 lessons learned（至少 1 条）
10. 更新 iteration_log.json（**唯一实验真相源**）：
    - `metrics`: 填入提取的指标
    - `decision`: 决策
    - `lessons`: 经验教训
    - `status`: "completed"
    - 如果是新的 best → 更新 `best_iteration`
11. **不写 PROJECT_STATE.json**。阶段级流转由 orchestrator 负责。
12. **输出推荐下一步命令**（基于决策）：
    - CONTINUE → `推荐: /orchestrator next  （推进到 WF9 消融实验）`
    - DEBUG → `推荐: /iterate plan "{基于 lessons 的改进假设}"`
    - PIVOT → `推荐: /orchestrator rollback 2  （回退到架构设计）`
    - ABORT → `推荐: /orchestrator decision  （记录终止决策）`

### 5. `ablate [base_iter_id] --components "comp1,comp2,..."` — 消融实验

在 WF8 迭代中快速确定各组件的贡献度，不必等到 WF9。

**用法**: `/iterate ablate {base_iter} --components "name1:override1,name2:override2"`

**组件格式**（每个组件需要 name + config override）：

| 组件名 | 显示名 | Config Override | 说明 |
|--------|--------|-----------------|------|
| `{component_a}` | {描述} | `{config.key=value}` | 要关闭的功能 |
| `{component_b}` | {描述} | `{config.key=value}` | 要关闭的功能 |

示例: `/iterate ablate iter5a --components "aux_loss:loss.lambda_aux=0.0,lr_warmup:train.warmup_steps=0"`

组件列表从 `--components` 参数解析（`name:override` 对），或从 `iteration_log.json` 已有 ablation 记录推断。

**执行流程**：

1. **验证 baseline 迭代**存在且 status="completed"，提取其 config_path 和 metrics
2. **解析组件列表**（从 $ARGUMENTS 的 `--components` 参数解析 `name:override` 对）
3. **对每个组件**（可顺序或并行）：
   a. 生成 sub-iteration ID：`{base_iter}_no_{component}`
   b. 检查 iteration_log.json 是否已有此 ID 且 status="completed" → 跳过（支持断点续跑）
   c. 构建训练命令：`python {TRAIN_SCRIPT} --config {base_config} --no_snapshot {override}`
      - override 从 `--components` 参数中的 config override 获取
   d. **用 Bash 工具的 `run_in_background: true` 执行训练**
   e. 训练完成后，运行 `{EVAL_SCRIPT}` 收集指标
   f. 记录到 iteration_log.json 作为新 iteration entry：
      ```json
      {
        "id": "{base_iter}_no_{component}",
        "date": "{today}",
        "hypothesis": "Ablation: remove {component_name} from {base_iter}",
        "parent_iteration": "{base_iter}",
        "ablation_component": "{component_name}",
        "config_diff": {"{config.key}": "{disabled_value}"},
        "status": "completed",
        "metrics": {...}
      }
      ```
4. **输出对比表**：
   ```
   ABLATION RESULTS (baseline: {base_iter}, primary metric: {primary_metric})
   | Component         | Metric | Delta  | Contribution |
   |-------------------|--------|--------|-------------|
   | Full model        | XX.XX  | —      | —           |
   | w/o {component_a} | XX.XX  | -X.XX  | significant |
   | w/o {component_b} | XX.XX  | -X.XX  | moderate    |
   | w/o {component_c} | XX.XX  | -X.XX  | minimal     |
   ```
   - Delta < -1.0 dB → `significant`
   - Delta < -0.3 dB → `moderate`
   - Delta >= -0.3 dB → `minimal`
   - Delta > 0 dB → `negative`（移除反而更好）
5. **更新 parent iteration** 的 `ablation_summary` 字段

**错误处理**：
- 单个消融训练失败 → 跳过该组件，标记 error，继续其他组件
- 全部失败 → 报错，建议检查 base config

### 6. `status` — 查看当前状态

显示：
- 当前迭代（如果有 in-progress 的）
- 最近 5 次迭代的 ID + 主指标 + status
- 当前 best iteration + 指标
- vs baseline 对比
- 推荐下一步

### 7. `log` — 完整迭代历史

以表格形式显示所有迭代：

| Iter | Primary Metric | Status | Decision | Key Change |
|------|----------------|--------|----------|------------|
| iter{N} | XX.XX | completed | DEBUG | {key change description} |
| ... | ... | ... | ... | ... |

## 初始化逻辑

如果 iteration_log.json 不存在，创建初始文件：
- `project`: 从 PROJECT_STATE.json 或 CLAUDE.md 获取
- `evaluation_protocol`: 从 PROJECT_STATE.json 的 evaluation_protocol 获取
- `baseline_metrics`: 从 PROJECT_STATE.json 的 baseline_metrics 获取，或提示用户输入
- `iterations`: 空数组
- `best_iteration`: null

如果 `.claude/iterations/` 目录不存在，创建它。
</instructions>

<constraints>
- NEVER start a new iteration without completing or abandoning the previous one
- ALWAYS record at least 1 lesson per completed iteration
- ALWAYS compare against baseline AND previous best when evaluating
- ALWAYS update iteration_log.json after every sub-command
- NEVER delete or modify completed iteration entries (append-only for completed)
- ALWAYS use /code-debug for actual code changes (don't modify code directly)
- ALWAYS use /evaluate for detailed analysis when available
- ALWAYS persist iteration context to `.claude/iterations/iter{N}/context.json`, use symlink for `.claude/current_iteration.json`
- ALWAYS output recommended next-step command after eval decision
- NEVER write to PROJECT_STATE.json — that is orchestrator's responsibility
- git_commit MUST be non-null after `code` completes; if missing, stay in "coding" status
- ALWAYS run lesson dedup guard during `plan` to warn about repeated failure patterns
- Core training/evaluation logic MUST stay in files listed in CLAUDE.md `## Entry Scripts`. Auxiliary scripts (ablation runners, submission packagers) may be created in `scripts/` as needed, but must not duplicate core logic.
- `run` MUST use `run_in_background: true` for training execution; parse stdout for metrics after completion
- `run` MUST handle training failures (OOM, NaN, crash) gracefully — report error, keep status="training"
- `ablate` MUST verify parent iteration exists and is completed before starting
- `ablate` MUST skip sub-iterations that already exist with status="completed" (idempotent)
- `ablate` MUST only use component overrides from the `--components` parameter or iteration_log.json history
</constraints>
