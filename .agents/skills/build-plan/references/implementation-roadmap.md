# Implementation Roadmap Template

## context_summary Standard Format

```markdown
<context_summary>
- **Project:** {project_name}
- **Current Stage:** WF5 - Implementation Planning
- **Prior Inputs:** Technical_Spec.md, Dataset_Stats.md
- **Deliverables:** Implementation_Roadmap.md
- **Key Conclusions:**
  1. {conclusion_1}
  2. {conclusion_2}
- **Open Issues:** {open_issues}
- **Next Step:** WF7 code-expert
</context_summary>
```

## Required Sections

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

For each new file, provide:
- Class/function signatures (with Type Hints)
- Core logic pseudocode
- Input/output examples (with tensor shapes)
- Dependency relationships

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
- Entry conditions: ...
- Execution steps: ...
- Validation checkpoints: ...
- Failure handling: ...

#### Stage 2: Module Integration
- Entry conditions: ...
- Execution steps: ...
- Validation checkpoints: ...
- Failure handling: ...

#### Stage 3: Full Training
- Entry conditions: ...
- Execution steps: ...
- Validation checkpoints: ...
- Failure handling: ...

### 5. validation_checkpoints

| Stage | Check Item | Pass Criteria |
|------|--------|----------|
| Smoke Test | Training can start | No errors |
| Module Integration | Gradient flow is normal | grad_norm > 0 |
| Full Training | Convergence | val_loss decreasing |
