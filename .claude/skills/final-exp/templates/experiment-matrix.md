# Final Experiment Matrix 模板

## context_summary 标准格式

```markdown
<context_summary>
- **项目:** {project_name}
- **当前阶段:** WF8 - 消融实验计划
- **前置输入:** Stage_Report.md (CONTINUE)
- **本次产出:** Final_Experiment_Matrix.md
- **关键结论:**
  1. {conclusion_1}
  2. {conclusion_2}
- **待解决问题:** {open_issues}
- **下一步:** 执行实验 → 论文撰写
</context_summary>
```

## 必须包含的 Sections

### 1. ablation_table

```markdown
## 消融实验

| 实验 ID | Component A | Component B | Component C | 预期结果 |
|---------|-------------|-------------|-------------|----------|
| Baseline | OFF | OFF | OFF | 基准性能 |
| Exp-1 | ON | OFF | OFF | 验证 A 的贡献 |
| Exp-2 | OFF | ON | OFF | 验证 B 的贡献 |
| Exp-3 | OFF | OFF | ON | 验证 C 的贡献 |
| Exp-AB | ON | ON | OFF | 验证 A+B 的协同 |
| Full | ON | ON | ON | 完整方法 |

原则: 每个实验只改变一个变量
```

### 2. hyperparameter_search

```yaml
search_space:
  learning_rate: [1e-4, 5e-4, 1e-3]
  weight_decay: [0, 1e-4, 1e-3]
  batch_size: [8, 16, 32]
  # 其他关键超参数

search_strategy: grid  # or random
total_trials: N
```

### 3. robustness_tests

```markdown
## 鲁棒性测试

| 测试场景 | 描述 | 预期行为 |
|---------|------|---------|
| 分辨率变化 | 输入 [640, 800, 1024] | 性能平稳下降 |
| 极端光照 | 过曝/欠曝图像 | 检测仍有效 |
| 严重遮挡 | >50% 遮挡 | 部分检出 |
| OOD 数据 | 训练集外类别 | 合理拒绝 |
```

### 4. cross_dataset_evaluation

```markdown
## 跨数据集评估

| 数据集 | 用途 | 预期指标 |
|--------|------|---------|
| COCO | 主数据集，完整评估 | mAP ≥ X |
| VOC | 迁移验证 | mAP ≥ Y |
| Objects365 | 泛化性验证 | mAP ≥ Z |
```

### 5. computation_budget

```markdown
## 计算预算

| 实验类型 | 数量 | 单次时长 | GPU 类型 | 总计 |
|----------|------|----------|---------|------|
| 消融实验 | N | Xh | V100 | NXh |
| 超参搜索 | M | Yh | V100 | MYh |
| 鲁棒性测试 | K | Zh | V100 | KZh |
| 跨数据集 | J | Wh | V100 | JWh |
| **总计** | | | | **XXh** |

预计总成本: $YYY (基于云 GPU 价格)
```

### 6. execution_order

```markdown
## 执行顺序

1. **Phase 1 (并行):** 消融实验 Exp-1, Exp-2, Exp-3
2. **Phase 2 (串行):** 根据 Phase 1 结果选择最佳组合
3. **Phase 3 (并行):** 超参搜索
4. **Phase 4 (串行):** 最终模型全量训练
5. **Phase 5 (并行):** 鲁棒性测试 + 跨数据集评估
```
