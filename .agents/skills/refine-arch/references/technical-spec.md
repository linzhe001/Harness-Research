# Technical Spec 模板

## context_summary 标准格式

```markdown
<context_summary>
- **项目:** {project_name}
- **当前阶段:** WF2 - 架构精修
- **前置输入:** Feasibility_Report.md
- **本次产出:** Technical_Spec.md
- **关键结论:**
  1. {conclusion_1}
  2. {conclusion_2}
- **待解决问题:** {open_issues}
- **下一步:** WF3 deep-check
</context_summary>
```

## 必须包含的 Sections

### 1. architecture_overview
- 包含 ASCII 架构图
- 数据流说明

### 2. module_modification_plan

| 文件 | 操作 | 说明 |
|------|------|------|
| src/models/new_module.py | 新增 | 核心创新模块 |
| configs/experiment.yaml | 新增 | 实验配置 |

### 3. mvp_definition
- 范围界定 (10% 数据，最简实现)
- 验证指标
- 预计工作量

### 4. alternative_plans

| 决策点 | 方案 A | 方案 B | 方案 C |
|--------|--------|--------|--------|
| {决策} | 简单/保守 | 推荐/平衡 | 激进/最优 |

每个方案包含:
- 优点
- 缺点
- 适用场景
- Rollback 策略

### 5. integration_points
- 与现有代码的集成点
- 需要修改的接口

### 6. resource_estimation

| 阶段 | GPU 类型 | 显存需求 | 预估时长 | 备注 |
|------|---------|---------|---------|------|
| MVP (10% 数据) | | | | |
| 完整训练 | | | | |
| 消融实验 | | | | |

### 7. risk_mitigation
- 每个主要变更的 rollback plan
- 失败时的备选方案
