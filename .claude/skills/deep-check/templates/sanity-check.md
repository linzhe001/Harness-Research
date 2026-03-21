# Sanity Check Log 模板

## context_summary 标准格式

```markdown
<context_summary>
- **项目:** {project_name}
- **当前阶段:** WF3 - 二次论证
- **前置输入:** Technical_Spec.md
- **本次产出:** Sanity_Check_Log.md
- **关键结论:**
  1. {conclusion_1}
  2. {conclusion_2}
- **待解决问题:** {open_issues}
- **下一步:** WF4 data-prep (如果 GO) / WF2 rollback (如果 NO-GO)
</context_summary>
```

## 必须包含的 Sections

### 1. failure_case_search_results
- 搜索到的负面结果
- 失败案例及原因

### 2. theoretical_analysis
对每个关键假设的质疑:
- 假设 1: [描述] → 反例? 失效条件?
- 假设 2: [描述] → 数学证明? 实验验证?

### 3. performance_estimation

| 场景 | 预估性能 | 依据 |
|------|---------|------|
| 上界 (乐观) | | |
| 期望值 (最可能) | | |
| 下界 (悲观) | | |

### 4. risk_matrix

| 风险项 | 概率 (1-5) | 影响 (1-5) | 风险值 | 缓解措施 |
|--------|-----------|-----------|--------|----------|
| 训练不收敛 | | | | |
| 性能不达预期 | | | | |
| 计算资源不足 | | | | |

### 5. go_nogo_recommendation

**决策: GO / CONDITIONAL GO / NO-GO**

**理由:** ...

**条件 (如果 CONDITIONAL GO):**
1. ...
2. ...

**建议的下一步:** ...
