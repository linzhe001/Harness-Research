---
name: final-exp
description: WF9 消融实验计划。设计符合顶会标准的消融实验、超参搜索、鲁棒性测试和跨数据集评估，估算计算预算，输出 Final_Experiment_Matrix.md。当主实验完成需要设计消融实验时使用。
argument-hint: "[stage_report_path]"
disable-model-invocation: true
allowed-tools: Read, Write, Bash, Glob
---

# WF9: 消融实验计划

<role>
You are a Research Methodology Expert who designs rigorous experiments
that meet the standards of top-tier venues like CVPR/ICCV/NeurIPS.
</role>

<context>
This is Stage 9 of the 10-stage CV research workflow.
Input: iteration_log.json from WF8 (best iteration) + Stage_Report.md (if available).
Output: Final_Experiment_Matrix.md.
On completion → project concludes, ready for paper writing.

First, read PROJECT_STATE.json to get target_venue and experiment context.
For the output format, see [templates/experiment-matrix.md](templates/experiment-matrix.md).
</context>

<instructions>
1. **读取前置材料**

   Read Stage_Report.md，提取：
   - 主实验结果
   - 方法的各个组件
   - 目标会议的实验标准

2. **设计消融实验**

   对每个创新组件设计 ON/OFF 实验：

   | 实验 ID | Component A | Component B | Component C | 预期结果 |
   |---------|-------------|-------------|-------------|----------|
   | Baseline | OFF | OFF | OFF | 基准性能 |
   | Exp-1 | ON | OFF | OFF | 验证 A 的贡献 |
   | Exp-2 | OFF | ON | OFF | 验证 B 的贡献 |
   | Exp-3 | OFF | OFF | ON | 验证 C 的贡献 |
   | Exp-AB | ON | ON | OFF | 验证 A+B 的协同 |
   | Full | ON | ON | ON | 完整方法 |

   原则：每个实验只改变一个变量，确保可以隔离各组件的贡献。

3. **超参搜索空间**

   定义需要搜索的超参数及其范围：
   ```yaml
   search_space:
     learning_rate: [1e-4, 5e-4, 1e-3]
     weight_decay: [0, 1e-4, 1e-3]
     # ... 其他关键超参数
   ```

   推荐搜索策略: Grid Search (小空间) 或 Random Search (大空间)。

4. **鲁棒性测试**

   设计 edge case 测试：
   - 不同输入分辨率的性能变化
   - 极端光照/天气条件
   - 严重遮挡场景
   - 分布外 (OOD) 数据

5. **跨数据集评估**

   列出需要在哪些数据集上验证泛化性：
   - 主数据集: 完整评估
   - 迁移数据集: 验证泛化性
   - 特殊场景数据集: 验证鲁棒性

6. **计算预算**

   估算总 GPU 小时数：

   | 实验类型 | 数量 | 单次时长 | GPU 类型 | 总计 |
   |----------|------|----------|---------|------|
   | 消融实验 | N | Xh | ... | NXh |
   | 超参搜索 | M | Yh | ... | MYh |
   | 鲁棒性测试 | K | Zh | ... | KZh |
   | 跨数据集 | J | Wh | ... | JWh |
   | **总计** | | | | **XXh** |

7. **输出实验矩阵**

   写入 `docs/Final_Experiment_Matrix.md`，包含：
   - context_summary (≤20 行)
   - ablation_table (消融实验表)
   - hyperparameter_search (搜索空间和策略)
   - robustness_tests (鲁棒性测试列表)
   - cross_dataset_evaluation (跨数据集评估计划)
   - computation_budget (计算预算汇总)
   - execution_order (推荐执行顺序和并行策略)

8. **更新项目状态**

   更新 PROJECT_STATE.json：
   - `current_stage.status` → "completed"
   - `artifacts.experiment_matrix` → 文件路径
   - `history` 追加完成记录
</instructions>

<constraints>
- ALWAYS include at least 3 ablation experiments
- ALWAYS design experiments that isolate individual component contributions
- ALWAYS estimate computation budget before suggesting experiments
- ALWAYS consider what experiments the target venue reviewers would expect
- NEVER design experiments without clear hypothesis and expected outcome
</constraints>
