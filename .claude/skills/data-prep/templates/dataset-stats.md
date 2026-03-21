# Dataset Stats 模板

## context_summary 标准格式

```markdown
<context_summary>
- **项目:** {project_name}
- **当前阶段:** WF4 - 数据工程
- **前置输入:** Sanity_Check_Log.md (GO)
- **本次产出:** Dataset_Stats.md, Data_Pipeline_Script.py, subset_indices.json
- **关键结论:**
  1. {conclusion_1}
  2. {conclusion_2}
- **待解决问题:** {open_issues}
- **下一步:** WF5 baseline-repro
</context_summary>
```

## 必须包含的 Sections

### 1. 全集统计

```markdown
## 原始数据集: {dataset_name}

- 图像总数: {total_images}
- 类别数: {num_classes}
- 标注总数: {total_annotations}

### 类别分布
| 类别 | 样本数 | 占比 |
|------|--------|------|

### BBox 尺寸分布
| 尺寸 | 数量 | 占比 |
|------|------|------|
| Small (<32²) | | |
| Medium (32²-96²) | | |
| Large (>96²) | | |
```

### 2. 子集统计

```markdown
## 子集 (ratio={subset_ratio})

- 图像数: {subset_images}
- 标注数: {subset_annotations}
```

### 3. 分布对比

| 指标 | 全集 | 子集 | 偏差 |
|------|------|------|------|
| 类别分布 | | | <5% |
| 尺寸分布 | | | <5% |

### 4. 验证结果

- [ ] 子集分布偏差 < 5%
- [ ] 随机种子已固定
- [ ] subset_indices.json 已保存
