---
name: validate-run
description: WF7.5 训练链路验证。在进入 WF8 迭代前，先 Codex 审查代码与 baseline 等价性，再执行 100-step smoke test 验证全链路可用。
argument-hint: "[config_path]"
allowed-tools: Read, Write, Bash, Glob, Grep
---

# WF7.5: 训练链路验证（代码审查 + Smoke Test）

<role>
You are a DevOps/ML Engineer and Code Reviewer who validates that the codebase
is correct (vs baseline equivalence) and the training pipeline works end-to-end,
before committing to expensive iteration cycles.
</role>

<context>
This is a gate between WF7 (code generation) and WF8 (iteration).
WF7 writes the full codebase, often by adapting baseline code. Two types of bugs
can slip through:
- **Semantic bugs**: data normalization mismatch, loss sign errors, metric
  computation differences vs baseline — code runs fine but produces wrong results.
- **Infrastructure bugs**: import errors, shape mismatches, OOM — code crashes.

This skill catches both: Codex code review (semantic) + smoke test (infrastructure).
Failure here means issues that must be fixed before entering WF8.

Input: Working codebase from WF7 + config file + baseline code (from baselines/).
Output: Code review findings + smoke test pass/fail report.
On PASS → WF8 (iterate). On FAIL → fix issues via /code-debug.
</context>

<instructions>
1. **确定配置与定位文件**

   从 $ARGUMENTS 获取 config_path，或从 CLAUDE.md 推断默认配置。
   读取配置文件确认训练参数。

   定位三组审查材料：

   **① WF7 新代码**（被审查对象）：
   - 从 `project_map.json` 的 `src/` 节点读取所有 stable 模块路径
   - 按职责分类读取：模型定义（forward pass）、数据加载（transforms, dataset）、
     loss 函数、评估指标计算（metrics）、预处理脚本
   - 从 CLAUDE.md `## Entry Scripts` 读取训练脚本 `{TRAIN_SCRIPT}` 和评估脚本 `{EVAL_SCRIPT}`

   **② Baseline 参考代码**（等价性基准）：
   - 从 `project_map.json` 的 `baselines/` 节点读取每个 baseline 的 `entry_point`
   - 从 baseline entry_point 出发，沿 import 链定位其对应模块：
     模型定义、数据加载、loss 计算、评估指标、训练循环
   - 优先选取 `status: verified` 的 baseline 作为参照

   **③ 设计文档**（实现意图参照）：
   - `docs/Technical_Spec.md`（WF2 的架构设计，说明哪些部分应与 baseline 等价、哪些是新增）

2. **Codex 代码审查**（始终尝试）

   WF7.5 是代码进入迭代前的**唯一审查机会**，始终尝试 Codex 审查。

   如果 Codex MCP 可用（`mcp__codex__codex` 工具存在）：

   a. **收集审查材料**：读取步骤 1 定位的三组文件内容。
      对于每个审查维度（数据、模型、loss、eval），将新代码和 baseline 对应模块
      **成对组织**，方便 Codex 逐对比较。

   b. **提交审查请求**，调用 `mcp__codex__codex`，prompt 结构：
      ```
      ## 审查任务
      检查新代码与 baseline 的等价性，逐项回答审查清单。

      ## 新代码（WF7 实现）
      ### 数据加载: src/data/...
      {文件内容}
      ### 模型: src/models/...
      {文件内容}
      ### Loss: src/losses/...
      {文件内容}
      ### 评估: scripts/{EVAL_SCRIPT} + src/utils/metrics.py
      {文件内容}
      ### 训练循环: scripts/{TRAIN_SCRIPT}
      {文件内容}

      ## Baseline 参考实现
      ### 数据加载: baselines/{name}/...
      {文件内容}
      ### 模型: baselines/{name}/...
      {文件内容}
      ### Loss: baselines/{name}/...
      {文件内容}
      ### 评估: baselines/{name}/...
      {文件内容}

      ## 设计意图
      {Technical_Spec.md 关键段落}

      ## 审查清单（逐项回答）
      {见下方}
      ```

   c. **审查清单**（Codex 需要逐项回答）：

      **数据管道等价性**：
      - 图像归一化方式是否一致（[0,1] vs [0,255]、RGB vs BGR 通道顺序）
      - 数据增强（或无增强）是否与 baseline 一致
      - 相机参数解析（内参、外参、坐标系约定）是否等价
      - Train/test split 逻辑是否一致

      **模型/渲染等价性**：
      - 模型初始化策略是否与 baseline 一致（随机初始化、点云初始化等）
      - Forward pass 的核心计算逻辑是否等价（保留的 baseline 部分）
      - 新增模块（如去雾/增强）是否正确集成，不破坏梯度流

      **Loss 计算等价性**：
      - 与 baseline 共享的 loss 项（如 L1、SSIM）计算方式是否一致
      - Loss 权重默认值是否合理
      - 新增 loss 项的梯度是否能正确回传

      **评估指标等价性**（关键，直接影响竞赛排名）：
      - PSNR 计算方式是否与 baseline/竞赛评估一致（值域、clamp、边界处理）
      - SSIM 的窗口大小、data_range 参数是否一致
      - LPIPS 的网络选择（alex vs vgg）是否与竞赛一致
      - 输出图像的后处理（clamp、dtype 转换、保存格式）是否与 baseline 一致

      **常见 ML Bug 检查**：
      - 是否有 tensor detach 导致的梯度流断裂
      - 是否有 in-place 操作破坏 autograd 图
      - 是否有 CPU/GPU device 混用
      - 学习率 scheduler 的 step 调用时机是否正确

   d. **解析审查结果**，分类为：
      - `critical`: 必定导致错误结果（如指标计算不一致、归一化错误）
      - `warning`: 可能导致性能差异（如初始化策略不同、loss 权重偏差）
      - `info`: 风格差异，不影响正确性

   e. 如果有 critical/warning 级别的 concern：
      - WebSearch 验证相关问题（如 SSIM 参数的正确用法）
      - `mcp__codex__codex-reply` 回复验证结果，确认或排除 concern
      - 最多 3 轮迭代

   f. 记录 `codex_review: "used"` + 审查结果

   **如果 Codex MCP 不可用**：
   Claude 自行执行简化版审查（只检查评估指标等价性和数据归一化），
   记录 `codex_review: "unavailable"`。

3. **执行 100-step 训练**

   从 CLAUDE.md `## Entry Scripts` 读取 `{TRAIN_SCRIPT}`：
   ```bash
   python {TRAIN_SCRIPT} --config {config_path} --max_steps 100 --exp_name smoke_test
   ```
   记录：
   - 是否成功启动（import 错误？）
   - 是否成功完成 100 步（crash？OOM？NaN？）
   - Loss 是否在合理范围（非 NaN, 非 Inf, 有下降趋势）
   - GPU 内存使用量

4. **验证 Checkpoint 保存**

   检查 smoke test 是否生成了 checkpoint 文件：
   - 文件是否存在
   - 是否可加载（`torch.load` 不报错）
   - 是否包含必需字段（model, optimizer, step, git_commit）

5. **验证评估流程**

   从 CLAUDE.md `## Entry Scripts` 读取 `{EVAL_SCRIPT}`：
   ```bash
   python {EVAL_SCRIPT} --checkpoint {smoke_test_checkpoint} --split val
   ```
   检查：
   - 评估是否完成
   - 指标是否在合理范围（PSNR > 5 dB 即可，smoke test 不要求性能）
   - 输出图像是否生成

6. **验证 wandb 连接**（如果启用）

   检查 smoke test 训练日志中 wandb 是否成功初始化。

7. **验证 git_snapshot**

   检查 smoke test 训练日志中 git_snapshot 是否成功执行。

8. **输出报告**

   向用户报告：

   **代码审查结果**：
   - Codex 审查状态（used / unavailable）
   - Critical 级别发现（如有，列出具体差异和建议修复）
   - Warning 级别发现（列出潜在风险）
   - Info 级别发现（仅供参考）

   **Smoke Test 结果**：
   - ✓/✗ 训练 100 步
   - ✓/✗ Checkpoint 保存/加载
   - ✓/✗ 评估流程
   - ✓/✗ wandb 连接
   - ✓/✗ git_snapshot
   - GPU 内存使用量

   **最终判定**：
   - **PASS**: Smoke test 全通过 且 代码审查无 critical（warning 记录但不阻塞）
   - **REVIEW**: Smoke test 通过 但 代码审查有 critical — 列出需确认的问题，用户决定是否继续
   - **FAIL**: Smoke test 有失败项 — 必须修复

9. **清理**

   删除 smoke test 生成的临时文件（checkpoint, 日志），避免污染实验目录。

10. **更新项目状态**

   如果 PASS 或 REVIEW（用户确认继续）：
   - 更新 PROJECT_STATE.json: current_stage → WF7.5 completed
   - history 追加 validate_run 通过记录（含代码审查摘要）
   如果 FAIL 或 REVIEW（用户要求修复）：
   - 列出失败项 + critical 审查发现
   - 建议 `/code-debug` 修复
</instructions>

<constraints>
- ALWAYS attempt Codex code review before smoke test (this is the only review gate before WF8)
- ALWAYS run the full validation chain (review → train → checkpoint → eval → wandb → git)
- ALWAYS clean up smoke test artifacts after validation
- NEVER skip any validation step even if previous steps passed
- ALWAYS report specific error messages for any failed step
- Code review critical findings produce REVIEW status, not automatic FAIL — user decides
- ALWAYS check evaluation metric equivalence vs baseline (PSNR/SSIM/LPIPS computation details)
- If Codex unavailable, ALWAYS perform simplified self-review of metric computation and data normalization
</constraints>
