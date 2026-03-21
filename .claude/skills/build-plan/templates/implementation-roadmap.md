# Implementation Roadmap 模板

## context_summary 标准格式

```markdown
<context_summary>
- **项目:** {project_name}
- **当前阶段:** WF5 - 代码执行计划
- **前置输入:** Technical_Spec.md, Dataset_Stats.md
- **本次产出:** Implementation_Roadmap.md
- **关键结论:**
  1. {conclusion_1}
  2. {conclusion_2}
- **待解决问题:** {open_issues}
- **下一步:** WF7 code-expert
</context_summary>
```

## 必须包含的 Sections

### 1. file_tree

```
project_root/
├── configs/
│   ├── base.yaml
│   └── experiments/
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── backbone.py
│   │   ├── neck.py
│   │   └── head.py
│   ├── data/
│   │   ├── dataset.py
│   │   └── transforms.py
│   ├── losses/
│   └── utils/
│       ├── registry.py
│       └── config.py
├── scripts/
│   ├── train.py
│   └── eval.py
└── tests/
```

### 2. module_pseudocode

对每个新增文件提供:
- 类/函数签名 (含 Type Hints)
- 核心逻辑伪代码
- 输入输出示例 (含 tensor shapes)
- 依赖关系说明

### 3. config_schema

```yaml
experiment:
  name: str
  seed: int

data:
  dataset_name: str
  batch_size: int

model:
  backbone: dict
  neck: dict
  head: dict

train:
  max_epochs: int
  learning_rate: float
```

### 4. training_pipeline

#### Stage 1: Smoke Test
- 输入条件: ...
- 执行步骤: ...
- 验证检查点: ...
- 失败处理: ...

#### Stage 2: Module Integration
- 输入条件: ...
- 执行步骤: ...
- 验证检查点: ...
- 失败处理: ...

#### Stage 3: Full Training
- 输入条件: ...
- 执行步骤: ...
- 验证检查点: ...
- 失败处理: ...

### 5. validation_checkpoints

| 阶段 | 检查项 | 通过条件 |
|------|--------|----------|
| Smoke Test | 训练可以启动 | 无报错 |
| Module Integration | 梯度流动正常 | grad_norm > 0 |
| Full Training | 收敛 | val_loss 下降 |
