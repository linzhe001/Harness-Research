# Stage Report 模板

## context_summary 标准格式

```markdown
<context_summary>
- **项目:** {project_name}
- **当前阶段:** WF7 - 结果分析
- **前置输入:** 训练日志, metrics.json
- **本次产出:** Stage_Report.md
- **关键结论:**
  1. {conclusion_1}
  2. {conclusion_2}
- **待解决问题:** {open_issues}
- **下一步:** WF9 final-exp (CONTINUE) / /iterate plan (DEBUG) / WF2 (PIVOT)
</context_summary>
```

## 必须包含的 Sections

### 1. training_analysis

```markdown
## 训练分析

### Loss 曲线
| Epoch | Train Loss | Val Loss | mAP |
|-------|------------|----------|-----|
| 1 | | | |
| ... | | | |

### Learning Rate
- 初始 LR:
- 最终 LR:
- Warmup epochs:

### Gradient Norm
- 平均:
- 最大:
- 是否稳定:
```

### 2. performance_comparison

```markdown
## 性能对比

| 指标 | Baseline | 本方法 | 差异 | 显著性 |
|------|----------|--------|------|--------|
| mAP | | | | |
| mAP50 | | | | |
| FPS | | | | |
| 参数量 | | | | |
```

### 3. issue_diagnosis

```markdown
## 问题诊断

### 发现的问题
1. [问题描述] → [严重程度] → [建议措施]

### 检查清单
- [ ] Loss 收敛?
- [ ] 无过拟合?
- [ ] Gradient norm 稳定?
- [ ] 无 NaN/Inf?
```

### 4. scaling_prediction

```markdown
## 全量训练预测

基于 scaling law:
- 当前 (10% 数据): {current_metric}
- 预计 (100% 数据): {predicted_metric}
- 置信区间: [{lower}, {upper}]
- 参考: [类似工作的 10%→100% 提升幅度]
```

### 5. recommendation

```markdown
## 建议

**决策: CONTINUE / DEBUG / PIVOT / ABORT**

**理由:**
1. ...
2. ...

**下一步:**
- ...
```

## 决策矩阵

| 情况 | 决策 | 下一步 |
|------|------|--------|
| 性能达标 + 训练稳定 | CONTINUE | WF8 |
| 存在可修复 bug | DEBUG | WF6 (带错误信息) |
| 性能差距 >5% | PIVOT | WF2 (备选方案) |
| 理论失败 / 资源不足 | ABORT | 记录经验终止 |
