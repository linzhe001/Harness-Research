# Feasibility Report 模板

## context_summary 标准格式

每个输出文件开头必须包含 context_summary 块，不超过 20 行：

```markdown
<context_summary>
- **项目:** {project_name}
- **当前阶段:** WF1 - 灵感调研
- **前置输入:** 用户 Idea 描述
- **本次产出:** Feasibility_Report.md
- **关键结论:**
  1. {conclusion_1}
  2. {conclusion_2}
- **待解决问题:** {open_issues}
- **下一步:** WF2 refine-arch
</context_summary>
```

## 完整模板

```markdown
# Feasibility Report: {project_name}

<context_summary>
- **Idea 概述:** [一句话描述]
- **检索时间范围:** {start_date} 至 {end_date}
- **检索关键词:** {keywords}
- **相关论文数量:** {paper_count}
- **最相关竞品:** {top_competitor}
</context_summary>

## 1. 可行性评分

**综合评分: {total_score}/10**

| 维度 | 分数 | 权重 | 加权分 | 说明 |
|------|------|------|--------|------|
| 新颖性 (Novelty) | /10 | 0.30 | | |
| 技术可行性 (Feasibility) | /10 | 0.25 | | |
| 影响力 (Impact) | /10 | 0.25 | | |
| 实现难度 (Difficulty) | /10 | 0.10 | | |
| 资源需求 (Resource) | /10 | 0.10 | | |

## 2. Gap 矩阵

| 维度 | 当前 SOTA | 本 Idea 改进点 | 预估提升 | 置信度 |
|------|----------|---------------|----------|--------|
| 精度 | | | | |
| 速度 | | | | |
| 鲁棒性 | | | | |
| 泛化性 | | | | |

## 3. Top 5 竞品分析

### 3.1 {competitor_name}
- **论文:** {title}, {venue} {year}
- **核心方法:** ...
- **与本 Idea 差异:** ...
- **已知局限:** ...

## 4. 前置依赖清单

- [ ] 必须复现的 Baseline: ...
- [ ] 必须准备的数据集: ...
- [ ] 必须阅读的论文: ...
- [ ] 必须掌握的技术: ...

## 5. 风险评估

| 风险项 | 概率 | 影响 | 缓解措施 |
|--------|------|------|----------|

## 6. 建议

**决策: PROCEED / PIVOT / ABANDON**

**理由:** ...

**下一步:** ...
```
